// Mirrors Registration.ticket_amount_euros / has_valid_ticket on the backend.

// What the ticket costs this registrant, before any donation. Ticket-typed
// events keep their price on the ticket type, so the registration is the
// source of truth and the event price is only a fallback.
export function ticketAmountDue(registration, event = registration?.event) {
  const amount = registration?.custom_amount_euros ?? registration?.final_amount_euros ?? event?.price_euros;
  return parseFloat(amount) || 0;
}

// 'Approved' on a paid ticket means the spot is offered but not yet paid for.
export function isAwaitingPayment(registration, event) {
  return registration?.status === 'Approved' && ticketAmountDue(registration, event) > 0;
}

export function hasValidTicket(registration, event) {
  if (registration?.status === 'Paid') return true;
  return registration?.status === 'Approved' && !isAwaitingPayment(registration, event);
}
