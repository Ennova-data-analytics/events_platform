"""
Charity events have their own donation link, /event/{id}/donate, that
organisers print as a QR code for the day of the event: whoever scans it goes
straight to paying a donation, with no account and no ticket.
"""
from decimal import Decimal
from io import BytesIO

import pytest
import stripe
from PIL import Image

from domain import models
from domain.services.stripe_service import stripe_service
from tests.conftest import auth_headers

D = Decimal
FRONTEND = 'https://events.example.invalid'


@pytest.fixture
def charity_event(make_event):
    return make_event(is_charitable=True, charity_name='Food Bank')


@pytest.fixture
def stripe_sessions(monkeypatch):
    """Stripe checkout sessions, faked. Records what each was created with."""
    created = []

    def create(**kwargs):
        created.append(kwargs)
        return type('FakeSession', (), {'id': f'cs_test_{len(created)}', 'url': f'https://checkout.test/{len(created)}'})()

    monkeypatch.setattr(stripe.checkout.Session, 'create', create)
    return created


def donate(client, event, headers=None, email='donor@example.com', amount='10.00'):
    return client.post(
        f'/events/{event.event_id}/donate',
        json={'email': email, 'amount_euros': amount},
        headers=headers or {},
    )


class TestDonatingFromTheLink:
    def test_anyone_can_donate_without_logging_in(self, client, db, charity_event, stripe_sessions):
        response = donate(client, charity_event, email='Donor@Example.com', amount='15.50')

        assert response.status_code == 201, response.text
        assert response.json()['checkout_url'] == 'https://checkout.test/1'
        donation = db.get(models.Donation, response.json()['donation_id'])
        assert donation.status == 'Pending'
        assert donation.user_id is None
        assert donation.email == 'donor@example.com'
        assert donation.amount_euros == D('15.50')
        assert stripe_sessions[0]['line_items'][0]['price_data']['unit_amount'] == 1550

    def test_stripe_sends_the_donor_back_to_the_donation_page(self, client, charity_event, stripe_sessions):
        donate(client, charity_event)

        session = stripe_sessions[0]
        assert session['success_url'] == f'{FRONTEND}/event/{charity_event.event_id}/donate?donation=success'
        assert session['cancel_url'] == f'{FRONTEND}/event/{charity_event.event_id}/donate?donation=cancelled'

    def test_a_paid_donation_shows_up_for_the_organiser(
        self, client, db, charity_event, stripe_sessions, organiser_headers, sent_emails
    ):
        donation_id = donate(client, charity_event, amount='20.00').json()['donation_id']
        stripe_service.handle_donation_payment_success(donation_id=donation_id, payment_intent_id='pi_test_d', db=db)

        listed = client.get(f'/events/{charity_event.event_id}/donations', headers=organiser_headers).json()
        assert [(d['email'], D(d['amount_euros'])) for d in listed] == [('donor@example.com', D('20.00'))]
        assert [email['to'] for email in sent_emails] == ['donor@example.com']

    def test_an_abandoned_checkout_is_not_counted(self, client, charity_event, stripe_sessions, organiser_headers):
        donate(client, charity_event)

        assert client.get(f'/events/{charity_event.event_id}/donations', headers=organiser_headers).json() == []

    def test_an_event_that_is_not_a_charity_event_refuses(self, client, make_event, stripe_sessions):
        response = donate(client, make_event(is_charitable=False))

        assert response.status_code == 400
        assert stripe_sessions == []

    def test_an_unpublished_event_is_not_found_by_the_public(self, client, make_event, stripe_sessions):
        response = donate(client, make_event(is_charitable=True, status='Draft'))

        assert response.status_code == 404
        assert stripe_sessions == []

    @pytest.mark.parametrize('amount', ['0.50', '10000.01', '5.555'])
    def test_out_of_range_amounts_are_refused(self, client, charity_event, stripe_sessions, amount):
        assert donate(client, charity_event, amount=amount).status_code == 422
        assert stripe_sessions == []

    def test_a_stripe_failure_is_reported_not_swallowed(self, client, charity_event, monkeypatch):
        def fail(**kwargs):
            raise stripe.error.APIConnectionError('Stripe is down')

        monkeypatch.setattr(stripe.checkout.Session, 'create', fail)

        response = donate(client, charity_event)

        assert response.status_code == 502
        assert response.json()['detail'] == 'Could not start the payment. Please try again.'


class TestDonationLinkForOrganisers:
    def test_organiser_gets_the_link(self, client, charity_event, organiser_headers):
        response = client.get(f'/events/{charity_event.event_id}/donate/url', headers=organiser_headers)

        assert response.status_code == 200
        assert response.json() == {'donation_url': f'{FRONTEND}/event/{charity_event.event_id}/donate'}

    def test_organiser_gets_a_printable_qr_code(self, client, charity_event, organiser_headers):
        response = client.get(f'/events/{charity_event.event_id}/donate/qr', headers=organiser_headers)

        assert response.status_code == 200
        assert response.headers['content-type'] == 'image/png'
        assert f'event_{charity_event.event_id}_donation_qr.png' in response.headers['content-disposition']
        image = Image.open(BytesIO(response.content))
        assert image.format == 'PNG'
        assert image.width >= 500  # big enough to print without going blurry

    @pytest.mark.parametrize('path', ['url', 'qr'])
    def test_not_for_an_event_that_is_not_a_charity_event(self, client, make_event, organiser_headers, path):
        event = make_event(is_charitable=False)

        response = client.get(f'/events/{event.event_id}/donate/{path}', headers=organiser_headers)

        assert response.status_code == 400
        assert 'does not accept donations' in response.json()['detail']

    @pytest.mark.parametrize('path', ['url', 'qr'])
    def test_unknown_event(self, client, organiser_headers, path):
        assert client.get(f'/events/999999/donate/{path}', headers=organiser_headers).status_code == 404

    @pytest.mark.parametrize('path', ['url', 'qr'])
    def test_attendees_and_the_public_cannot_get_it(self, client, charity_event, make_user, path):
        url = f'/events/{charity_event.event_id}/donate/{path}'

        assert client.get(url).status_code == 401
        assert client.get(url, headers=auth_headers(make_user())).status_code == 403
