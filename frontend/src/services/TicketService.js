import ApiClient from './ApiClient';
import { useAuthStore } from '@/stores/auth.store';

async function downloadBlob(url, filename, authenticated = true) {
  const headers = {};
  if (authenticated) {
    const authStore = useAuthStore();
    if (authStore.token) headers['Authorization'] = `Bearer ${authStore.token}`;
  }
  const response = await fetch(url, { headers });
  if (!response.ok) throw new Error('Download failed');
  const blob = await response.blob();
  const link = document.createElement('a');
  link.href = window.URL.createObjectURL(blob);
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(link.href);
}

export const TicketService = {
  // -------------------------------------------------------------------------
  // User ticket (auth required)
  // -------------------------------------------------------------------------

  getMyTicketInfo(registrationId) {
    return ApiClient.get(`/tickets/my/${registrationId}`);
  },

  getMyTicketQrUrl(registrationId) {
    return `/api/tickets/my/${registrationId}/qr`;
  },

  async downloadMyTicketPdf(registrationId, eventName) {
    const authStore = useAuthStore();
    const safe = (eventName || 'ticket').replace(/\s+/g, '_').slice(0, 50);
    await downloadBlob(
      `/api/tickets/my/${registrationId}/pdf`,
      `ticket-${safe}.pdf`,
      true,
    );
  },

  // -------------------------------------------------------------------------
  // Public token-based (guest + shareable links)
  // -------------------------------------------------------------------------

  getTicketByToken(token) {
    return ApiClient.get(`/tickets/view/${token}`);
  },

  getTicketQrUrl(token) {
    return `/api/tickets/view/${token}/qr`;
  },

  async downloadTicketPdf(token, eventName) {
    const safe = (eventName || 'ticket').replace(/\s+/g, '_').slice(0, 50);
    await downloadBlob(
      `/api/tickets/view/${token}/pdf`,
      `ticket-${safe}.pdf`,
      false,
    );
  },

  // -------------------------------------------------------------------------
  // Scanner (organiser)
  // -------------------------------------------------------------------------

  checkIn(token) {
    return ApiClient.post(`/tickets/check-in/${token}`);
  },

  // -------------------------------------------------------------------------
  // Guest tickets (organiser)
  // -------------------------------------------------------------------------

  createGuestTicket(eventId, { guest_name, guest_email }) {
    return ApiClient.post(`/admin/events/${eventId}/guest-tickets`, { guest_name, guest_email });
  },

  listGuestTickets(eventId) {
    return ApiClient.get(`/admin/events/${eventId}/guest-tickets`);
  },

  deleteGuestTicket(ticketId) {
    return ApiClient.delete(`/admin/guest-tickets/${ticketId}`);
  },

  resendGuestTicketEmail(ticketId) {
    return ApiClient.post(`/admin/guest-tickets/${ticketId}/resend`);
  },

  // -------------------------------------------------------------------------
  // Attendance sessions (multi-day)
  // -------------------------------------------------------------------------

  freezeSession(eventId, label) {
    return ApiClient.post(`/admin/events/${eventId}/sessions/freeze`, { label });
  },

  listSessions(eventId) {
    return ApiClient.get(`/admin/events/${eventId}/sessions`);
  },

  getSessionRecords(sessionId) {
    return ApiClient.get(`/admin/sessions/${sessionId}/records`);
  },
};