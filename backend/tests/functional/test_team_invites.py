"""
Leader-pays team tickets: invites are stored at checkout but only emailed once
the team lead has paid, and can't be claimed before then.
"""
from decimal import Decimal

import pytest

from domain import models
from domain.services.stripe_service import stripe_service
from tests.conftest import auth_headers

MATES = ['mate.one@example.com', 'mate.two@example.com']


@pytest.fixture(autouse=True)
def checkout(monkeypatch):
    monkeypatch.setattr(
        stripe_service, 'create_checkout_session',
        lambda registration, db: {'checkout_url': 'https://checkout.test/team'},
    )


@pytest.fixture
def team_ticket(make_event, make_ticket_type):
    event = make_event()
    return make_ticket_type(
        event, name='Team of 3', price_euros=Decimal('25'), requires_team=True,
        group_payment_mode='leader', group_size=3, group_price_euros=Decimal('60'),
    )


@pytest.fixture
def lead(make_user):
    return make_user(email='lead@example.com', full_name='Lee Lead')


@pytest.fixture
def lead_registration(client, db, lead, team_ticket):
    response = client.post(f'/events/{team_ticket.event_id}/register', headers=auth_headers(lead), json={
        'ticket_type_id': team_ticket.ticket_type_id,
        'team_selection': {'action': 'create', 'team_name': '<b>Owls</b>', 'teammate_emails': MATES},
    })
    assert response.status_code == 201, response.text
    return db.get(models.Registration, response.json()['registration']['registration_id'])


def invite_emails(sent_emails):
    return [email for email in sent_emails if email['to'] in MATES]


def pay(db, registration):
    stripe_service.handle_payment_success(
        payment_intent_id='pi_test_team', registration_id=registration.registration_id, db=db
    )


def test_invites_wait_for_the_lead_to_pay(db, lead_registration, sent_emails):
    invites = db.query(models.TeamInvite).all()

    assert sorted(invite.invited_email for invite in invites) == MATES
    assert all(invite.sent_at is None for invite in invites)
    assert invite_emails(sent_emails) == []


def test_paying_sends_the_invites(db, lead_registration, sent_emails):
    pay(db, lead_registration)

    db.expire_all()
    assert len(invite_emails(sent_emails)) == 2
    assert all(invite.sent_at is not None for invite in db.query(models.TeamInvite).all())


def test_paying_twice_doesnt_send_them_twice(db, lead_registration, sent_emails):
    pay(db, lead_registration)
    pay(db, lead_registration)

    assert len(invite_emails(sent_emails)) == 2


def test_an_invite_that_failed_to_send_is_tried_again(db, lead_registration, sent_emails):
    from domain.use_cases.db_registrations import send_pending_team_invites

    sent_emails.fail = True
    pay(db, lead_registration)
    sent_emails.fail = False
    db.expire_all()
    send_pending_team_invites(db, lead_registration)

    assert len(invite_emails(sent_emails)) == 2


def test_cant_claim_before_the_lead_pays(client, db, lead_registration, make_user):
    invite = db.query(models.TeamInvite).filter_by(invited_email=MATES[0]).one()
    mate = make_user(email=MATES[0])

    response = client.post(
        f'/events/{invite.event_id}/claim-invite', params={'token': invite.token}, headers=auth_headers(mate)
    )

    assert response.status_code == 400
    assert "hasn't paid" in response.json()['detail']


def test_claim_works_once_the_lead_has_paid(client, db, lead_registration, make_user):
    pay(db, lead_registration)
    invite = db.query(models.TeamInvite).filter_by(invited_email=MATES[0]).one()
    mate = make_user(email=MATES[0])

    response = client.post(
        f'/events/{invite.event_id}/claim-invite', params={'token': invite.token}, headers=auth_headers(mate)
    )

    assert response.status_code == 201
    assert response.json()['registration']['paid_by_team_leader'] is True


def test_invite_email_escapes_the_team_name(db, lead_registration, sent_emails):
    pay(db, lead_registration)

    html = invite_emails(sent_emails)[0]['html']
    assert '<b>Owls</b>' not in html
    assert '&lt;b&gt;Owls&lt;/b&gt;' in html
