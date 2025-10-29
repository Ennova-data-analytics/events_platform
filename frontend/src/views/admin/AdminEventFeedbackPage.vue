<template>
  <div>
    <div class="d-flex align-center mb-4">
      <v-btn icon="mdi-arrow-left" variant="text" :to="{ name: 'admin-view-event', params: { id: eventId } }"></v-btn>
      <h1 class="text-h5 ml-2">Feedback Responses</h1>
      <v-spacer></v-spacer>

      <v-btn
        color="primary"
        variant="elevated"
        prepend-icon="mdi-brain"
        @click="openSummaryModal"
        :disabled="!canGenerateSummary"
        class="mr-2"
      >
        Generate AI Summary
      </v-btn>

      <v-btn
        color="secondary"
        variant="outlined"
        prepend-icon="mdi-history"
        @click="showPastSummaries"
        :disabled="feedbackResponses.length === 0"
      >
        Past Summaries
      </v-btn>
    </div>

    <v-card>
      <v-card-text>
        <v-data-table
          :headers="headers"
          :items="feedbackResponses"
          :loading="isLoading"
          :items-per-page="25"
        >
          <template v-slot:item.user="{ item }">
            {{ item.is_anonymous ? 'Anonymous' : (item.user ? item.user.email : 'N/A') }}
          </template>

          <template v-slot:item.submitted_at="{ item }">
            {{ new Date(item.submitted_at).toLocaleString() }}
          </template>

          <template v-slot:item.actions="{ item }">
            <v-btn
              icon="mdi-eye"
              variant="text"
              size="small"
              @click="viewResponse(item)"
            ></v-btn>
          </template>
        </v-data-table>
      </v-card-text>
    </v-card>

    <!-- Response Details Dialog -->
    <v-dialog v-model="detailsDialog" max-width="700">
      <v-card v-if="selectedResponse">
        <v-card-title class="d-flex justify-space-between align-center">
          <span>Feedback Details</span>
          <v-btn icon="mdi-close" variant="text" @click="detailsDialog = false"></v-btn>
        </v-card-title>

        <v-card-text>
          <v-list>
            <v-list-item>
              <v-list-item-title>Submitter</v-list-item-title>
              <v-list-item-subtitle>
                {{ selectedResponse.is_anonymous ? 'Anonymous' : (selectedResponse.user ? selectedResponse.user.email : 'N/A') }}
              </v-list-item-subtitle>
            </v-list-item>

            <v-list-item>
              <v-list-item-title>Submitted At</v-list-item-title>
              <v-list-item-subtitle>
                {{ new Date(selectedResponse.submitted_at).toLocaleString() }}
              </v-list-item-subtitle>
            </v-list-item>

            <v-divider class="my-4"></v-divider>

            <div v-for="(value, field) in selectedResponse.form_responses" :key="field" class="mb-4">
              <v-list-item>
                <v-list-item-title class="font-weight-bold">{{ field }}</v-list-item-title>
                <v-list-item-subtitle class="mt-2 text-wrap">
                  {{ value }}
                </v-list-item-subtitle>
              </v-list-item>
            </div>
          </v-list>
        </v-card-text>
      </v-card>
    </v-dialog>

    <FeedbackSummaryModal
      v-model="summaryModalOpen"
      :event-id="parseInt(eventId)"
      :summary-data="selectedSummary"
      @summary-generated="onSummaryGenerated"
      @summary-sent="onSummarySent"
    />

    <v-dialog v-model="pastSummariesDialog" max-width="800px" scrollable>
      <v-card>
        <v-card-title class="d-flex align-center pa-4">
          <v-icon class="mr-2">mdi-history</v-icon>
          <span>Past AI Summaries</span>
          <v-spacer></v-spacer>
          <v-btn icon @click="pastSummariesDialog = false" variant="text">
            <v-icon>mdi-close</v-icon>
          </v-btn>
        </v-card-title>

        <v-card-text v-if="loadingPastSummaries" class="text-center pa-8">
          <v-progress-circular indeterminate color="primary"></v-progress-circular>
        </v-card-text>

        <v-card-text v-else-if="pastSummaries.length === 0" class="text-center pa-8">
          <v-icon size="64" color="grey-lighten-1">mdi-brain-off</v-icon>
          <p class="text-h6 mt-4">No summaries generated yet</p>
          <p class="text-body-2 text-grey">Generate your first AI summary to see it here.</p>
        </v-card-text>

        <v-list v-else>
          <v-list-item
            v-for="summary in pastSummaries"
            :key="summary.summary_id"
            @click="viewPastSummary(summary)"
            class="pa-4"
          >
            <template v-slot:prepend>
              <v-avatar color="primary" variant="tonal">
                <v-icon>mdi-brain</v-icon>
              </v-avatar>
            </template>

            <v-list-item-title>
              {{ formatDate(summary.generated_at) }}
            </v-list-item-title>
            <v-list-item-subtitle>
              {{ summary.feedback_count }} responses analyzed
              <v-chip
                v-if="summary.sent_at"
                size="x-small"
                color="success"
                class="ml-2"
              >
                Sent
              </v-chip>
            </v-list-item-subtitle>

            <template v-slot:append>
              <v-icon>mdi-chevron-right</v-icon>
            </template>
          </v-list-item>
        </v-list>
      </v-card>
    </v-dialog>

    <v-snackbar v-model="successSnackbar" color="success" :timeout="3000">
      {{ successMessage }}
    </v-snackbar>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { FeedbackService } from '@/services/FeedbackService.js';
import AISummaryService from '@/services/AISummaryService.js';
import FeedbackSummaryModal from '@/components/admin/FeedbackSummaryModal.vue';

const route = useRoute();
const eventId = route.params.id;

const feedbackResponses = ref([]);
const isLoading = ref(true);
const detailsDialog = ref(false);
const selectedResponse = ref(null);

// AI Summary state
const summaryModalOpen = ref(false);
const selectedSummary = ref(null);
const pastSummariesDialog = ref(false);
const pastSummaries = ref([]);
const loadingPastSummaries = ref(false);
const successSnackbar = ref(false);
const successMessage = ref('');

const headers = ref([
  { title: 'Submitter', key: 'user' },
  { title: 'Submitted At', key: 'submitted_at' },
  { title: 'Anonymous', key: 'is_anonymous' },
  { title: 'Actions', key: 'actions', sortable: false, align: 'end' },
]);

const canGenerateSummary = computed(() => {
  return feedbackResponses.value.length >= 3;
});

async function fetchFeedback() {
  isLoading.value = true;
  try {
    const response = await FeedbackService.getEventFeedback(eventId);
    feedbackResponses.value = response.data;
  } catch (error) {
    console.error('Failed to fetch feedback:', error);
  } finally {
    isLoading.value = false;
  }
}

function viewResponse(response) {
  selectedResponse.value = response;
  detailsDialog.value = true;
}

function openSummaryModal() {
  selectedSummary.value = null; 
  summaryModalOpen.value = true;
}

async function showPastSummaries() {
  pastSummariesDialog.value = true;
  loadingPastSummaries.value = true;

  try {
    const response = await AISummaryService.listSummaries(eventId);
    pastSummaries.value = response.summaries;
  } catch (error) {
    console.error('Failed to load past summaries:', error);
  } finally {
    loadingPastSummaries.value = false;
  }
}

function viewPastSummary(summary) {
  selectedSummary.value = summary;
  pastSummariesDialog.value = false;
  summaryModalOpen.value = true;
}

function onSummaryGenerated() {
  successMessage.value = 'AI summary generated successfully!';
  successSnackbar.value = true;
}

function onSummarySent(result) {
  successMessage.value = `Summary sent to ${result.sent_count} recipient(s)!`;
  successSnackbar.value = true;
}

function formatDate(dateString) {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
}

onMounted(fetchFeedback);
</script>
