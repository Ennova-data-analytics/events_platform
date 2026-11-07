<template>
  <v-card variant="tonal" color="pink-darken-1" class="mx-4 mb-4" data-test="charity-total">
    <v-card-text>
      <v-alert v-if="loadError" type="error" variant="tonal" data-test="charity-total-error">
        {{ loadError }}
      </v-alert>

      <v-progress-linear v-else-if="loading" indeterminate color="pink-darken-1" />

      <template v-else-if="summary">
        <div class="text-overline">Total to donate{{ summary.charity_name ? ` to ${summary.charity_name}` : '' }}</div>
        <div class="text-h4 font-weight-bold mb-3" data-test="charity-total-amount">
          {{ formatEuros(summary.total_to_donate) }}
        </div>

        <v-table density="compact" class="bg-transparent">
          <tbody>
            <tr data-test="charity-total-tickets">
              <td>
                Ticket sales
                <span class="text-medium-emphasis">({{ plural(summary.paid_tickets, 'paid ticket') }}<template v-if="Number(summary.refunds_given) > 0">, after {{ formatEuros(summary.refunds_given) }} refunded</template>)</span>
              </td>
              <td class="text-right">{{ formatEuros(summary.ticket_sales) }}</td>
            </tr>
            <tr data-test="charity-total-ticket-donations">
              <td>
                Donations added to a ticket
                <span class="text-medium-emphasis">({{ plural(summary.ticket_donation_count, 'donation') }})</span>
              </td>
              <td class="text-right">{{ formatEuros(summary.ticket_donations) }}</td>
            </tr>
            <tr data-test="charity-total-standalone">
              <td>
                Donations without a ticket: donation page, link and QR code
                <span class="text-medium-emphasis">({{ plural(summary.standalone_donation_count, 'donation') }})</span>
              </td>
              <td class="text-right">{{ formatEuros(summary.standalone_donations) }}</td>
            </tr>
            <tr class="font-weight-bold">
              <td>Total</td>
              <td class="text-right">{{ formatEuros(summary.total_to_donate) }}</td>
            </tr>
          </tbody>
        </v-table>

        <div class="text-caption text-medium-emphasis mt-2">
          Counts only money received, before Stripe fees.
          <span v-if="Number(summary.awaiting_payment) > 0" data-test="charity-total-awaiting">
            {{ formatEuros(summary.awaiting_payment) }} more is on approved tickets that haven't been paid yet.
          </span>
          <span v-if="Number(summary.commission_owed) > 0" data-test="charity-total-commission">
            Referral commission of {{ formatEuros(summary.commission_owed) }} is owed on this event and has not been taken off.
          </span>
        </div>
      </template>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { EventService } from '@/services/EventService.js';
import { formatEuros } from '@/utils/refunds.js';

const props = defineProps({
  eventId: { type: Number, required: true },
});

const summary = ref(null);
const loading = ref(false);
const loadError = ref('');

function plural(count, word) {
  return `${count} ${word}${count === 1 ? '' : 's'}`;
}

onMounted(async () => {
  loading.value = true;
  try {
    const response = await EventService.getCharitySummary(props.eventId);
    summary.value = response.data;
  } catch (error) {
    console.error('Failed to load charity total:', error);
    loadError.value = error.response?.data?.detail || 'Could not load the total raised for the charity.';
  } finally {
    loading.value = false;
  }
});
</script>
