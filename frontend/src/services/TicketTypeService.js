import apiClient from './ApiClient';

/**
 * Service for managing ticket types
 */
class TicketTypeService {
  /**
   * Get all ticket types for an event
   * @param {number} eventId - Event ID
   * @param {boolean} activeOnly - Only return active ticket types
   * @param {boolean} includeDeleted - Organisers: also return deleted_ticket_types
   * @returns {Promise} - Promise resolving to ticket types list
   */
  async getTicketTypes(eventId, activeOnly = false, includeDeleted = false) {
    const response = await apiClient.get(`/events/${eventId}/ticket-types`, {
      params: { active_only: activeOnly, include_deleted: includeDeleted }
    });
    return response.data;
  }

  /**
   * Get a specific ticket type
   * @param {number} eventId - Event ID
   * @param {number} ticketTypeId - Ticket type ID
   * @returns {Promise} - Promise resolving to ticket type details
   */
  async getTicketType(eventId, ticketTypeId) {
    const response = await apiClient.get(`/events/${eventId}/ticket-types/${ticketTypeId}`);
    return response.data;
  }

  /**
   * Create a new ticket type
   * @param {number} eventId - Event ID
   * @param {object} ticketTypeData - Ticket type data
   * @returns {Promise} - Promise resolving to created ticket type
   */
  async createTicketType(eventId, ticketTypeData) {
    const response = await apiClient.post(`/events/${eventId}/ticket-types`, ticketTypeData);
    return response.data;
  }

  /**
   * Update a ticket type
   * @param {number} eventId - Event ID
   * @param {number} ticketTypeId - Ticket type ID
   * @param {object} ticketTypeData - Updated ticket type data
   * @returns {Promise} - Promise resolving to updated ticket type
   */
  async updateTicketType(eventId, ticketTypeId, ticketTypeData) {
    const response = await apiClient.put(`/events/${eventId}/ticket-types/${ticketTypeId}`, ticketTypeData);
    return response.data;
  }

  /**
   * Delete a ticket type. Removed if nobody registered for it; otherwise taken
   * off sale and hidden, and the people registered keep it.
   * @param {number} eventId - Event ID
   * @param {number} ticketTypeId - Ticket type ID
   * @returns {Promise<{ticket_type_id: number, outcome: 'deleted'|'hidden', holders: number}>}
   */
  async deleteTicketType(eventId, ticketTypeId) {
    const response = await apiClient.delete(`/events/${eventId}/ticket-types/${ticketTypeId}`);
    return response.data;
  }

  /**
   * Toggle active status of a ticket type
   * @param {number} eventId - Event ID
   * @param {number} ticketTypeId - Ticket type ID
   * @returns {Promise} - Promise resolving to updated ticket type
   */
  async toggleActive(eventId, ticketTypeId) {
    const response = await apiClient.patch(`/events/${eventId}/ticket-types/${ticketTypeId}/toggle-active`);
    return response.data;
  }

  /**
   * Reorder ticket types
   * @param {number} eventId - Event ID
   * @param {number[]} ticketTypeIds - Array of ticket type IDs in desired order
   * @returns {Promise} - Promise resolving to reordered ticket types
   */
  async reorderTicketTypes(eventId, ticketTypeIds) {
    const response = await apiClient.post(`/events/${eventId}/ticket-types/reorder`, ticketTypeIds);
    return response.data;
  }

  /**
   * Check ticket availability
   * @param {number} eventId - Event ID
   * @param {number} ticketTypeId - Ticket type ID
   * @param {number} quantity - Number of tickets to check
   * @returns {Promise} - Promise resolving to availability info
   */
  async checkAvailability(eventId, ticketTypeId, quantity = 1) {
    const response = await apiClient.get(`/events/${eventId}/ticket-types/${ticketTypeId}/availability`, {
      params: { quantity }
    });
    return response.data;
  }
}

export default new TicketTypeService();
