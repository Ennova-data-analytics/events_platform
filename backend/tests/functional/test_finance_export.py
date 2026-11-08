"""The read-only finance export Finnova books ticket revenue from."""
from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
import stripe

from core.config import settings
from domain import models
from domain.services.stripe_service import StripeService
from domain.use_cases.db_finance_export import ticket_fee_cents

D = Decimal
TOKEN = "test-finance-token"
PAID = datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def finance_token(monkeypatch):
    monkeypatch.setattr(settings, "FINANCE_EXPORT_TOKEN", TOKEN)


def get(client, path, token=TOKEN):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return client.get(path, headers=headers)


def paid(make_registration, event, **fields):
    values = {"paid_at": PAID, "stripe_charge_id": "ch_1", "stripe_fee_cents": 150}
    values.update(fields)
    return make_registration(event, **values)


WINDOW = "start=2026-09-01&end=2027-08-31"


class TestAccess:
    def test_needs_the_token(self, client):
        assert get(client, "/internal/finance/events", token=None).status_code == 401
        assert get(client, "/internal/finance/events", token="wrong").status_code == 401
        assert get(client, "/internal/finance/events").status_code == 200

    def test_off_without_a_configured_token(self, client, monkeypatch):
        monkeypatch.setattr(settings, "FINANCE_EXPORT_TOKEN", "")
        r = get(client, "/internal/finance/events")
        assert r.status_code == 503 and r.json()["detail"] == "Finance export is not configured"

    def test_range_is_checked(self, client):
        assert get(client, "/internal/finance/payments?start=2027-01-01&end=2026-01-01").status_code == 400


class TestPayments:
    def test_what_counts_as_a_payment(self, client, make_event, make_registration):
        event = make_event()
        card = paid(make_registration, event, final_amount_euros=D("40.00"))
        by_hand = paid(make_registration, event, final_amount_euros=D("25.00"), stripe_charge_id=None, stripe_fee_cents=None, stripe_payment_intent_id=None)
        paid(make_registration, event, final_amount_euros=D("0.00"))  # free ticket
        paid(make_registration, event, final_amount_euros=None, paid_by_team_leader=True)  # covered by the leader
        make_registration(event, status="Approved", final_amount_euros=D("40.00"))  # not paid yet
        paid(make_registration, make_event(status="Cancelled"))  # cancelled event
        paid(make_registration, event, paid_at=datetime(2026, 8, 31, 23, 0, tzinfo=timezone.utc))  # before the window

        rows = get(client, f"/internal/finance/payments?{WINDOW}").json()
        assert [r["registration_id"] for r in rows] == [card.registration_id, by_hand.registration_id]
        first = rows[0]
        assert (first["gross_cents"], first["fee_cents"], first["stripe"], first["charity"], first["paid_at_estimated"]) == (4000, 150, True, False, False)
        assert (rows[1]["gross_cents"], rows[1]["fee_cents"], rows[1]["stripe"]) == (2500, None, False)
        assert "email" not in str(rows) and "user" not in str(rows)

    def test_donation_is_left_out_and_the_fee_is_shared(self, client, make_event, make_registration):
        event = make_event(is_charitable=True, charity_name="Cruz Roja")
        paid(make_registration, event, final_amount_euros=D("30.00"), donation_amount_euros=D("10.00"), stripe_fee_cents=100)
        row = get(client, f"/internal/finance/payments?{WINDOW}").json()[0]
        assert (row["gross_cents"], row["donation_cents"], row["fee_cents"], row["charity"]) == (3000, 1000, 75, True)

    def test_event_price_is_used_when_the_ticket_has_none(self, client, make_event, make_registration):
        paid(make_registration, make_event(price_euros=D("12.50")), final_amount_euros=None)
        assert get(client, f"/internal/finance/payments?{WINDOW}").json()[0]["gross_cents"] == 1250

    def test_fee_share_rounds_to_the_cent(self):
        assert ticket_fee_cents(None, 1000, 0) is None
        assert ticket_fee_cents(101, 1000, 1000) == 51  # 50.5 rounds half up
        assert ticket_fee_cents(5, 0, 0) == 0


class TestRefunds:
    @pytest.fixture
    def refund(self, db):
        def make(registration, status="succeeded", amount="10.00", when=PAID):
            r = models.Refund(registration_id=registration.registration_id, event_id=registration.event_id, amount_euros=D(amount),
                              reason="Wrong price", method="stripe", status=status, batch_id=__import__("uuid").uuid4(), created_at=when)
            db.add(r)
            db.commit()
            return r
        return make

    def test_only_settled_refunds_on_paid_tickets(self, client, make_event, make_registration, refund):
        event = make_event()
        keep = paid(make_registration, event)
        done = refund(keep, amount="5.00")
        refund(keep, status="pending")
        refund(keep, status="failed")
        gone = paid(make_registration, event, status="Cancelled")
        refund(gone)
        rows = get(client, f"/internal/finance/refunds?{WINDOW}").json()
        assert [(r["refund_id"], r["amount_cents"], r["method"]) for r in rows] == [(done.refund_id, 500, "stripe")]


class TestEvents:
    def test_lists_events_without_drafts(self, client, make_event):
        live = make_event(event_name="Idea Up", is_charitable=False)
        make_event(event_name="Draft thing", status="Draft")
        rows = get(client, "/internal/finance/events").json()
        assert [(r["event_id"], r["name"], r["charity"]) for r in rows] == [(live.event_id, "Idea Up", False)]


class TestPaidAt:
    def test_stripe_payment_records_when_and_the_fee(self, db, make_event, make_registration, monkeypatch):
        reg = make_registration(make_event(), status="Approved", stripe_payment_intent_id=None)
        monkeypatch.setattr(StripeService, "charge_and_fee", staticmethod(lambda pi: ("ch_9", 123)))
        StripeService.handle_payment_success("pi_9", reg.registration_id, db)
        db.refresh(reg)
        assert reg.status == "Paid" and reg.paid_at is not None and (reg.stripe_charge_id, reg.stripe_fee_cents) == ("ch_9", 123)

    def test_a_stripe_hiccup_still_confirms_the_payment(self, db, make_event, make_registration, monkeypatch):
        reg = make_registration(make_event(), status="Approved", stripe_payment_intent_id=None)

        def broken(pi):
            raise stripe.error.APIConnectionError("down")

        monkeypatch.setattr(StripeService, "charge_and_fee", staticmethod(broken))
        StripeService.handle_payment_success("pi_10", reg.registration_id, db)
        db.refresh(reg)
        assert reg.status == "Paid" and reg.paid_at is not None and reg.stripe_fee_cents is None

    def test_marked_paid_by_hand(self, client, db, make_event, make_registration, organiser_headers):
        reg = make_registration(make_event(), status="Approved", stripe_payment_intent_id=None)
        r = client.post(f"/admin/registrations/{reg.registration_id}/mark-paid", headers=organiser_headers)
        assert r.status_code == 200
        db.refresh(reg)
        assert reg.paid_at is not None and reg.paid_at_estimated is False

    def test_charge_and_fee_reads_the_expanded_charge(self, monkeypatch):
        intent = {"status": "succeeded", "latest_charge": {"id": "ch_1", "balance_transaction": {"fee": 87}}}
        monkeypatch.setattr(stripe.PaymentIntent, "retrieve", lambda pi, expand: intent)
        assert StripeService.charge_and_fee("pi_1") == ("ch_1", 87)
        monkeypatch.setattr(stripe.PaymentIntent, "retrieve", lambda pi, expand: {"status": "requires_payment_method", "latest_charge": None})
        assert StripeService.charge_and_fee("pi_2") is None


class TestBackfill:
    def test_fills_from_stripe_estimates_manual_and_reports_errors(self, db, make_event, make_registration, monkeypatch):
        from scripts import backfill_payments

        event = make_event()
        card = make_registration(event, paid_at=None)
        by_hand = make_registration(event, paid_at=None, stripe_payment_intent_id=None)
        broken = make_registration(event, paid_at=None)
        charged = datetime(2026, 9, 20, 10, 0, tzinfo=timezone.utc)

        def details(pi):
            if pi == broken.stripe_payment_intent_id:
                raise stripe.error.APIConnectionError("Stripe is down")
            return charged, "ch_card", 140

        monkeypatch.setattr(backfill_payments, "stripe_details", details)
        report = backfill_payments.backfill(db, apply=True)
        db.refresh(card); db.refresh(by_hand); db.refresh(broken)
        assert (card.paid_at, card.stripe_fee_cents, card.paid_at_estimated) == (charged, 140, False)
        assert by_hand.paid_at is not None and by_hand.paid_at_estimated is True
        assert broken.paid_at is None
        assert (report["from_stripe"], report["estimated"], report["fees"]) == (1, 1, 1)
        assert len(report["errors"]) == 1 and "Stripe is down" in report["errors"][0]
