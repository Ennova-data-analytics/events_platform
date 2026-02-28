<template>
  <div class="ticket-page-wrapper">
    <div v-if="loading" class="text-center mt-16">
      <v-progress-circular indeterminate color="primary" size="64" />
      <p class="mt-4">Loading your ticket...</p>
    </div>

    <v-alert v-else-if="error" type="error" class="mt-6">
      {{ error }}
    </v-alert>

    <div v-else-if="ticketInfo" class="ticket-container">
      <!-- Ticket card -->
      <v-card class="ticket-card mx-auto" max-width="520" elevation="4" rounded="xl">
        <!-- Header -->
        <div class="ticket-header pa-8">
          <div class="text-caption text-white text-uppercase letter-spacing-wide opacity-70 mb-2">
            Entrance Ticket
          </div>
          <div class="text-h5 font-weight-bold text-white">
            {{ ticketInfo.event_name }}
          </div>
          <v-chip
            v-if="ticketInfo.checked_in"
            color="success"
            size="small"
            class="mt-3"
          >
            <v-icon start size="14">mdi-check-circle</v-icon>
            Checked in
          </v-chip>
        </div>

        <!-- Body -->
        <v-card-text class="pa-8">
          <v-row>
            <v-col cols="7">
              <div class="detail-row mb-5">
                <div class="detail-label">Attendee</div>
                <div class="detail-value">{{ ticketInfo.attendee_name }}</div>
              </div>

              <div class="detail-row mb-5">
                <div class="detail-label">Date</div>
                <div class="detail-value">{{ formatDate(ticketInfo.event_date_start) }}</div>
              </div>

              <div class="detail-row mb-5">
                <div class="detail-label">Time</div>
                <div class="detail-value">{{ formatTime(ticketInfo.event_date_start) }}</div>
              </div>

              <div v-if="ticketInfo.event_location" class="detail-row mb-5">
                <div class="detail-label">Location</div>
                <div class="detail-value">{{ ticketInfo.event_location }}</div>
              </div>

              <div v-if="ticketInfo.ticket_type" class="detail-row">
                <div class="detail-label">Ticket Type</div>
                <div class="detail-value">{{ ticketInfo.ticket_type }}</div>
              </div>
            </v-col>

            <v-col cols="5" class="d-flex flex-column align-center justify-center">
              <div v-if="qrObjectUrl" class="qr-wrapper">
                <img :src="qrObjectUrl" alt="QR Code" class="qr-image" />
              </div>
              <div v-else class="qr-placeholder d-flex align-center justify-center">
                <v-progress-circular indeterminate size="32" color="grey-lighten-2" />
              </div>
              <div class="text-caption text-grey mt-2 text-center">Scan at entrance</div>
            </v-col>
          </v-row>
        </v-card-text>

        <!-- Divider -->
        <div class="ticket-divider mx-8" />

        <!-- Actions -->
        <v-card-actions class="pa-6 pt-4">
          <v-btn
            color="primary"
            variant="tonal"
            @click="downloadPdf"
            :loading="pdfLoading"
            prepend-icon="mdi-download"
          >
            Download PDF
          </v-btn>
          <v-spacer />
          <v-btn
            variant="text"
            color="grey"
            @click="$router.back()"
            prepend-icon="mdi-arrow-left"
          >
            Back
          </v-btn>
        </v-card-actions>
      </v-card>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useRoute } from 'vue-router';
import { TicketService } from '@/services/TicketService';
import { useAuthStore } from '@/stores/auth.store';

const route = useRoute();
const authStore = useAuthStore();

const ticketInfo = ref(null);
const loading = ref(true);
const error = ref(null);
const pdfLoading = ref(false);
const qrObjectUrl = ref(null);

const registrationId = computed(() => route.params.registrationId);

onMounted(async () => {
  try {
    const res = await TicketService.getMyTicketInfo(registrationId.value);
    ticketInfo.value = res.data;
    await fetchQr();
  } catch (e) {
    error.value = e.response?.data?.detail || 'Failed to load ticket';
  } finally {
    loading.value = false;
  }
});

onUnmounted(() => {
  if (qrObjectUrl.value) window.URL.revokeObjectURL(qrObjectUrl.value);
});

async function fetchQr() {
  try {
    const response = await fetch(`/api/tickets/my/${registrationId.value}/qr`, {
      headers: { Authorization: `Bearer ${authStore.token}` },
    });
    if (!response.ok) throw new Error('QR fetch failed');
    const blob = await response.blob();
    qrObjectUrl.value = window.URL.createObjectURL(blob);
  } catch {
    // QR load failure is non-fatal — ticket info still shown
  }
}

async function downloadPdf() {
  pdfLoading.value = true;
  try {
    await TicketService.downloadMyTicketPdf(registrationId.value, ticketInfo.value?.event_name);
  } catch (e) {
    error.value = 'Failed to download PDF';
  } finally {
    pdfLoading.value = false;
  }
}

function formatDate(dateStr) {
  return new Date(dateStr).toLocaleDateString('en-GB', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
  });
}

function formatTime(dateStr) {
  return new Date(dateStr).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
}
</script>

<style scoped>
.ticket-page-wrapper {
  padding: 32px 16px;
}

.ticket-header {
  background: #13182e;
  border-radius: 16px 16px 0 0;
}

.letter-spacing-wide {
  letter-spacing: 2px;
}

.detail-label {
  font-size: 10px;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: #9e9e9e;
  margin-bottom: 2px;
}

.detail-value {
  font-size: 15px;
  font-weight: 600;
  color: #13182e;
}

.qr-image {
  width: 130px;
  height: 130px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  display: block;
}

.qr-placeholder {
  width: 130px;
  height: 130px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  background: #fafafa;
}

.ticket-divider {
  border-top: 1px dashed #e0e0e0;
}
</style>