import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises } from '@vue/test-utils';
import { byTest, mountWithVuetify } from '@/test/mountWithVuetify.js';

vi.mock('@/services/EventService.js', () => ({
  EventService: { exportEventRegistrations: vi.fn() },
}));

import { EventService } from '@/services/EventService.js';
import { blobErrorDetail, filenameFromHeaders } from '@/utils/download.js';
import RegistrationsExportButton from './RegistrationsExportButton.vue';

describe('RegistrationsExportButton', () => {
  let wrapper;
  let downloads;

  beforeEach(() => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    window.URL.createObjectURL = vi.fn(() => 'blob:workbook');
    window.URL.revokeObjectURL = vi.fn();
    downloads = [];
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(function click() {
      downloads.push({ href: this.href, filename: this.download });
    });
  });

  afterEach(() => {
    wrapper?.unmount();
    document.body.innerHTML = '';
    vi.clearAllMocks();
  });

  async function clickExport(props = { eventId: 7, eventTitle: 'Spring Summit' }) {
    wrapper = mountWithVuetify(RegistrationsExportButton, { props });
    byTest('export-registrations').click();
    await flushPromises();
  }

  it("saves the workbook under the server's file name", async () => {
    EventService.exportEventRegistrations.mockResolvedValue({
      data: new Blob(['xlsx']),
      headers: { 'content-disposition': 'attachment; filename="spring-summit-attendees-2026-11-09.xlsx"' },
    });

    await clickExport();

    expect(EventService.exportEventRegistrations).toHaveBeenCalledWith(7);
    expect(downloads).toEqual([{ href: 'blob:workbook', filename: 'spring-summit-attendees-2026-11-09.xlsx' }]);
  });

  it("names the file after the event when the header can't be read", async () => {
    EventService.exportEventRegistrations.mockResolvedValue({ data: new Blob(['xlsx']), headers: {} });

    await clickExport({ eventId: 7, eventTitle: 'Ennova × ESADE: Gala!' });

    expect(downloads[0].filename).toBe('ennova-esade-gala-attendees.xlsx');
  });

  it("shows the server's reason when the export is refused", async () => {
    const body = new Blob([JSON.stringify({ detail: "You don't have permission to export this event's attendees" })]);
    EventService.exportEventRegistrations.mockRejectedValue(
      Object.assign(new Error('Request failed'), { response: { status: 403, data: body } }),
    );

    await clickExport();

    // Reading the error out of the Blob takes a FileReader round trip in jsdom.
    await vi.waitFor(() => expect(document.body.textContent).toContain(
      "Couldn't export the attendee list: You don't have permission to export this event's attendees",
    ));
    expect(downloads).toEqual([]);
  });

  it('still says something when the error has no detail', async () => {
    EventService.exportEventRegistrations.mockRejectedValue(new Error('Network Error'));

    await clickExport();

    expect(document.body.textContent).toContain("Couldn't export the attendee list: Network Error");
  });
});

describe('download helpers', () => {
  it('reads the file name from Content-Disposition', () => {
    expect(filenameFromHeaders({ 'content-disposition': 'attachment; filename="a.xlsx"' })).toBe('a.xlsx');
    expect(filenameFromHeaders({ 'content-disposition': 'attachment; filename=b.xlsx' })).toBe('b.xlsx');
    expect(filenameFromHeaders({})).toBeNull();
    expect(filenameFromHeaders(undefined)).toBeNull();
  });

  it('reads the detail out of a JSON error blob, and gives up on anything else', async () => {
    const error = (data) => ({ response: { data } });
    expect(await blobErrorDetail(error(new Blob(['{"detail":"Nope"}'])))).toBe('Nope');
    expect(await blobErrorDetail(error(new Blob(['<html>502</html>'])))).toBeNull();
    expect(await blobErrorDetail(error({ detail: 'Plain' }))).toBe('Plain');
    expect(await blobErrorDetail({})).toBeNull();
  });
});
