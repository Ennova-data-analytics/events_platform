import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises } from '@vue/test-utils';
import { allByTest, byTest, mountWithVuetify } from '@/test/mountWithVuetify.js';

vi.mock('@/services/TicketTypeService.js', () => ({
  default: { getTicketTypes: vi.fn(), deleteTicketType: vi.fn() },
}));
vi.mock('@/services/FormTemplateService.js', () => ({
  FormTemplateService: { getAllTemplates: vi.fn() },
}));

import TicketTypeService from '@/services/TicketTypeService.js';
import { FormTemplateService } from '@/services/FormTemplateService.js';
import TicketTypeManagement from './TicketTypeManagement.vue';

const ticketType = (fields) => ({
  ticket_type_id: 1, name: 'Participant', description: '', price_euros: '40.00', capacity: 100,
  tickets_sold: 0, is_active: true, deleted_at: null, ...fields,
});

describe('TicketTypeManagement', () => {
  let wrapper;

  beforeEach(() => {
    FormTemplateService.getAllTemplates.mockResolvedValue({ data: [] });
    TicketTypeService.getTicketTypes.mockResolvedValue({
      ticket_types: [ticketType({ ticket_type_id: 1, name: 'Early Bird', tickets_sold: 3 })],
      deleted_ticket_types: [ticketType({ ticket_type_id: 9, name: 'Wrong Price', tickets_sold: 2, deleted_at: '2026-11-04T10:00:00Z' })],
      total_count: 1,
    });
  });

  afterEach(() => {
    wrapper?.unmount();
    document.body.innerHTML = '';
  });

  async function mountIt() {
    wrapper = mountWithVuetify(TicketTypeManagement, { props: { eventId: 7 } });
    await flushPromises();
  }

  it('asks for deleted ticket types too', async () => {
    await mountIt();
    expect(TicketTypeService.getTicketTypes).toHaveBeenCalledWith(7, false, true);
  });

  it('lets you delete a ticket type that has been sold, and says holders keep it', async () => {
    await mountIt();
    const button = byTest('delete-ticket-type');
    expect(button.disabled).toBe(false);

    button.click();
    await flushPromises();

    expect(byTest('delete-message').textContent).toContain('3 people hold this ticket');
    expect(byTest('delete-message').textContent).toContain('They keep it');
  });

  it('reports the outcome and reloads', async () => {
    TicketTypeService.deleteTicketType.mockResolvedValue({ ticket_type_id: 1, outcome: 'hidden', holders: 3 });
    await mountIt();
    byTest('delete-ticket-type').click();
    await flushPromises();

    const deleteButton = [...document.body.querySelectorAll('.v-dialog button')].find(b => b.textContent.trim() === 'Delete');
    deleteButton.click();
    await flushPromises();

    expect(TicketTypeService.deleteTicketType).toHaveBeenCalledWith(7, 1);
    expect(document.body.textContent).toContain('Ticket type taken off sale. 3 registrations keep it.');
    expect(TicketTypeService.getTicketTypes).toHaveBeenCalledTimes(2);
    expect(wrapper.emitted('ticket-types-updated')).toHaveLength(1);
  });

  it('shows deleted ticket types in a collapsed section', async () => {
    await mountIt();
    const section = byTest('deleted-ticket-types');
    expect(section.textContent).toContain('Deleted (1)');

    section.querySelector('button').click();
    await flushPromises();

    expect(section.textContent).toContain('Wrong Price');
    expect(section.textContent).toContain('2 sold');
  });

  it('has no deleted section when nothing was deleted', async () => {
    TicketTypeService.getTicketTypes.mockResolvedValue({ ticket_types: [ticketType()], deleted_ticket_types: [], total_count: 1 });
    await mountIt();
    expect(allByTest('deleted-ticket-types')).toHaveLength(0);
  });

  it('shows the server error when deleting fails', async () => {
    TicketTypeService.deleteTicketType.mockRejectedValue({ response: { data: { detail: 'Ticket type not found' } } });
    vi.spyOn(console, 'error').mockImplementation(() => {});
    await mountIt();
    byTest('delete-ticket-type').click();
    await flushPromises();
    [...document.body.querySelectorAll('.v-dialog button')].find(b => b.textContent.trim() === 'Delete').click();
    await flushPromises();

    expect(document.body.textContent).toContain('Ticket type not found');
  });
});
