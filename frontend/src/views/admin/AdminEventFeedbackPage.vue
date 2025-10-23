<template>
  <div>
    <div class="d-flex align-center mb-4">
      <v-btn icon="mdi-arrow-left" variant="text" :to="{ name: 'admin-view-event', params: { id: eventId } }"></v-btn>
      <h1 class="text-h5 ml-2">Feedback Responses</h1>
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
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { FeedbackService } from '@/services/FeedbackService.js';

const route = useRoute();
const eventId = route.params.id;

const feedbackResponses = ref([]);
const isLoading = ref(true);
const detailsDialog = ref(false);
const selectedResponse = ref(null);

const headers = ref([
  { title: 'Submitter', key: 'user' },
  { title: 'Submitted At', key: 'submitted_at' },
  { title: 'Anonymous', key: 'is_anonymous' },
  { title: 'Actions', key: 'actions', sortable: false, align: 'end' },
]);

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

onMounted(fetchFeedback);
</script>
