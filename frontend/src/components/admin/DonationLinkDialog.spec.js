import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises } from '@vue/test-utils';
import { byTest, mountWithVuetify } from '@/test/mountWithVuetify.js';

vi.mock('@/services/EventService.js', () => ({
  EventService: { getDonationUrl: vi.fn(), getDonationQrCode: vi.fn() },
}));

import { EventService } from '@/services/EventService.js';
import DonationLinkDialog from './DonationLinkDialog.vue';

const URL_FOR_7 = 'https://events.example.com/event/7/donate';

describe('DonationLinkDialog', () => {
  let wrapper;
  let writeText;

  async function openIt() {
    wrapper = mountWithVuetify(DonationLinkDialog, { props: { eventId: 7 } });
    byTest('donation-link-open').click();
    await flushPromises();
  }

  beforeEach(() => {
    EventService.getDonationUrl.mockResolvedValue({ data: { donation_url: URL_FOR_7 } });
    EventService.getDonationQrCode.mockResolvedValue({ data: new Blob(['png'], { type: 'image/png' }) });
    globalThis.URL.createObjectURL = vi.fn(() => 'blob:qr');
    globalThis.URL.revokeObjectURL = vi.fn();
    writeText = vi.fn().mockResolvedValue();
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true });
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    wrapper?.unmount();
    document.body.innerHTML = '';
  });

  it('loads nothing until it is opened', () => {
    wrapper = mountWithVuetify(DonationLinkDialog, { props: { eventId: 7 } });

    expect(EventService.getDonationUrl).not.toHaveBeenCalled();
    expect(EventService.getDonationQrCode).not.toHaveBeenCalled();
  });

  it('shows the QR code and the link for the event', async () => {
    await openIt();

    expect(EventService.getDonationUrl).toHaveBeenCalledWith(7);
    expect(EventService.getDonationQrCode).toHaveBeenCalledWith(7);
    expect(byTest('donation-qr').getAttribute('src')).toBe('blob:qr');
    expect(byTest('donation-url').querySelector('input').value).toBe(URL_FOR_7);
  });

  it('copies the link', async () => {
    await openIt();

    byTest('donation-url-copy').click();
    await flushPromises();

    expect(writeText).toHaveBeenCalledWith(URL_FOR_7);
  });

  it('says so when the link cannot be copied', async () => {
    writeText.mockRejectedValue(new Error('denied'));
    await openIt();

    byTest('donation-url-copy').click();
    await flushPromises();

    expect(document.body.textContent).toContain("Couldn't copy the link");
  });

  it('downloads the QR code as a PNG named for the event', async () => {
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function () {
      expect(this.href).toBe('blob:qr');
      expect(this.download).toBe('event_7_donation_qr.png');
    });
    await openIt();

    byTest('donation-qr-download').click();

    expect(click).toHaveBeenCalledTimes(1);
  });

  it("shows the API's reason when it refuses, even from a blob response", async () => {
    const body = new Blob([JSON.stringify({ detail: 'This event does not accept donations. Mark it as a charity event first.' })]);
    EventService.getDonationQrCode.mockRejectedValue({ response: { status: 400, data: body } });
    await openIt();

    // Reading the Blob body takes an extra turn of the event loop.
    await vi.waitFor(() => expect(byTest('donation-link-error')).not.toBeNull());
    expect(byTest('donation-link-error').textContent).toContain('Mark it as a charity event first');
    expect(byTest('donation-qr')).toBeNull();
  });

  it('falls back to a generic message when the request fails outright', async () => {
    EventService.getDonationUrl.mockRejectedValue(new Error('Network Error'));
    await openIt();

    expect(byTest('donation-link-error').textContent).toContain('Could not load the donation link');
  });
});
