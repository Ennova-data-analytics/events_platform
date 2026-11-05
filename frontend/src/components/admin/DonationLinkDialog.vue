<template>
  <v-dialog v-model="open" max-width="520">
    <template #activator="{ props: activatorProps }">
      <v-btn
        color="pink-darken-1"
        variant="flat"
        prepend-icon="mdi-qrcode"
        v-bind="activatorProps"
        data-test="donation-link-open"
      >
        Donation link &amp; QR
      </v-btn>
    </template>

    <v-card>
      <v-card-title class="d-flex justify-space-between align-center">
        <span>Donation link &amp; QR code</span>
        <v-btn icon="mdi-close" variant="text" aria-label="Close" @click="open = false" />
      </v-card-title>

      <v-card-text class="text-center pb-6">
        <div v-if="loading" class="py-8">
          <v-progress-circular indeterminate color="pink-darken-1" />
        </div>

        <v-alert v-else-if="loadError" type="error" variant="tonal" class="text-left" data-test="donation-link-error">
          {{ loadError }}
          <template #append>
            <v-btn variant="text" size="small" @click="load">Retry</v-btn>
          </template>
        </v-alert>

        <template v-else-if="qrImageUrl">
          <p class="text-body-2 text-left mb-4">
            Print this and put it up at the event. Scanning it opens the donation page directly:
            no login, no ticket, just an amount, an email and a card.
          </p>

          <img :src="qrImageUrl" alt="QR code for the donation page" class="qr-image mb-4" data-test="donation-qr" />

          <v-text-field
            :model-value="donationUrl"
            readonly
            variant="outlined"
            density="compact"
            hide-details
            class="mb-4"
            data-test="donation-url"
          >
            <template #append-inner>
              <v-btn
                :icon="copied ? 'mdi-check' : 'mdi-content-copy'"
                :color="copied ? 'success' : undefined"
                variant="text"
                size="small"
                aria-label="Copy link"
                data-test="donation-url-copy"
                @click="copyUrl"
              />
            </template>
          </v-text-field>

          <div class="d-flex flex-column flex-sm-row ga-2">
            <v-btn
              class="flex-grow-1"
              color="pink-darken-1"
              variant="flat"
              prepend-icon="mdi-download"
              data-test="donation-qr-download"
              @click="download"
            >
              Download QR code
            </v-btn>
            <v-btn
              class="flex-grow-1"
              variant="outlined"
              prepend-icon="mdi-open-in-new"
              :href="donationUrl"
              target="_blank"
              rel="noopener"
            >
              Open page
            </v-btn>
          </div>
        </template>
      </v-card-text>
    </v-card>
  </v-dialog>

  <v-snackbar v-model="copyFailed" color="error" timeout="4000">
    Couldn't copy the link. Select it and copy it by hand.
  </v-snackbar>
</template>

<script setup>
import { ref, watch, onBeforeUnmount } from 'vue';
import { EventService } from '@/services/EventService.js';

const props = defineProps({
  eventId: { type: Number, required: true },
});

const open = ref(false);
const loading = ref(false);
const loadError = ref('');
const qrImageUrl = ref(null);
const donationUrl = ref('');
const copied = ref(false);
const copyFailed = ref(false);

watch(open, isOpen => {
  if (isOpen && !qrImageUrl.value) load();
});

// With responseType 'blob' an error body arrives as a Blob, not parsed JSON.
async function errorDetail(error) {
  let data = error.response?.data;
  if (data instanceof Blob) {
    try {
      data = JSON.parse(await data.text());
    } catch {
      return null;
    }
  }
  return typeof data?.detail === 'string' ? data.detail : null;
}

async function load() {
  loading.value = true;
  loadError.value = '';
  try {
    const [urlResponse, qrResponse] = await Promise.all([
      EventService.getDonationUrl(props.eventId),
      EventService.getDonationQrCode(props.eventId),
    ]);
    donationUrl.value = urlResponse.data.donation_url;
    qrImageUrl.value = URL.createObjectURL(new Blob([qrResponse.data], { type: 'image/png' }));
  } catch (error) {
    console.error('Failed to load donation link:', error);
    loadError.value = (await errorDetail(error)) || 'Could not load the donation link. Please try again.';
  } finally {
    loading.value = false;
  }
}

async function copyUrl() {
  try {
    await navigator.clipboard.writeText(donationUrl.value);
    copied.value = true;
    setTimeout(() => { copied.value = false; }, 2000);
  } catch (error) {
    console.error('Failed to copy donation link:', error);
    copyFailed.value = true;
  }
}

function download() {
  const link = document.createElement('a');
  link.href = qrImageUrl.value;
  link.download = `event_${props.eventId}_donation_qr.png`;
  link.click();
}

onBeforeUnmount(() => {
  if (qrImageUrl.value) URL.revokeObjectURL(qrImageUrl.value);
});
</script>

<style scoped>
.qr-image {
  max-width: 280px;
  width: 100%;
  height: auto;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
}
</style>
