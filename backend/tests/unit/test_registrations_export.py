"""The pieces of the registrations Excel export that don't need a database."""
from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace

from openpyxl import Workbook

from domain.use_cases import registrations_export as export


def registration(status="Approved", amount="40.00", paid_by_team_leader=False):
    return SimpleNamespace(
        status=status,
        ticket_amount_euros=Decimal(amount),
        paid_by_team_leader=paid_by_team_leader,
    )


class TestPaymentLabel:
    def test_labels(self):
        assert export.payment_label(registration("Paid")) == "Paid"
        assert export.payment_label(registration("Approved")) == "Awaiting payment"
        assert export.payment_label(registration("Approved", amount="0")) == "Free"
        assert export.payment_label(registration("Pending Approval", amount="0")) == "Free"
        assert export.payment_label(registration("Pending Approval")) == ""
        assert export.payment_label(registration("Approved", paid_by_team_leader=True)) == "Paid by team leader"


def test_export_filename():
    today = datetime(2026, 11, 9)
    event = SimpleNamespace(event_name="Ennova × ESADE: Spring Summit!")
    assert export.export_filename(event, today) == "ennova-esade-spring-summit-attendees-2026-11-09.xlsx"
    assert export.export_filename(SimpleNamespace(event_name="¡¡!!"), today) == "event-attendees-2026-11-09.xlsx"


def test_form_answers():
    assert export._form_answer(None) is None
    assert export._form_answer("text") == "text"
    assert export._form_answer(3) == 3
    assert export._form_answer(False) == "No"
    assert export._form_answer(["a", "b"]) == "a, b"
    assert export._form_answer({"city": "Barcelona"}) == '{"city": "Barcelona"}'


def test_sheet_titles_follow_excel_rules():
    book = Workbook()
    assert export._sheet_title(book, "Waiting: list/2026?") == "Waiting- list-2026-"
    long = "A status name that is far too long for Excel"
    book.create_sheet(export._sheet_title(book, long))
    assert len(book.sheetnames[-1]) == 31
    second = export._sheet_title(book, long)
    assert second.endswith(" (2)") and len(second) == 31
