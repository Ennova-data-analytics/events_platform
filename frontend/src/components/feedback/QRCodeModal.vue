<template>
  <v-dialog v-model="dialog" max-width="600">
    <template v-slot:activator="{ props }">
      <v-btn
        color="primary"
        prepend-icon="mdi-qrcode"
        v-bind="props"
      >
        Show QR Code
      </v-btn>
    </template>

    <v-card>
      <v-card-title class="d-flex justify-space-between align-center">
        <span>Feedback QR Code</span>
        <v-btn icon="mdi-close" variant="text" @click="dialog = false"></v-btn>
      </v-card-title>

      <v-card-text class="text-center py-6">
        <div v-if="isLoading" class="py-8">
          <v-progress-circular indeterminate color="primary"></v-progress-circular>
        </div>

        <div v-else-if="qrCodeUrl">
          <img :src="qrCodeUrl" alt="QR Code" class="qr-code-image mb-4" />

          <p class="text-body-2 mb-4">
            Scan this QR code to access the feedback form
          </p>

          <v-text-field
            :model-value="feedbackUrl"
            readonly
            variant="outlined"
            density="compact"
            class="mb-4"
          >
            <template v-slot:append-inner>
              <v-btn
                icon="mdi-content-copy"
                variant="text"
                size="small"
                @click="copyUrl"
              ></v-btn>
            </template>
          </v-text-field>

          <v-btn
            color="primary"
            prepend-icon="mdi-download"
            @click="downloadQRCode"
            block
          >
            Download QR Code
          </v-btn>
        </div>

        <v-alert v-else type="error" class="mb-0">
          Failed to generate QR code
        </v-alert>
      </v-card-text>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, watch } from 'vue';
import { FeedbackService } from '@/services/FeedbackService.js';

const props = defineProps({
  eventId: {
    type: Number,
    required: true
  }
});

const dialog = ref(false);
const isLoading = ref(false);
const qrCodeUrl = ref(null);
const feedbackUrl = ref('');

watch(dialog, async (newValue) => {
  if (newValue) {
    await loadQRCode();
  }
});

async function loadQRCode() {
  isLoading.value = true;
  try {
    // Get QR code image
    const qrResponse = await FeedbackService.getFeedbackQRCode(props.eventId);
    const blob = new Blob([qrResponse.data], { type: 'image/png' });
    qrCodeUrl.value = URL.createObjectURL(blob);

    // Get feedback URL
    const urlResponse = await FeedbackService.getFeedbackUrl(props.eventId);
    feedbackUrl.value = urlResponse.data.feedback_url;
  } catch (error) {
    console.error('Failed to load QR code:', error);
  } finally {
    isLoading.value = false;
  }
}

function copyUrl() {
  navigator.clipboard.writeText(feedbackUrl.value);
  // You could add a snackbar notification here
}

function downloadQRCode() {
  if (qrCodeUrl.value) {
    const link = document.createElement('a');
    link.href = qrCodeUrl.value;
    link.download = `event_${props.eventId}_feedback_qr.png`;
    link.click();
  }
}
</script>

<style scoped>
.qr-code-image {
  max-width: 300px;
  width: 100%;
  height: auto;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
}
</style>
