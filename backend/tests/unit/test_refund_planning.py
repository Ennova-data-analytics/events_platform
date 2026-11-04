"""How much each person gets back. Pure logic on unsaved model objects: no database."""
import uuid
from decimal import Decimal

import pytest

from domain import models
from domain.use_cases.db_refunds import plan_refund, price_after_discount

D = Decimal


def registration(status='Paid', paid='40.00', refunds=(), **fields):
    reg = models.Registration(
        status=status,
        final_amount_euros=D(paid) if paid is not None else None,
        paid_by_team_leader=fields.pop('paid_by_team_leader', False),
        **fields,
    )
    reg.refunds = [
        models.Refund(amount_euros=D(amount), status=state, batch_id=uuid.uuid4())
        for amount, state in refunds
    ]
    return reg


def discount(kind, value):
    return models.DiscountCode(code='SAVE', discount_type=kind, discount_value=D(value))


class TestFixedAmount:
    def test_refunds_the_amount(self):
        plan = plan_refund(registration(), 'fixed', amount_euros=D('10'))
        assert plan.refund == D('10.00')
        assert plan.skip_reason is None

    def test_is_capped_at_what_is_left(self):
        reg = registration(refunds=[('35.00', 'succeeded')])
        plan = plan_refund(reg, 'fixed', amount_euros=D('10'))
        assert plan.refund == D('5.00')
        assert plan.already_refunded == D('35.00')

    def test_pending_refunds_count_against_what_is_left(self):
        reg = registration(refunds=[('30.00', 'pending')])
        assert plan_refund(reg, 'fixed', amount_euros=D('20')).refund == D('10.00')

    def test_failed_refunds_dont_count(self):
        reg = registration(refunds=[('30.00', 'failed')])
        assert plan_refund(reg, 'fixed', amount_euros=D('20')).refund == D('20.00')

    def test_rounds_to_cents(self):
        assert plan_refund(registration(), 'fixed', amount_euros=D('3.335')).refund == D('3.34')

    def test_custom_amount_is_what_was_paid(self):
        reg = registration(paid='40.00', custom_amount_euros=D('25.00'))
        plan = plan_refund(reg, 'fixed', amount_euros=D('30'))
        assert plan.paid == D('25.00')
        assert plan.refund == D('25.00')


class TestWhoIsSkipped:
    @pytest.mark.parametrize('status', ['Approved', 'Pending Approval', 'Rejected', 'Cancelled'])
    def test_unpaid(self, status):
        plan = plan_refund(registration(status=status), 'fixed', amount_euros=D('5'))
        assert plan.refund == 0
        assert status in plan.skip_reason

    def test_covered_by_team_leader(self):
        plan = plan_refund(registration(paid='0', paid_by_team_leader=True), 'fixed', amount_euros=D('5'))
        assert 'team leader' in plan.skip_reason

    def test_free_ticket(self):
        plan = plan_refund(registration(paid='0.00', member_discount_applied=True), 'fixed', amount_euros=D('5'))
        assert plan.skip_reason == 'Paid nothing for the ticket'

    def test_fully_refunded(self):
        reg = registration(refunds=[('40.00', 'succeeded')])
        assert plan_refund(reg, 'fixed', amount_euros=D('5')).skip_reason == 'Already fully refunded'


class TestCorrectedPrice:
    def test_refunds_the_difference(self):
        plan = plan_refund(registration(paid='40.00'), 'corrected_price', corrected_price_euros=D('30'))
        assert plan.refund == D('10.00')

    def test_takes_earlier_refunds_into_account(self):
        reg = registration(paid='40.00', refunds=[('4.00', 'succeeded')])
        assert plan_refund(reg, 'corrected_price', corrected_price_euros=D('30')).refund == D('6.00')

    def test_running_it_twice_refunds_nothing_more(self):
        reg = registration(paid='40.00', refunds=[('10.00', 'succeeded')])
        plan = plan_refund(reg, 'corrected_price', corrected_price_euros=D('30'))
        assert plan.refund == 0
        assert 'at or below the corrected price' in plan.skip_reason

    def test_paid_less_than_the_corrected_price(self):
        plan = plan_refund(registration(paid='20.00'), 'corrected_price', corrected_price_euros=D('30'))
        assert plan.refund == 0
        assert plan.skip_reason

    def test_corrected_price_of_zero_refunds_everything(self):
        assert plan_refund(registration(), 'corrected_price', corrected_price_euros=D('0')).refund == D('40.00')

    def test_percentage_code_applies_to_the_corrected_price(self):
        # Paid 40 - 25% = 30. At 32 they'd have paid 24, so 6 comes back.
        reg = registration(paid='30.00', discount_amount_euros=D('10.00'))
        reg.discount_code = discount('percentage', '25')
        assert plan_refund(reg, 'corrected_price', corrected_price_euros=D('32')).refund == D('6.00')

    def test_fixed_code_applies_to_the_corrected_price(self):
        # Paid 40 - 15 = 25. At 30 they'd have paid 15, so 10 comes back.
        reg = registration(paid='25.00', discount_amount_euros=D('15.00'))
        reg.discount_code = discount('fixed_amount', '15')
        assert plan_refund(reg, 'corrected_price', corrected_price_euros=D('30')).refund == D('10.00')

    def test_fixed_code_bigger_than_the_corrected_price(self):
        reg = registration(paid='10.00', discount_amount_euros=D('30.00'))
        reg.discount_code = discount('fixed_amount', '30')
        assert plan_refund(reg, 'corrected_price', corrected_price_euros=D('20')).refund == D('10.00')

    def test_deleted_discount_code_needs_a_fixed_amount(self):
        reg = registration(paid='30.00', discount_amount_euros=D('10.00'))
        plan = plan_refund(reg, 'corrected_price', corrected_price_euros=D('20'))
        assert 'discount code' in plan.skip_reason

    def test_custom_price_needs_a_fixed_amount(self):
        reg = registration(custom_amount_euros=D('35.00'))
        plan = plan_refund(reg, 'corrected_price', corrected_price_euros=D('20'))
        assert 'custom price' in plan.skip_reason

    def test_group_priced_ticket_needs_a_fixed_amount(self):
        reg = registration(paid='100.00')
        reg.ticket_type = models.TicketType(name='Team', group_payment_mode='leader', group_size=4)
        plan = plan_refund(reg, 'corrected_price', corrected_price_euros=D('20'))
        assert 'Group-priced' in plan.skip_reason


def test_price_after_discount_without_a_code():
    assert price_after_discount(registration(), D('12.5')) == (D('12.50'), None)


def test_method_guess_follows_the_stripe_payment():
    assert plan_refund(registration(stripe_payment_intent_id='pi_1'), 'fixed', amount_euros=D('1')).method_guess == 'stripe'
    assert plan_refund(registration(stripe_payment_intent_id=None), 'fixed', amount_euros=D('1')).method_guess == 'manual'


def test_unknown_mode_is_a_bug():
    with pytest.raises(ValueError):
        plan_refund(registration(), 'percentage', amount_euros=D('1'))
