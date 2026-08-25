# Recruitment Module — Implementation Spec

Target repo: `Ennova-data-analytics/events_platform` (branch off `phase_3`)
Companion repo (front door only): `alanfijal/ennova_website` (Next.js 14 + HeroUI + Sanity, Vercel)

## 0. Context & Decision

We are replacing a forms + Google Drive recruitment process with a native module.
**Decision: build the recruitment backend and UIs inside `events_platform`.** It already provides everything needed: FastAPI + SQLAlchemy + Alembic on PostgreSQL, JWT auth, Resend email, S3 presigned uploads, Vue 3/Vuetify frontend, Docker + nginx deploy.

The marketing website only gets a `/join` (careers) page with open positions (content managed in Sanity) and a CTA linking to the application flow hosted on the events platform (either a new Vue route group, or subdomain `join.ennova-events.com` on the same nginx).

**Hard rule: candidates never create platform accounts.** All post-submission candidate actions (status page, slot booking) use signed magic-link tokens sent by email.

## 1. Backend structure

Create a new domain module following the existing layout:

```
backend/
├── api/recruitment/          # routers: public (candidate) + hr (protected)
├── domain/recruitment/       # business logic, matching service, scheduling service
├── db/models/recruitment.py  # SQLAlchemy models
└── alembic/versions/         # new migrations
```

Auth: extend the existing JWT with a role claim (`hr`, `admin`). All `/api/hr/*` routes require it. Public candidate routes are unauthenticated or magic-token-gated.

## 2. Data model

| Table | Key fields |
|---|---|
| `departments` | name, description (used verbatim as AI matching context), skills_sought, is_active |
| `recruitment_cycles` | name, opens_at, closes_at, is_active |
| `candidates` | full_name, email (unique per cycle), phone, links (jsonb), cv_s3_key, gdpr_consent (bool), gdpr_consent_at, talent_pool_consent (bool) |
| `applications` | candidate_id FK, cycle_id FK, answers (jsonb), status (enum: `applied`, `in_review`, `interview`, `decision`, `accepted`, `rejected`, `withdrawn`), suggested_department_id FK nullable, match_confidence (float), match_rationale (text), final_department_id FK nullable, created_at |
| `interviews` | application_id FK, interviewer_user_id FK, slot_id FK, meeting_link, outcome, scorecard (jsonb) |
| `availability_slots` | interviewer_user_id FK, department_id FK nullable, starts_at, ends_at, booked_application_id FK nullable — **unique constraint on booking to prevent double-book** |
| `application_events` | application_id FK, type (status_change / email_sent / note / ai_match / override), payload (jsonb), actor, created_at — append-only timeline |

Notes:
- `answers` as JSONB so form questions can change without migrations.
- Every status change, email send, AI suggestion, and HR override MUST write an `application_events` row.

## 3. Features

### 3.1 Application form (candidate-facing, public)
- Multi-step Vue form: contact → background → motivation → department preferences → CV upload.
- CV upload via S3 presigned URL (reuse existing presign pattern from event images). Accept PDF, max ~10 MB.
- Explicit GDPR consent checkbox (required) with retention wording + optional talent-pool consent checkbox. Store both with timestamps.
- On submit: create candidate + application, fire confirmation email, enqueue AI matching as a FastAPI background task, return a status-page magic link.
- Idempotency: same email + cycle should not create duplicate applications; return a friendly "already applied" state.

### 3.2 AI department matching
- **One structured-output LLM call per application. Do NOT build a multi-agent system.**
- Input: application answers + extracted CV text (parse PDF server-side; if extraction fails, proceed with answers only and flag it) + all active department descriptions.
- Output JSON schema:
  ```json
  {
    "ranked_departments": [
      {"department_id": 1, "confidence": 0.87, "rationale": "two sentences max"}
    ],
    "flags": ["optional strings, e.g. cv_unreadable"]
  }
  ```
- Persist top suggestion + confidence + rationale on the application; full ranking into `application_events`.
- This is a **suggestion only**. HR confirms or overrides with one click; overrides are logged with the chosen department (this data later evaluates matching quality).
- Must be retryable and failure-tolerant: an LLM failure must never block or lose an application. Show "matching pending" in the panel.

### 3.3 HR panel (protected)
- Kanban board by application status; columns match the status enum; drag between columns = status change.
- Filters: cycle, department (suggested and final), search by name/email.
- Candidate detail view: form answers, inline CV preview (presigned GET), AI suggestion + rationale + confirm/override control, event timeline, notes, interview scorecard.
- Status change is THE single trigger mechanism for candidate emails (see 3.4). No separate send buttons.
- Bulk actions: move to rejected + send outcome email.

### 3.4 Email (Resend — already integrated)
Templates, all triggered by domain events:
1. Application received (with status-page magic link)
2. Interview invitation → contains slot-booking magic link
3. Booking confirmation with `.ics` attachment (generate ICS server-side; include meeting link)
4. Reminder 24h before interview (scheduled job)
5. Outcome: offer / rejection (rejection copy must be warm and specific-ish)
6. Nudge: invited but no slot booked after 72h (scheduled job)

Log every send to `application_events`.

### 3.5 Scheduling (Calendly-lite, internal — NO Google Calendar OAuth in v1)
- HR panel: interviewers create/edit availability slots (optionally scoped to a department).
- Candidate magic link page: shows open slots for their department, picks one → atomic booking (rely on the unique constraint; handle conflict with "slot just taken, pick another").
- On booking: create `interviews` row, send ICS email to both candidate and interviewer.
- Cancel/reschedule from both sides (candidate via magic link, HR via panel).

### 3.6 Candidate status page (magic link)
- Read-only timeline: Application received → Under review → Interview booked (with details) → Outcome.
- Tokens: signed, scoped to one application, long-lived but revocable (store token id, allow invalidation).

### 3.7 Supporting features
- **CV parsing prefill**: extract name/email/links from uploaded PDF to prefill form fields (best-effort, editable).
- **Interview scorecard**: fixed rubric (e.g. motivation / skills / culture, 1–5 + comment) stored as jsonb on the interview.
- **Analytics view (HR)**: funnel per cycle and per department (applied → interviewed → offered → accepted), plus a `source` field on the form ("where did you hear about us").
- **Talent pool**: applications with `talent_pool_consent=true` remain queryable across cycles.
- **GDPR retention job**: scheduled task that hard-deletes candidate PII + S3 CV N months after cycle close (configurable, default 6) unless talent-pool consent. Deletion must also purge S3 objects and write an anonymized event row.

## 4. Website (`ennova_website`) — minimal scope
- New `/join` page: hero, open departments/positions pulled from Sanity, CTA button → application URL on the platform.
- New Sanity schema: `position` (title, department name, description, isOpen).
- No backend logic on the website. Do not add databases, auth, or API routes here.

## 5. Delivery phases (ship in this order)

**Phase 1 (MVP floor — must be live before recruitment opens):** migrations + models, application form, CV upload, confirmation email, plain HR table view, GDPR consent capture, website `/join` page.

**Phase 2:** AI matching + confirm/override, kanban with status-triggered emails, event timeline, notes.

**Phase 3:** availability slots, magic-link booking, ICS emails, reminders/nudges, candidate status page. (Can launch mid-cycle.)

**Phase 4:** analytics/funnel, scorecards, talent pool, GDPR retention job, CV prefill.

## 6. Non-functional requirements
- All new endpoints under `/api/recruitment/...` (public) and `/api/hr/recruitment/...` (protected); appear in Swagger.
- Rate-limit public submission endpoints; validate uploads (content-type, size) server-side.
- Background tasks must be idempotent and safe to retry.
- Alembic migrations reversible; no destructive changes to existing tables.
- Tests: unit tests for matching-response parsing, booking atomicity (concurrent booking test), magic-token validation, and the retention job.
- Env vars to add: `LLM_API_KEY`, `RECRUITMENT_TOKEN_SECRET`, `RETENTION_MONTHS`.

## 7. Acceptance criteria (Phase 1–3 summary)
- A candidate can apply with a CV, receive a confirmation email, and see their status via magic link — without creating an account.
- HR sees every application with an AI-suggested department + rationale within ~1 minute of submission, and can override it; the override is logged.
- Moving a card on the kanban sends the correct email exactly once, and it appears in the timeline.
- A candidate can book exactly one interview slot; double-booking is impossible under concurrent requests; both parties receive an ICS.
- An LLM outage degrades gracefully: applications still succeed, panel shows "matching pending".
