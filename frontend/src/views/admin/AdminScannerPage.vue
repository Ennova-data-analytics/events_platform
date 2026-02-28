<template>
  <div>
    <div class="d-flex align-center mb-6">
      <v-btn icon variant="text" @click="$router.back()" class="mr-2">
        <v-icon>mdi-arrow-left</v-icon>
      </v-btn>
      <h1 class="text-h5 font-weight-bold">Entrance Scanner</h1>
      <v-spacer />
      <v-btn-toggle v-model="mode" mandatory color="primary" density="compact" rounded="lg">
        <v-btn value="camera" prepend-icon="mdi-camera">Camera</v-btn>
        <v-btn value="manual" prepend-icon="mdi-keyboard">Manual</v-btn>
      </v-btn-toggle>
    </div>

    <!-- Camera mode -->
    <div v-if="mode === 'camera'">
      <v-card rounded="xl" elevation="2" class="overflow-hidden" max-width="500" mx-auto>
        <div v-if="cameraError" class="pa-8 text-center">
          <v-icon size="48" color="error">mdi-camera-off</v-icon>
          <p class="mt-3 text-body-1">{{ cameraError }}</p>
          <v-btn class="mt-4" @click="mode = 'manual'" color="primary" variant="tonal">
            Use manual entry instead
          </v-btn>
        </div>

        <div v-else class="scanner-frame">
          <qrcode-stream
            @detect="onDetect"
            @error="onCameraError"
            class="scanner-stream"
          >
            <div class="scanner-overlay">
              <div class="scanner-corners" />
            </div>
          </qrcode-stream>
          <div class="pa-4 text-center text-caption text-grey">
            Point the camera at the attendee's QR code
          </div>
        </div>
      </v-card>
    </div>

    <!-- Manual token entry -->
    <div v-else>
      <v-card rounded="xl" elevation="2" max-width="500" class="mx-auto pa-6">
        <p class="text-body-2 text-grey mb-4">Enter the token from the ticket URL manually.</p>
        <v-text-field
          v-model="manualToken"
          label="Ticket token"
          variant="outlined"
          density="compact"
          clearable
          @keyup.enter="checkInManual"
          autofocus
        />
        <v-btn
          color="primary"
          block
          :loading="checking"
          :disabled="!manualToken"
          @click="checkInManual"
        >
          Check In
        </v-btn>
      </v-card>
    </div>

    <!-- Result overlay -->
    <v-dialog v-model="resultDialog" max-width="400" persistent>
      <v-card rounded="xl" :color="resultColor" class="pa-4">
        <v-card-text class="text-center pb-0">
          <v-icon :icon="resultIcon" size="64" color="white" />
          <div class="text-h6 font-weight-bold text-white mt-3">{{ result?.message }}</div>

          <div v-if="result?.valid || result?.already_checked_in" class="mt-4 text-left">
            <v-list bg-color="transparent" density="compact">
              <v-list-item>
                <template #prepend><v-icon color="white" size="18">mdi-account</v-icon></template>
                <v-list-item-title class="text-white font-weight-medium">{{ result?.attendee_name }}</v-list-item-title>
                <v-list-item-subtitle class="text-white opacity-80">Attendee</v-list-item-subtitle>
              </v-list-item>
              <v-list-item v-if="result?.ticket_type">
                <template #prepend><v-icon color="white" size="18">mdi-ticket</v-icon></template>
                <v-list-item-title class="text-white font-weight-medium">{{ result?.ticket_type }}</v-list-item-title>
                <v-list-item-subtitle class="text-white opacity-80">Ticket type</v-list-item-subtitle>
              </v-list-item>
              <v-list-item v-if="result?.checked_in_at">
                <template #prepend><v-icon color="white" size="18">mdi-clock-outline</v-icon></template>
                <v-list-item-title class="text-white font-weight-medium">{{ formatTime(result.checked_in_at) }}</v-list-item-title>
                <v-list-item-subtitle class="text-white opacity-80">Checked in at</v-list-item-subtitle>
              </v-list-item>
            </v-list>
          </div>
        </v-card-text>

        <v-card-actions class="justify-center pt-4">
          <v-btn
            variant="elevated"
            color="white"
            :text-color="resultColor"
            @click="closeResult"
            size="large"
          >
            <v-icon start>mdi-qrcode-scan</v-icon>
            Scan Next
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { QrcodeStream } from 'vue-qrcode-reader';
import { TicketService } from '@/services/TicketService';

const mode = ref('camera');
const manualToken = ref('');
const checking = ref(false);
const cameraError = ref(null);

const result = ref(null);
const resultDialog = ref(false);

const resultColor = computed(() => {
  if (!result.value) return 'grey';
  if (!result.value.valid) return 'error';
  if (result.value.already_checked_in) return 'warning';
  return 'success';
});

const resultIcon = computed(() => {
  if (!result.value) return 'mdi-help-circle';
  if (!result.value.valid) return 'mdi-close-circle';
  if (result.value.already_checked_in) return 'mdi-alert-circle';
  return 'mdi-check-circle';
});

function onCameraError(err) {
  console.error('Camera error:', err);
  cameraError.value = err?.message || 'Camera access denied. Please allow camera permissions.';
}

async function onDetect(detectedCodes) {
  if (checking.value || resultDialog.value) return;
  const raw = detectedCodes?.[0]?.rawValue;
  if (!raw) return;

  // Extract token from URL if the QR encodes the full URL
  const token = raw.includes('/ticket/') ? raw.split('/ticket/').pop() : raw;
  await performCheckIn(token);
}

async function checkInManual() {
  if (!manualToken.value) return;
  await performCheckIn(manualToken.value.trim());
  manualToken.value = '';
}

async function performCheckIn(token) {
  checking.value = true;
  try {
    const res = await TicketService.checkIn(token);
    result.value = res.data;
    resultDialog.value = true;
  } catch (e) {
    result.value = {
      valid: false,
      already_checked_in: false,
      attendee_name: 'Unknown',
      event_name: '',
      ticket_type: null,
      checked_in_at: null,
      message: e.response?.data?.detail || 'Check-in failed',
    };
    resultDialog.value = true;
  } finally {
    checking.value = false;
  }
}

function closeResult() {
  resultDialog.value = false;
  result.value = null;
}

function formatTime(dateStr) {
  return new Date(dateStr).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
}
</script>

<style scoped>
.scanner-frame {
  position: relative;
}

.scanner-stream {
  width: 100%;
  max-height: 400px;
}

.scanner-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}

.scanner-corners {
  width: 200px;
  height: 200px;
  border: 3px solid white;
  border-radius: 12px;
  box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.4);
}
</style>