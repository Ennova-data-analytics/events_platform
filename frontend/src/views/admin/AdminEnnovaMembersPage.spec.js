import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises } from '@vue/test-utils';
import { byTest, mountWithVuetify } from '@/test/mountWithVuetify.js';

vi.mock('@/services/EnnovaMemberService', () => ({
  EnnovaMemberService: {
    getMembers: vi.fn(),
    searchUsers: vi.fn(),
    addMember: vi.fn(),
    removeMember: vi.fn(),
    bulkAddMembers: vi.fn(),
    importFromExcel: vi.fn(),
    getPendingMembers: vi.fn(),
    removePendingMember: vi.fn(),
    clearPendingMembers: vi.fn(),
  },
}));

import { EnnovaMemberService } from '@/services/EnnovaMemberService';
import AdminEnnovaMembersPage from './AdminEnnovaMembersPage.vue';

const refused = (status, detail) => Object.assign(new Error('Request failed'), { response: { status, data: { detail } } });

const buttons = (text) => [...document.body.querySelectorAll('button')].filter((b) => b.textContent.trim() === text);

const pending = (id, email, source = 'members.xlsx') => ({
  pending_member_id: id,
  email,
  source_filename: source,
  created_at: '2026-11-01T10:00:00Z',
});

describe('AdminEnnovaMembersPage – emails waiting for sign-up', () => {
  let wrapper;

  beforeEach(() => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    EnnovaMemberService.getMembers.mockResolvedValue({ data: { members: [], total_count: 0 } });
    EnnovaMemberService.getPendingMembers.mockResolvedValue({
      data: { pending: [pending(1, 'ana@esade.edu'), pending(2, 'bruno@esade.edu')], total_count: 2 },
    });
  });

  afterEach(() => {
    wrapper?.unmount();
    document.body.innerHTML = '';
    vi.clearAllMocks();
  });

  async function mountIt() {
    wrapper = mountWithVuetify(AdminEnnovaMembersPage);
    await flushPromises();
  }

  it('lists the emails waiting for sign-up', async () => {
    await mountIt();

    const section = byTest('pending-members').textContent;
    expect(section).toContain('Waiting for sign-up (2)');
    expect(section).toContain('ana@esade.edu');
    expect(section).toContain('bruno@esade.edu');
    expect(section).toContain('members.xlsx');
  });

  it('says why the list failed to load', async () => {
    EnnovaMemberService.getPendingMembers.mockRejectedValue(refused(403, 'Not enough permissions'));
    await mountIt();

    expect(byTest('pending-members').textContent).toContain(
      'Failed to load the emails waiting for sign-up: Not enough permissions',
    );
  });

  it('removes one email and reloads the list', async () => {
    EnnovaMemberService.removePendingMember.mockResolvedValue({ data: pending(1, 'ana@esade.edu') });
    await mountIt();

    document.body.querySelector('[aria-label="Remove ana@esade.edu from the list"]').click();
    await flushPromises();

    expect(EnnovaMemberService.removePendingMember).toHaveBeenCalledWith(1);
    expect(EnnovaMemberService.getPendingMembers).toHaveBeenCalledTimes(2);
  });

  it("shows the server's reason when removing fails", async () => {
    EnnovaMemberService.removePendingMember.mockRejectedValue(refused(404, 'Pending member not found'));
    await mountIt();

    document.body.querySelector('[aria-label="Remove ana@esade.edu from the list"]').click();
    await flushPromises();

    expect(document.body.textContent).toContain('Failed to remove ana@esade.edu: Pending member not found');
  });

  it('clears the list only after confirming', async () => {
    EnnovaMemberService.clearPendingMembers.mockResolvedValue({ data: { removed_count: 2 } });
    await mountIt();

    buttons('Clear list')[0].click();
    await flushPromises();
    expect(EnnovaMemberService.clearPendingMembers).not.toHaveBeenCalled();
    expect(document.body.textContent).toContain('Current members are not affected');

    buttons('Clear list').at(-1).click();
    await flushPromises();

    expect(EnnovaMemberService.clearPendingMembers).toHaveBeenCalledTimes(1);
    expect(document.body.textContent).toContain('Removed 2 emails from the list');
  });

  it('hides the clear button when nothing is waiting', async () => {
    EnnovaMemberService.getPendingMembers.mockResolvedValue({ data: { pending: [], total_count: 0 } });
    await mountIt();

    expect(buttons('Clear list')).toHaveLength(0);
    expect(byTest('pending-members').textContent).toContain('No emails waiting');
  });
});

describe('AdminEnnovaMembersPage – import summary', () => {
  it('explains who was saved for sign-up', () => {
    const { pendingSavedMessage } = AdminEnnovaMembersPage.methods;

    expect(pendingSavedMessage({ unmatched_count: 3, pending_saved_count: 3 })).toBe(
      "3 people don't have an account yet. They'll become members automatically when they sign up.",
    );
    expect(pendingSavedMessage({ unmatched_count: 1, pending_saved_count: 1 })).toBe(
      "1 person doesn't have an account yet. They'll become a member automatically when they sign up.",
    );
    expect(pendingSavedMessage({ unmatched_count: 3, pending_saved_count: 1 })).toContain(
      '(2 were already on the list from an earlier import.)',
    );
  });
});
