"""
The amount a charity event owes its charity: ticket sales (net of refunds),
donations added on top of a ticket, and donations made on their own through
the donation page, link or QR code.
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from domain import models
from domain.use_cases import db_revenue
from tests.conftest import auth_headers

D = Decimal


@pytest.fixture
def charity_event(make_event):
    return make_event(
        is_charitable=True,
        charity_name='Food Bank',
        event_date_start=datetime(2026, 11, 20, 18, tzinfo=timezone.utc),
    )


@pytest.fixture
def make_donation(db):
    def make(event, amount='10.00', status='Paid', user=None, email='donor@example.com'):
        donation = models.Donation(
            event_id=event.event_id,
            user_id=user.user_id if user else None,
            email=email,
            amount_euros=D(amount),
            status=status,
        )
        db.add(donation)
        db.commit()
        return donation
    return make


@pytest.fixture
def make_refund(db):
    def make(registration, amount, status='succeeded'):
        refund = models.Refund(
            registration_id=registration.registration_id,
            event_id=registration.event_id,
            amount_euros=D(amount),
            reason='Wrong price',
            method='stripe',
            status=status,
            batch_id=uuid.uuid4(),
        )
        db.add(refund)
        db.commit()
        return refund
    return make


def summary(client, event, headers):
    response = client.get(f'/events/{event.event_id}/charity-summary', headers=headers)
    assert response.status_code == 200, response.text
    return {
        key: D(value) if isinstance(value, str) and key != 'charity_name' else value
        for key, value in response.json().items()
    }


class TestCharitySummary:
    def test_adds_up_tickets_ticket_donations_and_standalone_donations(
        self, client, charity_event, organiser_headers, make_registration, make_donation, make_user
    ):
        make_registration(charity_event, final_amount_euros=D('20.00'), donation_amount_euros=D('5.00'))
        make_registration(charity_event, final_amount_euros=D('20.00'))
        make_donation(charity_event, '15.00')  # anonymous, e.g. scanned the QR code
        make_donation(charity_event, '7.50', user=make_user())  # logged in, without a ticket

        result = summary(client, charity_event, organiser_headers)

        assert result['charity_name'] == 'Food Bank'
        assert result['ticket_sales'] == D('40.00')
        assert result['paid_tickets'] == 2
        assert result['ticket_donations'] == D('5.00')
        assert result['ticket_donation_count'] == 1
        assert result['standalone_donations'] == D('22.50')
        assert result['standalone_donation_count'] == 2
        assert result['total_to_donate'] == D('67.50')

    def test_refunds_come_off_ticket_sales_but_donations_stay(
        self, client, charity_event, organiser_headers, make_registration, make_refund
    ):
        reg = make_registration(charity_event, final_amount_euros=D('30.00'), donation_amount_euros=D('10.00'))
        make_refund(reg, '12.00')
        make_refund(reg, '3.00', status='failed')

        result = summary(client, charity_event, organiser_headers)

        assert result['refunds_given'] == D('12.00')
        assert result['ticket_sales'] == D('18.00')
        assert result['ticket_donations'] == D('10.00')
        assert result['total_to_donate'] == D('28.00')

    def test_money_not_yet_received_is_left_out(
        self, client, charity_event, organiser_headers, make_registration, make_donation
    ):
        make_registration(charity_event, status='Approved', final_amount_euros=D('25.00'), donation_amount_euros=D('5.00'))
        make_registration(charity_event, status='Rejected', final_amount_euros=D('25.00'))
        make_donation(charity_event, '50.00', status='Pending')  # abandoned checkout

        result = summary(client, charity_event, organiser_headers)

        assert result['total_to_donate'] == 0
        assert result['standalone_donation_count'] == 0
        assert result['awaiting_payment'] == D('25.00')

    def test_other_events_are_not_counted(
        self, client, charity_event, make_event, organiser_headers, make_registration, make_donation
    ):
        other = make_event(is_charitable=True, charity_name='Shelter')
        make_registration(other)
        make_donation(other, '99.00')
        make_registration(charity_event, final_amount_euros=D('10.00'))

        assert summary(client, charity_event, organiser_headers)['total_to_donate'] == D('10.00')

    def test_empty_event_is_all_zero(self, client, charity_event, organiser_headers):
        result = summary(client, charity_event, organiser_headers)

        assert result['total_to_donate'] == 0
        assert result['paid_tickets'] == 0
        assert result['commission_owed'] == 0

    def test_referral_commission_is_reported_not_deducted(
        self, db, client, charity_event, organiser_headers, make_registration
    ):
        link = models.ReferralLink(event_id=charity_event.event_id, code='FRIEND', referrer_name='Sam',
                                   commission_percentage=D('10'))
        db.add(link)
        db.commit()
        make_registration(charity_event, final_amount_euros=D('50.00'), referral_link_id=link.link_id)

        result = summary(client, charity_event, organiser_headers)

        assert result['commission_owed'] == D('5.00')
        assert result['total_to_donate'] == D('50.00')

    def test_matches_the_revenue_page(
        self, db, client, charity_event, organiser_headers, make_registration, make_donation, make_refund
    ):
        reg = make_registration(charity_event, final_amount_euros=D('40.00'), donation_amount_euros=D('2.50'))
        make_refund(reg, '4.00')
        make_donation(charity_event, '11.00')

        overview = db_revenue.get_revenue_overview(db, 2026, now=datetime(2027, 7, 1, tzinfo=timezone.utc))
        [row] = [r for r in overview['events'] if r['event_id'] == charity_event.event_id]

        assert summary(client, charity_event, organiser_headers)['total_to_donate'] == row['raised_for_charity']


class TestCharitySummaryAccess:
    def test_attendees_cannot_see_it(self, client, charity_event, make_user):
        response = client.get(f'/events/{charity_event.event_id}/charity-summary', headers=auth_headers(make_user()))
        assert response.status_code == 403

    def test_requires_login(self, client, charity_event):
        response = client.get(f'/events/{charity_event.event_id}/charity-summary')
        assert response.status_code == 401

    def test_not_a_charity_event(self, client, make_event, organiser_headers):
        response = client.get(f'/events/{make_event().event_id}/charity-summary', headers=organiser_headers)
        assert response.status_code == 400
        assert 'charity event' in response.json()['detail']

    def test_unknown_event(self, client, organiser_headers):
        response = client.get('/events/999999/charity-summary', headers=organiser_headers)
        assert response.status_code == 404
