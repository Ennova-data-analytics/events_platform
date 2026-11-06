import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises } from '@vue/test-utils';
import { mountWithVuetify } from '@/test/mountWithVuetify.js';

vi.mock('@/services/EventService', () => ({
  getEventDiscountCodes: vi.fn(),
  createDiscountCode: vi.fn(),
  updateDiscountCode: vi.fn(),
  deleteDiscountCode: vi.fn(),
  getDiscountCodeUsages: vi.fn(),
  backpopulateDiscountCode: vi.fn(),
}));

import { createDiscountCode, getEventDiscountCodes } from '@/services/EventService';
import DiscountCodeManager from './DiscountCodeManager.vue';

const refused = (status, detail) => Object.assign(new Error('Request failed'), { response: { status, data: { detail } } });

const button = (text) => [...document.body.querySelectorAll('button')].find((b) => b.textContent.trim() === text);

async function type(input, value) {
  input.value = value;
  input.dispatchEvent(new Event('input'));
  await flushPromises();
}

describe('DiscountCodeManager', () => {
  let wrapper;

  beforeEach(() => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    getEventDiscountCodes.mockResolvedValue({ data: [] });
  });

  afterEach(() => {
    wrapper?.unmount();
    document.body.innerHTML = '';
    vi.clearAllMocks();
  });

  async function mountIt() {
    wrapper = mountWithVuetify(DiscountCodeManager, { props: { eventId: 7 } });
    await flushPromises();
  }

  it("shows why loading the codes failed", async () => {
    getEventDiscountCodes.mockRejectedValue(
      refused(403, "You don't have permission to view discount codes for this event"),
    );
    await mountIt();

    expect(document.body.textContent).toContain(
      "Failed to load discount codes: You don't have permission to view discount codes for this event",
    );
  });

  it("shows the server's reason when creating a code fails", async () => {
    createDiscountCode.mockRejectedValue(refused(400, "Discount code 'SAVE10' already exists for this event"));
    await mountIt();

    button('Create Discount Code').click();
    await flushPromises();
    const [code, , value] = document.body.querySelectorAll('.v-dialog input');
    await type(code, 'SAVE10');
    await type(value, '10');
    button('Create').click();
    await flushPromises();

    expect(createDiscountCode).toHaveBeenCalledWith(expect.objectContaining({ code: 'SAVE10', event_id: 7 }));
    expect(document.body.textContent).toContain(
      "Failed to create discount code: Discount code 'SAVE10' already exists for this event",
    );
  });
});
