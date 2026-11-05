import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises } from '@vue/test-utils';
import { reactive } from 'vue';
import { byTest, mountWithVuetify } from '@/test/mountWithVuetify.js';

const route = reactive({ params: { id: '7' }, query: {} });
const router = { replace: vi.fn() };
const authStore = reactive({ user: null });

vi.mock('vue-router', () => ({ useRoute: () => route, useRouter: () => router }));
vi.mock('@/stores/auth.store.js', () => ({ useAuthStore: () => authStore }));
vi.mock('@/services/EventService.js', () => ({
  EventService: { getEventById: vi.fn(), donateToEvent: vi.fn() },
}));
vi.mock('@/utils/navigation.js', () => ({ goToExternalUrl: vi.fn() }));

import { EventService } from '@/services/EventService.js';
import { goToExternalUrl } from '@/utils/navigation.js';
import EventDonatePage from './EventDonatePage.vue';

const charityEvent = (fields = {}) => ({
  event_id: 7, event_name: 'Spring Gala', event_date_start: '2027-05-01T17:00:00Z',
  is_charitable: true, charity_name: 'Food Bank', charity_description: null, ...fields,
});

const stubs = { RouterLink: true, 'router-link': true };

async function setEmail(value) {
  const input = byTest('donate-email').querySelector('input');
  input.value = value;
  input.dispatchEvent(new Event('input'));
  await flushPromises();
}

function submitButton() {
  return byTest('donate-submit');
}

describe('EventDonatePage', () => {
  let wrapper;

  async function mountIt() {
    wrapper = mountWithVuetify(EventDonatePage, { global: { stubs } });
    await flushPromises();
  }

  beforeEach(() => {
    route.query = {};
    authStore.user = null;
    EventService.getEventById.mockResolvedValue({ data: charityEvent() });
    EventService.donateToEvent.mockResolvedValue({ data: { donation_id: 1, checkout_url: 'https://checkout.test/1' } });
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    wrapper?.unmount();
    document.body.innerHTML = '';
  });

  it('opens straight on the donation form for the event, without logging in', async () => {
    await mountIt();

    expect(EventService.getEventById).toHaveBeenCalledWith('7');
    expect(byTest('donate-event-name').textContent).toContain('Spring Gala');
    expect(document.body.textContent).toContain('Donate to Food Bank');
    expect(submitButton().textContent).toContain('Donate €10.00');
  });

  it('needs a valid email before paying', async () => {
    await mountIt();
    expect(submitButton().disabled).toBe(true);

    await setEmail('not-an-email');
    expect(submitButton().disabled).toBe(true);

    await setEmail('donor@example.com');
    expect(submitButton().disabled).toBe(false);
  });

  it('sends the donor to the Stripe checkout with the chosen amount', async () => {
    await mountIt();
    await setEmail('  donor@example.com ');

    submitButton().click();
    await flushPromises();

    expect(EventService.donateToEvent).toHaveBeenCalledWith('7', { email: 'donor@example.com', amountEuros: 10 });
    expect(goToExternalUrl).toHaveBeenCalledWith('https://checkout.test/1');
  });

  it('fills in the email of someone who is logged in', async () => {
    authStore.user = { email: 'member@example.com' };
    await mountIt();

    expect(byTest('donate-email').querySelector('input').value).toBe('member@example.com');
    expect(submitButton().disabled).toBe(false);
  });

  it('shows why a donation could not start, and stays on the page', async () => {
    EventService.donateToEvent.mockRejectedValue({ response: { status: 400, data: { detail: 'This event does not accept donations' } } });
    await mountIt();
    await setEmail('donor@example.com');

    submitButton().click();
    await flushPromises();

    expect(byTest('donate-error').textContent).toContain('This event does not accept donations');
    expect(goToExternalUrl).not.toHaveBeenCalled();
    expect(submitButton().disabled).toBe(false);
  });

  it('says so when the payment could not start for an unknown reason', async () => {
    EventService.donateToEvent.mockRejectedValue(new Error('Network Error'));
    await mountIt();
    await setEmail('donor@example.com');

    submitButton().click();
    await flushPromises();

    expect(byTest('donate-error').textContent).toContain('You have not been charged');
  });

  it('thanks the donor on the way back from Stripe, and lets them give again', async () => {
    route.query = { donation: 'success' };
    await mountIt();

    expect(byTest('donate-thanks').textContent).toContain('Your donation to Food Bank was received');
    expect(router.replace).toHaveBeenCalledWith({ query: {} });

    byTest('donate-again').click();
    await flushPromises();

    expect(byTest('donate-thanks')).toBeNull();
    expect(submitButton()).not.toBeNull();
  });

  it('tells a donor who backed out that nothing was charged', async () => {
    route.query = { donation: 'cancelled' };
    await mountIt();

    expect(byTest('donate-cancelled').textContent).toContain('You have not been charged');
    expect(submitButton()).not.toBeNull();
  });

  it('refuses an event that is not a charity event', async () => {
    EventService.getEventById.mockResolvedValue({ data: charityEvent({ is_charitable: false }) });
    await mountIt();

    expect(byTest('donate-not-charitable').textContent).toContain("Spring Gala isn't taking donations");
    expect(submitButton()).toBeNull();
  });

  it('explains a link to an event that does not exist', async () => {
    EventService.getEventById.mockRejectedValue({ response: { status: 404 } });
    await mountIt();

    expect(byTest('donate-load-error').textContent).toContain("We couldn't find this event");
  });

  it('explains when the event could not be loaded at all', async () => {
    EventService.getEventById.mockRejectedValue(new Error('Network Error'));
    await mountIt();

    expect(byTest('donate-load-error').textContent).toContain('Check your connection');
  });
});
