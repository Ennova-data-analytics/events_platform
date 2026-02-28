from fastapi import APIRouter, Depends, status, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from io import BytesIO
import logging

from domain import models, schemas
from domain.use_cases import db_tickets
from domain.services.email_service import email_service
from domain.services.email_templates import render_guest_ticket_email
from api import deps
from core.config import settings
from core.qr_service import generate_ticket_qr_png

logger = logging.getLogger(__name__)

router = APIRouter()



def _build_ticket_pdf(event: models.Event, attendee_name: str, token: str, ticket_type: str | None) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib.colors import HexColor, white
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    from PIL import Image as PILImage

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
    )

    DARK = HexColor('#13182e')
    GREY = HexColor('#9e9e9e')

    styles = getSampleStyleSheet()

    def style(name, **kwargs):
        base = ParagraphStyle(name, parent=styles['Normal'], **kwargs)
        return base

    label_style = style('label', fontSize=8, textColor=GREY, spaceAfter=2, leading=10)
    value_style = style('value', fontSize=13, textColor=DARK, fontName='Helvetica-Bold', spaceAfter=0, leading=16)
    header_label_style = style('hlabel', fontSize=9, textColor=white, spaceAfter=4, leading=11)
    header_title_style = style('htitle', fontSize=22, textColor=white, fontName='Helvetica-Bold', leading=26)

    def detail(label, value):
        return [Paragraph(label.upper(), label_style), Paragraph(str(value), value_style)]

    event_date = event.event_date_start.strftime('%A, %d %B %Y')
    event_time = event.event_date_start.strftime('%H:%M')
    if event.event_date_end:
        event_time += f" – {event.event_date_end.strftime('%H:%M')}"

    qr_buf = generate_ticket_qr_png(token, settings.FRONTEND_URL, box_size=8)
    pil_img = PILImage.open(qr_buf)
    qr_img_buf = BytesIO()
    pil_img.save(qr_img_buf, format='PNG')
    qr_img_buf.seek(0)
    qr_img = RLImage(qr_img_buf, width=4*cm, height=4*cm)

    header_content = [
        Paragraph('ENTRANCE TICKET', header_label_style),
        Spacer(1, 4),
        Paragraph(event.event_name, header_title_style),
    ]
    if ticket_type == 'Guest':
        header_content.append(Spacer(1, 4))
        header_content.append(Paragraph('GUEST', style('guest_badge', fontSize=9, textColor=white)))

    header_table = Table([[header_content]], colWidths=[doc.width])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), DARK),
        ('TOPPADDING', (0, 0), (-1, -1), 20),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 20),
        ('LEFTPADDING', (0, 0), (-1, -1), 20),
        ('RIGHTPADDING', (0, 0), (-1, -1), 20),
        ('ROUNDEDCORNERS', [8]),
    ]))

    # Details + QR side by side
    left_details = []
    for lbl, val in [
        ('Attendee', attendee_name),
        ('Date', event_date),
        ('Time', event_time),
        ('Location', event.location or '—'),
        ('Ticket Type', ticket_type or 'General'),
    ]:
        left_details += detail(lbl, val)
        left_details.append(Spacer(1, 8))

    body_table = Table(
        [[left_details, qr_img]],
        colWidths=[doc.width - 5*cm, 5*cm],
    )
    body_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('BACKGROUND', (0, 0), (-1, -1), white),
        ('TOPPADDING', (0, 0), (-1, -1), 20),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 20),
        ('LEFTPADDING', (0, 0), (-1, -1), 20),
        ('RIGHTPADDING', (0, 0), (-1, -1), 20),
    ]))

    # Token URL footer
    ticket_url = f"{settings.FRONTEND_URL}/ticket/{token}"
    footer = Paragraph(ticket_url, style('footer', fontSize=8, textColor=GREY, alignment=TA_CENTER))

    story = [
        header_table,
        Spacer(1, 0.3*cm),
        body_table,
        Spacer(1, 0.3*cm),
        footer,
    ]
    doc.build(story)
    return buf.getvalue()


def _pdf_response(pdf_bytes: bytes, event_name: str) -> StreamingResponse:
    safe_name = event_name.replace(' ', '_')[:50]
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="ticket-{safe_name}.pdf"'},
    )




@router.get("/tickets/my/{registration_id}", response_model=schemas.TicketInfo)
def get_my_ticket_info(
    registration_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """Return ticket metadata for the current user's registration."""
    reg = db_tickets.get_registration_for_user(db, registration_id, current_user.user_id)
    return db_tickets.ticket_info_from_registration(reg)


@router.get("/tickets/my/{registration_id}/qr")
def get_my_ticket_qr(
    registration_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """Return QR code PNG for the current user's registration."""
    reg = db_tickets.get_registration_for_user(db, registration_id, current_user.user_id)
    buf = generate_ticket_qr_png(reg.ticket_token, settings.FRONTEND_URL)
    return StreamingResponse(buf, media_type="image/png", headers={"Cache-Control": "no-store"})


@router.get("/tickets/my/{registration_id}/pdf")
def download_my_ticket_pdf(
    registration_id: int,
    db: Session = Depends(deps.get_db),
    current_user: models.User = Depends(deps.get_current_user),
):
    """Download PDF ticket for the current user's registration."""
    reg = db_tickets.get_registration_for_user(db, registration_id, current_user.user_id)
    ticket_type = reg.ticket_type.name if reg.ticket_type else None
    pdf = _build_ticket_pdf(reg.event, current_user.full_name or current_user.email, reg.ticket_token, ticket_type)
    return _pdf_response(pdf, reg.event.event_name)




@router.get("/tickets/view/{token}", response_model=schemas.TicketInfo)
def get_ticket_by_token(token: str, db: Session = Depends(deps.get_db)):
    """Public — return ticket info for any valid token (guest or registered user)."""
    return db_tickets.get_ticket_by_token(db, token)


@router.get("/tickets/view/{token}/qr")
def get_ticket_qr_by_token(token: str, db: Session = Depends(deps.get_db)):
    """Public — return QR PNG for any valid token."""
    db_tickets.get_ticket_by_token(db, token)
    buf = generate_ticket_qr_png(token, settings.FRONTEND_URL)
    return StreamingResponse(buf, media_type="image/png", headers={"Cache-Control": "no-store"})


@router.get("/tickets/view/{token}/pdf")
def get_ticket_pdf_by_token(token: str, db: Session = Depends(deps.get_db)):
    """Public — download PDF ticket for any valid token."""
    info = db_tickets.get_ticket_by_token(db, token)

    reg = db_tickets.get_registration_by_token(db, token)
    if reg:
        pdf = _build_ticket_pdf(reg.event, info.attendee_name, token, info.ticket_type)
        return _pdf_response(pdf, reg.event.event_name)

    guest = db_tickets.get_guest_by_token(db, token)
    pdf = _build_ticket_pdf(guest.event, info.attendee_name, token, "Guest")
    return _pdf_response(pdf, guest.event.event_name)



@router.post("/tickets/check-in/{token}", response_model=schemas.TicketCheckInResponse)
def check_in_ticket(
    token: str,
    db: Session = Depends(deps.get_db),
    current_organiser: models.User = Depends(deps.get_current_active_organiser),
):
    """Scan and check-in a ticket. Marks as used and returns attendee details."""
    return db_tickets.check_in_by_token(db, token)



@router.post("/admin/events/{event_id}/guest-tickets", response_model=schemas.GuestTicketResponse, status_code=status.HTTP_201_CREATED)
def create_guest_ticket(
    event_id: int,
    data: schemas.GuestTicketCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(deps.get_db),
    current_organiser: models.User = Depends(deps.get_current_active_organiser),
):
    """Create a guest ticket and send the ticket link by email."""
    guest = db_tickets.create_guest_ticket(
        db=db,
        event_id=event_id,
        guest_name=data.guest_name,
        guest_email=data.guest_email,
        created_by_user_id=current_organiser.user_id,
    )
    background_tasks.add_task(
        _send_guest_ticket_email,
        guest_name=guest.guest_name,
        guest_email=guest.guest_email,
        event=guest.event,
        token=guest.ticket_token,
    )
    return guest


@router.get("/admin/events/{event_id}/guest-tickets", response_model=list[schemas.GuestTicketResponse])
def list_guest_tickets(
    event_id: int,
    db: Session = Depends(deps.get_db),
    current_organiser: models.User = Depends(deps.get_current_active_organiser),
):
    """List all guest tickets for an event."""
    return db_tickets.list_guest_tickets(db, event_id)


@router.delete("/admin/guest-tickets/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_guest_ticket(
    ticket_id: int,
    db: Session = Depends(deps.get_db),
    current_organiser: models.User = Depends(deps.get_current_active_organiser),
):
    """Delete a guest ticket."""
    db_tickets.delete_guest_ticket(db, ticket_id)


@router.post("/admin/guest-tickets/{ticket_id}/resend", status_code=status.HTTP_204_NO_CONTENT)
def resend_guest_ticket_email(
    ticket_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(deps.get_db),
    current_organiser: models.User = Depends(deps.get_current_active_organiser),
):
    """Resend the ticket invitation email to a guest."""
    guest = db_tickets.get_guest_by_id(db, ticket_id)
    background_tasks.add_task(
        _send_guest_ticket_email,
        guest_name=guest.guest_name,
        guest_email=guest.guest_email,
        event=guest.event,
        token=guest.ticket_token,
    )



@router.post("/admin/events/{event_id}/sessions/freeze", response_model=schemas.AttendanceSessionResponse, status_code=status.HTTP_201_CREATED)
def freeze_attendance_session(
    event_id: int,
    data: schemas.FreezeSessionRequest,
    db: Session = Depends(deps.get_db),
    current_organiser: models.User = Depends(deps.get_current_active_organiser),
):
    """Freeze the current check-in state as a named session and reset all tickets for a new session."""
    return db_tickets.freeze_session(db, event_id, data.label)


@router.get("/admin/events/{event_id}/sessions", response_model=list[schemas.AttendanceSessionResponse])
def list_attendance_sessions(
    event_id: int,
    db: Session = Depends(deps.get_db),
    current_organiser: models.User = Depends(deps.get_current_active_organiser),
):
    """List all frozen sessions for an event."""
    return db_tickets.list_sessions(db, event_id)


@router.get("/admin/sessions/{session_id}/records", response_model=list[schemas.AttendanceRecordResponse])
def get_session_records(
    session_id: int,
    db: Session = Depends(deps.get_db),
    current_organiser: models.User = Depends(deps.get_current_active_organiser),
):
    """Get the per-attendee snapshot for a specific session."""
    return db_tickets.get_session_records(db, session_id)



def _send_guest_ticket_email(guest_name: str, guest_email: str, event: models.Event, token: str):
    event_date = event.event_date_start.strftime('%A, %d %B %Y')
    html_content, text_content = render_guest_ticket_email(
        guest_name=guest_name,
        event_name=event.event_name,
        event_date=event_date,
        event_location=event.location,
    )
    pdf_bytes = _build_ticket_pdf(event, guest_name, token, "Guest")
    safe_name = event.event_name.replace(' ', '_')[:40]
    email_service.send_email(
        to_email=guest_email,
        to_name=guest_name,
        subject=f"Your ticket for {event.event_name}",
        html_content=html_content,
        text_content=text_content,
        attachments=[{"filename": f"ticket-{safe_name}.pdf", "content": pdf_bytes}],
    )