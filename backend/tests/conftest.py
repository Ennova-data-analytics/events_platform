"""
Shared test setup.

Tests run against a real Postgres (the models use JSONB, ARRAY and UUID), and
never the one in backend/.env: that is the live database. Point
TEST_DATABASE_URL at a disposable local database, e.g.

    docker run -d --name events-test-pg -e POSTGRES_USER=test -e POSTGRES_PASSWORD=test \\
        -e POSTGRES_DB=events_test -p 55432:5432 postgres:14-alpine

The default below matches that command. The schema is dropped and rebuilt
with the Alembic migrations at the start of every run, so the run refuses any
database that isn't local and named for testing.

Each test runs inside a transaction that is rolled back afterwards; the app's
own commits become savepoints within it. Stripe and Resend are never called:
the `stripe_fake` and `sent_emails` fixtures stand in for them, and any call
that slips past them fails the test.
"""
import os
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from urllib.parse import urlparse

import pytest

# --- environment: must be in place before any app module is imported --------

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql://test:test@127.0.0.1:55432/events_test"
)

_db = urlparse(TEST_DATABASE_URL)
if _db.hostname not in {"localhost", "127.0.0.1", "postgres"} or "test" not in (_db.path or ""):
    pytest.exit(
        f"Refusing to run tests against {_db.hostname}{_db.path}: the test run drops the "
        "whole schema. Use a local database with 'test' in its name (see tests/conftest.py).",
        returncode=2,
    )

os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
for key, value in {
    "SECRET_KEY": "test-secret",
    "ALGORITHM": "HS256",
    "ACCESS_TOKEN_EXPIRE_MINUTES": "30",
    "S3_ENDPOINT_URL": "https://example.invalid",
    "S3_BUCKET_NAME": "test",
    "S3_ACCESS_KEY_ID": "test",
    "S3_SECRET_ACCESS_KEY": "test",
    "R2_API_TOKEN_VALUE": "test",
    "ACCOUNT_ID": "test",
    "R2_PUBLIC_DOMAIN": "https://example.invalid",
    "RESEND_API_KEY": "test",
    "RESEND_FROM_EMAIL": "events@example.com",
    "RESEND_FROM_NAME": "Test Events",
    "EMAIL_NOTIFICATIONS_ENABLED": "false",
    "STRIPE_SECRET_KEY": "sk_test_not_a_real_key",
    "STRIPE_PUBLISHABLE_KEY": "pk_test_not_a_real_key",
    "STRIPE_WEBHOOK_SECRET": "whsec_test",
    "FRONTEND_URL": "https://events.example.invalid",
    "OPENAI_API_KEY": "test",
    "QDRANT_URL": "https://example.invalid",
    "QDRANT_API_KEY": "test",
    "QDRANT_PORT": "443",
    "RECRUITMENT_SCHEDULER_ENABLED": "false",
}.items():
    os.environ[key] = value

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# --- database ---------------------------------------------------------------

@pytest.fixture(scope="session")
def engine():
    engine = create_engine(TEST_DATABASE_URL)
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))

    config = Config(os.path.join(BACKEND_DIR, "alembic.ini"))
    config.set_main_option("script_location", os.path.join(BACKEND_DIR, "alembic"))
    command.upgrade(config, "head")

    yield engine
    engine.dispose()


@pytest.fixture
def db(engine):
    """
    A session whose work is all rolled back after the test. Factories commit
    (a savepoint here) like real data would be, so the app rolling back its
    own work can't take the test's data with it.
    """
    connection = engine.connect()
    outer = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    yield session
    session.close()
    outer.rollback()
    connection.close()


@pytest.fixture
def app(db):
    from app_setup import create_app
    from api import deps

    app = create_app()
    app.dependency_overrides[deps.get_db] = lambda: db
    return app


@pytest.fixture
def client(app):
    with TestClient(app) as client:
        yield client


# --- external services ------------------------------------------------------

@pytest.fixture(autouse=True)
def no_real_stripe(monkeypatch):
    """Fail loudly if anything reaches the real Stripe API."""
    import stripe

    def refuse(*args, **kwargs):
        raise AssertionError("Test tried to call the real Stripe API")

    monkeypatch.setattr(stripe.Refund, "create", refuse)
    monkeypatch.setattr(stripe.PaymentIntent, "retrieve", refuse)
    monkeypatch.setattr(stripe.checkout.Session, "create", refuse)


class StripeFake:
    """
    Stands in for StripeService's refund calls. Set `collected` to False to say
    a payment was never taken, or `refund_error` / `check_error` to an
    exception to have Stripe refuse.
    """

    def __init__(self):
        self.collected = True
        self.refund_status = "succeeded"
        self.refund_error = None
        self.check_error = None
        self.refunds = []

    def payment_was_collected(self, payment_intent_id):
        if self.check_error:
            raise self.check_error
        return self.collected

    def create_refund(self, payment_intent_id, amount_euros, idempotency_key, metadata):
        if self.refund_error:
            raise self.refund_error
        refund = type("FakeStripeRefund", (), {
            "id": f"re_test_{len(self.refunds) + 1}",
            "status": self.refund_status,
        })()
        self.refunds.append({
            "payment_intent": payment_intent_id,
            "amount_euros": Decimal(str(amount_euros)),
            "idempotency_key": idempotency_key,
            "metadata": metadata,
            "id": refund.id,
        })
        return refund


@pytest.fixture
def stripe_fake(monkeypatch):
    from domain.services.stripe_service import stripe_service

    fake = StripeFake()
    monkeypatch.setattr(stripe_service, "payment_was_collected", fake.payment_was_collected)
    monkeypatch.setattr(stripe_service, "create_refund", fake.create_refund)
    return fake


class EmailOutbox(list):
    """Emails the app tried to send. Set `fail` to True to make sending fail."""
    fail = False


@pytest.fixture(autouse=True)
def sent_emails(monkeypatch):
    from domain.services.email_service import email_service

    outbox = EmailOutbox()

    def send_email(to_email, to_name, subject, html_content, text_content=None, attachments=None):
        if outbox.fail:
            return False
        outbox.append({"to": to_email, "subject": subject, "html": html_content, "text": text_content})
        return True

    monkeypatch.setattr(email_service, "send_email", send_email)
    return outbox


# --- data -------------------------------------------------------------------

def _role(db, name):
    from domain import models

    role = db.query(models.Role).filter(models.Role.role_name == name).first()
    if role is None:
        role = models.Role(role_name=name)
        db.add(role)
        db.flush()
    return role


@pytest.fixture
def make_user(db):
    from domain import models

    def make(email=None, full_name="Test Person", roles=("attendee",), **fields):
        user = models.User(
            email=email or f"user-{uuid.uuid4().hex[:8]}@example.com",
            hashed_password="not-a-real-hash",
            full_name=full_name,
            **fields,
        )
        user.roles = [_role(db, name) for name in roles]
        db.add(user)
        db.commit()
        return user

    return make


@pytest.fixture
def organiser(make_user):
    return make_user(email="organiser@example.com", full_name="Olive Organiser", roles=("organiser",))


def auth_headers(user):
    from core.security import create_access_token

    return {"Authorization": f"Bearer {create_access_token({'sub': user.email})}"}


@pytest.fixture
def organiser_headers(organiser):
    return auth_headers(organiser)


@pytest.fixture
def make_event(db, organiser):
    from domain import models

    def make(**fields):
        values = {
            "event_name": "Spring Summit",
            "event_date_start": datetime.now(timezone.utc) + timedelta(days=30),
            "status": "Published",
            "price_euros": Decimal("40.00"),
            "requires_approval": False,
            "created_by_user_id": organiser.user_id,
        }
        values.update(fields)
        event = models.Event(**values)
        db.add(event)
        db.commit()
        return event

    return make


@pytest.fixture
def make_ticket_type(db):
    from domain import models

    def make(event, name="Participant", price_euros=Decimal("40.00"), **fields):
        ticket_type = models.TicketType(event_id=event.event_id, name=name, price_euros=price_euros, **fields)
        db.add(ticket_type)
        db.commit()
        return ticket_type

    return make


@pytest.fixture
def make_registration(db, make_user):
    """A registration, 'Paid' through Stripe for €40 unless told otherwise."""
    from domain import models

    def make(event, user=None, ticket_type=None, status="Paid", final_amount_euros=Decimal("40.00"),
             stripe_payment_intent_id="auto", **fields):
        if stripe_payment_intent_id == "auto":
            stripe_payment_intent_id = f"pi_test_{uuid.uuid4().hex[:12]}"
        registration = models.Registration(
            event_id=event.event_id,
            user_id=(user or make_user()).user_id,
            ticket_type_id=ticket_type.ticket_type_id if ticket_type else None,
            status=status,
            final_amount_euros=final_amount_euros,
            stripe_payment_intent_id=stripe_payment_intent_id,
            **fields,
        )
        db.add(registration)
        db.commit()
        return registration

    return make
