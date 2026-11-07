import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises } from '@vue/test-utils';
import { byTest, mountWithVuetify } from '@/test/mountWithVuetify.js';

vi.mock('@/services/EventService.js', () => ({
  EventService: { getCharitySummary: vi.fn() },
}));

import { EventService } from '@/services/EventService.js';
import CharityTotalCard from './CharityTotalCard.vue';

const SUMMARY = {
  event_id: 7,
  charity_name: 'Food Bank',
  ticket_sales: '28.00',
  paid_tickets: 2,
  refunds_given: '12.00',
  ticket_donations: '5.00',
  ticket_donation_count: 1,
  standalone_donations: '22.50',
  standalone_donation_count: 2,
  total_to_donate: '55.50',
  awaiting_payment: '0.00',
  commission_owed: '0.00',
};

describe('CharityTotalCard', () => {
  let wrapper;

  async function mountIt(summary = SUMMARY) {
    EventService.getCharitySummary.mockResolvedValue({ data: summary });
    wrapper = mountWithVuetify(CharityTotalCard, { props: { eventId: 7 } });
    await flushPromises();
  }

  beforeEach(() => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    wrapper?.unmount();
    document.body.innerHTML = '';
    vi.clearAllMocks();
  });

  it('shows the total owed to the charity and where it came from', async () => {
    await mountIt();

    expect(EventService.getCharitySummary).toHaveBeenCalledWith(7);
    expect(byTest('charity-total').textContent).toContain('Total to donate to Food Bank');
    expect(byTest('charity-total-amount').textContent.trim()).toBe('€55.50');

    const tickets = byTest('charity-total-tickets').textContent;
    expect(tickets).toContain('2 paid tickets');
    expect(tickets).toContain('after €12.00 refunded');
    expect(tickets).toContain('€28.00');

    expect(byTest('charity-total-ticket-donations').textContent).toContain('1 donation)');
    expect(byTest('charity-total-ticket-donations').textContent).toContain('€5.00');
    expect(byTest('charity-total-standalone').textContent).toContain('QR code');
    expect(byTest('charity-total-standalone').textContent).toContain('€22.50');
  });

  it('leaves out the refund note and the extra notes when they are zero', async () => {
    await mountIt({ ...SUMMARY, refunds_given: '0.00' });

    expect(byTest('charity-total-tickets').textContent).not.toContain('refunded');
    expect(byTest('charity-total-awaiting')).toBeNull();
    expect(byTest('charity-total-commission')).toBeNull();
  });

  it('flags unpaid tickets and referral commission', async () => {
    await mountIt({ ...SUMMARY, awaiting_payment: '25.00', commission_owed: '5.00' });

    expect(byTest('charity-total-awaiting').textContent).toContain('€25.00');
    expect(byTest('charity-total-commission').textContent).toContain('€5.00');
  });

  it('shows the API error when the total cannot be loaded', async () => {
    EventService.getCharitySummary.mockRejectedValue({
      response: { data: { detail: 'This event does not accept donations. Mark it as a charity event first.' } },
    });
    wrapper = mountWithVuetify(CharityTotalCard, { props: { eventId: 7 } });
    await flushPromises();

    expect(byTest('charity-total-error').textContent).toContain('Mark it as a charity event first');
    expect(byTest('charity-total-amount')).toBeNull();
    expect(console.error).toHaveBeenCalled();
  });
});
