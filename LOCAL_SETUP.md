# Local Development Setup

End-to-end guide for running the full Events Platform stack locally — backend API, frontend, PostgreSQL, and MinIO (S3-compatible storage).

---

## Prerequisites

| Tool | Version | Install |
|---|---|---|
| Docker + Docker Compose | latest | [docker.com](https://www.docker.com/get-started) |
| Python | 3.11+ | [python.org](https://www.python.org) or `brew install python` |
| Node.js | 18+ | [nodejs.org](https://nodejs.org) or `brew install node` |
| psql CLI | any | comes with PostgreSQL, or `brew install libpq` on macOS |

---

## 1. Clone and configure environment variables

```bash
git clone <repo-url>
cd events_platform
```

Create `backend/.env` by copying the example below. The values here work out of the box for local development.

```env
# Database
DATABASE_URL=postgresql://ennova_test:ennova123@localhost:5432/ennova_db

# Auth
SECRET_KEY=local-dev-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# MinIO (local S3-compatible storage)
S3_ENDPOINT_URL=http://localhost:9000
S3_BUCKET_NAME=ennova-events-platform
S3_ACCESS_KEY_ID=minioadmin
S3_SECRET_ACCESS_KEY=minioadmin
R2_API_TOKEN_VALUE=dummy
ACCOUNT_ID=dummy
R2_PUBLIC_DOMAIN=http://localhost:9000/ennova-events-platform

# Email (disabled locally — set to true and add a Resend key to test emails)
RESEND_API_KEY=dummy
RESEND_FROM_EMAIL=no-reply@localhost
RESEND_FROM_NAME=Ennova Events
EMAIL_NOTIFICATIONS_ENABLED=false

# Stripe — use Stripe test keys (no local setup needed, works against Stripe servers)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
FRONTEND_URL=http://localhost:5173

# OpenAI (only needed for AI chat feature)
OPENAI_API_KEY=dummy

# Qdrant (only needed for AI chat feature)
QDRANT_URL=http://localhost
QDRANT_API_KEY=dummy
QDRANT_COLLECTION_NAME=ennova_documents
QDRANT_PORT=6333
```

Create `frontend/.env`:

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_STRIPE_PUBLISHABLE_KEY=pk_test_...
```

---

## 2. Start backing services (PostgreSQL + MinIO)

```bash
cd backend
docker compose up -d
```

This starts:

| Service | URL | Credentials |
|---|---|---|
| PostgreSQL | `localhost:5432` | `ennova_test` / `ennova123` |
| MinIO S3 API | `http://localhost:9000` | `minioadmin` / `minioadmin` |
| MinIO console | `http://localhost:9001` | `minioadmin` / `minioadmin` |

The `minio-init` container automatically creates the `ennova-events-platform` bucket and sets it to public-read on first start.

---

## 3. Set up the backend

```bash
cd backend

# Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start the API server
uvicorn main:app --reload --port 8000
```

The API will be available at **http://localhost:8000**
API docs (Swagger): **http://localhost:8000/docs**

---

## 4. Load seed data

In a separate terminal, with the virtual environment active:

```bash
cd backend
psql -U ennova_test -d ennova_db -f seed.sql
```

### Test accounts (password: `password123`)

| Email | Role(s) | Notes |
|---|---|---|
| super_admin@dev.com | super_admin + organiser | Full admin access |
| organiser@dev.com | organiser | Can create and manage events |
| alice@dev.com | attendee | Ennova member, CS 3rd Year |
| bob@dev.com | attendee | Business 2nd Year |
| carol@dev.com | attendee | Ennova member, Engineering 4th Year |
| dave@dev.com | attendee | Has a pending registration |
| eve@dev.com | attendee | Mathematics MSc |

### Seeded events

| ID | Name | Status |
|---|---|---|
| 1 | Ennova Tech Conference 2026 | Published (+30 days) |
| 2 | 48-Hour AI Hackathon | Published (+60 days, teams) |
| 3 | Winter Networking Night | Completed (−30 days) |
| 4 | Spring Career Fair 2026 | Draft (+90 days) |

---

## 5. Set up the frontend

```bash
cd frontend

# Install dependencies
npm install

# Start the dev server
npm run dev
```

The app will be available at **http://localhost:5173**

---

## 6. Stripe webhooks (for local payment testing)

Stripe webhooks won't reach `localhost` unless you forward them. Install the Stripe CLI:

```bash
brew install stripe/stripe-cli/stripe   # macOS
# or: https://stripe.com/docs/stripe-cli
```

Log in and forward events to the local backend:

```bash
stripe login
stripe listen --forward-to http://localhost:8000/webhooks/stripe
```

Copy the webhook signing secret printed by `stripe listen` and update `backend/.env`:

```env
STRIPE_WEBHOOK_SECRET=whsec_<secret from stripe listen output>
```

---

## 7. Resetting data

To wipe all seed data and reload:

```bash
# Uncomment the TRUNCATE block at the top of seed.sql, then:
psql -U ennova_test -d ennova_db -f backend/seed.sql
```

To reset the entire schema:

```bash
cd backend
source venv/bin/activate
alembic downgrade base
alembic upgrade head
psql -U ennova_test -d ennova_db -f seed.sql
```

---

## 8. Stopping services

```bash
cd backend
docker compose down          # stop containers, keep data volumes
docker compose down -v       # stop containers AND delete all data
```

---

## Connection reference

| Service | URL / connection string |
|---|---|
| PostgreSQL | `postgresql://ennova_test:ennova123@localhost:5432/ennova_db` |
| Backend API | `http://localhost:8000` |
| API docs | `http://localhost:8000/docs` |
| Frontend | `http://localhost:5173` |
| MinIO S3 API | `http://localhost:9000` |
| MinIO console | `http://localhost:9001` |
