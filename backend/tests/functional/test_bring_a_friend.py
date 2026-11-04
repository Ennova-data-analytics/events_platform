"""
"Bring a friend": the buyer pays once for two tickets and names a friend by
email. Nothing reaches the friend until the buyer has paid; then the ticket
goes into the friend's account, or they get a link to sign up and claim it.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from domain import models
from domain.services.stripe_service import stripe_service
from domain.use_cases import db_friend_tickets
from tests.conftest import auth_headers

D = Decimal
FRIEND = 'friend@example.com'


@pytest.fixture(autouse=True)
def checkout(monkeypatch):
    """Stripe checkout sessions, faked. Records the registrations sent to pay."""
    started = []

    def create_checkout_session(registration, db):
        started.append(registration.registration_id)
        return {'checkout_url': f'https://checkout.test/{registration.registration_id}'}

    monkeypatch.setattr(stripe_service, 'create_checkout_session', create_checkout_session)
    return started


@pytest.fixture
def event(make_event):
    return make_event()


@pytest.fixture
def duo(event, make_ticket_type):
    return make_ticket_type(event, name='Duo', price_euros=D('20.00'), bring_a_friend=True, capacity=10)


@pytest.fixture
def buyer(make_user):
    return make_user(email='buyer@example.com', full_name='Bea Buyer')


def buy(client, buyer, ticket_type, friend_email=FRIEND, **extra):
    body = {'ticket_type_id': ticket_type.ticket_type_id, 'friend_email': friend_email, **extra}
    return client.post(f'/events/{ticket_type.event_id}/register', json=body, headers=auth_headers(buyer))


def pay(db, registration_id):
    stripe_service.handle_payment_success(
        payment_intent_id=f'pi_test_{registration_id}', registration_id=registration_id, db=db
    )


def bought(db, response) -> models.FriendTicket:
    assert response.status_code == 201, response.text
    registration_id = response.json()['registration']['registration_id']
    db.expire_all()
    return db.query(models.FriendTicket).filter_by(buyer_registration_id=registration_id).one()


def emails_to(sent_emails, address):
    return [email for email in sent_emails if email['to'] == address]


def my_friend_ticket(client, buyer, event):
    return client.get(f'/events/{event.event_id}/my-friend-ticket', headers=auth_headers(buyer))


class TestCheckout:
    def test_buyer_pays_the_price_once_and_nothing_goes_to_the_friend_yet(
        self, client, db, buyer, duo, sent_emails, checkout
    ):
        response = buy(client, buyer, duo)

        friend_ticket = bought(db, response)
        body = response.json()
        assert body['requires_immediate_payment'] is True
        assert D(body['registration']['final_amount_euros']) == D('20.00')
        assert friend_ticket.status == 'awaiting_payment'
        assert friend_ticket.friend_email == FRIEND
        assert emails_to(sent_emails, FRIEND) == []

    def test_an_abandoned_checkout_gives_the_friend_nothing(self, client, db, buyer, duo, make_user):
        friend_ticket = bought(db, buy(client, buyer, duo))
        friend = make_user(email=FRIEND)

        preview = client.get(f'/events/{duo.event_id}/friend-ticket', params={'token': friend_ticket.token})
        claim = client.post(
            f'/events/{duo.event_id}/friend-ticket/claim',
            json={'token': friend_ticket.token}, headers=auth_headers(friend),
        )

        assert preview.json()['status'] == 'unavailable'
        assert claim.status_code == 400
        assert 'Bea Buyer' in claim.json()['detail']

    def test_email_is_stored_lowercase(self, client, db, buyer, duo):
        assert bought(db, buy(client, buyer, duo, friend_email='Friend@Example.com')).friend_email == FRIEND

    @pytest.mark.parametrize('friend_email, extra, message', [
        (None, {}, "Enter your friend's email"),
        ('BUYER@example.com', {}, 'your own email'),
        (FRIEND, {'discount_code': 'SAVE10'}, "Discount codes can't be used"),
    ])
    def test_refused(self, client, buyer, duo, friend_email, extra, message):
        response = buy(client, buyer, duo, friend_email=friend_email, **extra)

        assert response.status_code == 400
        assert message in response.json()['detail']

    def test_refused_when_the_friend_is_already_registered(self, client, buyer, duo, event, make_user, make_registration):
        make_registration(event, user=make_user(email=FRIEND), ticket_type=duo)

        response = buy(client, buyer, duo)

        assert response.status_code == 400
        assert 'already registered' in response.json()['detail']

    def test_refused_when_someone_else_already_bought_for_the_friend(self, client, buyer, duo, make_user):
        assert buy(client, make_user(), duo).status_code == 201

        response = buy(client, buyer, duo)

        assert response.status_code == 400
        assert 'already bought a ticket for friend@example.com' in response.json()['detail']

    def test_a_normal_ticket_takes_no_friend(self, client, buyer, event, make_ticket_type):
        single = make_ticket_type(event)

        response = buy(client, buyer, single)

        assert response.status_code == 400
        assert "Only a 'bring a friend' ticket" in response.json()['detail']

    def test_guest_checkout_is_refused_before_the_account_is_made(self, client, db, duo, buyer):
        response = client.post(f'/events/{duo.event_id}/register-and-create-account', json={
            'email': 'guest@example.com', 'full_name': 'Gus Guest', 'password': 'secret123',
            'ticket_type_id': duo.ticket_type_id, 'friend_email': 'guest@example.com',
        })

        assert response.status_code == 400
        assert 'your own email' in response.json()['detail']
        assert db.query(models.User).filter_by(email='guest@example.com').first() is None

    def test_guest_checkout_holds_the_friend_ticket(self, client, db, duo, buyer):
        # (buyer: any user, so the default 'attendee' role exists for the new account)
        response = client.post(f'/events/{duo.event_id}/register-and-create-account', json={
            'email': 'guest@example.com', 'full_name': 'Gus Guest', 'password': 'secret123',
            'ticket_type_id': duo.ticket_type_id, 'friend_email': FRIEND,
        })

        assert bought(db, response).status == 'awaiting_payment'


class TestSeats:
    def test_each_purchase_needs_two_seats(self, client, db, buyer, event, make_ticket_type, make_user):
        duo = make_ticket_type(event, name='Duo', price_euros=D('20'), bring_a_friend=True, capacity=3)
        assert buy(client, make_user(), duo, friend_email='first@example.com').status_code == 201

        response = buy(client, buyer, duo)

        assert response.status_code == 409
        assert 'needs two' in response.json()['detail']

    def test_unclaimed_friend_seats_count_as_taken(self, client, db, buyer, event, make_ticket_type, make_user):
        duo = make_ticket_type(event, name='Duo', price_euros=D('20'), bring_a_friend=True, capacity=2)
        assert buy(client, make_user(), duo, friend_email='first@example.com').status_code == 201

        response = buy(client, buyer, duo)

        assert response.status_code == 409
        assert 'sold out' in response.json()['detail']

    def test_a_cancelled_purchase_frees_both_seats(self, client, db, buyer, event, make_ticket_type, make_user):
        duo = make_ticket_type(event, name='Duo', price_euros=D('20'), bring_a_friend=True, capacity=2)
        first = bought(db, buy(client, make_user(), duo, friend_email='first@example.com'))
        first.buyer_registration.status = 'Cancelled'
        db.commit()

        assert buy(client, buyer, duo).status_code == 201


class TestRelease:
    def test_payment_puts_the_ticket_straight_into_an_existing_account(
        self, client, db, buyer, duo, make_user, sent_emails
    ):
        friend = make_user(email=FRIEND, full_name='Fay Friend')
        friend_ticket = bought(db, buy(client, buyer, duo))

        pay(db, friend_ticket.buyer_registration_id)

        db.expire_all()
        mine = friend_ticket.friend_registration
        assert friend_ticket.status == 'claimed'
        assert mine.user_id == friend.user_id
        assert mine.status == 'Paid'
        assert mine.final_amount_euros == D('0.00')
        assert mine.ticket_type_id == duo.ticket_type_id
        assert mine.ticket_token
        assert mine.paid_by_team_leader is True
        assert duo.tickets_sold == 2

        [email] = emails_to(sent_emails, FRIEND)
        assert email['subject'] == 'Bea Buyer got you a ticket to Spring Summit'
        assert f'/event/{duo.event_id}/ticket/{mine.registration_id}' in email['text']
        assert "It's in your Ennova account now" in email['text']

    def test_payment_emails_a_link_when_the_friend_has_no_account(self, client, db, buyer, duo, sent_emails):
        friend_ticket = bought(db, buy(client, buyer, duo))

        pay(db, friend_ticket.buyer_registration_id)

        db.expire_all()
        assert friend_ticket.status == 'sent'
        assert friend_ticket.last_emailed_at is not None
        assert duo.tickets_sold == 2
        [email] = emails_to(sent_emails, FRIEND)
        assert email['subject'] == 'Bea Buyer got you a ticket to Spring Summit'
        assert f'/event/{duo.event_id}/friend-ticket?token={friend_ticket.token}' in email['text']
        assert 'friend@example.com' in email['text']

    def test_a_free_deal_goes_out_at_checkout(self, client, db, buyer, event, make_ticket_type, sent_emails):
        free = make_ticket_type(event, name='Duo', price_euros=D('0'), bring_a_friend=True)

        friend_ticket = bought(db, buy(client, buyer, free))

        assert friend_ticket.status == 'sent'
        assert len(emails_to(sent_emails, FRIEND)) == 1

    def test_organiser_marking_it_paid_releases_it(self, client, db, buyer, duo, organiser_headers, sent_emails):
        friend_ticket = bought(db, buy(client, buyer, duo))

        response = client.post(
            f'/admin/registrations/{friend_ticket.buyer_registration_id}/mark-paid', headers=organiser_headers
        )

        assert response.status_code == 200
        db.expire_all()
        assert friend_ticket.status == 'sent'
        assert len(emails_to(sent_emails, FRIEND)) == 1

    def test_a_second_payment_notice_changes_nothing(self, client, db, buyer, duo, sent_emails):
        friend_ticket = bought(db, buy(client, buyer, duo))
        pay(db, friend_ticket.buyer_registration_id)
        pay(db, friend_ticket.buyer_registration_id)

        db.expire_all()
        assert duo.tickets_sold == 2
        assert len(emails_to(sent_emails, FRIEND)) == 1

    def test_a_failed_email_shows_and_can_be_resent(self, client, db, buyer, duo, event, sent_emails):
        friend_ticket = bought(db, buy(client, buyer, duo))
        sent_emails.fail = True
        pay(db, friend_ticket.buyer_registration_id)

        status = my_friend_ticket(client, buyer, event).json()
        assert status['status'] == 'sent'
        assert status['emailed'] is False
        assert status['can_resend'] is True

        sent_emails.fail = False
        resent = client.post(f'/events/{event.event_id}/my-friend-ticket/resend', headers=auth_headers(buyer))

        assert resent.status_code == 200
        assert resent.json()['emailed'] is True
        assert len(emails_to(sent_emails, FRIEND)) == 1

    def test_a_resend_that_fails_says_so(self, client, db, buyer, duo, event, sent_emails):
        friend_ticket = bought(db, buy(client, buyer, duo))
        sent_emails.fail = True
        pay(db, friend_ticket.buyer_registration_id)

        resent = client.post(f'/events/{event.event_id}/my-friend-ticket/resend', headers=auth_headers(buyer))

        assert resent.status_code == 502

    def test_a_friend_who_registered_on_their_own_meanwhile(
        self, client, db, buyer, duo, event, make_user, make_registration, sent_emails
    ):
        friend_ticket = bought(db, buy(client, buyer, duo))
        make_registration(event, user=make_user(email=FRIEND), ticket_type=duo)

        pay(db, friend_ticket.buyer_registration_id)

        status = my_friend_ticket(client, buyer, event).json()
        assert status['needs_new_friend'] is True
        assert status['can_resend'] is False
        assert status['can_change'] is True
        [email] = emails_to(sent_emails, 'buyer@example.com')[-1:]
        assert email['subject'] == 'Your second ticket to Spring Summit needs a new owner'


class TestClaim:
    @pytest.fixture
    def released(self, client, db, buyer, duo):
        friend_ticket = bought(db, buy(client, buyer, duo))
        pay(db, friend_ticket.buyer_registration_id)
        db.expire_all()
        return friend_ticket

    def claim(self, client, friend_ticket, user):
        return client.post(
            f'/events/{friend_ticket.event_id}/friend-ticket/claim',
            json={'token': friend_ticket.token}, headers=auth_headers(user),
        )

    def test_preview_before_logging_in(self, client, released):
        response = client.get(f'/events/{released.event_id}/friend-ticket', params={'token': released.token})

        assert response.json() | {'event_date_start': None} == {
            'event_id': released.event_id, 'event_name': 'Spring Summit', 'event_date_start': None,
            'buyer_name': 'Bea Buyer', 'friend_email': FRIEND, 'status': 'sent',
        }

    def test_friend_signs_up_and_claims(self, client, db, released, make_user, sent_emails, duo):
        friend = make_user(email=FRIEND, full_name='Fay Friend')

        response = self.claim(client, released, friend)

        assert response.status_code == 201
        db.expire_all()
        registration = db.get(models.Registration, response.json()['registration_id'])
        assert registration.user_id == friend.user_id
        assert registration.status == 'Paid'
        assert released.status == 'claimed'
        assert duo.tickets_sold == 2

        [email] = emails_to(sent_emails, 'buyer@example.com')[-1:]
        assert email['subject'] == 'Fay Friend has their ticket to Spring Summit'

    def test_claiming_twice_gives_the_same_ticket(self, client, released, make_user):
        friend = make_user(email=FRIEND)
        first = self.claim(client, released, friend).json()

        second = self.claim(client, released, friend)

        assert second.status_code == 201
        assert second.json() == first

    def test_someone_else_cant_claim_it(self, client, released, make_user):
        response = self.claim(client, released, make_user(email='stranger@example.com'))

        assert response.status_code == 403
        assert 'friend@example.com' in response.json()['detail']

    def test_after_the_friend_claims_nobody_else_can(self, client, db, released, make_user):
        self.claim(client, released, make_user(email=FRIEND))
        released.friend_email = 'other@example.com'  # as if the link had been forwarded
        db.commit()

        assert self.claim(client, released, make_user(email='other@example.com')).status_code == 409

    def test_reverted_buyer_ticket_stops_the_link(self, client, db, released, make_user, organiser_headers, duo):
        client.post(
            f'/admin/registrations/{released.buyer_registration_id}/revert-to-pending', headers=organiser_headers
        )

        db.expire_all()
        assert released.status == 'awaiting_payment'
        assert duo.tickets_sold == 0
        assert self.claim(client, released, make_user(email=FRIEND)).status_code == 400


class TestBuyerControls:
    @pytest.fixture
    def released(self, client, db, buyer, duo):
        friend_ticket = bought(db, buy(client, buyer, duo))
        pay(db, friend_ticket.buyer_registration_id)
        db.expire_all()
        return friend_ticket

    def change(self, client, buyer, event, email):
        return client.put(
            f'/events/{event.event_id}/my-friend-ticket', json={'friend_email': email}, headers=auth_headers(buyer)
        )

    def test_status(self, client, buyer, event, released):
        assert my_friend_ticket(client, buyer, event).json() == {
            'event_id': event.event_id, 'friend_email': FRIEND, 'status': 'sent', 'friend_name': None,
            'emailed': True, 'needs_new_friend': False, 'can_change': True, 'can_resend': True,
        }

    def test_nobody_else_sees_it(self, client, event, released, make_user):
        assert my_friend_ticket(client, make_user(), event).status_code == 404

    def test_changing_the_email_kills_the_old_link(self, client, db, buyer, event, released, sent_emails):
        old_token = released.token

        response = self.change(client, buyer, event, 'New.Friend@example.com')

        assert response.status_code == 200
        assert response.json()['friend_email'] == 'new.friend@example.com'
        db.expire_all()
        assert released.token != old_token
        assert client.get(f'/events/{event.event_id}/friend-ticket', params={'token': old_token}).status_code == 404
        [email] = emails_to(sent_emails, 'new.friend@example.com')
        assert released.token in email['text']

    def test_changing_to_someone_with_an_account_gives_it_to_them(
        self, client, db, buyer, event, released, make_user
    ):
        other = make_user(email='other@example.com', full_name='Otto Other')

        response = self.change(client, buyer, event, 'other@example.com')

        assert response.json()['status'] == 'claimed'
        assert response.json()['friend_name'] == 'Otto Other'
        db.expire_all()
        assert released.friend_registration.user_id == other.user_id

    def test_changing_before_payment_just_updates_it(self, client, db, buyer, duo, event, sent_emails):
        friend_ticket = bought(db, buy(client, buyer, duo))

        response = self.change(client, buyer, event, 'other@example.com')

        assert response.json()['status'] == 'awaiting_payment'
        assert emails_to(sent_emails, 'other@example.com') == []

    def test_cant_change_once_claimed(self, client, buyer, event, released, make_user):
        client.post(
            f'/events/{event.event_id}/friend-ticket/claim',
            json={'token': released.token}, headers=auth_headers(make_user(email=FRIEND)),
        )

        response = self.change(client, buyer, event, 'other@example.com')

        assert response.status_code == 400
        assert my_friend_ticket(client, buyer, event).json()['can_change'] is False

    def test_cant_change_after_the_event_starts(self, client, db, buyer, event, released):
        event.event_date_start = datetime.now(timezone.utc) - timedelta(hours=1)
        db.commit()

        response = self.change(client, buyer, event, 'other@example.com')

        assert response.status_code == 400
        assert 'started' in response.json()['detail']

    def test_change_runs_the_same_checks(self, client, buyer, event, released):
        response = self.change(client, buyer, event, 'buyer@example.com')

        assert response.status_code == 400
        assert 'your own email' in response.json()['detail']

    def test_resending_straight_away_is_refused(self, client, buyer, event, released):
        response = client.post(f'/events/{event.event_id}/my-friend-ticket/resend', headers=auth_headers(buyer))

        assert response.status_code == 429


class TestReminders:
    @pytest.fixture
    def released(self, client, db, buyer, duo):
        friend_ticket = bought(db, buy(client, buyer, duo))
        pay(db, friend_ticket.buyer_registration_id)
        db.expire_all()
        return friend_ticket

    def age(self, db, friend_ticket, days):
        friend_ticket.released_at = datetime.now(timezone.utc) - timedelta(days=days)
        db.commit()

    def test_reminded_once_after_three_days(self, db, released, sent_emails):
        self.age(db, released, 4)

        assert db_friend_tickets.send_reminders(db) == 1
        assert db_friend_tickets.send_reminders(db) == 0
        reminder = emails_to(sent_emails, FRIEND)[-1]
        assert reminder['subject'] == 'Your ticket to Spring Summit is waiting'

    def test_not_before_three_days(self, db, released):
        self.age(db, released, 2)

        assert db_friend_tickets.send_reminders(db) == 0

    def test_a_friend_who_made_an_account_gets_the_ticket_instead(self, db, released, make_user):
        friend = make_user(email=FRIEND)
        self.age(db, released, 4)

        db_friend_tickets.send_reminders(db)

        db.expire_all()
        assert released.status == 'claimed'
        assert released.friend_registration.user_id == friend.user_id

    def test_no_reminder_after_the_event_started(self, db, released, event):
        self.age(db, released, 4)
        event.event_date_start = datetime.now(timezone.utc) - timedelta(hours=1)
        db.commit()

        assert db_friend_tickets.send_reminders(db) == 0


class TestOrganiser:
    def test_attendee_list_shows_who_bought_for_whom(self, client, db, buyer, duo, make_user, organiser_headers):
        make_user(email=FRIEND, full_name='Fay Friend')
        friend_ticket = bought(db, buy(client, buyer, duo))
        pay(db, friend_ticket.buyer_registration_id)

        rows = client.get(f'/events/{duo.event_id}/registrations', headers=organiser_headers).json()

        by_email = {row['user']['email']: row for row in rows}
        assert by_email['buyer@example.com']['friend_ticket']['friend_email'] == FRIEND
        assert by_email['buyer@example.com']['friend_ticket']['status'] == 'claimed'
        assert by_email['buyer@example.com']['bought_by_name'] is None
        assert by_email[FRIEND]['bought_by_name'] == 'Bea Buyer'
        assert by_email[FRIEND]['friend_ticket'] is None

    def test_refund_goes_to_the_buyer(self, client, db, buyer, duo, make_user, organiser_headers):
        make_user(email=FRIEND)
        friend_ticket = bought(db, buy(client, buyer, duo))
        pay(db, friend_ticket.buyer_registration_id)
        db.expire_all()

        preview = client.post(f'/admin/events/{duo.event_id}/refunds/preview', headers=organiser_headers, json={
            'registration_ids': [friend_ticket.buyer_registration_id, friend_ticket.friend_registration_id],
            'mode': 'corrected_price', 'corrected_price_euros': '16.00',
        }).json()

        rows = {row['registration_id']: row for row in preview['rows']}
        assert D(rows[friend_ticket.buyer_registration_id]['refund_euros']) == D('4.00')
        assert 'Refund the buyer' in rows[friend_ticket.friend_registration_id]['skip_reason']

    def test_deleting_an_unclaimed_purchase_frees_the_friend_seat(self, client, db, buyer, duo, organiser_headers):
        friend_ticket = bought(db, buy(client, buyer, duo))
        pay(db, friend_ticket.buyer_registration_id)

        response = client.delete(
            f'/admin/registrations/{friend_ticket.buyer_registration_id}', headers=organiser_headers
        )

        assert response.status_code == 204
        db.expire_all()
        assert duo.tickets_sold == 0
        assert db.query(models.FriendTicket).count() == 0


class TestTicketTypeSettings:
    def url(self, event):
        return f'/events/{event.event_id}/ticket-types'

    def test_create(self, client, event, organiser_headers):
        response = client.post(self.url(event), headers=organiser_headers, json={
            'name': 'Duo', 'price_euros': '20.00', 'bring_a_friend': True,
        })

        assert response.status_code == 201
        assert response.json()['bring_a_friend'] is True

    @pytest.mark.parametrize('extra', [
        {'is_free_for_members': True},
        {'requires_team': True},
        {'requires_team': True, 'group_payment_mode': 'leader', 'group_size': 2, 'group_price_euros': '20'},
    ])
    def test_doesnt_mix_with_team_or_member_pricing(self, client, event, organiser_headers, extra):
        response = client.post(self.url(event), headers=organiser_headers, json={
            'name': 'Duo', 'price_euros': '20.00', 'bring_a_friend': True, **extra,
        })

        assert response.status_code == 422

    def test_update_checks_the_combination(self, client, duo, event, organiser_headers):
        response = client.put(
            f'{self.url(event)}/{duo.ticket_type_id}', headers=organiser_headers, json={'is_free_for_members': True}
        )

        assert response.status_code == 400

    def test_cant_switch_once_people_registered(self, client, duo, event, buyer, organiser_headers):
        buy(client, buyer, duo)

        response = client.put(
            f'{self.url(event)}/{duo.ticket_type_id}', headers=organiser_headers, json={'bring_a_friend': False}
        )

        assert response.status_code == 400
        assert 'Create a new ticket type' in response.json()['detail']
