<template>
  <v-card class="mb-4">
    <v-card-title class="d-flex justify-space-between align-center">
      <span>Feedback</span>
      <QRCodeModal v-if="hasFeedbackTemplate" :event-id="eventId" />
    </v-card-title>

    <v-card-text>
      <div v-if="isLoading">
        <v-progress-linear indeterminate color="primary"></v-progress-linear>
      </div>

      <div v-else-if="!hasFeedbackTemplate">
        <v-alert type="info" variant="tonal">
          No feedback template attached to this event.
        </v-alert>
      </div>

      <div v-else>
        <!-- Statistics Overview -->
        <v-row class="mb-4">
          <v-col cols="12" sm="4">
            <v-card variant="tonal" color="primary">
              <v-card-text class="text-center">
                <div class="text-h4">{{ stats.total_responses || 0 }}</div>
                <div class="text-caption">Total Responses</div>
              </v-card-text>
            </v-card>
          </v-col>
          <v-col cols="12" sm="4">
            <v-card variant="tonal" color="success">
              <v-card-text class="text-center">
                <div class="text-h4">{{ stats.response_rate ? stats.response_rate.toFixed(1) : 0 }}%</div>
                <div class="text-caption">Response Rate</div>
              </v-card-text>
            </v-card>
          </v-col>
          <v-col cols="12" sm="4">
            <v-card variant="tonal" color="info">
              <v-card-text class="text-center">
                <div class="text-h4">{{ stats.total_registrations || 0 }}</div>
                <div class="text-caption">Total Registrations</div>
              </v-card-text>
            </v-card>
          </v-col>
        </v-row>

        <!-- Field Statistics -->
        <div v-if="Object.keys(stats.field_statistics || {}).length > 0" class="mb-4">
          <h3 class="text-h6 mb-3">Response Summary</h3>
          <v-expansion-panels>
            <v-expansion-panel
              v-for="(fieldData, fieldName) in stats.field_statistics"
              :key="fieldName"
            >
              <v-expansion-panel-title>
                {{ fieldName }}
                <template v-slot:actions>
                  <v-chip size="small">{{ fieldData.response_count }} responses</v-chip>
                </template>
              </v-expansion-panel-title>
              <v-expansion-panel-text>
                <!-- Numeric statistics -->
                <div v-if="fieldData.average !== undefined">
                  <p><strong>Average:</strong> {{ fieldData.average.toFixed(2) }}</p>
                  <p><strong>Min:</strong> {{ fieldData.min }} | <strong>Max:</strong> {{ fieldData.max }}</p>
                </div>

                <!-- Value distribution -->
                <div v-if="fieldData.value_distribution">
                  <p class="mb-2"><strong>Distribution:</strong></p>
                  <div v-for="(count, value) in fieldData.value_distribution" :key="value" class="mb-1">
                    <v-chip size="small" class="mr-2">{{ count }}</v-chip> {{ value }}
                  </div>
                </div>
              </v-expansion-panel-text>
            </v-expansion-panel>
          </v-expansion-panels>
        </div>

        <!-- Recent Responses -->
        <div v-if="stats.recent_responses && stats.recent_responses.length > 0">
          <h3 class="text-h6 mb-3">Recent Responses</h3>
          <v-list>
            <v-list-item
              v-for="response in stats.recent_responses"
              :key="response.feedback_id"
            >
              <v-list-item-title>
                {{ response.is_anonymous ? 'Anonymous' : 'User' }}
              </v-list-item-title>
              <v-list-item-subtitle>
                {{ new Date(response.submitted_at).toLocaleString() }}
              </v-list-item-subtitle>
            </v-list-item>
          </v-list>
        </div>

        <!-- View All Button -->
        <v-btn
          :to="{ name: 'admin-event-feedback', params: { id: eventId } }"
          color="primary"
          variant="outlined"
          block
          class="mt-4"
        >
          View All Feedback Responses
        </v-btn>
      </div>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue';
import { FeedbackService } from '@/services/FeedbackService.js';
import QRCodeModal from './QRCodeModal.vue';

const props = defineProps({
  eventId: {
    type: Number,
    required: true
  },
  hasFeedbackTemplate: {
    type: Boolean,
    default: false
  }
});

const stats = ref({});
const isLoading = ref(false);

async function loadFeedbackStats() {
  if (!props.hasFeedbackTemplate) {
    stats.value = {};
    return;
  }

  isLoading.value = true;
  try {
    const response = await FeedbackService.getFeedbackStatistics(props.eventId);
    stats.value = response.data;
  } catch (error) {
    console.error('Failed to load feedback statistics:', error);
  } finally {
    isLoading.value = false;
  }
}

// Watch for changes to hasFeedbackTemplate prop
watch(() => props.hasFeedbackTemplate, (newValue) => {
  if (newValue) {
    loadFeedbackStats();
  }
});

onMounted(loadFeedbackStats);
</script>
