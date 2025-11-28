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
  },

  uploadEventPhotos(eventId, photoFiles, processImages = true) {
    const formData = new FormData();
    photoFiles.forEach(file => {
      formData.append('photo_files', file);
    });
    return ApiClient.post(`/events/${eventId}/photos`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      params: { process_images: processImages }
    });
  },

  getEventPhotos(eventId) {
    return ApiClient.get(`/events/${eventId}/photos`);
  },

  deleteEventPhoto(eventId, photoId) {
    return ApiClient.delete(`/events/${eventId}/photos/${photoId}`);
  },

  updateEventPhoto(eventId, photoId, photoData) {
    return ApiClient.patch(`/events/${eventId}/photos/${photoId}`, photoData);
  },

  reorderEventPhotos(eventId, photoIds) {
    return ApiClient.post(`/events/${eventId}/photos/reorder`, { photo_ids: photoIds });
  },

  // Event Attachments Methods
  uploadEventAttachment(eventId, file, description = null) {
    const formData = new FormData();
    formData.append('file', file);
    if (description) {
      formData.append('description', description);
    }
    return ApiClient.post(`/events/${eventId}/attachments`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  },

  getEventAttachments(eventId) {
    return ApiClient.get(`/events/${eventId}/attachments`);
  },

  updateEventAttachment(eventId, attachmentId, updateData) {
    return ApiClient.patch(`/events/${eventId}/attachments/${attachmentId}`, updateData);
  },

  deleteEventAttachment(eventId, attachmentId) {
    return ApiClient.delete(`/events/${eventId}/attachments/${attachmentId}`);
  },

  reorderEventAttachments(eventId, attachmentIds) {
    return ApiClient.post(`/events/${eventId}/attachments/reorder`, { attachment_ids: attachmentIds });
  },

  // Discount Code Methods
  validateDiscountCode(eventId, code) {
    return ApiClient.post('/discount-codes/validate', {
      event_id: eventId,
      code: code
    });
  },

  createDiscountCode(discountCodeData) {
    return ApiClient.post('/discount-codes', discountCodeData);
  },

  getEventDiscountCodes(eventId) {
    return ApiClient.get(`/discount-codes/event/${eventId}`);
  },

  updateDiscountCode(codeId, updateData) {
    return ApiClient.put(`/discount-codes/${codeId}`, updateData);
  },

  deleteDiscountCode(codeId) {
    return ApiClient.delete(`/discount-codes/${codeId}`);
  }
};

// Export individual functions for direct import
export const {
  getAllEvents,
  getEventById,
  createEvent,
  updateEvent,
  deleteEvent,
  registerForEvent,
  getEventRegistrations,
  toggleSignups,
  uploadEventPhotos,
  getEventPhotos,
  deleteEventPhoto,
  updateEventPhoto,
  reorderEventPhotos,
  uploadEventAttachment,
  getEventAttachments,
  updateEventAttachment,
  deleteEventAttachment,
  reorderEventAttachments,
  validateDiscountCode,
  createDiscountCode,
  getEventDiscountCodes,
  updateDiscountCode,
  deleteDiscountCode
} = EventService;
