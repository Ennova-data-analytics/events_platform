#!/usr/bin/env bash
# Runs ON THE SERVER, piped over SSH by .github/workflows/deploy.yml:
#   ssh prod "bash -s -- <app_dir> <commit_sha>" < deploy/remote-deploy.sh
#
# Expects the workflow to have uploaded the new frontend build to
# <app_dir>/frontend/dist-incoming/ beforehand. Every step must succeed; the
# script stops at the first failure and the workflow run goes red. The last
# line it prints is "==> Deployed <sha>", which the workflow checks for.
#
# Everything lives in main(), called on the last line with stdin from
# /dev/null. bash reads a piped script as it goes, so any command that reads
# stdin (docker compose run/exec do) would otherwise swallow the rest of the
# script, and bash would then exit 0 having skipped every remaining step.
set -euo pipefail

BACKEND_IMAGE="events_management_platform-backend"

log() { echo "==> $*"; }
fail() { echo "::error::$*"; exit 1; }

main() {
  local APP_DIR="$1"
  local SHA="$2"

  cd "$APP_DIR"

  log "Updating code to $SHA"
  # Refuse to deploy over edits made directly on the server (for example in
  # the Hostinger Docker Manager editor) rather than silently discarding them.
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

  docker network inspect ennova-shared >/dev/null 2>&1 || {
    log "Creating the ennova-shared network (used to reach Finnova)"
    docker network create ennova-shared >/dev/null
  }

  # nginx refuses to start if a certificate it names is missing, which would
  # take the whole site down when "up" recreates it. Check before touching it.
  log "Checking TLS certificates named in nginx.conf"
  local cert
  for cert in $(grep -oE 'ssl_certificate +/etc/letsencrypt/[^;]+' nginx/nginx.conf | awk '{print $2}' | sort -u); do
    docker compose run --rm -T --no-deps --entrypoint test certbot -f "$cert" \
      || fail "Certificate $cert does not exist. Issue it with certbot before deploying this nginx.conf."
  done

  log "Testing the nginx config before restarting nginx"
  docker compose run --rm -T --no-deps nginx nginx -t \
    || fail "nginx -t failed; the running nginx was left untouched."

  log "Running database migrations"
  docker compose run --rm -T --no-deps backend alembic upgrade head

  log "Starting containers"
  docker compose up -d --remove-orphans

  log "Waiting for the backend to answer"
  local i
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

  # nginx.conf is bind-mounted as a single file. git replaces the file rather
  # than editing it, so a running container keeps reading the old copy and a
  # reload changes nothing. When what nginx runs differs from the repo, recreate
  # nginx (a second or two; the config already passed nginx -t above).
  local running wanted
  running=$(docker compose exec -T nginx cat /etc/nginx/conf.d/default.conf | sha256sum)
  wanted=$(sha256sum < nginx/nginx.conf)
  if [ "$running" != "$wanted" ]; then
    log "nginx.conf changed: recreating nginx"
    docker compose up -d --force-recreate --no-deps nginx
    running=$(docker compose exec -T nginx cat /etc/nginx/conf.d/default.conf | sha256sum)
    [ "$running" = "$wanted" ] || fail "nginx is still running an old nginx.conf after recreating it."
  else
    log "Reloading nginx"
    docker compose exec -T nginx nginx -t
    docker compose exec -T nginx nginx -s reload
  fi

  docker image prune -f >/dev/null
  log "Deployed $SHA"
}

main "$@" </dev/null
