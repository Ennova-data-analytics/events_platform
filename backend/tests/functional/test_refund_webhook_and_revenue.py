"""Stripe telling us how a refund ended, and refunds in the revenue and referral figures."""
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
import stripe

from domain import models
from domain.use_cases import db_revenue
from domain.use_cases.db_referral_links import ReferralLinkUseCases

D = Decimal


@pytest.fixture
def make_refund(db):
    def make(registration, amount='10.00', status='pending', stripe_refund_id=None, method='stripe'):
        refund = models.Refund(
            registration_id=registration.registration_id,
            event_id=registration.event_id,
            amount_euros=D(amount),
            reason='Wrong price',
            method=method,
            status=status,
            stripe_refund_id=stripe_refund_id,
            batch_id=uuid.uuid4(),
        )
        db.add(refund)
        db.commit()
        return refund
    return make


@pytest.fixture
def send_webhook(client, monkeypatch):
    """Post a Stripe event to the webhook, skipping the signature check."""
    def send(event_type, obj):
        event = {'type': event_type, 'data': {'object': obj}}
        monkeypatch.setattr(stripe.Webhook, 'construct_event', lambda payload, sig, secret: event)
        return client.post('/payments/webhook/stripe', content=b'{}', headers={'stripe-signature': 't=1,v1=x'})
    return send


class TestWebhook:
    @pytest.mark.parametrize('event_type', ['refund.updated', 'charge.refund.updated'])
    def test_pending_refund_settles(self, db, send_webhook, make_event, make_registration, make_refund, event_type):
        refund = make_refund(make_registration(make_event()), stripe_refund_id='re_1')

        response = send_webhook(event_type, {'id': 're_1', 'status': 'succeeded'})

        assert response.status_code == 200
        db.refresh(refund)
        assert refund.status == 'succeeded'

    def test_refund_that_fails_later_is_marked_failed(self, db, send_webhook, make_event, make_registration, make_refund):
        reg = make_registration(make_event())
        refund = make_refund(reg, status='succeeded', stripe_refund_id='re_2')

        send_webhook('refund.failed', {'id': 're_2', 'status': 'failed', 'failure_reason': 'expired_or_canceled_card'})

        db.refresh(refund)
        db.refresh(reg)
        assert refund.status == 'failed'
        assert 'expired_or_canceled_card' in refund.failure_reason
        assert reg.refunded_amount_euros == 0

    def test_refund_whose_create_call_was_cut_off_is_matched_by_metadata(
        self, db, send_webhook, make_event, make_registration, make_refund
    ):
        refund = make_refund(make_registration(make_event()))  # no Stripe id: we never heard back

        send_webhook('refund.created', {'id': 're_3', 'status': 'succeeded', 'metadata': {'refund_id': str(refund.refund_id)}})

        db.refresh(refund)
        assert (refund.stripe_refund_id, refund.status) == ('re_3', 'succeeded')

    def test_refunds_made_outside_the_platform_are_ignored(self, db, send_webhook):
        response = send_webhook('refund.updated', {'id': 're_dashboard', 'status': 'succeeded', 'metadata': {}})

        assert response.status_code == 200
        assert db.query(models.Refund).count() == 0


class TestRevenue:
    @pytest.fixture
    def fiscal_year(self):
        return 2026  # FY26/27: September 2026 to June 2027

    @pytest.fixture
    def event(self, make_event):
        return make_event(event_date_start=datetime(2026, 11, 20, 18, tzinfo=timezone.utc))

    def overview_row(self, db, event, fiscal_year):
        overview = db_revenue.get_revenue_overview(db, fiscal_year, now=datetime(2027, 7, 1, tzinfo=timezone.utc))
        [row] = [r for r in overview['events'] if r['event_id'] == event.event_id]
        return row, overview['totals']

    def test_refunds_come_off_ticket_income(self, db, event, fiscal_year, make_registration, make_refund):
        a = make_registration(event)
        make_registration(event)
        make_refund(a, '10.00', status='succeeded')
        make_refund(a, '5.00', status='pending')
        make_refund(a, '7.00', status='failed')

        row, totals = self.overview_row(db, event, fiscal_year)

        assert row['refunds_given'] == D('15.00')
        assert row['ticket_revenue'] == D('65.00')
        assert row['total_collected'] == D('65.00')
        assert row['net_revenue'] == D('65.00')
        assert row['paid_tickets'] == 2
        assert totals['refunds_given'] == D('15.00')

    def test_refunds_on_tickets_no_longer_paid_arent_taken_off_twice(
        self, db, event, fiscal_year, make_registration, make_refund
    ):
        reverted = make_registration(event)
        make_registration(event)
        make_refund(reverted, '10.00', status='succeeded')
        reverted.status = 'Pending Approval'
        db.commit()

        row, _ = self.overview_row(db, event, fiscal_year)

        assert row['refunds_given'] == 0
        assert row['ticket_revenue'] == D('40.00')

    def test_commission_is_on_what_was_kept(self, db, event, fiscal_year, make_registration, make_refund):
        link = models.ReferralLink(event_id=event.event_id, code='FRIEND', referrer_name='Sam', commission_percentage=D('10'))
        db.add(link)
        db.commit()
        reg = make_registration(event, referral_link_id=link.link_id)
        make_registration(event, referral_link_id=link.link_id)
        make_refund(reg, '10.00', status='succeeded')

        row, _ = self.overview_row(db, event, fiscal_year)
        referral_stats = ReferralLinkUseCases._to_response(link, db)

        assert row['commission_owed'] == D('7.00')  # 10% of 70
        assert referral_stats['total_revenue'] == D('70.00')
        assert referral_stats['commission_owed'] == row['commission_owed']
