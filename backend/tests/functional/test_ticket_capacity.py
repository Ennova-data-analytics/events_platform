"""
Seats: what the event page shows as left and what sign-up and approval allow
must be the same number. A seat is held by an approved or paid registration
(plus a bring-a-friend seat it bought); pending, rejected and cancelled ones
don't hold one.
"""
from decimal import Decimal

import pytest

from domain import models
from domain.services.stripe_service import stripe_service
from domain.use_cases import db_registrations
from tests.conftest import auth_headers

D = Decimal


@pytest.fixture(autouse=True)
def checkout(monkeypatch):
    monkeypatch.setattr(
        stripe_service, 'create_checkout_session',
        lambda registration, db: {'checkout_url': f'https://checkout.test/{registration.registration_id}'},
    )


@pytest.fixture
def event(make_event):
    return make_event(requires_approval=True)


def register(client, user, event, ticket_type=None, **body):
    if ticket_type is not None:
        body['ticket_type_id'] = ticket_type.ticket_type_id
    return client.post(f'/events/{event.event_id}/register', json=body, headers=auth_headers(user))


def shown(client, ticket_type):
    """The ticket type as the event page gets it."""
    response = client.get(f'/events/{ticket_type.event_id}/ticket-types')
    assert response.status_code == 200, response.text
    [row] = [t for t in response.json()['ticket_types'] if t['ticket_type_id'] == ticket_type.ticket_type_id]
    return row


def approve(client, headers, registration):
    return client.post(f'/admin/registrations/{registration.registration_id}/approve', json={}, headers=headers)


class TestPageAndSignUpAgree:
    def test_pending_rejected_and_cancelled_hold_no_seat(
        self, client, db, event, make_ticket_type, make_registration, make_user
    ):
        ticket_type = make_ticket_type(event, capacity=1)
        for status in ('Pending Approval', 'Rejected', 'Cancelled'):
            make_registration(event, ticket_type=ticket_type, status=status, stripe_payment_intent_id=None)

        row = shown(client, ticket_type)
        assert (row['tickets_sold'], row['tickets_available']) == (0, 1)

        response = register(client, make_user(), event, ticket_type)
        assert response.status_code == 201, response.text

    def test_approved_and_paid_hold_a_seat(self, client, db, event, make_ticket_type, make_registration, make_user):
        ticket_type = make_ticket_type(event, capacity=2)
        make_registration(event, ticket_type=ticket_type, status='Approved', stripe_payment_intent_id=None)
        make_registration(event, ticket_type=ticket_type, status='Paid')

        row = shown(client, ticket_type)
        assert (row['tickets_sold'], row['tickets_available']) == (2, 0)

        response = register(client, make_user(), event, ticket_type)
        assert response.status_code == 409
        assert response.json()['detail'] == "The 'Participant' ticket type is sold out"

    def test_a_free_ticket_counts_as_soon_as_it_is_taken(self, client, make_event, make_ticket_type, make_user):
        event = make_event(requires_approval=False)
        free = make_ticket_type(event, name='Free', price_euros=D('0'), capacity=1)

        assert register(client, make_user(), event, free).status_code == 201
        assert shown(client, free)['tickets_available'] == 0

        second = register(client, make_user(), event, free)
        assert second.status_code == 409
        assert 'sold out' in second.json()['detail']

    def test_rejecting_frees_the_seat(
        self, client, db, event, organiser_headers, make_ticket_type, make_registration, make_user
    ):
        ticket_type = make_ticket_type(event, capacity=1)
        taken = make_registration(event, ticket_type=ticket_type, status='Approved', stripe_payment_intent_id=None)
        assert shown(client, ticket_type)['tickets_available'] == 0

        response = client.post(f'/admin/registrations/{taken.registration_id}/reject', headers=organiser_headers)

        assert response.status_code == 200, response.text
        assert shown(client, ticket_type)['tickets_available'] == 1
        assert register(client, make_user(), event, ticket_type).status_code == 201

    def test_cancelling_an_unpaid_registration_frees_only_its_own_seat(
        self, client, db, event, make_ticket_type, make_registration
    ):
        ticket_type = make_ticket_type(event, capacity=3)
        unpaid = make_registration(event, ticket_type=ticket_type, status='Approved', stripe_payment_intent_id=None)
        make_registration(event, ticket_type=ticket_type, status='Paid')

        db_registrations.cancel_registration(db, unpaid.registration_id)

        row = shown(client, ticket_type)
        assert (row['tickets_sold'], row['tickets_available']) == (1, 2)

    def test_the_availability_check_matches(self, client, event, make_ticket_type, make_registration):
        ticket_type = make_ticket_type(event, capacity=2)
        make_registration(event, ticket_type=ticket_type, status='Paid')
        make_registration(event, ticket_type=ticket_type, status='Pending Approval', stripe_payment_intent_id=None)

        response = client.get(f'/events/{event.event_id}/ticket-types/{ticket_type.ticket_type_id}/availability')

        assert response.json()['tickets_remaining'] == 1
        assert response.json()['available'] is True


class TestApproval:
    def test_approving_takes_a_seat(self, client, db, event, organiser_headers, make_ticket_type, make_registration):
        ticket_type = make_ticket_type(event, capacity=1)
        pending = make_registration(event, ticket_type=ticket_type, status='Pending Approval', stripe_payment_intent_id=None)

        response = approve(client, organiser_headers, pending)

        assert response.status_code == 200, response.text
        assert shown(client, ticket_type)['tickets_available'] == 0

    def test_approving_when_full_is_refused(
        self, client, db, event, organiser_headers, make_ticket_type, make_registration
    ):
        ticket_type = make_ticket_type(event, name='International', capacity=1)
        make_registration(event, ticket_type=ticket_type, status='Paid')
        pending = make_registration(event, ticket_type=ticket_type, status='Pending Approval', stripe_payment_intent_id=None)

        response = approve(client, organiser_headers, pending)

        assert response.status_code == 409
        assert response.json()['detail'] == (
            "The 'International' ticket type is full: approving this registration needs 1 seat "
            "and 0 left. Raise its capacity or free a seat first."
        )
        db.refresh(pending)
        assert pending.status == 'Pending Approval'

    def test_approving_again_needs_no_extra_seat(
        self, client, db, event, organiser_headers, make_ticket_type, make_registration
    ):
        ticket_type = make_ticket_type(event, capacity=1)
        approved = make_registration(event, ticket_type=ticket_type, status='Approved', stripe_payment_intent_id=None)

        assert approve(client, organiser_headers, approved).status_code == 200

    def test_a_bring_a_friend_purchase_needs_two_seats_to_approve(
        self, client, db, event, organiser_headers, make_ticket_type, make_registration, make_user
    ):
        duo = make_ticket_type(event, name='Duo', price_euros=D('20.00'), bring_a_friend=True, capacity=3)
        response = register(client, make_user(), event, duo, friend_email='friend@example.com')
        assert response.status_code == 201, response.text
        buyer = db.get(models.Registration, response.json()['registration']['registration_id'])
        assert buyer.status == 'Pending Approval'
        assert shown(client, duo)['tickets_sold'] == 0
        make_registration(event, ticket_type=duo, status='Paid')
        make_registration(event, ticket_type=duo, status='Paid')

        refused = approve(client, organiser_headers, buyer)

        assert refused.status_code == 409
        assert 'needs 2 seats and 1 left' in refused.json()['detail']

    def test_approving_on_an_event_without_ticket_types_checks_its_capacity(
        self, client, db, make_event, organiser_headers, make_registration
    ):
        event = make_event(requires_approval=True, capacity=1)
        make_registration(event, status='Paid')
        pending = make_registration(event, status='Pending Approval', stripe_payment_intent_id=None)

        response = approve(client, organiser_headers, pending)

        assert response.status_code == 409
        assert response.json()['detail'].startswith('This event is full')


class TestEventWithoutTicketTypes:
    def test_only_accepted_registrations_fill_it(self, client, make_event, make_registration, make_user):
        event = make_event(requires_approval=True, capacity=1)
        make_registration(event, status='Pending Approval', stripe_payment_intent_id=None)
        make_registration(event, status='Rejected', stripe_payment_intent_id=None)

        assert register(client, make_user(), event).status_code == 201

        make_registration(event, status='Approved', stripe_payment_intent_id=None)
        full = register(client, make_user(), event)
        assert full.status_code == 409
        assert full.json()['detail'] == 'This event is full'


class TestCapacityChanges:
    def test_capacity_cant_go_below_the_seats_taken(
        self, client, event, organiser_headers, make_ticket_type, make_registration
    ):
        ticket_type = make_ticket_type(event, capacity=5)
        make_registration(event, ticket_type=ticket_type, status='Paid')
        make_registration(event, ticket_type=ticket_type, status='Approved', stripe_payment_intent_id=None)

        response = client.put(
            f'/events/{event.event_id}/ticket-types/{ticket_type.ticket_type_id}',
            json={'capacity': 1}, headers=organiser_headers,
        )

        assert response.status_code == 400
        assert response.json()['detail'] == 'Cannot reduce capacity to 1. 2 seats are already taken.'


class TestDiscountCodes:
    def test_the_code_use_is_saved_with_the_registration(self, client, db, make_event, make_ticket_type, make_user):
        event = make_event(requires_approval=False)
        ticket_type = make_ticket_type(event, capacity=5)
        code = models.DiscountCode(event_id=event.event_id, code='HALF', discount_type='percentage', discount_value=D('50'))
        db.add(code)
        db.commit()

        response = register(client, make_user(), event, ticket_type, discount_code='HALF')

        assert response.status_code == 201, response.text
        db.refresh(code)
        assert code.used_count == 1
