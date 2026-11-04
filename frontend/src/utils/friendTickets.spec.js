import { describe, expect, it } from 'vitest';
import {
  apiErrorMessage, dealLabel, dealPrices, friendEmailError, friendTicketMessage, isBringAFriend,
} from './friendTickets.js';

const status = (fields = {}) => ({
  friend_email: 'fay@example.com', status: 'sent', friend_name: null, emailed: true,
  needs_new_friend: false, can_change: true, can_resend: true, ...fields,
});

describe('the deal', () => {
  it('is recognised by its flag', () => {
    expect(isBringAFriend({ bring_a_friend: true })).toBe(true);
    expect(isBringAFriend({ bring_a_friend: false })).toBe(false);
    expect(isBringAFriend(null)).toBe(false);
  });

  it('shows the price for both and per person', () => {
    expect(dealPrices({ price_euros: '20.00' })).toEqual({ total: '20.00', each: '10.00' });
    expect(dealLabel({ price_euros: '25' })).toBe('2 tickets for €25.00 (€12.50 each)');
  });
});

describe('friendEmailError', () => {
  it('accepts an email that is not the buyer\'s', () => {
    expect(friendEmailError(' Fay@Example.com ', 'bea@example.com')).toBeNull();
  });

  it.each([
    ['', /Enter your friend's email/],
    ['fay@', /doesn't look like an email/],
    ['BEA@example.com', /your own email/],
  ])('refuses %j', (email, message) => {
    expect(friendEmailError(email, 'bea@example.com')).toMatch(message);
  });

  it('can\'t compare with the buyer before they have typed their email', () => {
    expect(friendEmailError('fay@example.com', '')).toBeNull();
  });
});

describe('friendTicketMessage', () => {
  it('says who has the ticket once claimed', () => {
    expect(friendTicketMessage(status({ status: 'claimed', friend_name: 'Fay' }))).toEqual({
      text: 'Fay has their ticket.', color: 'success',
    });
  });

  it('says where the link went', () => {
    expect(friendTicketMessage(status()).text).toContain("We've emailed fay@example.com");
  });

  it('flags a failed send, before or after release', () => {
    expect(friendTicketMessage(status({ emailed: false })).color).toBe('error');
    expect(friendTicketMessage(status({ status: 'awaiting_payment', emailed: false, can_resend: true })).color).toBe('error');
  });

  it('waits for the payment', () => {
    const message = friendTicketMessage(status({ status: 'awaiting_payment', emailed: false, can_resend: false }));
    expect(message).toEqual({ text: expect.stringContaining('payment goes through'), color: 'info' });
  });

  it('asks for someone else when the friend already has a ticket', () => {
    const message = friendTicketMessage(status({ needs_new_friend: true }));
    expect(message.color).toBe('warning');
    expect(message.text).toContain('needs someone else');
  });
});

describe('apiErrorMessage', () => {
  it('reads both kinds of FastAPI error', () => {
    expect(apiErrorMessage({ response: { data: { detail: 'Nope' } } }, 'x')).toBe('Nope');
    expect(apiErrorMessage({ response: { data: { detail: [{ msg: 'bad email' }, { msg: 'too long' }] } } }, 'x'))
      .toBe('bad email. too long');
    expect(apiErrorMessage(new Error('network'), 'Try again')).toBe('Try again');
  });
});
