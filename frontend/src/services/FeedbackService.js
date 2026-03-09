import ApiClient from './ApiClient';

export const FeedbackService = {
  // Public endpoints
  getFeedbackTemplate(eventId, templateId = null) {
    const params = templateId ? { template_id: templateId } : {};
    return ApiClient.get(`/events/${eventId}/feedback/template`, { params });
  },
  submitFeedback(eventId, feedbackData) {
    return ApiClient.post(`/events/${eventId}/feedback`, feedbackData);
  },
  submitFeedbackAuthenticated(eventId, feedbackData) {
    return ApiClient.post(`/events/${eventId}/feedback/authenticated`, feedbackData);
  },
  submitFeedbackViaToken(eventId, token, formResponses) {
    return ApiClient.post(`/events/${eventId}/feedback/via-token`, { token, form_responses: formResponses });
  },

  // Organiser endpoints
  getEventFeedback(eventId, skip = 0, limit = 100) {
    return ApiClient.get(`/events/${eventId}/feedback`, { params: { skip, limit } });
  },
  getFeedbackStatistics(eventId) {
    return ApiClient.get(`/events/${eventId}/feedback/stats`);
  },
  getFeedbackQRCode(eventId, templateId = null) {
    const params = templateId ? { template_id: templateId } : {};
    return ApiClient.get(`/events/${eventId}/feedback/qr`, { responseType: 'blob', params });
  },
  getFeedbackUrl(eventId, templateId = null) {
    const params = templateId ? { template_id: templateId } : {};
    return ApiClient.get(`/events/${eventId}/feedback/url`, { params });
  },

  // Event ↔ FeedbackTemplate management
  getEventFeedbackTemplates(eventId) {
    return ApiClient.get(`/events/${eventId}/feedback/templates`);
  },
  attachFeedbackTemplate(eventId, templateId, isPrimary = false) {
    return ApiClient.post(`/events/${eventId}/feedback/templates`, { template_id: templateId, is_primary: isPrimary });
  },
  detachFeedbackTemplate(eventId, templateId) {
    return ApiClient.delete(`/events/${eventId}/feedback/templates/${templateId}`);
  },
  setPrimaryFeedbackTemplate(eventId, templateId) {
    return ApiClient.patch(`/events/${eventId}/feedback/templates/${templateId}/set-primary`);
  },

  // Invitation management
  previewInvitations(eventId, payload) {
    return ApiClient.post(`/events/${eventId}/feedback/invitations/preview`, payload);
  },
  sendInvitations(eventId, payload) {
    return ApiClient.post(`/events/${eventId}/feedback/invitations/send`, payload);
  },
  resendInvitations(eventId, payload) {
    return ApiClient.post(`/events/${eventId}/feedback/invitations/resend`, payload);
  },
  getInvitationStats(eventId) {
    return ApiClient.get(`/events/${eventId}/feedback/invitations/stats`);
  },
};
