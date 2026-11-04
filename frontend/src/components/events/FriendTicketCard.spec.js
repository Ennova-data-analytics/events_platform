import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises } from '@vue/test-utils';
import { byTest, mountWithVuetify } from '@/test/mountWithVuetify.js';

vi.mock('@/services/EventService.js', () => ({
  EventService: { getMyFriendTicket: vi.fn(), changeFriendEmail: vi.fn(), resendFriendTicket: vi.fn() },
}));

import { EventService } from '@/services/EventService.js';
import FriendTicketCard from './FriendTicketCard.vue';

const status = (fields = {}) => ({
  event_id: 7, friend_email: 'fay@example.com', status: 'sent', friend_name: null, emailed: true,
  needs_new_friend: false, can_change: true, can_resend: true, ...fields,
});

async function setValue(name, value) {
  const input = byTest(name).querySelector('input');
  input.value = value;
  input.dispatchEvent(new Event('input'));
  await flushPromises();
}

describe('FriendTicketCard', () => {
  let wrapper;

  async function mountIt() {
    wrapper = mountWithVuetify(FriendTicketCard, { props: { eventId: 7, buyerEmail: 'bea@example.com' } });
    await flushPromises();
  }

  beforeEach(() => {
    EventService.getMyFriendTicket.mockResolvedValue({ data: status() });
  });

  afterEach(() => {
    wrapper?.unmount();
    document.body.innerHTML = '';
  });

  it('is not shown for a normal ticket', async () => {
    EventService.getMyFriendTicket.mockRejectedValue({ response: { status: 404 } });
    await mountIt();

    expect(byTest('friend-ticket-card')).toBeNull();
  });

  it('logs a failure to load that is not a 404', async () => {
    EventService.getMyFriendTicket.mockRejectedValue({ response: { status: 500 } });
    vi.spyOn(console, 'error').mockImplementation(() => {});
    await mountIt();

    expect(console.error).toHaveBeenCalled();
  });

  it('says where the ticket went', async () => {
    await mountIt();

    expect(byTest('friend-ticket-status').textContent).toContain("We've emailed fay@example.com");
    expect(byTest('friend-ticket-change')).not.toBeNull();
    expect(byTest('friend-ticket-resend')).not.toBeNull();
  });

  it('shows who has it, with nothing left to do', async () => {
    EventService.getMyFriendTicket.mockResolvedValue({
      data: status({ status: 'claimed', friend_name: 'Fay Friend', can_change: false, can_resend: false }),
    });
    await mountIt();

    expect(byTest('friend-ticket-status').textContent).toContain('Fay Friend has their ticket.');
    expect(byTest('friend-ticket-change')).toBeNull();
    expect(byTest('friend-ticket-resend')).toBeNull();
  });

  it('changes the email', async () => {
    EventService.changeFriendEmail.mockResolvedValue({ data: status({ friend_email: 'otto@example.com' }) });
    await mountIt();
    byTest('friend-ticket-change').click();
    await flushPromises();

    await setValue('friend-ticket-new-email', 'bea@example.com');
    expect(byTest('friend-ticket-save').disabled).toBe(true);

    await setValue('friend-ticket-new-email', ' otto@example.com ');
    byTest('friend-ticket-save').click();
    await flushPromises();

    expect(EventService.changeFriendEmail).toHaveBeenCalledWith(7, 'otto@example.com');
    expect(byTest('friend-ticket-status').textContent).toContain('otto@example.com');
    expect(byTest('friend-ticket-notice').textContent).toContain('The old link no longer works');
    expect(byTest('friend-ticket-new-email')).toBeNull();
  });

  it('shows why a change was refused and keeps the form open', async () => {
    EventService.changeFriendEmail.mockRejectedValue({
      response: { data: { detail: 'otto@example.com is already registered for this event. Choose someone else.' } },
    });
    vi.spyOn(console, 'error').mockImplementation(() => {});
    await mountIt();
    byTest('friend-ticket-change').click();
    await flushPromises();
    await setValue('friend-ticket-new-email', 'otto@example.com');
    byTest('friend-ticket-save').click();
    await flushPromises();

    expect(byTest('friend-ticket-error').textContent).toContain('already registered');
    expect(byTest('friend-ticket-new-email')).not.toBeNull();
  });

  it('resends, and says so when it fails', async () => {
    EventService.resendFriendTicket.mockRejectedValueOnce({
      response: { data: { detail: "We couldn't send the email. Please try again in a few minutes." } },
    });
    EventService.resendFriendTicket.mockResolvedValueOnce({ data: status() });
    vi.spyOn(console, 'error').mockImplementation(() => {});
    await mountIt();

    byTest('friend-ticket-resend').click();
    await flushPromises();
    expect(byTest('friend-ticket-error').textContent).toContain("couldn't send the email");

    byTest('friend-ticket-resend').click();
    await flushPromises();
    expect(byTest('friend-ticket-notice').textContent).toContain('Sent again.');
  });
});
