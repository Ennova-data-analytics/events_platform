import ApiClient from './ApiClient';

export const EventService = {
  // includeUnpublished is honoured for organisers only; the API ignores it for
  // everyone else, so the public list never sees drafts.
  getAllEvents({ includeUnpublished = false } = {}) {
    return ApiClient.get('/events', {
      params: includeUnpublished ? { include_unpublished: true } : {},
    });
  },

  getEventById(id) {
    return ApiClient.get(`/events/${id}`);
  },

  duplicateEvent(id, payload = {}) {
    return ApiClient.post(`/events/${id}/duplicate`, payload);
  },

  updateEventStatus(id, status) {
    return ApiClient.patch(`/events/${id}/status`, { status });
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

  // Donate to a charity event without registering. Public - no account needed.
  donateToEvent(eventId, { email, amountEuros }) {
    return ApiClient.post(`/events/${eventId}/donate`, { email, amount_euros: amountEuros });
  },

  getEventDonations(eventId) {
    return ApiClient.get(`/events/${eventId}/donations`);
  },

  updateRegistrationFormResponses(eventId, formResponses) {
    return ApiClient.patch(`/events/${eventId}/registration/form-responses`, { form_responses: formResponses });
  },

  updateCharityEmailConsent(eventId, consent) {
    return ApiClient.patch(`/events/${eventId}/registration/charity-email-consent`, { charity_email_consent: consent });
  },

  getMyTeam(eventId) {
    return ApiClient.get(`/events/${eventId}/my-team`);
  },

  getTeamInvitePreview(eventId, token) {
    return ApiClient.get(`/events/${eventId}/invite-preview`, { params: { token } });
  },

  claimTeamInvite(eventId, token) {
    return ApiClient.post(`/events/${eventId}/claim-invite`, null, { params: { token } });
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
  },

  getDiscountCodeUsages(codeId) {
    return ApiClient.get(`/discount-codes/${codeId}/usages`);
  },

  backpopulateDiscountCode(codeId) {
    return ApiClient.post(`/discount-codes/${codeId}/backpopulate`);
  },

  createReferralLink(data) {
    return ApiClient.post('/referral-links', data);
  },

  getEventReferralLinks(eventId) {
    return ApiClient.get(`/referral-links/event/${eventId}`);
  },

  updateReferralLink(linkId, updateData) {
    return ApiClient.put(`/referral-links/${linkId}`, updateData);
  },

  deleteReferralLink(linkId) {
    return ApiClient.delete(`/referral-links/${linkId}`);
  },

  getReferralLinkUsages(linkId) {
    return ApiClient.get(`/referral-links/${linkId}/usages`);
  }
};

// Export individual functions for direct import
export const {
  getAllEvents,
  getEventById,
  duplicateEvent,
  updateEventStatus,
  createEvent,
  updateEvent,
  deleteEvent,
  registerForEvent,
  updateRegistrationFormResponses,
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
  deleteDiscountCode,
  createReferralLink,
  getEventReferralLinks,
  updateReferralLink,
  deleteReferralLink,
  getDiscountCodeUsages,
  backpopulateDiscountCode,
  getReferralLinkUsages
} = EventService;
