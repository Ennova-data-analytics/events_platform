"""
An event's registrations as an Excel workbook: an "All" sheet, then one sheet
per status (Pending Approval, Approved, Paid, Rejected, and any other status
someone is in), with the registration form's answers as extra columns.
"""
from datetime import datetime
from decimal import Decimal
from io import BytesIO
import json
import re
from zoneinfo import ZoneInfo

from openpyxl import Workbook
from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from sqlalchemy.orm import Session, joinedload, selectinload

from core.config import settings
from domain import models

XLSX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

# Always get a sheet, even when empty, so the workbook looks the same for every event.
MAIN_STATUSES = ["Pending Approval", "Approved", "Paid", "Rejected"]

EURO_FORMAT = '"€"#,##0.00'
DATETIME_FORMAT = "yyyy-mm-dd hh:mm"
HEADER_FILL = PatternFill("solid", fgColor="DDE3EA")
MAX_COLUMN_WIDTH = 50

# Excel's sheet-name rules: at most 31 characters, none of these.
_SHEET_NAME_FORBIDDEN = re.compile(r"[\[\]:*?/\\]")


def registrations_for_export(db: Session, event_id: int) -> list[models.Registration]:
    """Everything the export reads, loaded up front, oldest registration first."""
    return (
        db.query(models.Registration)
        .options(
            joinedload(models.Registration.user),
            joinedload(models.Registration.ticket_type),
            joinedload(models.Registration.discount_code),
            selectinload(models.Registration.refunds),
            selectinload(models.Registration.friend_ticket),
            selectinload(models.Registration.received_friend_ticket)
            .joinedload(models.FriendTicket.buyer_registration)
            .joinedload(models.Registration.user),
            selectinload(models.Registration.team_membership).joinedload(models.TeamMember.team),
        )
        .filter(models.Registration.event_id == event_id)
        .order_by(models.Registration.registration_date, models.Registration.registration_id)
        .all()
    )


def payment_label(registration: models.Registration) -> str:
    """Where the registration stands on money, in the words the admin page uses."""
    if registration.paid_by_team_leader:
        return "Paid by team leader"
    if registration.status == "Paid":
        return "Paid"
    if not registration.ticket_amount_euros > 0:
        return "Free"
    if registration.status == "Approved":
        return "Awaiting payment"
    return ""


def export_filename(event: models.Event, today: datetime | None = None) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", (event.event_name or "event").lower()).strip("-") or "event"
    day = (today or datetime.now(ZoneInfo(settings.APP_TIMEZONE))).strftime("%Y-%m-%d")
    return f"{slug[:60]}-attendees-{day}.xlsx"


def build_registrations_workbook(event: models.Event, registrations: list[models.Registration]) -> bytes:
    tz = ZoneInfo(settings.APP_TIMEZONE)
    columns = _columns(event, registrations, tz)

    workbook = Workbook()
    workbook.remove(workbook.active)

    _write_sheet(workbook, "All", columns, registrations)
    present = list(dict.fromkeys(r.status for r in registrations))
    for status in MAIN_STATUSES + [s for s in present if s not in MAIN_STATUSES]:
        _write_sheet(workbook, status, columns, [r for r in registrations if r.status == status])

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


# --- columns ------------------------------------------------------------------

def _columns(event, registrations, tz):
    """(header, value-of-registration, number format) for each column, in order.
    Optional columns only appear when some registration uses them."""

    def yes_no(value):
        return "Yes" if value else "No"

    def local(moment):
        # Excel has no time zones: show the time as the admin page does.
        return moment.astimezone(tz).replace(tzinfo=None) if moment else None

    columns = [
        ("Status", lambda r: r.status, None),
        ("Payment", payment_label, None),
        ("Full Name", lambda r: r.user.full_name, None),
        ("Email", lambda r: r.user.email, None),
        ("Phone", lambda r: r.user.phone_number, None),
        ("Ennova Member", lambda r: yes_no(r.user.is_ennova_member), None),
        ("Degree", lambda r: r.user.degree, None),
        ("Year", lambda r: r.user.study_year, None),
    ]
    if any(r.ticket_type for r in registrations):
        columns.append(("Ticket Type", lambda r: r.ticket_type.name if r.ticket_type else None, None))
    columns.append(("Ticket Price", lambda r: r.ticket_amount_euros, EURO_FORMAT))
    if any(r.discount_code for r in registrations):
        columns.append(("Discount Code", lambda r: r.discount_code.code if r.discount_code else None, None))
    if any(r.member_discount_applied for r in registrations):
        columns.append(("Member Price Applied", lambda r: yes_no(r.member_discount_applied), None))
    if event.is_charitable:
        columns.append(("Donation", lambda r: r.donation_amount_euros or Decimal("0"), EURO_FORMAT))
    if any(r.refunds for r in registrations):
        columns.append(("Refunded", lambda r: r.refunded_amount_euros, EURO_FORMAT))
    if any(r.team_membership for r in registrations):
        columns.append(("Team", lambda r: r.team_membership.team.team_name if r.team_membership else None, None))
    if any(r.friend_ticket for r in registrations):
        columns.append(("Friend's Email", lambda r: r.friend_ticket.friend_email if r.friend_ticket else None, None))
    if any(r.received_friend_ticket for r in registrations):
        columns.append(("Ticket Bought By", lambda r: r.bought_by_name, None))
    columns += [
        ("Registered At", lambda r: local(r.registration_date), DATETIME_FORMAT),
        ("Paid At", lambda r: local(r.paid_at), DATETIME_FORMAT),
        ("Checked In", lambda r: yes_no(r.checked_in), None),
        ("Checked In At", lambda r: local(r.checked_in_at), DATETIME_FORMAT),
    ]

    # One column per form question, in the order they were first answered.
    questions = list(dict.fromkeys(q for r in registrations for q in (r.form_responses or {})))
    taken = {header for header, _, _ in columns}
    for question in questions:
        header = question if question not in taken else f"Form: {question}"
        columns.append((header, lambda r, q=question: _form_answer((r.form_responses or {}).get(q)), None))
    return columns


def _form_answer(value):
    if value is None or isinstance(value, (int, float, str)) and not isinstance(value, bool):
        return value
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return json.dumps(value, ensure_ascii=False)


# --- writing ------------------------------------------------------------------

def _write_sheet(workbook, title, columns, registrations):
    sheet = workbook.create_sheet(_sheet_title(workbook, title))
    sheet.append([header for header, _, _ in columns])
    for cell in sheet[1]:
        cell.font = Font(bold=True)
        cell.fill = HEADER_FILL

    widths = [len(header) for header, _, _ in columns]
    for row_number, registration in enumerate(registrations, start=2):
        for index, (_, value_of, number_format) in enumerate(columns):
            value = value_of(registration)
            cell = sheet.cell(row=row_number, column=index + 1, value=_safe(value))
            if isinstance(value, str):
                # Attendee-typed text starting with "=" would otherwise be saved as a formula.
                cell.data_type = "s"
            if number_format and value is not None:
                cell.number_format = number_format
            widths[index] = max(widths[index], len(str(value)) if value is not None else 0)

    for index, width in enumerate(widths, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = min(width + 2, MAX_COLUMN_WIDTH)
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions


def _safe(value):
    if isinstance(value, str):
        return ILLEGAL_CHARACTERS_RE.sub("", value)
    if isinstance(value, Decimal):
        return float(value)
    return value


def _sheet_title(workbook, title):
    base = _SHEET_NAME_FORBIDDEN.sub("-", title)[:31] or "Sheet"
    name, n = base, 2
    while name in workbook.sheetnames:
        suffix = f" ({n})"
        name, n = base[: 31 - len(suffix)] + suffix, n + 1
    return name
