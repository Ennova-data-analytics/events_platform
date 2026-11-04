"""Deleting a ticket type: removed if nobody registered, otherwise off sale and hidden while holders keep it."""
import secrets
from decimal import Decimal

import pytest

from domain import models
from tests.conftest import auth_headers

D = Decimal


@pytest.fixture
def event(make_event):
    return make_event()


def delete(client, headers, ticket_type):
    return client.delete(f"/events/{ticket_type.event_id}/ticket-types/{ticket_type.ticket_type_id}", headers=headers)


class TestDelete:
    def test_unsold_ticket_type_is_removed(self, client, db, organiser_headers, event, make_ticket_type):
        ticket_type = make_ticket_type(event)
        ticket_type_id = ticket_type.ticket_type_id

        response = delete(client, organiser_headers, ticket_type)

        assert response.status_code == 200
        assert response.json() == {'ticket_type_id': ticket_type_id, 'outcome': 'deleted', 'holders': 0}
        db.expire_all()
        assert db.get(models.TicketType, ticket_type_id) is None

    def test_held_ticket_type_is_hidden_and_holders_keep_it(
        self, client, db, organiser_headers, event, make_ticket_type, make_registration
    ):
        ticket_type = make_ticket_type(event, name='Early Bird', tickets_sold=1)
        paid = make_registration(event, ticket_type=ticket_type, ticket_token='tok-early')
        pending = make_registration(event, ticket_type=ticket_type, status='Pending Approval')

        response = delete(client, organiser_headers, ticket_type)

        assert response.json() == {'ticket_type_id': ticket_type.ticket_type_id, 'outcome': 'hidden', 'holders': 2}
        db.refresh(ticket_type)
        db.refresh(paid)
        db.refresh(pending)
        assert ticket_type.deleted_at is not None
        assert ticket_type.tickets_sold == 1
        assert paid.ticket_type_id == ticket_type.ticket_type_id
        assert pending.ticket_type_id == ticket_type.ticket_type_id

        ticket = client.get('/tickets/view/tok-early').json()
        assert ticket['ticket_type'] == 'Early Bird'

    def test_hidden_ticket_type_cant_be_deleted_edited_or_toggled_again(
        self, client, organiser_headers, event, make_ticket_type, make_registration
    ):
        ticket_type = make_ticket_type(event)
        make_registration(event, ticket_type=ticket_type)
        delete(client, organiser_headers, ticket_type)
        url = f"/events/{event.event_id}/ticket-types/{ticket_type.ticket_type_id}"

        assert delete(client, organiser_headers, ticket_type).status_code == 404
        assert client.put(url, json={'price_euros': '1.00'}, headers=organiser_headers).status_code == 404
        assert client.patch(f"{url}/toggle-active", headers=organiser_headers).status_code == 404
        assert client.get(url).status_code == 404

    def test_attendees_cant_delete(self, client, event, make_ticket_type, make_user):
        ticket_type = make_ticket_type(event)
        assert delete(client, auth_headers(make_user()), ticket_type).status_code == 403


class TestHiddenFromListings:
    @pytest.fixture
    def hidden(self, client, organiser_headers, event, make_ticket_type, make_registration):
        make_ticket_type(event, name='Participant', display_order=0)
        hidden = make_ticket_type(event, name='Early Bird', display_order=1)
        make_registration(event, ticket_type=hidden)
        delete(client, organiser_headers, hidden)
        return hidden

    def test_event_page(self, client, event, hidden):
        names = [tt['name'] for tt in client.get(f"/events/{event.event_id}").json()['ticket_types']]
        assert names == ['Participant']

    def test_ticket_type_list(self, client, event, hidden):
        body = client.get(f"/events/{event.event_id}/ticket-types").json()
        assert [tt['name'] for tt in body['ticket_types']] == ['Participant']
        assert body['total_count'] == 1
        assert body['deleted_ticket_types'] == []

    def test_organisers_can_ask_for_the_deleted_ones(self, client, organiser_headers, event, hidden):
        body = client.get(f"/events/{event.event_id}/ticket-types?include_deleted=true", headers=organiser_headers).json()
        [deleted] = body['deleted_ticket_types']
        assert deleted['name'] == 'Early Bird'
        assert deleted['deleted_at'] is not None
        assert [tt['name'] for tt in body['ticket_types']] == ['Participant']

    def test_nobody_else_can(self, client, event, hidden, make_user):
        anonymous = client.get(f"/events/{event.event_id}/ticket-types?include_deleted=true").json()
        attendee = client.get(f"/events/{event.event_id}/ticket-types?include_deleted=true",
                              headers=auth_headers(make_user())).json()
        assert anonymous['deleted_ticket_types'] == []
        assert attendee['deleted_ticket_types'] == []

    def test_availability_says_no_longer_available(self, client, event, hidden):
        body = client.get(f"/events/{event.event_id}/ticket-types/{hidden.ticket_type_id}/availability").json()
        assert body['available'] is False
        assert body['message'] == 'This ticket type is no longer available'

    def test_reordering_ignores_it(self, client, organiser_headers, event, hidden):
        response = client.post(f"/events/{event.event_id}/ticket-types/reorder",
                               json=[hidden.ticket_type_id], headers=organiser_headers)
        assert response.status_code == 400

    def test_duplicated_event_leaves_it_out(self, client, organiser_headers, event, hidden):
        response = client.post(f"/events/{event.event_id}/duplicate", json={}, headers=organiser_headers)
        assert response.status_code == 201, response.text
        assert [tt['name'] for tt in response.json()['ticket_types']] == ['Participant']


class TestRegistration:
    def test_cant_be_bought(self, client, organiser_headers, event, make_ticket_type, make_registration, make_user):
        hidden = make_ticket_type(event)
        make_ticket_type(event, name='Still on sale')
        make_registration(event, ticket_type=hidden)
        delete(client, organiser_headers, hidden)

        response = client.post(f"/events/{event.event_id}/register", json={'ticket_type_id': hidden.ticket_type_id},
                               headers=auth_headers(make_user()))

        assert response.status_code == 400
        assert response.json()['detail'] == 'This ticket type is no longer available'

    def test_pending_holder_can_still_be_approved_and_paid(
        self, client, db, organiser_headers, event, make_ticket_type, make_registration
    ):
        hidden = make_ticket_type(event)
        pending = make_registration(event, ticket_type=hidden, status='Pending Approval', stripe_payment_intent_id=None)
        delete(client, organiser_headers, hidden)

        approve = client.post(f"/admin/registrations/{pending.registration_id}/approve", json={}, headers=organiser_headers)
        paid = client.post(f"/admin/registrations/{pending.registration_id}/mark-paid", headers=organiser_headers)

        assert approve.status_code == 200, approve.text
        assert paid.status_code == 200, paid.text
        db.refresh(hidden)
        assert hidden.tickets_sold == 1

    def test_team_invite_paid_by_the_leader_can_still_be_claimed(
        self, client, db, organiser_headers, event, make_ticket_type, make_registration, make_user
    ):
        hidden = make_ticket_type(event, name='Team of 3', requires_team=True, group_payment_mode='leader',
                                  group_size=3, group_price_euros=D('90.00'), team_max_members=3)
        leader = make_user(full_name='Lee Leader')
        leader_reg = make_registration(event, user=leader, ticket_type=hidden, final_amount_euros=D('90.00'))
        team = models.EventTeam(event_id=event.event_id, team_name='Rockets', max_members=3,
                                created_by_user_id=leader.user_id)
        db.add(team)
        db.commit()
        db.add(models.TeamMember(team_id=team.team_id, registration_id=leader_reg.registration_id))
        invitee = make_user(email='mate@example.com')
        invite = models.TeamInvite(team_id=team.team_id, event_id=event.event_id, ticket_type_id=hidden.ticket_type_id,
                                   invited_email=invitee.email, token=secrets.token_urlsafe(16))
        db.add(invite)
        db.commit()
        delete(client, organiser_headers, hidden)

        response = client.post(f"/events/{event.event_id}/claim-invite?token={invite.token}",
                               headers=auth_headers(invitee))

        assert response.status_code == 201, response.text
        registration = response.json()['registration']
        assert registration['status'] == 'Paid'
        assert registration['paid_by_team_leader'] is True
        assert registration['ticket_type_id'] == hidden.ticket_type_id
