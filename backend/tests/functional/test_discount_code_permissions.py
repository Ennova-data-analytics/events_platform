"""Discount codes can be managed by the event's organiser and by any super admin, and by nobody else."""
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
def make_code(db):
    def make(event, code="SAVE10"):
        discount = models.DiscountCode(
            event_id=event.event_id, code=code, discount_type="percentage", discount_value=Decimal("10")
        )
        db.add(discount)
        db.commit()
        return discount

    return make


def create(client, headers, event, code="save 10"):
    return client.post(
        "/discount-codes",
        json={"event_id": event.event_id, "code": code, "discount_type": "percentage", "discount_value": "10"},
        headers=headers,
    )


class TestSuperAdmin:
    def test_can_create_a_code_for_an_event_they_did_not_create(self, client, db, admin_headers, event):
        response = create(client, admin_headers, event)

        assert response.status_code == 201
        assert response.json()["code"] == "SAVE10"
        assert db.query(models.DiscountCode).filter_by(event_id=event.event_id).count() == 1

    def test_can_list_update_and_delete_codes_on_any_event(self, client, db, admin_headers, event, make_code):
        discount = make_code(event)
        code_id = discount.code_id

        listed = client.get(f"/discount-codes/event/{event.event_id}", headers=admin_headers)
        assert listed.status_code == 200
        assert [c["code_id"] for c in listed.json()] == [code_id]

        updated = client.put(f"/discount-codes/{code_id}", json={"is_active": False}, headers=admin_headers)
        assert updated.status_code == 200
        assert updated.json()["is_active"] is False

        usages = client.get(f"/discount-codes/{code_id}/usages", headers=admin_headers)
        assert usages.status_code == 200
        assert usages.json()["usages"] == []

        backfilled = client.post(f"/discount-codes/{code_id}/backpopulate", headers=admin_headers)
        assert backfilled.status_code == 200
        assert backfilled.json()["matched_count"] == 0

        deleted = client.delete(f"/discount-codes/{code_id}", headers=admin_headers)
        assert deleted.status_code == 204
        db.expire_all()
        assert db.get(models.DiscountCode, code_id) is None


class TestEventOrganiser:
    def test_can_create_a_code_for_their_own_event(self, client, organiser_headers, event):
        assert create(client, organiser_headers, event).status_code == 201


class TestOtherOrganiser:
    def test_is_refused_with_a_real_403(self, client, db, other_organiser_headers, event):
        response = create(client, other_organiser_headers, event)

        assert response.status_code == 403
        assert response.json()["detail"] == "You don't have permission to create discount codes for this event"
        assert db.query(models.DiscountCode).filter_by(event_id=event.event_id).count() == 0

    def test_cannot_touch_another_organisers_codes(self, client, other_organiser_headers, event, make_code):
        code_id = make_code(event).code_id

        assert client.get(f"/discount-codes/event/{event.event_id}", headers=other_organiser_headers).status_code == 403
        assert client.put(f"/discount-codes/{code_id}", json={"is_active": False},
                          headers=other_organiser_headers).status_code == 403
        assert client.delete(f"/discount-codes/{code_id}", headers=other_organiser_headers).status_code == 403
        assert client.get(f"/discount-codes/{code_id}/usages", headers=other_organiser_headers).status_code == 403
        assert client.post(f"/discount-codes/{code_id}/backpopulate",
                           headers=other_organiser_headers).status_code == 403


class TestErrorsKeepTheirStatus:
    def test_unknown_event_is_404_not_400(self, client, admin_headers):
        response = client.post(
            "/discount-codes",
            json={"event_id": 999999, "code": "X", "discount_type": "percentage", "discount_value": "10"},
            headers=admin_headers,
        )

        assert response.status_code == 404

    def test_duplicate_code_is_400_with_a_clear_message(self, client, admin_headers, event, make_code):
        make_code(event, code="SAVE10")

        response = create(client, admin_headers, event, code="SAVE10")

        assert response.status_code == 400
        assert response.json()["detail"] == "Discount code 'SAVE10' already exists for this event"
