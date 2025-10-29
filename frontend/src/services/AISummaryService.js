import ApiClient from './ApiClient';


export default {

  async generateSummary(eventId) {
    const response = await ApiClient.post(
      `/admin/events/${eventId}/feedback/summaries/generate`
    );
    return response.data;
  },


  async listSummaries(eventId, limit = 50, offset = 0) {
    const response = await ApiClient.get(
      `/admin/events/${eventId}/feedback/summaries`,
      { params: { limit, offset } }
    );
    return response.data;
  },


  async getSummary(eventId, summaryId) {
    const response = await ApiClient.get(
      `/admin/events/${eventId}/feedback/summaries/${summaryId}`
    );
    return response.data;
  },


  async sendSummary(eventId, summaryId, recipients) {
    const response = await ApiClient.post(
      `/admin/events/${eventId}/feedback/summaries/${summaryId}/send`,
      recipients
    );
    return response.data;
  }
};
