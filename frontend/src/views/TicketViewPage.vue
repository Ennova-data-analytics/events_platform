<template>
  <div class="ticket-page-wrapper">
    <div v-if="loading" class="text-center mt-16">
      <v-progress-circular indeterminate color="primary" size="64" />
      <p class="mt-4">Loading ticket...</p>
    </div>

    <v-alert v-else-if="error" type="error" class="mt-6">
      {{ error }}
    </v-alert>

    <div v-else-if="ticketInfo" class="ticket-container">
      <v-card class="ticket-card mx-auto" max-width="520" elevation="4" rounded="xl">
        <!-- Header -->
        <div class="ticket-header pa-8" :class="ticketInfo.is_guest ? 'guest-header' : ''">
          <div class="text-caption text-white text-uppercase letter-spacing-wide opacity-70 mb-2">
            Entrance Ticket
          </div>
          <div class="text-h5 font-weight-bold text-white">
            {{ ticketInfo.event_name }}
          </div>
          <v-chip v-if="ticketInfo.is_guest" color="white" text-color="black" size="small" class="mt-3">
            Guest
          </v-chip>
          <v-chip v-if="ticketInfo.checked_in" color="success" size="small" class="mt-3 ml-1">
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
              <img :src="qrUrl" alt="QR Code" class="qr-image" />
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
        </v-card-actions>
      </v-card>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { TicketService } from '@/services/TicketService';

const route = useRoute();

const ticketInfo = ref(null);
const loading = ref(true);
const error = ref(null);
const pdfLoading = ref(false);

const token = computed(() => route.params.token);
const qrUrl = computed(() => token.value ? TicketService.getTicketQrUrl(token.value) : null);

onMounted(async () => {
  try {
    const res = await TicketService.getTicketByToken(token.value);
    ticketInfo.value = res.data;
  } catch (e) {
    error.value = e.response?.data?.detail || 'Ticket not found or invalid';
  } finally {
    loading.value = false;
  }
});

async function downloadPdf() {
  pdfLoading.value = true;
  try {
    await TicketService.downloadTicketPdf(token.value, ticketInfo.value?.event_name);
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

.guest-header {
  background: #2d5016;
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
}

.ticket-divider {
  border-top: 1px dashed #e0e0e0;
}
</style>