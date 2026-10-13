<template>
  <div>
    <div class="d-flex align-center mb-4 pa-4">
      <div>
        <h3 class="text-subtitle-1 font-weight-bold">Donations</h3>
        <p class="text-caption text-grey">
          Paid donations made without registering. Donations added to a ticket are in the Donation column of the attendee tabs.
        </p>
      </div>
      <v-spacer />
      <v-chip color="pink-darken-1" variant="tonal" prepend-icon="mdi-hand-heart">
        {{ donations.length }} donation{{ donations.length === 1 ? '' : 's' }} · €{{ total.toFixed(2) }}
      </v-chip>
    </div>

    <v-alert v-if="loadError" type="error" variant="tonal" class="mx-4 mb-4">
      {{ loadError }}
    </v-alert>

    <v-data-table
      :headers="headers"
      :items="donations"
      :loading="loading"
      item-value="donation_id"
      no-data-text="No donations yet"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { EventService } from '@/services/EventService.js';

const props = defineProps({
  eventId: { type: Number, required: true },
});

const donations = ref([]);
const loading = ref(false);
const loadError = ref('');

const headers = [
  { title: 'Email', key: 'email' },
  { title: 'Amount', key: 'amount_euros', value: item => `€${Number(item.amount_euros).toFixed(2)}` },
  { title: 'Paid at', key: 'paid_at', value: item => item.paid_at ? new Date(item.paid_at).toLocaleString('en-GB') : '—' },
];

const total = computed(() => donations.value.reduce((sum, d) => sum + Number(d.amount_euros), 0));

onMounted(async () => {
  loading.value = true;
  try {
    const response = await EventService.getEventDonations(props.eventId);
    donations.value = response.data;
  } catch (error) {
    console.error('Failed to load donations:', error);
    loadError.value = error.response?.data?.detail || 'Could not load donations.';
  } finally {
    loading.value = false;
  }
});
</script>
