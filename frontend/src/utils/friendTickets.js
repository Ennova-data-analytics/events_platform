// Display rules for the "bring a friend" deal. The backend decides who gets
// a ticket; these only shape what people see.
import { BRING_A_FRIEND as COPY } from '@/content/bringAFriend.js';

export function isBringAFriend(ticketType) {
  return !!ticketType?.bring_a_friend;
}

// The deal's price for both, and what that works out to per person.
export function dealPrices(ticketType) {
  const total = Number(ticketType?.price_euros || 0);
  return { total: total.toFixed(2), each: (total / 2).toFixed(2) };
}

export function dealLabel(ticketType) {
  const { total, each } = dealPrices(ticketType);
  return COPY.dealLabel(total, each);
}

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

// What's wrong with the friend's email, or null. The backend checks again
// (and also whether that person already has a ticket).
export function friendEmailError(email, buyerEmail) {
  const value = (email || '').trim().toLowerCase();
  if (!value) return COPY.friendFieldMissing;
  if (!EMAIL_PATTERN.test(value)) return COPY.friendFieldInvalid;
  if (buyerEmail && value === buyerEmail.trim().toLowerCase()) return COPY.friendFieldIsYou;
  return null;
}

// The line on the buyer's card, and its colour.
export function friendTicketMessage(friendTicket) {
  if (friendTicket.status === 'claimed') {
    return { text: COPY.statusClaimed(friendTicket.friend_name || friendTicket.friend_email), color: 'success' };
  }
  if (friendTicket.needs_new_friend) {
    return { text: COPY.statusNeedsNewFriend(friendTicket.friend_email), color: 'warning' };
  }
  if (friendTicket.status === 'awaiting_payment') {
    // Paid but not released means the release failed: can_resend says so.
    return friendTicket.can_resend
      ? { text: COPY.statusNotSent, color: 'error' }
      : { text: COPY.statusAwaitingPayment, color: 'info' };
  }
  if (!friendTicket.emailed) return { text: COPY.statusNotSent, color: 'error' };
  return { text: COPY.statusSent(friendTicket.friend_email), color: 'info' };
}

// The message from a failed API call. FastAPI sends a string for errors the
// app raises and a list for validation errors.
export function apiErrorMessage(error, fallback) {
  const detail = error?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && detail.length) return detail.map(d => d.msg).filter(Boolean).join('. ') || fallback;
  return fallback;
}
