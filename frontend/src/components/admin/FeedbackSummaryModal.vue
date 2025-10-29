<template>
  <v-dialog v-model="dialog" max-width="1000px" scrollable>
    <v-card>
      <!-- Header -->
      <v-card-title class="d-flex align-center pa-4">
        <v-icon class="mr-2">mdi-brain</v-icon>
        <span class="text-h5">AI Feedback Analysis</span>
        <v-spacer></v-spacer>
        <v-btn icon @click="close" variant="text">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>

      <!-- Loading State -->
      <v-card-text v-if="loading" class="text-center pa-8">
        <v-progress-circular
          indeterminate
          color="primary"
          size="64"
        ></v-progress-circular>
        <p class="mt-4 text-h6">{{ loadingMessage }}</p>
        <p class="text-caption text-medium-emphasis">This may take 10-30 seconds...</p>
      </v-card-text>

      <!-- Error State -->
      <v-alert v-if="error" type="error" class="ma-4">
        {{ error }}
      </v-alert>

      <!-- Summary Content -->
      <v-card-text v-if="!loading && summary" style="max-height: 600px;" class="pa-6">
        <!-- Metadata -->
        <v-row class="mb-4">
          <v-col cols="12" md="4">
            <v-chip variant="tonal" prepend-icon="mdi-chart-box" size="small">
              {{ summary.feedback_count }} Responses
            </v-chip>
          </v-col>
          <v-col cols="12" md="4">
            <v-chip variant="tonal" prepend-icon="mdi-calendar" size="small">
              {{ formatDate(summary.generated_at) }}
            </v-chip>
          </v-col>
          <v-col cols="12" md="4">
            <v-chip variant="tonal" prepend-icon="mdi-robot" size="small">
              {{ summary.model_used }}
            </v-chip>
          </v-col>
        </v-row>

        <v-divider class="mb-4"></v-divider>

        <!-- Sentiment Score -->
        <v-card v-if="summary.summary_json?.sentiment_score" class="mb-4" variant="tonal">
          <v-card-text>
            <div class="d-flex align-center justify-space-between">
              <div>
                <div class="text-caption text-medium-emphasis">Overall Sentiment</div>
                <div class="text-h6 mt-1 text-capitalize">
                  {{ summary.summary_json.sentiment }}
                  <v-icon :color="getSentimentColor(summary.summary_json.sentiment)" size="small">
                    {{ getSentimentIcon(summary.summary_json.sentiment) }}
                  </v-icon>
                </div>
              </div>
              <v-rating
                :model-value="summary.summary_json.sentiment_score / 2"
                half-increments
                readonly
                color="amber"
                size="small"
                density="compact"
              ></v-rating>
            </div>
            <v-progress-linear
              :model-value="summary.summary_json.sentiment_score * 10"
              :color="getSentimentColor(summary.summary_json.sentiment)"
              height="6"
              rounded
              class="mt-3"
            ></v-progress-linear>
          </v-card-text>
        </v-card>

        <!-- Markdown Content -->
        <div v-html="renderedMarkdown" class="markdown-content"></div>

        <!-- Email Send Section -->
        <v-divider class="my-6" v-if="!sendSuccess"></v-divider>

        <v-expand-transition>
          <div v-if="showEmailSection && !sendSuccess">
            <v-card variant="outlined" class="pa-4">
              <v-card-subtitle class="text-subtitle-1 font-weight-medium pa-0 mb-3">
                Send Summary via Email
              </v-card-subtitle>

              <v-card-text class="pa-0">
                <!-- Recipient Selection -->
                <div class="mb-4">
                  <div class="text-body-2 mb-2">Select Recipients:</div>

                  <v-chip-group v-model="selectedStatuses" column multiple>
                    <v-chip
                      v-for="status in availableStatuses"
                      :key="status"
                      filter
                      variant="outlined"
                      :value="status"
                      size="small"
                    >
                      {{ status }}
                    </v-chip>
                  </v-chip-group>
                </div>

                <!-- Custom Emails -->
                <v-text-field
                  v-model="customEmails"
                  label="Additional Email Addresses (comma-separated)"
                  placeholder="user1@example.com, user2@example.com"
                  variant="outlined"
                  density="compact"
                  prepend-inner-icon="mdi-email-plus"
                  hint="Optional: Add custom email addresses"
                  persistent-hint
                  class="mb-3"
                ></v-text-field>

                <!-- Include Organizers -->
                <v-checkbox
                  v-model="includeOrganizers"
                  label="Include event organizers"
                  density="compact"
                  hide-details
                ></v-checkbox>

                <!-- Recipient Count Preview -->
                <v-alert v-if="recipientPreview" type="info" variant="tonal" density="compact" class="mt-3">
                  {{ recipientPreview }}
                </v-alert>
              </v-card-text>
            </v-card>
          </div>
        </v-expand-transition>

        <!-- Send Success Message -->
        <v-alert v-if="sendSuccess" type="success" variant="tonal" class="mt-4">
          <v-icon class="mr-2">mdi-check-circle</v-icon>
          Successfully sent to {{ sendResult.sent_count }} recipient(s)
          <span v-if="sendResult.failed_count > 0">
            ({{ sendResult.failed_count }} failed)
          </span>
        </v-alert>
      </v-card-text>

      <!-- Actions -->
      <v-card-actions class="pa-4" v-if="!loading && summary">
        <!-- Send Now Button (shown first when email section is open) -->
        <v-btn
          v-if="showEmailSection && !sendSuccess"
          color="primary"
          @click="sendEmail"
          :loading="sending"
          :disabled="!canSend"
          prepend-icon="mdi-send"
        >
          Send Now
        </v-btn>

        <!-- Send via Email Button (shown when email section is closed) -->
        <v-btn
          v-if="!showEmailSection && !sendSuccess"
          color="primary"
          @click="showEmailSection = true"
          prepend-icon="mdi-email-send"
        >
          Send via Email
        </v-btn>

        <!-- Cancel Button -->
        <v-btn
          v-if="showEmailSection && !sendSuccess"
          variant="text"
          @click="showEmailSection = false"
        >
          Cancel
        </v-btn>

        <v-spacer></v-spacer>

        <!-- Close Button -->
        <v-btn
          variant="text"
          @click="close"
        >
          Close
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script>
import { marked } from 'marked';
import AISummaryService from '@/services/AISummaryService';

export default {
  name: 'FeedbackSummaryModal',

  props: {
    modelValue: {
      type: Boolean,
      default: false
    },
    eventId: {
      type: Number,
      required: true
    },
    summaryData: {
      type: Object,
      default: null
    }
  },

  emits: ['update:modelValue', 'summary-generated', 'summary-sent'],

  data() {
    return {
      loading: false,
      loadingMessage: 'Analyzing feedback...',
      error: null,
      summary: null,
      showEmailSection: false,
      sending: false,
      sendSuccess: false,
      sendResult: null,

      // Email form
      selectedStatuses: [],
      customEmails: '',
      includeOrganizers: false,

      // Available registration statuses
      availableStatuses: ['Pending Approval', 'Approved', 'Paid', 'Rejected']
    };
  },

  computed: {
    dialog: {
      get() {
        return this.modelValue;
      },
      set(value) {
        this.$emit('update:modelValue', value);
      }
    },

    renderedMarkdown() {
      if (!this.summary?.summary_text) return '';
      return marked(this.summary.summary_text);
    },

    canSend() {
      return this.selectedStatuses.length > 0 ||
             this.customEmails.trim() !== '' ||
             this.includeOrganizers;
    },

    recipientPreview() {
      const parts = [];

      if (this.selectedStatuses.length > 0) {
        parts.push(`${this.selectedStatuses.length} registration status group(s)`);
      }

      if (this.customEmails.trim()) {
        const emails = this.customEmails.split(',').filter(e => e.trim());
        parts.push(`${emails.length} custom email(s)`);
      }

      if (this.includeOrganizers) {
        parts.push('organizers');
      }

      if (parts.length === 0) return null;

      return `Will send to: ${parts.join(', ')}`;
    }
  },

  watch: {
    modelValue(newVal) {
      if (newVal) {
        this.onOpen();
      } else {
        this.onClose();
      }
    }
  },

  methods: {
    async onOpen() {
      if (this.summaryData) {
        // Display existing summary
        this.summary = this.summaryData;
        this.loading = false;
      } else {
        // Generate new summary
        await this.generateSummary();
      }
    },

    onClose() {
      // Reset state
      this.showEmailSection = false;
      this.sendSuccess = false;
      this.sendResult = null;
      this.error = null;
      this.selectedStatuses = [];
      this.customEmails = '';
      this.includeOrganizers = false;
    },

    async generateSummary() {
      this.loading = true;
      this.loadingMessage = 'Analyzing feedback with AI...';
      this.error = null;

      try {
        const response = await AISummaryService.generateSummary(this.eventId);
        this.summary = response;
        this.$emit('summary-generated', response);
      } catch (err) {
        console.error('Failed to generate summary:', err);
        this.error = err.response?.data?.detail || 'Failed to generate AI summary. Please try again.';
      } finally {
        this.loading = false;
      }
    },

    async sendEmail() {
      this.sending = true;
      this.error = null;

      try {
        const customEmailList = this.customEmails
          .split(',')
          .map(e => e.trim())
          .filter(e => e);

        const payload = {
          recipient_statuses: this.selectedStatuses,
          custom_emails: customEmailList.length > 0 ? customEmailList : null,
          include_organizers: this.includeOrganizers
        };

        const response = await AISummaryService.sendSummary(
          this.eventId,
          this.summary.summary_id,
          payload
        );

        this.sendResult = response;
        this.sendSuccess = true;
        this.showEmailSection = false;
        this.$emit('summary-sent', response);
      } catch (err) {
        console.error('Failed to send summary:', err);
        this.error = err.response?.data?.detail || 'Failed to send summary. Please try again.';
      } finally {
        this.sending = false;
      }
    },

    close() {
      this.dialog = false;
    },

    formatDate(dateString) {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      });
    },

    getSentimentColor(sentiment) {
      const colors = {
        positive: 'success',
        neutral: 'warning',
        negative: 'error'
      };
      return colors[sentiment?.toLowerCase()] || 'grey';
    },

    getSentimentIcon(sentiment) {
      const icons = {
        positive: 'mdi-emoticon-happy',
        neutral: 'mdi-emoticon-neutral',
        negative: 'mdi-emoticon-sad'
      };
      return icons[sentiment?.toLowerCase()] || 'mdi-emoticon-neutral';
    }
  }
};
</script>

<style scoped>
.markdown-content {
  line-height: 1.7;
}

.markdown-content :deep(h1) {
  font-size: 1.75rem;
  font-weight: 600;
  margin: 1.5rem 0 1rem;
  padding-bottom: 0.5rem;
}

.markdown-content :deep(h2) {
  font-size: 1.375rem;
  font-weight: 600;
  margin: 1.25rem 0 0.75rem;
  padding-bottom: 0.3rem;
}

.markdown-content :deep(h3) {
  font-size: 1.125rem;
  font-weight: 600;
  margin: 1rem 0 0.5rem;
}

.markdown-content :deep(p) {
  margin: 0.75rem 0;
}

.markdown-content :deep(ul),
.markdown-content :deep(ol) {
  margin: 0.75rem 0;
  padding-left: 1.5rem;
}

.markdown-content :deep(li) {
  margin: 0.4rem 0;
}

.markdown-content :deep(blockquote) {
  border-left: 4px solid rgb(var(--v-theme-primary));
  margin: 0.5rem 0;
  padding: 1rem 1.5rem;
  background: rgba(var(--v-theme-primary), 0.05);
  font-style: italic;
  opacity: 1;
  border-radius: 4px;
  font-size: 0.95rem;
  line-height: 1.6;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.markdown-content :deep(code) {
  background: rgb(var(--v-theme-surface-variant));
  padding: 0.2rem 0.4rem;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 0.9em;
}

.markdown-content :deep(strong) {
  font-weight: 600;
}
</style>
