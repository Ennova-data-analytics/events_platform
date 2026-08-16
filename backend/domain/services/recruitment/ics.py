from datetime import datetime, timedelta, timezone
from icalendar import Calendar, Event as ICalEvent


def build_interview_ics(
    *,
    application_id: int,
    department_name: str,
    starts_at: datetime,
    ends_at: datetime | None,
    candidate_name: str,
    candidate_email: str,
    interviewer_email: str | None = None,
    meeting_link: str | None = None,
) -> bytes:
    """Generate an .ics invite for an interview, sent to both parties (spec §3.5)."""
    cal = Calendar()
    cal.add("prodid", "-//Ennova Recruitment//Interview//EN")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("method", "REQUEST")

    ev = ICalEvent()
    ev.add("uid", f"interview-{application_id}@ennova-recruitment")
    ev.add("summary", f"Ennova interview — {department_name}")
    desc = f"Interview with {candidate_name} for {department_name}."
    if meeting_link:
        desc += f"\nJoin: {meeting_link}"
    ev.add("description", desc)
    if meeting_link:
        ev.add("location", meeting_link)
    ev.add("dtstart", starts_at)
    ev.add("dtend", ends_at or (starts_at + timedelta(minutes=45)))
    ev.add("dtstamp", datetime.now(timezone.utc))
    ev.add("status", "CONFIRMED")
    ev.add("transp", "OPAQUE")
    if interviewer_email:
        ev.add("organizer", f"mailto:{interviewer_email}")
    ev.add("attendee", f"mailto:{candidate_email}")

    cal.add_component(ev)
    return cal.to_ical()
