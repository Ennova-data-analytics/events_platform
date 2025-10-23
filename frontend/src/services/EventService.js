import ApiClient from './ApiClient';

export const EventService = {
  getAllEvents() {
    return ApiClient.get('/events');
  },

  getEventById(id) {
    return ApiClient.get(`/events/${id}`);
  },

  createEvent(eventData) {
    return ApiClient.post('/events', eventData);
  },

  updateEvent(id, eventData) {
    return ApiClient.put(`/events/${id}`, eventData);
  },

  deleteEvent(eventId) {
    return ApiClient.delete(`/events/${eventId}`);
  },

  registerForEvent(eventId, registrationData) {
    return ApiClient.post(`/events/${eventId}/register`, registrationData);
  },

  getEventRegistrations(eventId) {
    return ApiClient.get(`/events/${eventId}/registrations`);
  },

  toggleSignups(eventId) {
    return ApiClient.patch(`/events/${eventId}/toggle-signups`);
  }
};
