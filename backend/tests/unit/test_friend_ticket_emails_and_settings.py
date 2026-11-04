"""The "bring a friend" emails and ticket type rules. No database."""
import pytest
from pydantic import ValidationError

from domain import schemas
from domain.services import friend_ticket_copy as copy
from domain.services.email_templates import render_friend_ticket_email

VALUES = {
    'buyer': 'Bea Buyer', 'friend': 'Fay Friend', 'event': 'Spring Summit',
    'date': 'May 01, 2027 at 07:00 PM', 'email': 'fay@example.com',
}
ALL_EMAILS = [
    copy.FRIEND_INVITED, copy.FRIEND_ASSIGNED, copy.FRIEND_REMINDER,
    copy.BUYER_FRIEND_CLAIMED, copy.BUYER_FRIEND_ALREADY_REGISTERED,
]


@pytest.mark.parametrize('wording', ALL_EMAILS, ids=lambda wording: wording['subject'])
def test_every_email_fills_all_its_placeholders(wording):
    subject, html, text = render_friend_ticket_email(wording, VALUES, 'https://events.example.invalid/x')

    for part in (subject, html, text):
        for placeholder in ('{buyer}', '{friend}', '{event}', '{date}', '{email}'):
            assert placeholder not in part
    assert 'https://events.example.invalid/x' in text
    assert wording['button'] in html


def test_names_are_escaped():
    values = VALUES | {'buyer': '<script>alert(1)</script>'}

    subject, html, text = render_friend_ticket_email(copy.FRIEND_INVITED, values, 'https://x.invalid/?a=1&b="2"')

    assert '<script>' not in html
    assert '&lt;script&gt;' in html
    assert 'href="https://x.invalid/?a=1&amp;b=&quot;2&quot;"' in html
    # Plain text and the subject aren't HTML, so they keep the name as typed.
    assert subject.startswith('<script>')


def test_a_typo_in_the_copy_doesnt_break_the_send():
    wording = copy.FRIEND_INVITED | {'subject': 'Hi {frend}, {buyer} got you a ticket'}

    subject, _, _ = render_friend_ticket_email(wording, VALUES, 'https://x.invalid')

    assert subject == 'Hi {frend}, Bea Buyer got you a ticket'


def test_invite_wording_tells_the_friend_which_email_to_use():
    _, _, text = render_friend_ticket_email(copy.FRIEND_INVITED, VALUES, 'https://x.invalid')

    assert 'fay@example.com' in text
    assert 'already paid for' in text


class TestTicketTypeRules:
    def base(self, **fields):
        return {'name': 'Duo', 'price_euros': '20', 'bring_a_friend': True, **fields}

    def test_plain_deal_is_fine(self):
        assert schemas.TicketTypeCreate(**self.base()).bring_a_friend is True

    @pytest.mark.parametrize('fields', [
        {'is_free_for_members': True},
        {'requires_team': True},
        {'group_payment_mode': 'leader', 'group_size': 2},
    ])
    def test_doesnt_mix(self, fields):
        with pytest.raises(ValidationError, match="can't also be a team ticket"):
            schemas.TicketTypeCreate(**self.base(**fields))

    def test_conflicts_only_apply_to_the_deal(self):
        assert schemas.bring_a_friend_conflicts(False, True, 'leader', True) is False
        assert schemas.bring_a_friend_conflicts(True, False, None, False) is False


def test_friend_email_must_be_an_email():
    with pytest.raises(ValidationError):
        schemas.RegistrationCreate(ticket_type_id=1, friend_email='not-an-email')
    assert schemas.RegistrationCreate(ticket_type_id=1, friend_email='a@example.com').friend_email == 'a@example.com'
