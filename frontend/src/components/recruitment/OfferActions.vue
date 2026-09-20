<template>
  <div>
    <div class="d-flex align-center justify-space-between flex-wrap ga-2 mb-2">
      <span class="text-subtitle-2 font-weight-bold">
        <v-icon size="small" color="teal" class="mr-1">mdi-email-seal-outline</v-icon>
        You've got an offer from {{ departmentName }}
      </span>
      <v-chip :color="offer?.overdue ? 'error' : 'teal'" variant="tonal" size="small">
        {{ offer?.overdue ? 'Deadline passed' : `${countdown} to answer` }}
      </v-chip>
    </div>
    <p class="text-body-2 text-medium-emphasis mb-2">
      Please accept or decline by {{ deadline }}.
      <template v-if="offer?.overdue">The deadline has passed, but you can still answer.</template>
    </p>
    <!-- Shown before any click, so the trade-off is visible up front. -->
    <p v-if="otherOpenCount" class="text-body-2 mb-3">
      <v-icon size="small" color="warning" class="mr-1">mdi-alert-outline</v-icon>
      You have {{ otherOpenCount }} other application{{ otherOpenCount === 1 ? '' : 's' }} in progress.
      Accepting this offer closes {{ otherOpenCount === 1 ? 'it' : 'them' }}.
    </p>
    <div class="d-flex ga-2 flex-wrap">
      <v-btn color="success" variant="flat" size="small" prepend-icon="mdi-check" @click="$emit('respond', 'accept')">
        Accept offer
      </v-btn>
      <v-btn variant="outlined" size="small" prepend-icon="mdi-close" @click="$emit('respond', 'decline')">
        Decline
      </v-btn>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  offer: { type: Object, default: null },
  departmentName: { type: String, default: 'the team' },
  // The candidate's other applications still in progress, which accepting closes.
  otherOpenCount: { type: Number, default: 0 },
});
defineEmits(['respond']);

const deadline = computed(() =>
  props.offer?.expires_at
    ? new Date(props.offer.expires_at).toLocaleString('en-GB', { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })
    : 'the deadline'
);
const countdown = computed(() => {
  if (!props.offer?.expires_at) return '';
  const diff = new Date(props.offer.expires_at).getTime() - Date.now();
  const hrs = Math.max(1, Math.round(diff / 3600000));
  return hrs < 24 ? `${hrs}h` : `${Math.round(hrs / 24)}d`;
});
</script>
