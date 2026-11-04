"""Request validation for refund batches, and the refund email's content."""
import uuid
from decimal import Decimal

import pytest
from pydantic import ValidationError

from domain import schemas
from domain.services.email_templates import render_partial_refund_email


def batch(**overrides):
    values = {
        'batch_id': str(uuid.uuid4()),
        'registration_ids': [1, 2],
        'mode': 'fixed',
        'amount_euros': '10.00',
        'reason': 'We charged the wrong price.',
    }
    values.update(overrides)
    return schemas.RefundBatchRequest(**values)


class TestRefundBatchRequest:
    def test_valid_fixed(self):
        assert batch().amount_euros == Decimal('10.00')

    def test_valid_corrected_price_with_price_update(self):
        request = batch(mode='corrected_price', amount_euros=None, corrected_price_euros='30', update_ticket_type_price=True)
        assert request.update_ticket_type_price

    @pytest.mark.parametrize('overrides, message', [
        ({'amount_euros': None}, "amount_euros is required"),
        ({'mode': 'corrected_price'}, "corrected_price_euros is required"),
        ({'update_ticket_type_price': True}, "only applies when mode is 'corrected_price'"),
        ({'reason': '   '}, "reason must not be blank"),
        ({'registration_ids': [3, 3]}, "duplicates"),
        ({'registration_ids': []}, "at least 1"),
        ({'amount_euros': '0'}, "greater than 0"),
        ({'amount_euros': '1.234'}, "decimal places"),
        ({'mode': 'everything'}, "'fixed' or 'corrected_price'"),
    ])
    def test_rejects(self, overrides, message):
        with pytest.raises(ValidationError, match=message):
            batch(**overrides)

    def test_reason_is_required(self):
        values = {'batch_id': str(uuid.uuid4()), 'registration_ids': [1], 'mode': 'fixed', 'amount_euros': '5'}
        with pytest.raises(ValidationError, match='reason'):
            schemas.RefundBatchRequest(**values)

    def test_preview_needs_no_reason_or_batch(self):
        preview = schemas.RefundPreviewRequest(registration_ids=[1], mode='fixed', amount_euros='5')
        assert preview.amount_euros == Decimal('5')


class TestRefundEmail:
    def render(self, **overrides):
        values = {
            'user_name': 'Ada',
            'event_name': 'Spring Summit',
            'amount': 10.0,
            'reason': 'We set the price too high.\n\nSorry about that.',
            'method': 'stripe',
            'ticket_url': 'https://events.example.invalid/event/1/ticket/2',
        }
        values.update(overrides)
        return render_partial_refund_email(**values)

    def test_says_how_much_and_that_the_ticket_stands(self):
        html, text = self.render()
        for body in (html, text):
            assert '€10.00' in body
            assert 'Spring Summit' in body
            assert 'ticket is still valid' in body
            assert 'We set the price too high.' in body
        assert 'https://events.example.invalid/event/1/ticket/2' in html

    def test_card_refunds_mention_the_bank_delay(self):
        html, _ = self.render(method='stripe')
        assert 'card you paid with' in html
        assert '5–10 business days' in html

    def test_manual_refunds_say_the_organisers_pay_back(self):
        html, text = self.render(method='manual')
        assert 'organisers will return' in html
        assert 'card you paid with' not in text

    def test_organiser_text_is_escaped(self):
        html, _ = self.render(reason='<script>alert(1)</script>', user_name='<b>Ada</b>')
        assert '<script>' not in html
        assert '&lt;script&gt;' in html
        assert '<b>Ada</b>' not in html

    def test_keeps_paragraphs(self):
        html, _ = self.render()
        assert '<p>We set the price too high.</p><p>Sorry about that.</p>' in html
