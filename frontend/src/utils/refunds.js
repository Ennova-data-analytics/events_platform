// Display and eligibility rules for partial refunds in the admin attendee list.
// The backend decides what is actually refunded; these only shape the UI.

export function formatEuros(value) {
  return `€${Number(value || 0).toFixed(2)}`;
}

// What the ticket cost this person, before any donation. Mirrors
// Registration.ticket_amount_euros on the backend.
export function ticketAmount(attendee, eventPrice = 0) {
  if (attendee.custom_amount_euros !== null && attendee.custom_amount_euros !== undefined) {
    return Number(attendee.custom_amount_euros);
  }
  if (attendee.final_amount_euros !== null && attendee.final_amount_euros !== undefined) {
    return Number(attendee.final_amount_euros);
  }
  return Number(eventPrice || 0);
}

// Why someone paid a different amount than the list price, for the Paid
// column. null when they paid the normal price.
export function priceNote(attendee) {
  if (attendee.custom_amount_euros !== null && attendee.custom_amount_euros !== undefined) {
    return 'Custom price';
  }
  if (Number(attendee.discount_amount_euros) > 0) {
    return `${formatEuros(attendee.discount_amount_euros)} off with code`;
  }
  if (attendee.member_discount_applied) return 'Free for members';
  return null;
}

export function refundedAmount(attendee) {
  return Number(attendee.refunded_amount_euros || 0);
}

// Whether the attendee can be ticked for a refund. People with nothing left
// to refund are greyed out rather than refused after the fact.
export function canRefund(attendee, eventPrice = 0) {
  if (attendee.status !== 'Paid' || attendee.paid_by_team_leader) return false;
  return ticketAmount(attendee, eventPrice) - refundedAmount(attendee) > 0.004;
}

// The chip in the attendee row. null when there is nothing to show.
export function refundBadge(attendee) {
  const refunds = attendee.refunds || [];
  if (!refunds.length) return null;

  const failed = refunds.filter(r => r.status === 'failed');
  const pending = refunds.filter(r => r.status === 'pending');
  const emailMissing = refunds.some(r => r.status !== 'failed' && !r.email_sent);
  const refunded = refundedAmount(attendee);

  if (refunded > 0) {
    return {
      text: `Refunded ${formatEuros(refunded)}${pending.length ? ' (pending)' : ''}`,
      color: emailMissing || pending.length ? 'warning' : 'info',
      warning: emailMissing ? 'Refund email not sent' : null,
    };
  }
  if (failed.length) {
    return { text: 'Refund failed', color: 'error', warning: failed[failed.length - 1].failure_reason || null };
  }
  return null;
}

export const DEFAULT_REFUND_REASON =
  "We set the wrong price for this event's tickets when you bought yours, so we're refunding you the difference. Sorry for the mix-up!";

// One line for the snackbar after a batch.
export function summarizeBatch(result) {
  const parts = [`${result.refunded_count} refunded (${formatEuros(result.total_refunded_euros)})`];
  if (result.failed_count) parts.push(`${result.failed_count} failed`);
  if (result.skipped_count) parts.push(`${result.skipped_count} skipped`);
  if (result.emails_failed) parts.push(`${result.emails_failed} email(s) not sent`);
  if (result.ticket_type_price_updated) parts.push('ticket price updated');
  return parts.join(', ');
}

export function batchColor(result) {
  if (result.failed_count || result.emails_failed) return result.refunded_count ? 'warning' : 'error';
  return 'success';
}

export function newBatchId() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  // Fallback for old browsers: RFC 4122 v4 layout from Math.random.
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = (Math.random() * 16) | 0;
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16);
  });
}
