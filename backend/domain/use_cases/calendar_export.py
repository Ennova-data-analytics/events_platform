from datetime import datetime, timedelta
from sqlalchemy.orm import Session 
from icalendar import Calendar, Event as ICalEvent 

from domain.models import Event, Registration, User 
from domain.exceptions import EventNotFoundException, RegistrationNotFoundException, UnauthorizedCalendarAccessException
import re 

class GenerateEventCalendarUseCase:
    """
    Use case for generating an .ics calendar file for a specific event
    """
    def __init__(self, db: Session):
        self.db = db 
    
    def execute(self, event_id: int, user: User, frontend_url: str | None = None):
        """
        Generate an .ics calendar file for the event
        Args:
            event_id: The ID of the event
            user: The authenticated user requesting the calendar export 
            frontend_url: frontend URL for event link
        Returns:
            bytes: The .ics file content as bytes
        """
        event = self.db.query(Event).filter(Event.event_id == event_id).first()
        if not event:
            raise EventNotFoundException(f"Event with ID {event_id} not found")
        
        registration = self.db.query(Registration).filter(
            Registration.event_id == event_id,
            Registration.user_id == user.user_id
        ).first()

        if not registration:
            raise RegistrationNotFoundException("You are not registered for this event")
        
        if registration.status not in ['Approved', 'Paid']:
            raise UnauthorizedCalendarAccessException("Calendar export is only available for confirmed attendees")
        
        ics_content = self._generate_ics_file(event, frontend_url)
        return ics_content
    
    def _generate_ics_file(self, event: Event, frontend_url: str | None) -> bytes:
        """
        Generate the actual .ics file content.
        Args:
            event: The Event model instance
            frontend_url: Optional base URL for frontend event link
        Returns:
            bytes: The .ics file content
        """
        cal = Calendar()
        cal.add('prodid', '-//Events Platform//Calendar Export//EN')
        cal.add('version', '2.0')
        cal.add('calscale', 'GREGORIAN')
        cal.add('method', 'PUBLISH')
        
        ical_event = ICalEvent()
        
        ical_event.add('uid', f'event-{event.event_id}@eventsplatform.com')
        
        ical_event.add('summary', event.event_name)
        ical_event.add('description', self._format_description(event.description))
        
        if event.location:
            ical_event.add('location', event.location)
        
        ical_event.add('dtstart', event.event_date_start)
        
        if event.event_date_end:
            ical_event.add('dtend', event.event_date_end)
        else:
            default_end = event.event_date_start + timedelta(hours=2)
            ical_event.add('dtend', default_end)
        
        # 
        ical_event.add('dtstamp', datetime.utcnow())
        ical_event.add('status', 'CONFIRMED')
        ical_event.add('transp', 'OPAQUE')  
        
        if frontend_url:
            event_url = f"{frontend_url}/event/{event.event_id}"
            ical_event.add('url', event_url)
        
        if event.creator and event.creator.email:
            ical_event.add('organizer', f'mailto:{event.creator.email}')
        
        cal.add_component(ical_event)
        
        return cal.to_ical()
    
    def _format_description(self, description: str | None) -> str:
        """
        Format event description for calendar export.
        Strips HTML/Markdown for plain text calendar viewers.
        Args:
            description: Raw event description
        Returns:
            str: Formatted plain text description
        """
        if not description:
            return ''
        
        text = re.sub(r'<[^>]+>', '', description)
        
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        
        text = re.sub(r'\*\*([^\*]+)\*\*', r'\1', text)
        text = re.sub(r'\*([^\*]+)\*', r'\1', text)
        
        if len(text) > 500:
            text = text[:497] + '...'
        
        return text.strip()
    
    @staticmethod
    def get_safe_filename(event_name: str) -> str:
        """
        Generate a safe filename from event name.
        Args:
            event_name: The event name
        Returns:
            str: Safe filename for .ics file
        """
        safe_name = re.sub(r'[^\w\s-]', '', event_name)
        safe_name = re.sub(r'[\s]+', '_', safe_name)
        safe_name = safe_name[:50] 
        return f"{safe_name}.ics"


