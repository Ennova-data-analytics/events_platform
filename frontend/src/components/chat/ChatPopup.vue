<template>
  <div v-if="authStore.isOrganiser">
    <!-- Floating Chat Button -->
    <v-btn
      icon="mdi-chat-outline"
      color="primary"
      :size="$vuetify.display.mobile ? 'default' : 'large'"
      position="fixed"
      location="bottom right"
      class="chat-btn"
      elevation="8"
      @click="toggleChat"
    >
      <v-icon>mdi-chat-outline</v-icon>
      <v-tooltip activator="parent" location="left">Ask Ennova AI</v-tooltip>
    </v-btn>

    <!-- Chat Dialog -->
    <v-dialog
      v-model="isOpen"
      :fullscreen="$vuetify.display.mobile"
      :max-width="$vuetify.display.mobile ? '100%' : '600px'"
      transition="dialog-bottom-transition"
      persistent
      no-click-animation
    >
      <v-card class="chat-card" elevation="24">
        <!-- Header -->
        <v-card-title class="chat-header bg-primary d-flex align-center pa-4">
          <v-avatar size="40" color="white" class="mr-3">
            <v-icon color="primary">mdi-robot-happy</v-icon>
          </v-avatar>
          <div class="flex-grow-1">
            <div class="text-h6 text-white">Ennova AI Assistant</div>
            <div class="text-caption text-white opacity-80">Ask about events & association</div>
          </div>
          <v-btn
            icon
            variant="text"
            class="text-white"
            @click="minimizeChat"
          >
            <v-icon color="white">mdi-minus</v-icon>
          </v-btn>
          <v-btn
            icon
            variant="text"
            class="text-white"
            @click="closeChat"
          >
            <v-icon color="white">mdi-close</v-icon>
          </v-btn>
        </v-card-title>

        <!-- Messages Container -->
        <v-card-text
          ref="messagesContainer"
          class="messages-container pa-4"
          :style="{ height: $vuetify.display.mobile ? 'calc(100vh - 200px)' : '500px' }"
        >
          <!-- Welcome Message -->
          <div v-if="chatStore.currentMessages.length === 0" class="welcome-message text-center pa-8">
            <v-icon size="64" color="primary" class="mb-4">mdi-robot-happy-outline</v-icon>
            <h3 class="text-h6 mb-2">Hi! I'm your Ennova AI Assistant</h3>
            <p class="text-body-2 text-medium-emphasis">
              Ask me about upcoming events, membership, or how to get involved with Ennova!
            </p>

            <!-- Quick Questions -->
            <div class="mt-6">
              <v-chip
                v-for="(question, i) in quickQuestions"
                :key="i"
                class="ma-1"
                variant="outlined"
                @click="sendQuickQuestion(question)"
              >
                {{ question }}
              </v-chip>
            </div>
          </div>

          <!-- Messages List -->
          <div v-else>
            <div
              v-for="(message, index) in chatStore.currentMessages"
              :key="index"
              :class="['message-wrapper', message.role === 'user' ? 'user-message' : 'assistant-message']"
            >
              <v-card
                :class="['message-bubble', message.role === 'user' ? 'user-bubble' : 'assistant-bubble']"
                elevation="1"
              >
                <v-card-text class="pa-3">
                  <div v-if="message.role === 'assistant'" class="d-flex align-start">
                    <v-avatar size="24" color="primary" class="mr-2 mt-1">
                      <v-icon size="16" color="white">mdi-robot</v-icon>
                    </v-avatar>
                    <div class="flex-grow-1">
                      <div class="message-content" v-html="formatMessage(message.content)"></div>
                      <div class="text-caption text-medium-emphasis mt-1">
                        {{ formatTime(message.created_at) }}
                      </div>
                    </div>
                  </div>
                  <div v-else>
                    <div class="message-content">{{ message.content }}</div>
                    <div class="text-caption text-white opacity-70 mt-1 text-right">
                      {{ formatTime(message.created_at) }}
                    </div>
                  </div>
                </v-card-text>
              </v-card>
            </div>

            <!-- Typing Indicator -->
            <div v-if="isTyping" class="message-wrapper assistant-message">
              <v-card class="message-bubble assistant-bubble" elevation="1">
                <v-card-text class="pa-3 d-flex align-center">
                  <v-avatar size="24" color="primary" class="mr-2">
                    <v-icon size="16" color="white">mdi-robot</v-icon>
                  </v-avatar>
                  <div class="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                </v-card-text>
              </v-card>
            </div>
          </div>
        </v-card-text>

        <!-- Input Area -->
        <v-divider></v-divider>
        <v-card-actions class="pa-4">
          <v-text-field
            v-model="inputMessage"
            placeholder="Ask about Ennova events..."
            variant="outlined"
            density="comfortable"
            hide-details
            class="flex-grow-1"
            :disabled="isTyping"
            @keydown.enter="sendMessage"
          >
            <template #append-inner>
              <v-btn
                icon
                size="small"
                color="primary"
                :disabled="!inputMessage.trim() || isTyping"
                :loading="isTyping"
                @click="sendMessage"
              >
                <v-icon>mdi-send</v-icon>
              </v-btn>
            </template>
          </v-text-field>
        </v-card-actions>

        <!-- Footer -->
        <v-card-text class="text-center text-caption text-medium-emphasis pa-2">
          Powered by Ennova AI • Rate limited to 10 messages/min
        </v-card-text>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted } from 'vue';
import { useChatStore } from '@/stores/chat.store';
import { useAuthStore } from '@/stores/auth.store';
import { marked } from 'marked';

const chatStore = useChatStore();
const authStore = useAuthStore();

const isOpen = ref(false);
const inputMessage = ref('');
const messagesContainer = ref(null);
const isTyping = ref(false);

const quickQuestions = [
  'What events are coming up?',
  'How do I become a member?',
  'Tell me about Ennova',
  'How do I register for an event?'
];

const toggleChat = async () => {
  isOpen.value = !isOpen.value;
  if (isOpen.value && !chatStore.hasCurrentChat) {
    await chatStore.createChat();
  }
};

const closeChat = () => {
  isOpen.value = false;
};

const minimizeChat = () => {
  isOpen.value = false;
};

const sendQuickQuestion = (question) => {
  inputMessage.value = question;
  sendMessage();
};

const sendMessage = async () => {
  if (!inputMessage.value.trim() || isTyping.value) return;

  const messageText = inputMessage.value.trim();
  inputMessage.value = '';
  isTyping.value = true;

  try {
    await chatStore.sendMessage(messageText);
  } catch (error) {
    console.error('Error sending message:', error);
  } finally {
    isTyping.value = false;
    await nextTick();
    scrollToBottom();
  }
};

const scrollToBottom = () => {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight;
  }
};

const formatMessage = (content) => {
  return marked.parse(content);
};

const formatTime = (timestamp) => {
  if (!timestamp) return '';
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
  return date.toLocaleDateString();
};

onMounted(async () => {
  if (chatStore.hasCurrentChat) {
    await chatStore.loadChatHistory();
    await nextTick();
    scrollToBottom();
  }
});
</script>

<style scoped>
.chat-btn {
  margin: 0 24px 85px 0;
  z-index: 1000;
}

.chat-card {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.chat-header {
  position: sticky;
  top: 0;
  z-index: 10;
}

.messages-container {
  overflow-y: auto;
  overflow-x: hidden;
  flex: 1;
  background: #f5f5f5;
}

.welcome-message {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
}

.message-wrapper {
  margin-bottom: 16px;
  display: flex;
}

.user-message {
  justify-content: flex-end;
}

.assistant-message {
  justify-content: flex-start;
}

.message-bubble {
  max-width: 85%;
  word-wrap: break-word;
}

.user-bubble {
  background: rgb(var(--v-theme-primary));
  color: white;
}

.assistant-bubble {
  background: white;
}

.message-content {
  line-height: 1.6;
}

.message-content :deep(p) {
  margin: 0;
}

.message-content :deep(ul),
.message-content :deep(ol) {
  margin: 8px 0;
  padding-left: 20px;
}

.message-content :deep(code) {
  background: rgba(0, 0, 0, 0.05);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.9em;
}

/* Typing Indicator */
.typing-indicator {
  display: flex;
  gap: 4px;
  align-items: center;
  padding: 8px 0;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  background: #999;
  border-radius: 50%;
  animation: typing 1.4s infinite;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 60%, 100% {
    transform: translateY(0);
    opacity: 0.5;
  }
  30% {
    transform: translateY(-10px);
    opacity: 1;
  }
}

/* Scrollbar Styling */
.messages-container::-webkit-scrollbar {
  width: 6px;
}

.messages-container::-webkit-scrollbar-track {
  background: transparent;
}

.messages-container::-webkit-scrollbar-thumb {
  background: #ccc;
  border-radius: 3px;
}

.messages-container::-webkit-scrollbar-thumb:hover {
  background: #999;
}
</style>
