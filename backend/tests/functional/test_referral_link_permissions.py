"""Referral links can be created, edited and deleted by the event's organiser and by any super admin."""
from decimal import Decimal

import pytest

from domain import models
from tests.conftest import auth_headers


@pytest.fixture
def event(make_event):
    return make_event()


@pytest.fixture
def admin_headers(make_user):
    return auth_headers(make_user(email="admin@example.com", roles=("super_admin",)))


@pytest.fixture
def other_organiser_headers(make_user):
    return auth_headers(make_user(email="other-organiser@example.com", roles=("organiser",)))


@pytest.fixture
def link(db, event):
    made = models.ReferralLink(event_id=event.event_id, code="FRIEND1234", referrer_name="Ann",
                               commission_percentage=Decimal("10"))
    db.add(made)
    db.commit()
    return made


def create(client, headers, event):
    return client.post("/referral-links", json={"event_id": event.event_id, "referrer_name": "Ann",
                                                "commission_percentage": "10"}, headers=headers)


class TestSuperAdmin:
    def test_can_create_a_link_for_an_event_they_did_not_create(self, client, db, admin_headers, event):
        response = create(client, admin_headers, event)

        assert response.status_code == 201
        assert response.json()["referrer_name"] == "Ann"
        assert db.query(models.ReferralLink).filter_by(event_id=event.event_id).count() == 1

    def test_can_update_and_delete_a_link_on_any_event(self, client, db, admin_headers, link):
        link_id = link.link_id

        updated = client.put(f"/referral-links/{link_id}", json={"is_active": False}, headers=admin_headers)
        assert updated.status_code == 200
        assert updated.json()["is_active"] is False

        assert client.delete(f"/referral-links/{link_id}", headers=admin_headers).status_code == 204
        db.expire_all()
        assert db.get(models.ReferralLink, link_id) is None


class TestEventOrganiser:
    def test_can_create_update_and_delete_on_their_own_event(self, client, organiser_headers, event, link):
        assert create(client, organiser_headers, event).status_code == 201
        assert client.put(f"/referral-links/{link.link_id}", json={"is_active": False},
                          headers=organiser_headers).status_code == 200
        assert client.delete(f"/referral-links/{link.link_id}", headers=organiser_headers).status_code == 204


class TestOtherOrganiser:
    def test_is_refused_and_nothing_changes(self, client, db, other_organiser_headers, event, link):
        created = create(client, other_organiser_headers, event)
        assert created.status_code == 403
        assert created.json()["detail"] == "You don't have permission to create referral links for this event"

        assert client.put(f"/referral-links/{link.link_id}", json={"is_active": False},
                          headers=other_organiser_headers).status_code == 403
        assert client.delete(f"/referral-links/{link.link_id}", headers=other_organiser_headers).status_code == 403

        db.expire_all()
        assert db.query(models.ReferralLink).filter_by(event_id=event.event_id).count() == 1
        assert db.get(models.ReferralLink, link.link_id).is_active is True
