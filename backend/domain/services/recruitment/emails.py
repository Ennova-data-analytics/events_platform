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


def send_application_received(*, to_email: str, to_name: str, department_names: list[str], status_token: str) -> bool:
    """
    Confirmation email with the private status-page magic link (spec §3.4.1).

    A candidate applying to several departments files one application per
    department but gets a single email naming all of them, and a single link.
    """
    url = _status_url(status_token)
    names = [n for n in department_names if n] or ["Ennova"]
    if len(names) == 1:
        applied_to = f"<strong>{names[0]}</strong>"
        teams_note = ""
    else:
        applied_to = ", ".join(f"<strong>{n}</strong>" for n in names[:-1]) + f" and <strong>{names[-1]}</strong>"
        teams_note = (
            "<p>Each team reviews your application separately, so they may progress at "
            "different speeds. Your status page shows all of them.</p>"
        )
    body = _shell(
        "Application received 🎉",
        f"""
        <p>Hi {to_name.split(' ')[0] if to_name else 'there'},</p>
        <p>Thanks for applying to {applied_to} at Ennova. Your application is in
        and our team reviews every one personally.</p>
        {teams_note}
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
        text_content=f"Thanks for applying to {', '.join(names)}. Track your status: {url}",
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


def send_offer(*, to_email: str, to_name: str, department_name: str, deadline_str: str,
               status_token: str, other_open_departments: list[str]) -> bool:
    """
    Offer email. The candidate accepts or declines it on their status page;
    nothing is final until they do.
    """
    first = to_name.split(' ')[0] if to_name else 'there'
    url = _status_url(status_token)
    others_note = ""
    if other_open_departments:
        names = ", ".join(f"<strong>{n}</strong>" for n in other_open_departments)
        others_note = (
            f"<p>You also have applications in progress with {names}. You don't have to decide "
            f"straight away - you have until {deadline_str}. Accepting this offer closes those "
            "applications.</p>"
        )
    body = _shell(
        "You've got an offer! 🎉",
        f"""
        <p>Hi {first},</p>
        <p>We're delighted to offer you a place in <strong>{department_name}</strong>. Congratulations — it was a
        genuinely strong application.</p>
        {others_note}
        <p>Please accept or decline the offer from your status page by <strong>{deadline_str}</strong>:</p>
        <p style="margin: 20px 0;">
          <a href="{url}" style="background:#1867c0;color:#fff;text-decoration:none;padding:10px 18px;border-radius:8px;display:inline-block;">
            Respond to my offer
          </a>
        </p>
        <p style="color:#666;font-size:13px;">Or copy this link: {url}</p>
        """,
    )
    return email_service.send_email(
        to_email=to_email, to_name=to_name,
        subject=f"Your offer from {department_name} at Ennova",
        html_content=body,
        text_content=(
            f"You've got an offer from {department_name} at Ennova. "
            f"Accept or decline it by {deadline_str}: {url}"
        ),
    )


def send_offer_accepted(*, to_email: str, to_name: str, department_name: str,
                        closed_departments: list[str]) -> bool:
    """Confirmation to the candidate that their acceptance was recorded."""
    first = to_name.split(' ')[0] if to_name else 'there'
    closed_note = ""
    if closed_departments:
        names = ", ".join(f"<strong>{n}</strong>" for n in closed_departments)
        closed_note = f"<p>Your applications with {names} are now closed, and those teams have been told.</p>"
    body = _shell(
        f"Welcome to {department_name}! 🎉",
        f"""
        <p>Hi {first},</p>
        <p>You've accepted your offer from <strong>{department_name}</strong>. We can't wait to have you on the team.</p>
        {closed_note}
        <p>We'll be in touch shortly with onboarding details.</p>
        """,
    )
    return email_service.send_email(
        to_email=to_email, to_name=to_name,
        subject=f"You're in — welcome to {department_name} at Ennova",
        html_content=body,
        text_content=f"You've accepted your offer from {department_name} at Ennova. Welcome to the team!",
    )


def send_recruiter_offer_update(*, to_email: str, to_name: str, candidate_name: str,
                                department_name: str, outcome: str,
                                accepted_department: str | None = None) -> bool:
    """
    Tell a department's recruiters what happened to one of their candidates.

    outcome is 'accepted' or 'declined' (their own offer), or 'locked' (the
    candidate accepted another department's offer, so theirs is closed).
    """
    if outcome == "accepted":
        subject = f"{candidate_name} accepted the {department_name} offer"
        line = f"<strong>{candidate_name}</strong> accepted your offer for <strong>{department_name}</strong>."
    elif outcome == "declined":
        subject = f"{candidate_name} declined the {department_name} offer"
        line = f"<strong>{candidate_name}</strong> declined your offer for <strong>{department_name}</strong>."
    else:
        subject = f"{candidate_name} accepted an offer from {accepted_department}"
        line = (
            f"<strong>{candidate_name}</strong> accepted an offer from <strong>{accepted_department}</strong>, "
            f"so their {department_name} application is now locked. No further emails will go to them "
            "about it. If they had an interview booked with you, please cancel it."
        )
    body = _shell("Offer update", f"<p>Hi {to_name.split(' ')[0] if to_name else 'there'},</p><p>{line}</p>")
    return email_service.send_email(
        to_email=to_email, to_name=to_name, subject=subject,
        html_content=body, text_content=subject,
    )


def send_rejection(*, to_email: str, to_name: str, department_name: str) -> bool:
    """Warm rejection email (spec §3.4.5)."""
    first = to_name.split(' ')[0] if to_name else 'there'
    inner = f"""
    <p>Hi {first},</p>
    <p>Thank you for applying to <strong>{department_name}</strong> and for the time you put into it.
    After careful consideration we won't be moving forward this time — it was a close, difficult decision.</p>
    <p>Please don't let this discourage you from applying again next cycle. We'd genuinely welcome it.</p>
    """
    return email_service.send_email(
        to_email=to_email, to_name=to_name, subject="Your Ennova application",
        html_content=_shell("An update on your application", inner),
        text_content=f"Thank you for applying to {department_name}. Unfortunately we won't be moving forward this time.",
    )


def send_application_failure_alert(
    *,
    full_name: str | None,
    email: str | None,
    phone: str | None,
    departments: str | None,
    stage: str,
    error: str,
) -> bool:
    """
    Internal alert: a candidate tried to apply and couldn't.

    Goes to RECRUITMENT_ALERT_EMAIL so someone can reach out directly - hence
    the phone number. Silently does nothing when no alert address is
    configured, which is the expected state in local development.
    """
    to = settings.RECRUITMENT_ALERT_EMAIL
    if not to:
        logger.info("Application failure not alerted: RECRUITMENT_ALERT_EMAIL is unset")
        return False

    def _row(label: str, value: str | None) -> str:
        return (
            f'<tr><td style="padding:4px 12px 4px 0;color:#666;">{label}</td>'
            f'<td style="padding:4px 0;"><strong>{value or "-"}</strong></td></tr>'
        )

    body = _shell(
        "An application failed to submit",
        f"""
        <p>Someone tried to apply and hit an error. Their details, so you can follow up:</p>
        <table style="border-collapse:collapse;margin:16px 0;">
          {_row("Name", full_name)}
          {_row("Email", email)}
          {_row("Phone", phone)}
          {_row("Departments", departments)}
          {_row("Failed at", stage)}
        </table>
        <p style="background:#fff4f4;border-left:3px solid #d32f2f;padding:10px 14px;margin:16px 0;">
          <code style="font-size:13px;">{error}</code>
        </p>
        <p style="color:#666;font-size:13px;">
          Reported by the application form, so it covers upload failures that never reached the
          submit endpoint.
        </p>
        """,
    )
    return email_service.send_email(
        to_email=to,
        to_name="Ennova Recruitment",
        subject=f"Application failed - {full_name or email or 'unknown candidate'}",
        html_content=body,
        text_content=(
            f"Application failed at {stage}.\n"
            f"Name: {full_name or '-'}\nEmail: {email or '-'}\nPhone: {phone or '-'}\n"
            f"Departments: {departments or '-'}\nError: {error}"
        ),
    )
