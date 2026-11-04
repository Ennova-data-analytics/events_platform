<template>
  <v-dialog :model-value="modelValue" max-width="760px" persistent scrollable @update:model-value="close">
    <v-card>
      <v-card-title class="d-flex align-center">
        <v-icon start>mdi-cash-refund</v-icon>
        Partial refund
        <v-chip size="small" class="ml-2" variant="tonal">{{ attendees.length }} selected</v-chip>
      </v-card-title>

      <v-card-text>
        <v-alert v-if="error" type="error" variant="tonal" density="compact" class="mb-4" data-test="refund-error">
          {{ error }}
        </v-alert>

        <!-- Step 1: how much and why -->
        <div v-if="step === 'form'">
          <p class="text-body-2 mb-4">
            Everyone keeps their ticket. Card payments are refunded to the card; tickets marked paid by hand
            are recorded as refunds for you to pay back yourselves. Each person gets an email with your explanation.
          </p>

          <v-btn-toggle v-model="mode" mandatory color="primary" density="comfortable" class="mb-4" data-test="refund-mode">
            <v-btn value="corrected_price">Correct the price</v-btn>
            <v-btn value="fixed">Fixed amount</v-btn>
          </v-btn-toggle>

          <v-text-field
            v-if="mode === 'corrected_price'"
            v-model="correctedPrice"
            label="What the price should have been"
            prefix="€"
            type="number"
            min="0"
            step="0.01"
            hint="Each person gets back the difference from what they paid. Discount codes are applied to the corrected price."
            persistent-hint
            data-test="corrected-price"
          />
          <v-text-field
            v-else
            v-model="amount"
            label="Amount to refund each person"
            prefix="€"
            type="number"
            min="0.01"
            step="0.01"
            hint="Never more than what's left of what they paid for the ticket."
            persistent-hint
            data-test="fixed-amount"
          />

          <v-textarea
            v-model="reason"
            class="mt-4"
            label="Explanation for the email"
            rows="4"
            auto-grow
            counter="2000"
            data-test="refund-reason"
          />
        </div>

        <!-- Step 2: who gets what -->
        <div v-else-if="step === 'review' && preview">
          <v-table density="compact" class="mb-4">
            <thead>
              <tr>
                <th>Attendee</th>
                <th class="text-end">Paid</th>
                <th class="text-end">Refunded before</th>
                <th class="text-end">Refund now</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in preview.rows" :key="row.registration_id" :class="{ 'text-disabled': row.skip_reason }" data-test="preview-row">
                <td>
                  <div>{{ row.full_name || row.email }}</div>
                  <div v-if="row.skip_reason" class="text-caption">{{ row.skip_reason }}</div>
                </td>
                <td class="text-end">{{ formatEuros(row.paid_euros) }}</td>
                <td class="text-end">{{ Number(row.already_refunded_euros) ? formatEuros(row.already_refunded_euros) : '—' }}</td>
                <td class="text-end font-weight-medium">{{ row.skip_reason ? '—' : formatEuros(row.refund_euros) }}</td>
                <td>
                  <v-chip v-if="row.method" size="x-small" variant="tonal" :color="row.method === 'stripe' ? 'primary' : 'deep-orange'">
                    {{ row.method === 'stripe' ? 'Card' : 'Pay back yourselves' }}
                  </v-chip>
                </td>
              </tr>
            </tbody>
          </v-table>

          <v-checkbox
            v-if="mode === 'corrected_price'"
            v-model="updatePrice"
            density="compact"
            hide-details
            data-test="update-price"
            :label="`Also change the price of ${preview.ticket_type_name ? `'${preview.ticket_type_name}'` : 'the event'} from ${formatEuros(preview.current_price_euros)} to ${formatEuros(correctedPrice)} for future buyers`"
          />

          <v-alert v-if="!preview.refundable_count" type="info" variant="tonal" density="compact" class="mt-4">
            Nobody selected has anything to refund.
          </v-alert>
        </div>

        <!-- Step 3: what happened -->
        <div v-else-if="step === 'done' && result">
          <v-alert :type="batchColor(result)" variant="tonal" density="compact" class="mb-4" data-test="refund-summary">
            {{ summarizeBatch(result) }}
          </v-alert>
          <v-list density="compact">
            <v-list-item v-for="row in result.results" :key="row.registration_id" data-test="result-row">
              <template #prepend>
                <v-icon :color="OUTCOME[row.outcome].color">{{ OUTCOME[row.outcome].icon }}</v-icon>
              </template>
              <v-list-item-title>
                {{ row.full_name || row.email }}
                <span v-if="Number(row.amount_euros)" class="text-medium-emphasis">· {{ formatEuros(row.amount_euros) }}</span>
              </v-list-item-title>
              <v-list-item-subtitle>
                {{ OUTCOME[row.outcome].label }}<template v-if="row.message"> — {{ row.message }}</template>
              </v-list-item-subtitle>
            </v-list-item>
          </v-list>
        </div>
      </v-card-text>

      <v-card-actions>
        <v-btn v-if="step === 'review'" variant="text" :disabled="busy" @click="step = 'form'">Back</v-btn>
        <v-spacer />
        <template v-if="step === 'form'">
          <v-btn variant="text" @click="close">Cancel</v-btn>
          <v-btn color="primary" :disabled="!formValid" :loading="busy" data-test="review-btn" @click="loadPreview">Review</v-btn>
        </template>
        <template v-else-if="step === 'review'">
          <v-btn variant="text" :disabled="busy" @click="close">Cancel</v-btn>
          <v-btn
            color="error"
            :disabled="!preview?.refundable_count"
            :loading="busy"
            data-test="confirm-btn"
            @click="issue"
          >
            Refund {{ formatEuros(preview?.total_refund_euros) }} to {{ preview?.refundable_count }}
            {{ preview?.refundable_count === 1 ? 'person' : 'people' }}
          </v-btn>
        </template>
        <v-btn v-else color="primary" data-test="done-btn" @click="close">Done</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue';
import { AdminService } from '@/services/AdminService.js';
import { DEFAULT_REFUND_REASON, batchColor, formatEuros, newBatchId, summarizeBatch } from '@/utils/refunds.js';

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  eventId: { type: Number, required: true },
  attendees: { type: Array, required: true },
});
const emit = defineEmits(['update:modelValue', 'refunded']);

const OUTCOME = {
  refunded: { label: 'Refunded', icon: 'mdi-check-circle', color: 'success' },
  pending: { label: 'Refund pending', icon: 'mdi-clock-outline', color: 'warning' },
  failed: { label: 'Failed', icon: 'mdi-alert-circle', color: 'error' },
  skipped: { label: 'Skipped', icon: 'mdi-minus-circle', color: 'grey' },
};

const step = ref('form');
const mode = ref('corrected_price');
const amount = ref('');
const correctedPrice = ref('');
const reason = ref(DEFAULT_REFUND_REASON);
const updatePrice = ref(false);
const preview = ref(null);
const result = ref(null);
const busy = ref(false);
const error = ref('');
// One per opening of the dialog: a retry after a timeout reuses it, so the
// backend never refunds the same person twice for the same submit.
const batchId = ref(newBatchId());

watch(() => props.modelValue, open => {
  if (!open) return;
  step.value = 'form';
  mode.value = 'corrected_price';
  amount.value = '';
  correctedPrice.value = '';
  reason.value = DEFAULT_REFUND_REASON;
  updatePrice.value = false;
  preview.value = null;
  result.value = null;
  error.value = '';
  batchId.value = newBatchId();
});

watch(mode, () => { updatePrice.value = false; });

function money(value) {
  const number = Number(value);
  return value === '' || value === null || Number.isNaN(number) ? null : Math.round(number * 100) / 100;
}

const formValid = computed(() => {
  if (!props.attendees.length || !reason.value.trim() || reason.value.length > 2000) return false;
  if (mode.value === 'fixed') return money(amount.value) > 0;
  return money(correctedPrice.value) !== null && money(correctedPrice.value) >= 0;
});

function amounts() {
  return mode.value === 'fixed'
    ? { mode: 'fixed', amount_euros: money(amount.value).toFixed(2) }
    : { mode: 'corrected_price', corrected_price_euros: money(correctedPrice.value).toFixed(2) };
}

function errorText(err, fallback) {
  const detail = err.response?.data?.detail;
  if (Array.isArray(detail)) return detail.map(d => d.msg).join('; ');
  return detail || fallback;
}

async function loadPreview() {
  busy.value = true;
  error.value = '';
  try {
    const response = await AdminService.previewRefunds(props.eventId, {
      registration_ids: props.attendees.map(a => a.registration_id),
      ...amounts(),
    });
    preview.value = response.data;
    step.value = 'review';
  } catch (err) {
    console.error('Failed to preview refunds:', err);
    error.value = errorText(err, 'Could not work out the refunds. Please try again.');
  } finally {
    busy.value = false;
  }
}

async function issue() {
  busy.value = true;
  error.value = '';
  try {
    const response = await AdminService.issueRefunds(props.eventId, {
      batch_id: batchId.value,
      registration_ids: props.attendees.map(a => a.registration_id),
      ...amounts(),
      reason: reason.value.trim(),
      update_ticket_type_price: mode.value === 'corrected_price' && updatePrice.value,
    });
    result.value = response.data;
    step.value = 'done';
    emit('refunded', response.data);
  } catch (err) {
    console.error('Failed to issue refunds:', err);
    error.value = errorText(
      err,
      'The refund request failed. Some people may already have been refunded: pressing the button again is safe and only finishes what is left.'
    );
  } finally {
    busy.value = false;
  }
}

function close() {
  if (busy.value) return;
  emit('update:modelValue', false);
}
</script>
