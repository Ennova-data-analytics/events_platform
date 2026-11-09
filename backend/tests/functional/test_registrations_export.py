"""Downloading an event's registrations as an Excel workbook."""
from datetime import datetime, timezone
from decimal import Decimal
from io import BytesIO

from openpyxl import load_workbook

from domain import models
from tests.conftest import auth_headers


def export(client, event, headers):
    return client.get(f"/events/{event.event_id}/registrations/export", headers=headers)


def open_workbook(response):
    return load_workbook(BytesIO(response.content))


def rows(sheet):
    """Each data row as {header: value}."""
    values = list(sheet.values)
    headers = values[0]
    return [dict(zip(headers, row)) for row in values[1:]]


class TestAccess:
    def test_event_creator_can_export(self, client, make_event, organiser_headers):
        r = export(client, make_event(event_name="Spring Summit 2027!"), organiser_headers)

        assert r.status_code == 200, r.text
        assert r.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        assert 'filename="spring-summit-2027-attendees-' in r.headers["content-disposition"]

    def test_other_organisers_cannot(self, client, make_event, make_user):
        other = make_user(email="other-organiser@example.com", roles=("organiser",))
        r = export(client, make_event(), auth_headers(other))
        assert r.status_code == 403
        assert r.json()["detail"] == "You don't have permission to export this event's attendees"

    def test_super_admin_can(self, client, make_event, make_user):
        admin = make_user(email="admin@example.com", roles=("organiser", "super_admin"))
        assert export(client, make_event(), auth_headers(admin)).status_code == 200

    def test_attendees_cannot(self, client, make_event, make_user):
        assert export(client, make_event(), auth_headers(make_user())).status_code == 403

    def test_unknown_event(self, client, organiser_headers):
        r = client.get("/events/999999/registrations/export", headers=organiser_headers)
        assert r.status_code == 404


class TestWorkbook:
    def test_one_sheet_per_status_plus_all(self, client, make_event, make_registration, make_user, organiser_headers):
        event = make_event()
        make_registration(event, user=make_user(full_name="Pat Pending"), status="Pending Approval")
        make_registration(event, user=make_user(full_name="Avery Approved"), status="Approved")
        make_registration(event, user=make_user(full_name="Paula Paid"), status="Paid", paid_at=datetime.now(timezone.utc))
        make_registration(event, user=make_user(full_name="Rex Rejected"), status="Rejected")
        make_registration(event, user=make_user(full_name="Cleo Cancelled"), status="Cancelled")

        book = open_workbook(export(client, event, organiser_headers))

        assert book.sheetnames == ["All", "Pending Approval", "Approved", "Paid", "Rejected", "Cancelled"]
        assert len(rows(book["All"])) == 5
        assert [r["Full Name"] for r in rows(book["Paid"])] == ["Paula Paid"]
        assert [r["Full Name"] for r in rows(book["Pending Approval"])] == ["Pat Pending"]

    def test_empty_event_still_has_every_main_sheet(self, client, make_event, organiser_headers):
        book = open_workbook(export(client, make_event(), organiser_headers))
        assert book.sheetnames == ["All", "Pending Approval", "Approved", "Paid", "Rejected"]
        assert rows(book["All"]) == []
        assert book["All"]["A1"].value == "Status"

    def test_row_contents(self, client, db, make_event, make_registration, make_user, make_ticket_type, organiser_headers):
        event = make_event(price_euros=Decimal("40.00"))
        ticket = make_ticket_type(event, name="Early Bird", price_euros=Decimal("25.00"))
        member = make_user(email="ana@esade.edu", full_name="Ana García", degree="BBA", study_year="2",
                           phone_number="+34 600 000 000", is_ennova_member=True)
        make_registration(
            event, user=member, ticket_type=ticket, status="Approved", final_amount_euros=Decimal("25.00"),
            registration_date=datetime(2026, 7, 1, 10, 30, tzinfo=timezone.utc),
            form_responses={"Dietary needs": "Vegetarian", "Workshops": ["AI", "Finance"], "Agree to photos": True},
        )

        row = rows(open_workbook(export(client, event, organiser_headers))["All"])[0]

        assert row["Status"] == "Approved"
        assert row["Payment"] == "Awaiting payment"
        assert (row["Full Name"], row["Email"], row["Phone"]) == ("Ana García", "ana@esade.edu", "+34 600 000 000")
        assert (row["Ennova Member"], row["Degree"], row["Year"]) == ("Yes", "BBA", "2")
        assert (row["Ticket Type"], row["Ticket Price"]) == ("Early Bird", 25)
        # Shown in the app's time zone (Madrid is UTC+2 in July), as a real date Excel can sort.
        assert row["Registered At"] == datetime(2026, 7, 1, 12, 30)
        assert (row["Paid At"], row["Checked In"]) == (None, "No")
        assert row["Dietary needs"] == "Vegetarian"
        assert row["Workshops"] == "AI, Finance"
        assert row["Agree to photos"] == "Yes"

    def test_optional_columns_only_when_used(self, client, db, make_event, make_registration, organiser_headers):
        plain = make_event()
        make_registration(plain)
        headers = list(rows(open_workbook(export(client, plain, organiser_headers))["All"])[0])
        for optional in ("Ticket Type", "Discount Code", "Donation", "Refunded", "Team", "Friend's Email"):
            assert optional not in headers

        charity = make_event(is_charitable=True, charity_name="Cruz Roja")
        registration = make_registration(charity, donation_amount_euros=Decimal("10.00"))
        team = models.EventTeam(event_id=charity.event_id, team_name="The Optimists")
        db.add(team)
        db.flush()
        db.add(models.TeamMember(team_id=team.team_id, registration_id=registration.registration_id))
        db.commit()

        row = rows(open_workbook(export(client, charity, organiser_headers))["All"])[0]
        assert (row["Donation"], row["Team"]) == (10, "The Optimists")

    def test_typed_text_is_never_a_formula(self, client, make_event, make_registration, make_user, organiser_headers):
        event = make_event()
        make_registration(
            event, user=make_user(full_name='=HYPERLINK("http://evil.example","click")'),
            form_responses={"Comments": "=1+1", "Notes": "bell\x07char"},
        )

        sheet = open_workbook(export(client, event, organiser_headers))["All"]
        row = rows(sheet)[0]

        assert row["Full Name"] == '=HYPERLINK("http://evil.example","click")'
        assert row["Comments"] == "=1+1"
        assert row["Notes"] == "bellchar"
        assert all(cell.data_type != "f" for line in sheet.iter_rows() for cell in line)

    def test_only_this_events_registrations(self, client, make_event, make_registration, make_user, organiser_headers):
        event = make_event()
        make_registration(event, user=make_user(full_name="Mine"))
        make_registration(make_event(event_name="Other"), user=make_user(full_name="Not mine"))

        names = [r["Full Name"] for r in rows(open_workbook(export(client, event, organiser_headers))["All"])]
        assert names == ["Mine"]
