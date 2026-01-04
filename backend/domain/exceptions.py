class EventNotFoundException(Exception):
    """Raised when an event is not found"""
    pass


class RegistrationNotFoundException(Exception):
    """Raised when a registration is not found"""
    pass


class UnauthorizedCalendarAccessException(Exception):
    """Raised when user attempts to access calendar without proper status"""
    pass