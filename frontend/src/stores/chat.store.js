import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { ChatService } from '@/services/ChatService';

export const useChatStore = defineStore('chat', () => {
  const chats = ref([]);
  const currentChatId = ref(null);
  const currentMessages = ref([]);
  const isLoading = ref(false);
  const error = ref(null);

  const hasCurrentChat = computed(() => !!currentChatId.value);

  async function createChat() {
    try {
      isLoading.value = true;
      error.value = null;

      const response = await ChatService.createChat();
      currentChatId.value = response.data.id;
      currentMessages.value = [];

      return response.data;
    } catch (err) {
      console.error('Failed to create chat:', err);
      error.value = err.response?.data?.detail || 'Failed to create chat';
      throw err;
    } finally {
      isLoading.value = false;
    }
  }

  async function loadChats() {
    try {
      isLoading.value = true;
      error.value = null;

      const response = await ChatService.listChats();
      chats.value = response.data;
    } catch (err) {
      console.error('Failed to load chats:', err);
      error.value = err.response?.data?.detail || 'Failed to load chats';
      throw err;
    } finally {
      isLoading.value = false;
    }
  }

  async function loadChatHistory() {
    if (!currentChatId.value) return;

    try {
      isLoading.value = true;
      error.value = null;

      const response = await ChatService.getChat(currentChatId.value);
      currentMessages.value = response.data.messages;
    } catch (err) {
      console.error('Failed to load chat history:', err);
      error.value = err.response?.data?.detail || 'Failed to load chat history';
      throw err;
    } finally {
      isLoading.value = false;
    }
  }

  async function sendMessage(content) {
    if (!currentChatId.value) {
      await createChat();
    }

    const userMessage = {
      role: 'user',
      content,
      created_at: new Date().toISOString()
    };

    currentMessages.value.push(userMessage);

    try {
      const response = await ChatService.sendMessage(currentChatId.value, content);

      // Stream the response
      const reader = response.body.getReader();
      const decoder = new TextDecoder();

      let assistantMessage = {
        role: 'assistant',
        content: '',
        created_at: new Date().toISOString()
      };

      currentMessages.value.push(assistantMessage);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        assistantMessage.content += chunk;
      }

      return assistantMessage;
    } catch (err) {
      currentMessages.value.pop(); // Remove assistant message on error
      error.value = err.message || 'Failed to send message';
      throw err;
    }
  }

  async function deleteChat(chatId) {
    try {
      await ChatService.deleteChat(chatId);
      chats.value = chats.value.filter(chat => chat.id !== chatId);

      if (currentChatId.value === chatId) {
        currentChatId.value = null;
        currentMessages.value = [];
      }
    } catch (err) {
      console.error('Failed to delete chat:', err);
      error.value = err.response?.data?.detail || 'Failed to delete chat';
      throw err;
    }
  }

  function clearError() {
    error.value = null;
  }

  return {
    chats,
    currentChatId,
    currentMessages,
    isLoading,
    error,
    hasCurrentChat,
    createChat,
    loadChats,
    loadChatHistory,
    sendMessage,
    deleteChat,
    clearError
  };
});
