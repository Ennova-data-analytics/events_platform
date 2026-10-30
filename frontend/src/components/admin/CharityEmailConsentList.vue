<template>
  <div>
    <div class="d-flex align-center mb-4 pa-4">
      <div>
        <h3 class="text-subtitle-1 font-weight-bold">Charity Emails</h3>
        <p class="text-caption text-grey">
          Attendees who agreed to share their email with the charity. Download a fresh list each time you send one: people can withdraw at any time.
        </p>
      </div>
      <v-spacer />
      <v-btn
        color="pink-darken-1"
        variant="tonal"
        prepend-icon="mdi-download"
        :disabled="consented.length === 0"
        @click="downloadCsv"
      >
        Download CSV ({{ consented.length }})
      </v-btn>
    </div>

    <v-data-table
      :headers="headers"
      :items="consented"
      item-value="registration_id"
      no-data-text="Nobody has opted in yet"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  eventId: { type: Number, required: true },
  registrations: { type: Array, required: true },
});

const headers = [
  { title: 'Name', key: 'user.full_name' },
  { title: 'Email', key: 'user.email' },
  { title: 'Status', key: 'status' },
  { title: 'Consented at', key: 'charity_email_consent_at', value: item => formatConsentedAt(item) },
];

// Someone who cancelled has left the event, so leave them out of what goes to
// the charity even though they never withdrew.
const consented = computed(() => props.registrations.filter(
  r => r.charity_email_consent && r.status !== 'Cancelled'
));

function formatConsentedAt(registration) {
  return registration.charity_email_consent_at
    ? new Date(registration.charity_email_consent_at).toLocaleString('en-GB')
    : '—';
}

// Names are typed by attendees, and Excel runs a cell starting with one of
// these characters as a formula.
function csvCell(value) {
  const text = String(value ?? '');
  const safe = /^[=+\-@\t\r]/.test(text) ? `'${text}` : text;
  return `"${safe.replace(/"/g, '""')}"`;
}

function downloadCsv() {
  const rows = [
    ['Name', 'Email', 'Consented at'],
    ...consented.value.map(r => [r.user.full_name, r.user.email, formatConsentedAt(r)]),
  ];
  const csv = rows.map(row => row.map(csvCell).join(',')).join('\r\n');

  // The BOM makes Excel read accented names as UTF-8.
  const blob = new Blob([`\ufeff${csv}`], { type: 'text/csv;charset=utf-8' });
  const downloadUrl = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = downloadUrl;
  link.download = `event-${props.eventId}-charity-emails.csv`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(downloadUrl);
}
</script>
