import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises } from '@vue/test-utils';
import { reactive } from 'vue';
import { byTest, mountWithVuetify } from '@/test/mountWithVuetify.js';

const authStore = reactive({
  isAuthenticated: false,
  user: null,
  setAuthFromResponse: vi.fn((token, user) => {
    authStore.isAuthenticated = true;
    authStore.user = user;
  }),
  fetchCurrentUser: vi.fn(),
  logout: vi.fn(),
});

vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { id: '7' }, query: { token: 'tok-123' } }),
}));
vi.mock('@/stores/auth.store.js', () => ({ useAuthStore: () => authStore }));
vi.mock('@/services/EventService.js', () => ({
  EventService: { getFriendTicketPreview: vi.fn(), claimFriendTicket: vi.fn() },
}));
vi.mock('@/services/AuthService.js', () => ({
  AuthService: { register: vi.fn(), login: vi.fn() },
}));

import { EventService } from '@/services/EventService.js';
import { AuthService } from '@/services/AuthService.js';
import FriendTicketClaimPage from './FriendTicketClaimPage.vue';

const preview = (fields = {}) => ({
  event_id: 7, event_name: 'Spring Summit', event_date_start: '2027-05-01T17:00:00Z',
  buyer_name: 'Bea Buyer', friend_email: 'fay@example.com', status: 'sent', ...fields,
});

const stubs = { RouterLink: true, 'router-link': true };

async function setValue(name, value) {
  const input = byTest(name).querySelector('input');
  input.value = value;
  input.dispatchEvent(new Event('input'));
  await flushPromises();
}

describe('FriendTicketClaimPage', () => {
  let wrapper;

  async function mountIt() {
    wrapper = mountWithVuetify(FriendTicketClaimPage, { global: { stubs } });
    await flushPromises();
  }

  beforeEach(() => {
    Object.assign(authStore, { isAuthenticated: false, user: null });
    EventService.getFriendTicketPreview.mockResolvedValue({ data: preview() });
    EventService.claimFriendTicket.mockResolvedValue({ data: { registration_id: 55 } });
    AuthService.register.mockResolvedValue({ data: {} });
    AuthService.login.mockResolvedValue({ data: { access_token: 'jwt', user: { email: 'fay@example.com' } } });
  });

  afterEach(() => {
    wrapper?.unmount();
    document.body.innerHTML = '';
  });

  it('leads with who bought it and which email to use', async () => {
    await mountIt();

    expect(EventService.getFriendTicketPreview).toHaveBeenCalledWith('7', 'tok-123');
    expect(byTest('claim-headline').textContent).toContain('Bea Buyer got you a ticket');
    expect(document.body.textContent).toContain('Your ticket is for fay@example.com');
  });

  it('creates the account with the invited email, then claims', async () => {
    await mountIt();
    await setValue('claim-full-name', 'Fay Friend');
    await setValue('claim-password', 'secret123');
    await setValue('claim-confirm-password', 'secret123');

    byTest('claim-button').click();
    await flushPromises();

    expect(AuthService.register).toHaveBeenCalledWith({
      email: 'fay@example.com', full_name: 'Fay Friend', password: 'secret123',
    });
    expect(authStore.setAuthFromResponse).toHaveBeenCalledWith('jwt', { email: 'fay@example.com' });
    expect(EventService.claimFriendTicket).toHaveBeenCalledWith('7', 'tok-123');
    expect(byTest('claim-done').textContent).toContain("You've got your ticket");
  });

  it('checks the passwords before making an account', async () => {
    await mountIt();
    await setValue('claim-password', 'secret123');
    await setValue('claim-confirm-password', 'secret124');
    vi.spyOn(console, 'error').mockImplementation(() => {});

    byTest('claim-button').click();
    await flushPromises();

    expect(AuthService.register).not.toHaveBeenCalled();
    expect(byTest('claim-error').textContent).toContain("passwords don't match");
  });

  it('logs in with an existing account', async () => {
    await mountIt();
    byTest('tab-login').click();
    await flushPromises();
    await setValue('claim-password', 'secret123');

    byTest('claim-button').click();
    await flushPromises();

    expect(AuthService.register).not.toHaveBeenCalled();
    expect(AuthService.login).toHaveBeenCalledWith({ email: 'fay@example.com', password: 'secret123' });
    expect(EventService.claimFriendTicket).toHaveBeenCalled();
  });

  it('claims straight away when already logged in with the right email', async () => {
    Object.assign(authStore, { isAuthenticated: true, user: { email: 'Fay@Example.com' } });
    await mountIt();

    byTest('claim-button').click();
    await flushPromises();

    expect(AuthService.login).not.toHaveBeenCalled();
    expect(byTest('claim-done')).not.toBeNull();
  });

  it('stops someone logged in with another email', async () => {
    Object.assign(authStore, { isAuthenticated: true, user: { email: 'stranger@example.com' } });
    await mountIt();

    expect(byTest('claim-wrong-account').textContent).toContain('this ticket is for');
    expect(byTest('claim-button')).toBeNull();
  });

  it('shows why a claim was refused', async () => {
    Object.assign(authStore, { isAuthenticated: true, user: { email: 'fay@example.com' } });
    EventService.claimFriendTicket.mockRejectedValue({
      response: { data: { detail: "You're already registered for this event, so you can't use this ticket." } },
    });
    vi.spyOn(console, 'error').mockImplementation(() => {});
    await mountIt();

    byTest('claim-button').click();
    await flushPromises();

    expect(byTest('claim-error').textContent).toContain('already registered');
    expect(console.error).toHaveBeenCalled();
  });

  it('says when the ticket is not available', async () => {
    EventService.getFriendTicketPreview.mockResolvedValue({ data: preview({ status: 'unavailable' }) });
    await mountIt();

    expect(byTest('claim-unavailable').textContent).toContain('Ask Bea Buyer about it.');
  });

  it('says when the link no longer works', async () => {
    EventService.getFriendTicketPreview.mockRejectedValue({
      response: { status: 404, data: { detail: "This link doesn't work any more." } },
    });
    vi.spyOn(console, 'error').mockImplementation(() => {});
    await mountIt();

    expect(byTest('claim-load-error').textContent).toContain("doesn't work any more");
  });
});
