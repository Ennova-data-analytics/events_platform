"""Members list emails without an account become Ennova members when they sign up."""
from decimal import Decimal
from io import BytesIO

import pandas as pd
import pytest

from domain import models
from tests.conftest import _role, auth_headers


@pytest.fixture(autouse=True)
def attendee_role(db):
    """Signing up gives the new account this role, so it has to exist."""
    _role(db, "attendee")
    db.commit()


def members_file(emails, column="Esade email", name="members.xlsx"):
    buffer = BytesIO()
    pd.DataFrame({column: emails, "Name": [f"Person {i}" for i in range(len(emails))]}).to_excel(buffer, index=False)
    return {"file": (name, buffer.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}


def import_members(client, headers, emails, **kwargs):
    return client.post("/admin/ennova-members/import-excel", files=members_file(emails, **kwargs), headers=headers)


def pending_emails(db):
    return sorted(p.email for p in db.query(models.PendingEnnovaMember).all())


def sign_up(client, email, password="a-good-password"):
    return client.post("/users/register", json={"email": email, "password": password, "full_name": "New Person"})


class TestImport:
    def test_unmatched_emails_are_kept_for_sign_up(self, client, db, organiser_headers, make_user):
        existing = make_user(email="existing@esade.edu")

        r = import_members(client, organiser_headers, ["existing@esade.edu", "New.Person@Esade.edu", "later@esade.edu"])

        assert r.status_code == 200, r.text
        body = r.json()
        assert (body["added_count"], body["unmatched_count"], body["pending_saved_count"]) == (1, 2, 2)
        db.refresh(existing)
        assert existing.is_ennova_member
        assert pending_emails(db) == ["later@esade.edu", "new.person@esade.edu"]
        saved = db.query(models.PendingEnnovaMember).filter_by(email="later@esade.edu").one()
        assert saved.source_filename == "members.xlsx"

    def test_reimporting_doesnt_duplicate_pending_emails(self, client, db, organiser_headers):
        import_members(client, organiser_headers, ["later@esade.edu"])
        r = import_members(client, organiser_headers, ["LATER@esade.edu", "another@esade.edu"])

        assert r.json()["pending_saved_count"] == 1
        assert pending_emails(db) == ["another@esade.edu", "later@esade.edu"]

    def test_existing_account_matches_whatever_the_case(self, client, db, organiser_headers, make_user):
        user = make_user(email="Maria.Lopez@esade.edu")

        body = import_members(client, organiser_headers, ["maria.lopez@esade.edu"]).json()

        assert (body["added_count"], body["unmatched_count"]) == (1, 0)
        db.refresh(user)
        assert user.is_ennova_member
        assert pending_emails(db) == []

    def test_missing_email_column_is_a_bad_request(self, client, organiser_headers):
        r = import_members(client, organiser_headers, ["a@esade.edu"], column="Name ")
        assert r.status_code == 400
        assert "No email column found" in r.json()["detail"]

    def test_needs_an_organiser(self, client, make_user):
        attendee = make_user()
        r = import_members(client, auth_headers(attendee), ["a@esade.edu"])
        assert r.status_code == 403


class TestSignUp:
    def test_listed_email_becomes_a_member(self, client, db, organiser_headers):
        import_members(client, organiser_headers, ["new.person@esade.edu"])

        r = sign_up(client, "New.Person@esade.edu")

        assert r.status_code == 201, r.text
        assert r.json()["is_ennova_member"] is True
        assert pending_emails(db) == []

    def test_other_emails_dont(self, client, db, organiser_headers):
        import_members(client, organiser_headers, ["new.person@esade.edu"])

        r = sign_up(client, "someone.else@esade.edu")

        assert r.json()["is_ennova_member"] is False
        assert pending_emails(db) == ["new.person@esade.edu"]

    def test_member_price_applies_when_signing_up_while_registering(self, client, db, organiser_headers, make_event, stripe_fake):
        event = make_event(price_euros=Decimal("40.00"), is_free_for_members=True)
        import_members(client, organiser_headers, ["new.person@esade.edu"])

        r = client.post(f"/events/{event.event_id}/register-and-create-account", json={
            "email": "new.person@esade.edu",
            "password": "a-good-password",
            "full_name": "New Person",
        })

        assert r.status_code in (200, 201), r.text
        body = r.json()
        assert body["user"]["is_ennova_member"] is True
        assert body["checkout_url"] is None
        assert body["registration"]["member_discount_applied"] is True


class TestManagingThePendingList:
    def test_list_and_search(self, client, organiser_headers):
        import_members(client, organiser_headers, ["ana@esade.edu", "bruno@esade.edu"])

        everyone = client.get("/admin/ennova-members/pending", headers=organiser_headers).json()
        assert everyone["total_count"] == 2
        found = client.get("/admin/ennova-members/pending?search=BRU", headers=organiser_headers).json()
        assert [p["email"] for p in found["pending"]] == ["bruno@esade.edu"]

    def test_removed_email_no_longer_becomes_a_member(self, client, db, organiser_headers):
        import_members(client, organiser_headers, ["ana@esade.edu"])
        pending_id = db.query(models.PendingEnnovaMember).one().pending_member_id

        r = client.delete(f"/admin/ennova-members/pending/{pending_id}", headers=organiser_headers)

        assert r.status_code == 200 and r.json()["email"] == "ana@esade.edu"
        assert sign_up(client, "ana@esade.edu").json()["is_ennova_member"] is False

    def test_removing_an_unknown_one_is_not_found(self, client, organiser_headers):
        r = client.delete("/admin/ennova-members/pending/999999", headers=organiser_headers)
        assert r.status_code == 404

    def test_clear_leaves_existing_members_alone(self, client, db, organiser_headers, make_user):
        member = make_user(email="member@esade.edu")
        import_members(client, organiser_headers, ["member@esade.edu", "ana@esade.edu", "bruno@esade.edu"])

        r = client.delete("/admin/ennova-members/pending", headers=organiser_headers)

        assert r.json() == {"removed_count": 2}
        assert pending_emails(db) == []
        db.refresh(member)
        assert member.is_ennova_member

    def test_needs_an_organiser(self, client, make_user):
        headers = auth_headers(make_user())
        assert client.get("/admin/ennova-members/pending", headers=headers).status_code == 403
        assert client.delete("/admin/ennova-members/pending", headers=headers).status_code == 403
