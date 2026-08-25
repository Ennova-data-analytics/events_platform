import logging
from core.config import settings
from domain.services.email_service import email_service

logger = logging.getLogger(__name__)


def _status_url(token: str) -> str:
    return f"{settings.FRONTEND_URL.rstrip('/')}/join/status/{token}"


def _shell(title: str, body_html: str) -> str:
    return f"""
    <div style="font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif; max-width: 560px; margin: 0 auto; color: #1a1a1a;">
      <h2 style="margin: 0 0 16px;">{title}</h2>
      {body_html}
      <p style="color: #888; font-size: 12px; margin-top: 28px;">Ennova Recruitment</p>
    </div>
    """


def send_application_received(*, to_email: str, to_name: str, department_name: str, status_token: str) -> bool:
    """Confirmation email with the private status-page magic link (spec §3.4.1)."""
    url = _status_url(status_token)
    body = _shell(
        "Application received 🎉",
        f"""
        <p>Hi {to_name.split(' ')[0] if to_name else 'there'},</p>
        <p>Thanks for applying to <strong>{department_name}</strong> at Ennova. Your application is in
        and our team reviews every one personally.</p>
        <p>You can track your application any time here — no account needed:</p>
        <p style="margin: 20px 0;">
          <a href="{url}" style="background:#1867c0;color:#fff;text-decoration:none;padding:10px 18px;border-radius:8px;display:inline-block;">
            View my application status
          </a>
        </p>
        <p style="color:#666;font-size:13px;">Or copy this link: {url}</p>
        """,
    )
    return email_service.send_email(
        to_email=to_email,
        to_name=to_name,
        subject="We received your Ennova application",
        html_content=body,
        text_content=f"Thanks for applying to {department_name}. Track your status: {url}",
    )


def send_interview_invite(*, to_email: str, to_name: str, department_name: str, calendly_link: str, status_token: str) -> bool:
    """Interview invitation with the department's Calendly booking link (spec §3.4.2)."""
    first = to_name.split(' ')[0] if to_name else 'there'
    body = _shell(
        "You're through to interviews! 🎉",
        f"""
        <p>Hi {first},</p>
        <p>Great news — we'd love to interview you for <strong>{department_name}</strong>. Pick a time that works for you:</p>
        <p style="margin: 20px 0;">
          <a href="{calendly_link}" style="background:#1867c0;color:#fff;text-decoration:none;padding:10px 18px;border-radius:8px;display:inline-block;">
            Book my interview
          </a>
        </p>
        <p style="color:#666;font-size:13px;">Or copy this link: {calendly_link}</p>
        <p>Track your application: <a href="{_status_url(status_token)}">status page</a>.</p>
        """,
    )
    return email_service.send_email(
        to_email=to_email, to_name=to_name,
        subject=f"Interview invitation — {department_name} at Ennova",
        html_content=body,
        text_content=f"You're invited to interview for {department_name}. Book here: {calendly_link}",
    )


def send_marketing_case(*, to_email: str, to_name: str, brief_url: str, deadline_str: str, status_token: str) -> bool:
    """Marketing case brief with a 48h deadline (spec: unique Marketing stage)."""
    first = to_name.split(' ')[0] if to_name else 'there'
    body = _shell(
        "Your Marketing case study",
        f"""
        <p>Hi {first},</p>
        <p>Nice work getting this far! The next step for Marketing is a short case study.</p>
        <p>Download the brief and submit your response by <strong>{deadline_str}</strong>:</p>
        <p style="margin: 20px 0;">
          <a href="{brief_url}" style="background:#6a1b9a;color:#fff;text-decoration:none;padding:10px 18px;border-radius:8px;display:inline-block;">
            Download the brief
          </a>
        </p>
        <p>Track your application: <a href="{_status_url(status_token)}">status page</a>.</p>
        """,
    )
    return email_service.send_email(
        to_email=to_email, to_name=to_name,
        subject="Your Ennova Marketing case study (48h)",
        html_content=body,
        text_content=f"Marketing case brief: {brief_url} — due {deadline_str}",
    )


def send_booking_confirmation(*, to_email: str, to_name: str, department_name: str,
                              when_str: str, meeting_link: str | None, ics_bytes: bytes,
                              status_token: str | None = None) -> bool:
    """Interview booking confirmation with an .ics attachment (spec §3.5)."""
    first = to_name.split(' ')[0] if to_name else 'there'
    link_html = f'<p>Join link: <a href="{meeting_link}">{meeting_link}</a></p>' if meeting_link else ''
    status_html = f'<p>Track your application: <a href="{_status_url(status_token)}">status page</a>.</p>' if status_token else ''
    body = _shell(
        "Your interview is booked ✅",
        f"""
        <p>Hi {first},</p>
        <p>Your interview for <strong>{department_name}</strong> is confirmed for <strong>{when_str}</strong>.</p>
        {link_html}
        <p>The calendar invite is attached.</p>
        {status_html}
        """,
    )
    return email_service.send_email(
        to_email=to_email, to_name=to_name,
        subject=f"Interview confirmed — {department_name} at Ennova",
        html_content=body,
        text_content=f"Your interview for {department_name} is confirmed for {when_str}.",
        attachments=[{"filename": "interview.ics", "content": ics_bytes}],
    )


def send_booking_reminder(*, to_email: str, to_name: str, department_name: str, when_str: str, meeting_link: str | None) -> bool:
    """24h-before interview reminder (spec §3.4.4)."""
    first = to_name.split(' ')[0] if to_name else 'there'
    link_html = f'<p>Join link: <a href="{meeting_link}">{meeting_link}</a></p>' if meeting_link else ''
    body = _shell(
        "Reminder: your Ennova interview is tomorrow",
        f"<p>Hi {first},</p><p>Just a reminder that your <strong>{department_name}</strong> interview is coming up on "
        f"<strong>{when_str}</strong>. Looking forward to it!</p>{link_html}",
    )
    return email_service.send_email(
        to_email=to_email, to_name=to_name,
        subject=f"Reminder: your {department_name} interview is tomorrow",
        html_content=body, text_content=f"Reminder: your {department_name} interview is on {when_str}.",
    )


def send_booking_nudge(*, to_email: str, to_name: str, department_name: str, calendly_link: str, status_token: str) -> bool:
    """Nudge for candidates invited to interview who haven't booked (spec §3.4.6)."""
    first = to_name.split(' ')[0] if to_name else 'there'
    body = _shell(
        "Don't forget to book your interview",
        f"""
        <p>Hi {first},</p>
        <p>We noticed you haven't picked an interview slot for <strong>{department_name}</strong> yet.
        Slots fill up — grab one when you get a moment:</p>
        <p style="margin: 20px 0;">
          <a href="{calendly_link}" style="background:#1867c0;color:#fff;text-decoration:none;padding:10px 18px;border-radius:8px;display:inline-block;">
            Book my interview
          </a>
        </p>
        """,
    )
    return email_service.send_email(
        to_email=to_email, to_name=to_name,
        subject=f"Reminder: book your {department_name} interview",
        html_content=body, text_content=f"Book your interview: {calendly_link}",
    )


def send_outcome(*, to_email: str, to_name: str, department_name: str, accepted: bool) -> bool:
    """Offer or (warm) rejection email (spec §3.4.5)."""
    first = to_name.split(' ')[0] if to_name else 'there'
    if accepted:
        title = "Welcome to Ennova! 🎉"
        inner = f"""
        <p>Hi {first},</p>
        <p>We're delighted to offer you a place in <strong>{department_name}</strong>. Congratulations — it was a
        genuinely strong application.</p>
        <p>We'll be in touch shortly with onboarding details. Welcome to the team!</p>
        """
        subject = f"You're in — welcome to {department_name} at Ennova"
        text = f"Congratulations! You've been accepted into {department_name} at Ennova."
    else:
        title = "An update on your application"
        inner = f"""
        <p>Hi {first},</p>
        <p>Thank you for applying to <strong>{department_name}</strong> and for the time you put into it.
        After careful consideration we won't be moving forward this time — it was a close, difficult decision.</p>
        <p>Please don't let this discourage you from applying again next cycle. We'd genuinely welcome it.</p>
        """
        subject = "Your Ennova application"
        text = f"Thank you for applying to {department_name}. Unfortunately we won't be moving forward this time."
    return email_service.send_email(
        to_email=to_email, to_name=to_name, subject=subject,
        html_content=_shell(title, inner), text_content=text,
    )
