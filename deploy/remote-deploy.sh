#!/usr/bin/env bash
# Runs ON THE SERVER, piped over SSH by .github/workflows/deploy.yml:
#   ssh prod "bash -s -- <app_dir> <commit_sha>" < deploy/remote-deploy.sh
#
# Expects the workflow to have uploaded the new frontend build to
# <app_dir>/frontend/dist-incoming/ beforehand. Every step must succeed; the
# script stops at the first failure and the workflow run goes red.
set -euo pipefail

APP_DIR="$1"
SHA="$2"
BACKEND_IMAGE="events_management_platform-backend"

log() { echo "==> $*"; }
fail() { echo "::error::$*"; exit 1; }

cd "$APP_DIR"

log "Updating code to $SHA"
# Refuse to deploy over edits made directly on the server (for example in the
# Hostinger Docker Manager editor) rather than silently discarding them.
if ! git diff --quiet || ! git diff --cached --quiet; then
  git status --short
  fail "Tracked files were changed on the server. Commit them to the repo or revert them on the server, then re-run the deploy."
fi
# Fast-forward to exactly the commit that passed CI, not whatever the branch
# tip is by now (a newer push gets its own deploy run).
GIT_TERMINAL_PROMPT=0 git fetch --quiet
git merge --ff-only --quiet "$SHA" \
  || fail "Could not fast-forward to ${SHA:0:7}. Check that the server's branch tracks main and has no local commits."
[ "$(git rev-parse HEAD)" = "$SHA" ] \
  || fail "Server is at $(git rev-parse --short HEAD), expected ${SHA:0:7}."

log "Building backend image (the running site stays up meanwhile)"
# Keep the current image so a bad release can be rolled back by hand.
if docker image inspect "$BACKEND_IMAGE:latest" >/dev/null 2>&1; then
  docker tag "$BACKEND_IMAGE:latest" "$BACKEND_IMAGE:previous"
fi
docker compose build backend

log "Running database migrations"
docker compose run --rm --no-deps backend alembic upgrade head

log "Starting containers"
docker compose up -d --remove-orphans

log "Waiting for the backend to answer"
for i in $(seq 1 60); do
  if docker compose exec -T nginx wget -q -O /dev/null http://backend:8000/ 2>/dev/null; then
    log "Backend is up after ~$((i * 5))s"
    break
  fi
  if [ "$i" -eq 60 ]; then
    docker compose logs --tail 80 backend
    fail "Backend did not answer within 5 minutes. To roll back the backend: cd $APP_DIR && docker tag $BACKEND_IMAGE:previous $BACKEND_IMAGE:latest && docker compose up -d --no-build backend"
  fi
  sleep 5
done

log "Publishing the new frontend"
[ -f frontend/dist-incoming/index.html ] || fail "frontend/dist-incoming/index.html is missing; the frontend upload step did not run."
# nginx bind-mounts frontend/dist, so it is updated in place (a rename would
# leave nginx serving the old directory). --delay-updates puts the new files
# in place together at the end; old hashed assets are kept so visitors still
# on the previous page don't get 404s for its lazily loaded chunks.
mkdir -p frontend/dist
rsync -a --delay-updates frontend/dist-incoming/ frontend/dist/

log "Reloading nginx"
docker compose exec -T nginx nginx -t
docker compose exec -T nginx nginx -s reload

docker image prune -f >/dev/null
log "Deployed ${SHA:0:7}"
