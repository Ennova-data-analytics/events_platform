import ApiClient from './ApiClient';

export const FeedbackService = {
  // Public endpoints
  getFeedbackTemplate(eventId) {
    return ApiClient.get(`/events/${eventId}/feedback/template`);
  },
  submitFeedback(eventId, feedbackData) {
    return ApiClient.post(`/events/${eventId}/feedback`, feedbackData);
  },
  submitFeedbackAuthenticated(eventId, feedbackData) {
    return ApiClient.post(`/events/${eventId}/feedback/authenticated`, feedbackData);
  },

  // Organiser endpoints
  getEventFeedback(eventId, skip = 0, limit = 100) {
    return ApiClient.get(`/events/${eventId}/feedback`, {
      params: { skip, limit }
    });
  },
  getFeedbackStatistics(eventId) {
    return ApiClient.get(`/events/${eventId}/feedback/stats`);
  },
  getFeedbackQRCode(eventId) {
    return ApiClient.get(`/events/${eventId}/feedback/qr`, {
      responseType: 'blob'
    });
  },
  getFeedbackUrl(eventId) {
    return ApiClient.get(`/events/${eventId}/feedback/url`);
  },
};
