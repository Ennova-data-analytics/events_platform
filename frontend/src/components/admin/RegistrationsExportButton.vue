<template>
  <v-btn
    color="success"
    variant="tonal"
    prepend-icon="mdi-microsoft-excel"
    :loading="exporting"
    :size="$vuetify.display.mobile ? 'small' : 'default'"
    data-test="export-registrations"
    @click="exportToExcel"
  >
    <span class="d-none d-sm-inline">Export to Excel</span>
    <span class="d-sm-none">Export</span>
  </v-btn>
  <v-snackbar v-model="error.show" color="error" :timeout="6000">
    {{ error.text }}
  </v-snackbar>
</template>

<script setup>
import { ref } from 'vue';
import { EventService } from '@/services/EventService.js';
import { blobErrorDetail, filenameFromHeaders, saveBlob } from '@/utils/download.js';

const props = defineProps({
  eventId: { type: [Number, String], required: true },
  eventTitle: { type: String, default: '' },
});

const exporting = ref(false);
const error = ref({ show: false, text: '' });

function fallbackFilename() {
  const slug = (props.eventTitle || 'event').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'event';
  return `${slug}-attendees.xlsx`;
}

async function exportToExcel() {
  exporting.value = true;
  try {
    const response = await EventService.exportEventRegistrations(props.eventId);
    saveBlob(response.data, filenameFromHeaders(response.headers) || fallbackFilename());
  } catch (err) {
    console.error('Failed to export registrations:', err);
    const detail = await blobErrorDetail(err);
    error.value = { show: true, text: `Couldn't export the attendee list: ${detail || err.message || 'unknown error'}` };
  } finally {
    exporting.value = false;
  }
}
</script>
