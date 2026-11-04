import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises } from '@vue/test-utils';
import { allByTest, byTest, mountWithVuetify } from '@/test/mountWithVuetify.js';

vi.mock('@/services/AdminService.js', () => ({
  AdminService: { previewRefunds: vi.fn(), issueRefunds: vi.fn() },
}));

import { AdminService } from '@/services/AdminService.js';
import RefundDialog from './RefundDialog.vue';

const attendees = [
  { registration_id: 11, user: { full_name: 'Ada' } },
  { registration_id: 12, user: { full_name: 'Bo' } },
];

const preview = {
  rows: [
    { registration_id: 11, full_name: 'Ada', paid_euros: '40.00', already_refunded_euros: '0.00', refund_euros: '10.00', method: 'stripe', skip_reason: null },
    { registration_id: 12, full_name: 'Bo', paid_euros: '40.00', already_refunded_euros: '0.00', refund_euros: '10.00', method: 'manual', skip_reason: null },
  ],
  total_refund_euros: '20.00',
  refundable_count: 2,
  ticket_type_id: 5,
  ticket_type_name: 'Participant',
  current_price_euros: '40.00',
};

const batchResult = {
  batch_id: 'x',
  results: [
    { registration_id: 11, full_name: 'Ada', outcome: 'refunded', amount_euros: '10.00', method: 'stripe', email_sent: true },
    { registration_id: 12, full_name: 'Bo', outcome: 'failed', amount_euros: '10.00', method: 'stripe', message: 'Card expired' },
  ],
  refunded_count: 1, failed_count: 1, skipped_count: 0, total_refunded_euros: '10.00', emails_failed: 0,
  ticket_type_price_updated: true,
};

async function setValue(name, value) {
  const input = byTest(name).querySelector('input, textarea');
  input.value = value;
  input.dispatchEvent(new Event('input'));
  await flushPromises();
}

async function click(name) {
  byTest(name).click();
  await flushPromises();
}

async function open() {
  const wrapper = mountWithVuetify(RefundDialog, { props: { modelValue: false, eventId: 7, attendees } });
  await wrapper.setProps({ modelValue: true });
  await flushPromises();
  return wrapper;
}

describe('RefundDialog', () => {
  let wrapper;

  beforeEach(() => {
    AdminService.previewRefunds.mockResolvedValue({ data: preview });
    AdminService.issueRefunds.mockResolvedValue({ data: batchResult });
  });

  afterEach(() => {
    wrapper?.unmount();
    document.body.innerHTML = '';
  });

  it('needs a price and an explanation before review', async () => {
    wrapper = await open();
    expect(byTest('review-btn').disabled).toBe(true);

    await setValue('corrected-price', '30');
    expect(byTest('review-btn').disabled).toBe(false);

    await setValue('refund-reason', '   ');
    expect(byTest('review-btn').disabled).toBe(true);
  });

  it('previews, then refunds with the corrected price and the price update', async () => {
    wrapper = await open();
    await setValue('corrected-price', '30');
    await click('review-btn');

    expect(AdminService.previewRefunds).toHaveBeenCalledWith(7, {
      registration_ids: [11, 12], mode: 'corrected_price', corrected_price_euros: '30.00',
    });
    expect(allByTest('preview-row')).toHaveLength(2);
    expect(byTest('confirm-btn').textContent).toContain('Refund €20.00 to 2 people');
    expect(byTest('update-price').textContent).toContain("'Participant' from €40.00 to €30.00");

    byTest('update-price').querySelector('input').click();
    await flushPromises();
    await click('confirm-btn');

    const [eventId, request] = AdminService.issueRefunds.mock.calls[0];
    expect(eventId).toBe(7);
    expect(request).toMatchObject({
      registration_ids: [11, 12],
      mode: 'corrected_price',
      corrected_price_euros: '30.00',
      update_ticket_type_price: true,
    });
    expect(request.reason).toMatch(/wrong price/);
    expect(request.batch_id).toMatch(/^[0-9a-f-]{36}$/);

    expect(byTest('refund-summary').textContent).toContain('1 refunded (€10.00), 1 failed, ticket price updated');
    expect(allByTest('result-row').map(row => row.textContent).join(' ')).toContain('Card expired');
    expect(wrapper.emitted('refunded')[0][0]).toEqual(batchResult);
  });

  it('sends a fixed amount', async () => {
    wrapper = await open();
    byTest('refund-mode').querySelectorAll('button')[1].click();
    await flushPromises();
    await setValue('fixed-amount', '7.5');
    await click('review-btn');

    expect(AdminService.previewRefunds).toHaveBeenCalledWith(7, {
      registration_ids: [11, 12], mode: 'fixed', amount_euros: '7.50',
    });
    expect(byTest('update-price')).toBeNull();
  });

  it('shows why the preview was refused and stays on the form', async () => {
    AdminService.previewRefunds.mockRejectedValue({ response: { data: { detail: 'The people selected hold different ticket types' } } });
    vi.spyOn(console, 'error').mockImplementation(() => {});
    wrapper = await open();
    await setValue('corrected-price', '30');
    await click('review-btn');

    expect(byTest('refund-error').textContent).toContain('different ticket types');
    expect(byTest('review-btn')).not.toBeNull();
    expect(console.error).toHaveBeenCalled();
  });

  it('retries a failed submit with the same batch id, so nobody is refunded twice', async () => {
    AdminService.issueRefunds.mockRejectedValueOnce(new Error('timeout'));
    vi.spyOn(console, 'error').mockImplementation(() => {});
    wrapper = await open();
    await setValue('corrected-price', '30');
    await click('review-btn');
    await click('confirm-btn');

    expect(byTest('refund-error').textContent).toContain('pressing the button again is safe');
    await click('confirm-btn');

    const [first, second] = AdminService.issueRefunds.mock.calls.map(([, request]) => request.batch_id);
    expect(second).toBe(first);
    expect(byTest('refund-summary')).not.toBeNull();
  });

  it('uses a new batch id each time it is opened', async () => {
    wrapper = await open();
    await setValue('corrected-price', '30');
    await click('review-btn');
    await click('confirm-btn');
    await wrapper.setProps({ modelValue: false });
    await wrapper.setProps({ modelValue: true });
    await flushPromises();
    await setValue('corrected-price', '30');
    await click('review-btn');
    await click('confirm-btn');

    const [first, second] = AdminService.issueRefunds.mock.calls.map(([, request]) => request.batch_id);
    expect(second).not.toBe(first);
  });
});
