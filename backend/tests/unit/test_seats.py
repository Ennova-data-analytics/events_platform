from types import SimpleNamespace

from domain import models
from domain.use_cases.db_registrations import seats_needed


def registration(friend_status=None):
    friend_ticket = SimpleNamespace(status=friend_status) if friend_status else None
    return SimpleNamespace(friend_ticket=friend_ticket)


def test_only_accepted_registrations_hold_seats():
    assert models.SEAT_HOLDING_STATUSES == ('Approved', 'Paid')


def test_a_registration_needs_its_own_seat():
    assert seats_needed(registration()) == 1


def test_an_unclaimed_friend_ticket_needs_a_second_seat():
    assert seats_needed(registration('awaiting_payment')) == 2
    assert seats_needed(registration('sent')) == 2


def test_a_claimed_friend_ticket_is_counted_as_the_friends_own_registration():
    assert seats_needed(registration('claimed')) == 1


def test_seats_left_is_none_without_a_capacity():
    assert models.TicketType(capacity=None).tickets_available is None
