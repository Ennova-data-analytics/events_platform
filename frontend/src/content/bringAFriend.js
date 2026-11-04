// Wording of the "bring a friend" deal on the website. Marketing can edit
// this file freely. The emails are in
// backend/domain/services/friend_ticket_copy.py.
//
// Entries that are functions fill in details such as the price or a name:
// edit the text between the backticks, and keep the ${...} parts.

export const BRING_A_FRIEND = {
  // Ticket picker and the selected ticket's card
  dealLabel: (total, each) => `2 tickets for €${total} (€${each} each)`,
  dealBanner:
    'Bring a friend: you pay once, and we send your friend their own ticket.',

  // Checkout
  friendFieldTitle: "Your friend's ticket",
  friendFieldLabel: "Your friend's email",
  friendFieldHint:
    "The one they use for Ennova. No account? They'll create one in a minute with this address.",
  friendFieldMissing: "Enter your friend's email so we can send them their ticket.",
  friendFieldInvalid: "That doesn't look like an email address.",
  friendFieldIsYou: "That's your own email. Enter your friend's instead.",

  // Buyer: confirmation page and ticket page
  cardTitle: "Your friend's ticket",
  statusAwaitingPayment: "We'll send it as soon as your payment goes through.",
  statusNotSent: "We haven't been able to send it yet. Press Resend to try again.",
  statusSent: (email) => `We've emailed ${email}. They just need to create their account with that address.`,
  statusClaimed: (name) => `${name} has their ticket.`,
  statusNeedsNewFriend: (email) =>
    `${email} already has their own ticket, so this one needs someone else. Change the email below.`,
  changeButton: 'Change email',
  resendButton: 'Resend',
  saveButton: 'Send to this email',
  changedMessage: 'Done. The old link no longer works.',
  resentMessage: 'Sent again.',

  // Friend: the page their link opens
  claimHeadline: (buyer) => `${buyer} got you a ticket`,
  claimSubtitle: (event) => `You're going to ${event}. It's already paid for.`,
  claimEmailNote: (email) => `Your ticket is for ${email}. Create your account with that address, or log in if you already have one.`,
  claimButton: 'Get my ticket',
  claimedHeadline: "You've got your ticket",
  claimedSubtitle: (event) => `See you at ${event}!`,
  unavailableHeadline: "This ticket isn't available",
  unavailableSubtitle: (buyer) => `Ask ${buyer} about it.`,
};
