<template>
  <div>
    <div class="d-flex align-center mb-6 flex-wrap gap-2">
      <v-btn icon variant="text" @click="$router.back()" class="mr-2">
        <v-icon>mdi-arrow-left</v-icon>
      </v-btn>
      <div>
        <h1 class="text-h5 font-weight-bold">Entrance Scanner</h1>
        <div v-if="currentSessionLabel" class="text-caption text-grey">
          Current session: <strong>{{ currentSessionLabel }}</strong>
        </div>
      </div>
      <v-spacer />
      <v-btn-toggle v-model="mode" mandatory color="primary" density="compact" rounded="lg" class="mr-2">
        <v-btn value="camera" prepend-icon="mdi-camera">Camera</v-btn>
        <v-btn value="manual" prepend-icon="mdi-keyboard">Manual</v-btn>
      </v-btn-toggle>
      <v-btn color="warning" variant="tonal" prepend-icon="mdi-snowflake" @click="openFreezeDialog">
        Freeze & New Session
      </v-btn>
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

    <!-- Freeze session dialog -->
    <v-dialog v-model="freezeDialog" max-width="420" persistent>
      <v-card rounded="xl">
        <v-card-title class="pa-6 pb-2 font-weight-bold">Freeze & Start New Session</v-card-title>
        <v-card-text class="pa-6 pt-2">
          <p class="text-body-2 text-grey mb-4">
            This will archive today's check-ins under a session name, then reset all tickets so attendees can be scanned again for the next session.
          </p>
          <v-text-field
            v-model="freezeLabel"
            label="Session name"
            variant="outlined"
            density="compact"
            placeholder="e.g. Day 1, Morning Session"
            :error-messages="freezeError ? [freezeError] : []"
          />
        </v-card-text>
        <v-card-actions class="pa-6 pt-0">
          <v-spacer />
          <v-btn variant="text" @click="freezeDialog = false">Cancel</v-btn>
          <v-btn color="warning" :loading="freezing" @click="doFreeze">
            Freeze & Reset
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-snackbar v-model="snackbar.show" :color="snackbar.color" timeout="4000" location="top">
      {{ snackbar.message }}
    </v-snackbar>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { QrcodeStream } from 'vue-qrcode-reader';
import { TicketService } from '@/services/TicketService';

const route = useRoute();
const eventId = computed(() => Number(route.params.id));

const mode = ref('camera');
const manualToken = ref('');
const checking = ref(false);
const cameraError = ref(null);

const result = ref(null);
const resultDialog = ref(false);

// Session freeze
const freezeDialog = ref(false);
const freezeLabel = ref('');
const freezeError = ref(null);
const freezing = ref(false);
const sessionCount = ref(0);
const currentSessionLabel = ref(null);

const snackbar = ref({ show: false, message: '', color: 'success' });

function showSnack(message, color = 'success') {
  snackbar.value = { show: true, message, color };
}

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

async function loadSessions() {
  try {
    const res = await TicketService.listSessions(eventId.value);
    sessionCount.value = res.data.length;
    if (res.data.length > 0) {
      currentSessionLabel.value = res.data[0].label; // most recent first
    }
  } catch {
    // non-fatal
  }
}

function openFreezeDialog() {
  freezeLabel.value = `Day ${sessionCount.value + 1}`;
  freezeError.value = null;
  freezeDialog.value = true;
}

async function doFreeze() {
  if (!freezeLabel.value.trim()) {
    freezeError.value = 'Session name is required';
    return;
  }
  freezing.value = true;
  freezeError.value = null;
  try {
    await TicketService.freezeSession(eventId.value, freezeLabel.value.trim());
    const label = freezeLabel.value.trim();
    freezeDialog.value = false;
    await loadSessions();
    showSnack(`"${label}" archived — scanner reset for new session`);
  } catch (e) {
    freezeError.value = e.response?.data?.detail || 'Failed to freeze session';
  } finally {
    freezing.value = false;
  }
}

function onCameraError(err) {
  console.error('Camera error:', err);
  cameraError.value = err?.message || 'Camera access denied. Please allow camera permissions.';
}

async function onDetect(detectedCodes) {
  if (checking.value || resultDialog.value) return;
  const raw = detectedCodes?.[0]?.rawValue;
  if (!raw) return;

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

onMounted(loadSessions);
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
