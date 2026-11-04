import { afterEach, describe, expect, it, vi } from 'vitest';
import { flushPromises } from '@vue/test-utils';
import { byTest, mountWithVuetify } from '@/test/mountWithVuetify.js';

vi.mock('@/stores/auth.store', () => ({ useAuthStore: () => ({ user: null }) }));

import TicketTypeSelector from './TicketTypeSelector.vue';

const duo = {
  ticket_type_id: 3, name: 'Duo', description: 'Bring someone', price_euros: '20.00', is_active: true,
  bring_a_friend: true, capacity: 10, tickets_available: 6, show_availability: true,
};

describe('TicketTypeSelector with a bring-a-friend ticket', () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    document.body.innerHTML = '';
  });

  async function mountIt(ticketType) {
    wrapper = mountWithVuetify(TicketTypeSelector, { props: { ticketTypes: [ticketType], modelValue: ticketType.ticket_type_id } });
    await flushPromises();
  }

  it('shows the price for two and the deal', async () => {
    await mountIt(duo);

    expect(byTest('deal-price').textContent).toContain('€20.00');
    expect(byTest('deal-price').textContent).toContain('€10.00 each');
    expect(byTest('deal-banner').textContent).toContain('you pay once');
  });

  it('is unavailable with only one seat left', async () => {
    await mountIt({ ...duo, tickets_available: 1 });
    document.body.querySelector('.v-field').dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
    await flushPromises();

    const option = [...document.body.querySelectorAll('.v-list-item')].find(item => item.textContent.includes('Duo'));
    expect(option.classList.contains('v-list-item--disabled')).toBe(true);
  });
});
