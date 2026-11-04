"""Partial refunds through the admin API, end to end against the database, with Stripe and email faked."""
import uuid
from decimal import Decimal

import pytest
import stripe

from domain import models
from tests.conftest import auth_headers

D = Decimal
REASON = "We charged €40 instead of €30 by mistake. Sorry!"


@pytest.fixture
def event(make_event):
    return make_event()


def refund(client, headers, event, registrations, **body):
    payload = {
        'batch_id': str(uuid.uuid4()),
        'registration_ids': [r.registration_id for r in registrations],
        'mode': 'fixed',
        'amount_euros': '10.00',
        'reason': REASON,
    }
    payload.update(body)
    return client.post(f"/admin/events/{event.event_id}/refunds", json=payload, headers=headers)


def preview(client, headers, event, registrations, **body):
    payload = {
        'registration_ids': [r.registration_id for r in registrations],
        'mode': 'fixed',
        'amount_euros': '10.00',
    }
    payload.update(body)
    return client.post(f"/admin/events/{event.event_id}/refunds/preview", json=payload, headers=headers)


def refunds_of(db, registration):
    return db.query(models.Refund).filter(models.Refund.registration_id == registration.registration_id).all()


class TestStripeRefund:
    def test_refunds_the_card_and_the_ticket_stays_valid(
        self, client, db, organiser_headers, event, make_ticket_type, make_registration, stripe_fake, sent_emails
    ):
        ticket_type = make_ticket_type(event, tickets_sold=1)
        reg = make_registration(event, ticket_type=ticket_type, ticket_token='tok-123')

        response = refund(client, organiser_headers, event, [reg])

        assert response.status_code == 200, response.text
        body = response.json()
        assert body['refunded_count'] == 1
        assert D(body['total_refunded_euros']) == D('10.00')
        [result] = body['results']
        assert result['outcome'] == 'refunded'
        assert result['method'] == 'stripe'
        assert result['email_sent'] is True

        [call] = stripe_fake.refunds
        assert call['payment_intent'] == reg.stripe_payment_intent_id
        assert call['amount_euros'] == D('10.00')
        assert call['idempotency_key'] == f"refund:{body['batch_id']}:{reg.registration_id}"
        assert call['metadata']['registration_id'] == str(reg.registration_id)

        [row] = refunds_of(db, reg)
        assert (row.status, row.method, row.stripe_refund_id) == ('succeeded', 'stripe', call['id'])
        assert row.reason == REASON

        db.refresh(reg)
        db.refresh(ticket_type)
        assert reg.status == 'Paid'
        assert reg.ticket_token == 'tok-123'
        assert reg.has_valid_ticket
        assert ticket_type.tickets_sold == 1

    def test_emails_and_notifies_the_attendee(
        self, client, db, organiser_headers, event, make_user, make_registration, stripe_fake, sent_emails
    ):
        user = make_user(email='ada@example.com', full_name='Ada')
        reg = make_registration(event, user=user)

        refund(client, organiser_headers, event, [reg])

        [email] = sent_emails
        assert email['to'] == 'ada@example.com'
        assert email['subject'] == 'Partial refund for Spring Summit'
        assert '€10.00' in email['text']
        assert REASON in email['text']
        assert f"/event/{event.event_id}/ticket/{reg.registration_id}" in email['text']

        notice = db.query(models.InAppNotification).filter(models.InAppNotification.user_id == user.user_id).one()
        assert notice.title == 'Partial refund issued'

    def test_pending_stripe_refund_counts_and_is_reported_pending(
        self, client, db, organiser_headers, event, make_registration, stripe_fake
    ):
        stripe_fake.refund_status = 'pending'
        reg = make_registration(event)

        [result] = refund(client, organiser_headers, event, [reg]).json()['results']

        assert result['outcome'] == 'pending'
        assert result['email_sent'] is True
        db.refresh(reg)
        assert reg.refunded_amount_euros == D('10.00')


class TestManualRefund:
    def test_ticket_marked_paid_by_hand_is_recorded_not_sent_to_stripe(
        self, client, db, organiser_headers, event, make_registration, stripe_fake, sent_emails
    ):
        reg = make_registration(event, stripe_payment_intent_id=None)

        [result] = refund(client, organiser_headers, event, [reg]).json()['results']

        assert result['outcome'] == 'refunded'
        assert result['method'] == 'manual'
        assert stripe_fake.refunds == []
        [row] = refunds_of(db, reg)
        assert (row.method, row.status) == ('manual', 'succeeded')
        assert 'organisers will return' in sent_emails[0]['text']

    def test_abandoned_checkout_then_marked_paid_is_manual(
        self, client, db, organiser_headers, event, make_registration, stripe_fake
    ):
        stripe_fake.collected = False
        reg = make_registration(event)  # has a payment intent, but Stripe never took the money

        [result] = refund(client, organiser_headers, event, [reg]).json()['results']

        assert result['method'] == 'manual'
        assert stripe_fake.refunds == []


class TestLimitsAndSkips:
    def test_never_more_than_was_paid(self, client, db, organiser_headers, event, make_registration, stripe_fake):
        reg = make_registration(event)

        first = refund(client, organiser_headers, event, [reg], amount_euros='30.00').json()
        second = refund(client, organiser_headers, event, [reg], amount_euros='30.00').json()
        third = refund(client, organiser_headers, event, [reg], amount_euros='5.00').json()

        assert D(first['results'][0]['amount_euros']) == D('30.00')
        assert D(second['results'][0]['amount_euros']) == D('10.00')
        assert third['results'][0]['outcome'] == 'skipped'
        assert third['results'][0]['message'] == 'Already fully refunded'
        assert sum(r.amount_euros for r in refunds_of(db, reg)) == D('40.00')

    def test_donation_is_not_refundable(self, client, organiser_headers, event, make_registration, stripe_fake):
        reg = make_registration(event, final_amount_euros=D('40.00'), donation_amount_euros=D('25.00'))

        [result] = refund(client, organiser_headers, event, [reg], amount_euros='60.00').json()['results']

        assert D(result['amount_euros']) == D('40.00')

    def test_skips_people_with_nothing_to_refund(
        self, client, organiser_headers, event, make_registration, stripe_fake, sent_emails
    ):
        unpaid = make_registration(event, status='Approved')
        covered = make_registration(event, final_amount_euros=D('0'), paid_by_team_leader=True)
        paying = make_registration(event)

        body = refund(client, organiser_headers, event, [unpaid, covered, paying]).json()

        outcomes = {r['registration_id']: r['outcome'] for r in body['results']}
        assert outcomes == {
            unpaid.registration_id: 'skipped',
            covered.registration_id: 'skipped',
            paying.registration_id: 'refunded',
        }
        assert (body['refunded_count'], body['skipped_count']) == (1, 2)
        assert len(sent_emails) == 1

    def test_registrations_of_another_event_are_refused(
        self, client, organiser_headers, event, make_event, make_registration, stripe_fake
    ):
        other = make_registration(make_event(event_name='Other'))

        response = refund(client, organiser_headers, event, [other])

        assert response.status_code == 404
        assert str(other.registration_id) in response.json()['detail']
        assert stripe_fake.refunds == []


class TestFailures:
    def test_stripe_refusal_fails_that_person_only(
        self, client, db, organiser_headers, event, make_registration, stripe_fake, sent_emails, monkeypatch
    ):
        refused = make_registration(event)
        fine = make_registration(event)
        real_create = stripe_fake.create_refund

        def create_refund(payment_intent_id, **kwargs):
            if payment_intent_id == refused.stripe_payment_intent_id:
                raise stripe.error.InvalidRequestError("Charge has already been refunded.", param=None)
            return real_create(payment_intent_id, **kwargs)

        from domain.services.stripe_service import stripe_service
        monkeypatch.setattr(stripe_service, 'create_refund', create_refund)

        body = refund(client, organiser_headers, event, [refused, fine]).json()

        results = {r['registration_id']: r for r in body['results']}
        assert results[refused.registration_id]['outcome'] == 'failed'
        assert 'already been refunded' in results[refused.registration_id]['message']
        assert results[fine.registration_id]['outcome'] == 'refunded'
        assert (body['refunded_count'], body['failed_count']) == (1, 1)

        [row] = refunds_of(db, refused)
        assert row.status == 'failed'
        db.refresh(refused)
        assert refused.refunded_amount_euros == 0  # a failed refund doesn't count
        assert [e['to'] for e in sent_emails] == [fine.user.email]

    def test_lost_connection_stays_pending_and_tells_nobody(
        self, client, db, organiser_headers, event, make_registration, stripe_fake, sent_emails
    ):
        stripe_fake.refund_error = stripe.error.APIConnectionError("Network down")
        reg = make_registration(event)

        [result] = refund(client, organiser_headers, event, [reg]).json()['results']

        assert result['outcome'] == 'pending'
        assert 'Stripe dashboard' in result['message']
        assert sent_emails == []
        db.refresh(reg)
        assert reg.refunded_amount_euros == D('10.00')  # still blocks a second refund of the same money

    def test_cant_check_the_payment(self, client, db, organiser_headers, event, make_registration, stripe_fake):
        stripe_fake.check_error = stripe.error.APIConnectionError("Network down")
        reg = make_registration(event)

        [result] = refund(client, organiser_headers, event, [reg]).json()['results']

        assert result['outcome'] == 'failed'
        assert 'nothing was refunded' in result['message']
        assert refunds_of(db, reg) == []

    def test_email_failure_is_reported_and_can_be_resent(
        self, client, db, organiser_headers, event, make_registration, stripe_fake, sent_emails
    ):
        sent_emails.fail = True
        reg = make_registration(event)

        body = refund(client, organiser_headers, event, [reg]).json()

        [result] = body['results']
        assert result['outcome'] == 'refunded'
        assert result['email_sent'] is False
        assert "email didn't go out" in result['message']
        assert body['emails_failed'] == 1

        response = client.post(f"/admin/refunds/{result['refund_id']}/resend-email", headers=organiser_headers)
        assert response.status_code == 502

        sent_emails.fail = False
        response = client.post(f"/admin/refunds/{result['refund_id']}/resend-email", headers=organiser_headers)
        assert response.status_code == 200
        assert response.json()['email_sent'] is True
        assert len(sent_emails) == 1

    def test_failed_refund_email_cant_be_resent(
        self, client, organiser_headers, event, make_registration, stripe_fake
    ):
        stripe_fake.refund_error = stripe.error.InvalidRequestError("No such payment", param=None)
        reg = make_registration(event)
        [result] = refund(client, organiser_headers, event, [reg]).json()['results']

        response = client.post(f"/admin/refunds/{result['refund_id']}/resend-email", headers=organiser_headers)

        assert response.status_code == 400


class TestResubmit:
    def test_same_batch_twice_refunds_once(self, client, db, organiser_headers, event, make_registration, stripe_fake):
        reg = make_registration(event)
        batch_id = str(uuid.uuid4())

        first = refund(client, organiser_headers, event, [reg], batch_id=batch_id).json()
        second = refund(client, organiser_headers, event, [reg], batch_id=batch_id).json()

        assert first['results'][0]['outcome'] == 'refunded'
        assert second['results'][0]['outcome'] == 'refunded'
        assert second['results'][0]['message'].startswith('Already processed in this batch')
        assert len(stripe_fake.refunds) == 1
        assert len(refunds_of(db, reg)) == 1


class TestCorrectedPrice:
    def test_refunds_the_difference_per_person(
        self, client, db, organiser_headers, event, make_ticket_type, make_registration, stripe_fake
    ):
        ticket_type = make_ticket_type(event, price_euros=D('40.00'))
        code = models.DiscountCode(event_id=event.event_id, code='HALF', discount_type='percentage', discount_value=D('50'))
        db.add(code)
        db.flush()
        full = make_registration(event, ticket_type=ticket_type)
        half = make_registration(event, ticket_type=ticket_type, final_amount_euros=D('20.00'),
                                 discount_code_id=code.code_id, discount_amount_euros=D('20.00'))

        body = refund(client, organiser_headers, event, [full, half],
                      mode='corrected_price', amount_euros=None, corrected_price_euros='30.00').json()

        amounts = {r['registration_id']: D(r['amount_euros']) for r in body['results']}
        assert amounts == {full.registration_id: D('10.00'), half.registration_id: D('5.00')}
        db.refresh(ticket_type)
        assert ticket_type.price_euros == D('40.00')  # not asked to change it
        assert body['ticket_type_price_updated'] is False

    def test_can_also_fix_the_ticket_price(
        self, client, db, organiser_headers, event, make_ticket_type, make_registration, stripe_fake
    ):
        ticket_type = make_ticket_type(event, price_euros=D('40.00'))
        reg = make_registration(event, ticket_type=ticket_type)

        body = refund(client, organiser_headers, event, [reg], mode='corrected_price', amount_euros=None,
                      corrected_price_euros='30.00', update_ticket_type_price=True).json()

        assert body['ticket_type_price_updated'] is True
        db.refresh(ticket_type)
        assert ticket_type.price_euros == D('30.00')

    def test_fixes_the_event_price_when_there_are_no_ticket_types(
        self, client, db, organiser_headers, event, make_registration, stripe_fake
    ):
        reg = make_registration(event)

        refund(client, organiser_headers, event, [reg], mode='corrected_price', amount_euros=None,
               corrected_price_euros='30.00', update_ticket_type_price=True)

        db.refresh(event)
        assert event.price_euros == D('30.00')

    def test_one_ticket_type_at_a_time(
        self, client, organiser_headers, event, make_ticket_type, make_registration, stripe_fake
    ):
        a = make_registration(event, ticket_type=make_ticket_type(event, name='Participant'))
        b = make_registration(event, ticket_type=make_ticket_type(event, name='Spectator'))

        response = refund(client, organiser_headers, event, [a, b], mode='corrected_price',
                          amount_euros=None, corrected_price_euros='30.00')

        assert response.status_code == 400
        assert 'Participant, Spectator' in response.json()['detail']
        assert stripe_fake.refunds == []


class TestPreview:
    def test_shows_each_person_without_refunding(
        self, client, db, organiser_headers, event, make_ticket_type, make_registration, stripe_fake, sent_emails
    ):
        ticket_type = make_ticket_type(event, name='Participant', price_euros=D('40.00'))
        card = make_registration(event, ticket_type=ticket_type)
        by_hand = make_registration(event, ticket_type=ticket_type, stripe_payment_intent_id=None)
        unpaid = make_registration(event, ticket_type=ticket_type, status='Approved')

        response = preview(client, organiser_headers, event, [card, by_hand, unpaid],
                           mode='corrected_price', amount_euros=None, corrected_price_euros='35.00')

        assert response.status_code == 200, response.text
        body = response.json()
        rows = {r['registration_id']: r for r in body['rows']}
        assert (D(rows[card.registration_id]['refund_euros']), rows[card.registration_id]['method']) == (D('5.00'), 'stripe')
        assert rows[by_hand.registration_id]['method'] == 'manual'
        assert rows[unpaid.registration_id]['skip_reason'].startswith('Not paid')
        assert (D(body['total_refund_euros']), body['refundable_count']) == (D('10.00'), 2)
        assert (body['ticket_type_name'], D(body['current_price_euros'])) == ('Participant', D('40.00'))

        assert stripe_fake.refunds == []
        assert sent_emails == []
        assert db.query(models.Refund).count() == 0


class TestAccess:
    def test_attendees_cant_refund(self, client, event, make_user, make_registration, stripe_fake):
        reg = make_registration(event)
        response = refund(client, auth_headers(make_user()), event, [reg])
        assert response.status_code == 403
        assert stripe_fake.refunds == []

    def test_unknown_event(self, client, organiser_headers, make_registration, event, stripe_fake):
        reg = make_registration(event)
        response = client.post("/admin/events/999999/refunds/preview", headers=organiser_headers,
                               json={'registration_ids': [reg.registration_id], 'mode': 'fixed', 'amount_euros': '1'})
        assert response.status_code == 404


def test_attendee_list_shows_refunds(client, organiser_headers, event, make_registration, stripe_fake):
    reg = make_registration(event)
    refund(client, organiser_headers, event, [reg], amount_euros='7.50')

    response = client.get(f"/events/{event.event_id}/registrations", headers=organiser_headers)

    [row] = response.json()
    assert D(row['refunded_amount_euros']) == D('7.50')
    [summary] = row['refunds']
    assert (summary['status'], summary['method'], summary['email_sent']) == ('succeeded', 'stripe', True)
