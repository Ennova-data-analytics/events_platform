import ApiClient from './ApiClient';
import { useAuthStore } from '@/stores/auth.store';

export const ChatService = {
  // Create a new chat
  async createChat() {
    return await ApiClient.post('/chat/', {});
  },

  // List all chats for current user
  async listChats(skip = 0, limit = 50) {
    return await ApiClient.get('/chat/', {
      params: { skip, limit }
    });
  },

  // Get specific chat with messages
  async getChat(chatId) {
    return await ApiClient.get(`/chat/${chatId}`);
  },

  // Send message (streaming)
  async sendMessage(chatId, content) {
    const authStore = useAuthStore();
    const token = authStore.token;

    const response = await fetch(`/api/chat/${chatId}/messages`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ content })
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Failed to send message');
    }

    return response;
  },

  // Delete chat
  async deleteChat(chatId) {
    return await ApiClient.delete(`/chat/${chatId}`);
  },

  // Update chat title
  async updateChatTitle(chatId, title) {
    return await ApiClient.patch(`/chat/${chatId}/title`, { title });
  },

  // Vectorize document (admin only)
  async vectorizeDocument(file, eventId = null) {
    const formData = new FormData();
    formData.append('file', file);
    if (eventId) {
      formData.append('event_id', eventId);
    }

    return await ApiClient.post('/chat/documents/vectorize', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
  }
};
