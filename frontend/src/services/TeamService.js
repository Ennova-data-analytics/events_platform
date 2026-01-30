import ApiClient from './ApiClient.js';

export const TeamService = {
  
  getTeamsForEvent(eventId) {
    return ApiClient.get(`/events/${eventId}/teams`);
  },

  getTeamById(eventId, teamId) {
    return ApiClient.get(`/events/${eventId}/teams/${teamId}`);
  },


  createTeam(eventId, teamData) {
    return ApiClient.post(`/events/${eventId}/teams`, teamData);
  },

  updateTeam(eventId, teamId, updateData) {
    return ApiClient.put(`/events/${eventId}/teams/${teamId}`, updateData);
  },

  deleteTeam(eventId, teamId, force = false) {
    return ApiClient.delete(`/events/${eventId}/teams/${teamId}`, {
      params: { force }
    });
  },


  addMemberToTeam(eventId, teamId, registrationId) {
    return ApiClient.post(`/events/${eventId}/teams/${teamId}/members/${registrationId}`);
  },

  removeMemberFromTeam(eventId, teamId, registrationId) {
    return ApiClient.delete(`/events/${eventId}/teams/${teamId}/members/${registrationId}`);
  }
};
