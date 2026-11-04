import { describe, expect, it } from 'vitest';
import { batchColor, canRefund, newBatchId, refundBadge, summarizeBatch, ticketAmount } from './refunds.js';

const paid = (fields = {}) => ({ status: 'Paid', final_amount_euros: '40.00', refunded_amount_euros: '0.00', refunds: [], ...fields });

describe('ticketAmount', () => {
  it('prefers a custom amount, then the final amount, then the event price', () => {
    expect(ticketAmount({ custom_amount_euros: 25, final_amount_euros: '40.00' })).toBe(25);
    expect(ticketAmount({ final_amount_euros: '40.00' })).toBe(40);
    expect(ticketAmount({}, '12.50')).toBe(12.5);
  });

  it('treats a custom amount of 0 as free, not missing', () => {
    expect(ticketAmount({ custom_amount_euros: 0, final_amount_euros: '40.00' })).toBe(0);
  });
});

describe('canRefund', () => {
  it('allows paid tickets with money left to refund', () => {
    expect(canRefund(paid())).toBe(true);
    expect(canRefund(paid({ refunded_amount_euros: '39.99' }))).toBe(true);
  });

  it.each([
    ['unpaid', { status: 'Approved' }],
    ['covered by the team leader', { paid_by_team_leader: true, final_amount_euros: '0' }],
    ['free', { final_amount_euros: '0.00' }],
    ['fully refunded', { refunded_amount_euros: '40.00' }],
  ])('refuses tickets that are %s', (_, fields) => {
    expect(canRefund(paid(fields))).toBe(false);
  });
});

describe('refundBadge', () => {
  it('is empty without refunds', () => {
    expect(refundBadge(paid())).toBeNull();
  });

  it('shows the amount refunded', () => {
    const badge = refundBadge(paid({
      refunded_amount_euros: '10.00',
      refunds: [{ status: 'succeeded', email_sent: true }],
    }));
    expect(badge).toEqual({ text: 'Refunded €10.00', color: 'info', warning: null });
  });

  it('warns when the email did not go out or the refund is pending', () => {
    const noEmail = refundBadge(paid({ refunded_amount_euros: '10', refunds: [{ status: 'succeeded', email_sent: false }] }));
    expect(noEmail.color).toBe('warning');
    expect(noEmail.warning).toBe('Refund email not sent');

    const pending = refundBadge(paid({ refunded_amount_euros: '10', refunds: [{ status: 'pending', email_sent: true }] }));
    expect(pending.text).toBe('Refunded €10.00 (pending)');
  });

  it('flags a failed refund with its reason', () => {
    const badge = refundBadge(paid({ refunds: [{ status: 'failed', email_sent: false, failure_reason: 'Card expired' }] }));
    expect(badge).toEqual({ text: 'Refund failed', color: 'error', warning: 'Card expired' });
  });
});

describe('summarizeBatch', () => {
  it('lists what happened', () => {
    const result = {
      refunded_count: 3, total_refunded_euros: '30.00', failed_count: 1, skipped_count: 2,
      emails_failed: 1, ticket_type_price_updated: true,
    };
    expect(summarizeBatch(result)).toBe(
      '3 refunded (€30.00), 1 failed, 2 skipped, 1 email(s) not sent, ticket price updated'
    );
    expect(batchColor(result)).toBe('warning');
  });

  it('is green only when nothing went wrong', () => {
    const clean = { refunded_count: 2, total_refunded_euros: '20', failed_count: 0, skipped_count: 1, emails_failed: 0 };
    expect(summarizeBatch(clean)).toBe('2 refunded (€20.00), 1 skipped');
    expect(batchColor(clean)).toBe('success');
    expect(batchColor({ ...clean, refunded_count: 0, failed_count: 2 })).toBe('error');
  });
});

describe('newBatchId', () => {
  it('makes a distinct UUID each time', () => {
    const a = newBatchId();
    expect(a).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
    expect(newBatchId()).not.toBe(a);
  });
});
