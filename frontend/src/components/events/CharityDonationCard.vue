<template>
  <v-card variant="tonal" color="pink-darken-1" class="charity-card">
    <v-card-text>
      <div class="d-flex align-start">
        <v-icon color="pink-darken-1" size="28" class="mr-3 mt-1">mdi-hand-heart</v-icon>
        <div>
          <div class="text-subtitle-1 font-weight-bold">
            {{ donationOnly ? `Donate to ${charityLabel}` : 'This is a charity event' }}
          </div>
          <div class="text-body-2">
            <template v-if="donationOnly">
              Support <strong>{{ charityLabel }}</strong> without attending the event. No account needed.
            </template>
            <template v-else-if="ticketPrice > 0">
              Your ticket price of <strong>€{{ formatAmount(ticketPrice) }}</strong> goes to
              <strong>{{ charityLabel }}</strong>.
            </template>
            <template v-else>
              Proceeds from this event go to <strong>{{ charityLabel }}</strong>.
            </template>
          </div>
          <div v-if="charityDescription" class="text-body-2 mt-1 charity-description">{{ charityDescription }}</div>
        </div>
      </div>

      <template v-if="allowDonation">
        <v-divider class="my-4"></v-divider>

        <div class="text-subtitle-2 font-weight-bold mb-2">
          {{ donationOnly ? 'How much would you like to donate?' : 'Would you like to add a donation?' }}
        </div>
        <v-chip-group v-model="selectedPreset" mandatory selected-class="text-white bg-pink-darken-1" column>
          <v-chip v-if="!donationOnly" :value="0" variant="outlined" filter>No thanks</v-chip>
          <v-chip v-for="amount in presets" :key="amount" :value="amount" variant="outlined" filter>
            €{{ amount }}
          </v-chip>
          <v-chip value="custom" variant="outlined" filter>Other amount</v-chip>
        </v-chip-group>

        <v-text-field
          v-if="selectedPreset === 'custom'"
          v-model="customAmount"
          label="Donation amount (€)"
          type="number"
          min="0"
          :max="MAX_DONATION_EUROS"
          step="0.01"
          prefix="€"
          variant="outlined"
          density="comfortable"
          bg-color="white"
          class="mt-3"
          :error-messages="customAmountError"
          hide-details="auto"
        ></v-text-field>

        <template v-if="!donationOnly">
          <div class="d-flex justify-space-between align-center mt-4 text-body-2">
            <span>Ticket</span>
            <span>€{{ formatAmount(ticketPrice) }}</span>
          </div>
          <div v-if="donation > 0" class="d-flex justify-space-between align-center text-body-2">
            <span>Extra donation</span>
            <span>€{{ formatAmount(donation) }}</span>
          </div>
        </template>
        <div class="d-flex justify-space-between align-center font-weight-bold" :class="donationOnly ? 'mt-4' : 'mt-1'">
          <span>Total to pay</span>
          <span>€{{ formatAmount(ticketPrice + donation) }}</span>
        </div>

        <div class="charity-total-note d-flex align-start text-body-2 mt-3 pa-3 rounded">
          <v-icon color="pink-darken-1" size="18" class="mr-2 mt-1">mdi-information-outline</v-icon>
          <span v-if="donationOnly">
            This is a donation only and does not include a ticket to the event.
          </span>
          <span v-else-if="donation > 0">
            Your ticket is a donation too: the full <strong>€{{ formatAmount(ticketPrice + donation) }}</strong>
            goes to <strong>{{ charityLabel }}</strong> (€{{ formatAmount(ticketPrice) }} ticket +
            €{{ formatAmount(donation) }} extra donation).
          </span>
          <span v-else>
            Your ticket is itself a donation: the full <strong>€{{ formatAmount(ticketPrice) }}</strong>
            goes to <strong>{{ charityLabel }}</strong>. Anything you add above is on top of that.
          </span>
        </div>
      </template>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref, computed, watch } from 'vue';

// Mirror MAX_DONATION_EUROS and MIN_STANDALONE_DONATION_EUROS in backend/domain/schemas.py.
const MAX_DONATION_EUROS = 10000;
const MIN_STANDALONE_DONATION_EUROS = 1;
const presets = [5, 10, 20];

const props = defineProps({
  // Donation in euros; 0 means none.
  modelValue: { type: Number, default: 0 },
  charityName: { type: String, default: null },
  charityDescription: { type: String, default: null },
  ticketPrice: { type: Number, default: 0 },
  // False when there is nothing to pay (free or member-free ticket): the
  // donation rides on the ticket's checkout, so only the notice is shown.
  allowDonation: { type: Boolean, default: true },
  // Donating without registering: no ticket, and an amount is required.
  donationOnly: { type: Boolean, default: false },
});

// `update:valid` is false while the custom amount can't be submitted.
const emit = defineEmits(['update:modelValue', 'update:valid']);

const charityLabel = computed(() => props.charityName || 'charity');

const initial = props.modelValue > 0 ? props.modelValue : (props.donationOnly ? 10 : 0);
const selectedPreset = ref(initial === 0 || presets.includes(initial) ? initial : 'custom');
const customAmount = ref(selectedPreset.value === 'custom' ? String(initial) : '');

const isCustomEmpty = computed(() => customAmount.value === '' || customAmount.value === null);

const customAmountError = computed(() => {
  if (selectedPreset.value !== 'custom' || isCustomEmpty.value) return '';
  if (!/^\d+(\.\d{1,2})?$/.test(String(customAmount.value))) {
    return 'Enter an amount in euros with at most two decimal places.';
  }
  if (Number(customAmount.value) > MAX_DONATION_EUROS) return `The maximum donation is €${MAX_DONATION_EUROS}.`;
  if (props.donationOnly && Number(customAmount.value) < MIN_STANDALONE_DONATION_EUROS) {
    return `The minimum donation is €${MIN_STANDALONE_DONATION_EUROS}.`;
  }
  return '';
});

// A donation-only checkout has nothing else on it, so an empty amount is not submittable.
const isValid = computed(() => {
  if (customAmountError.value) return false;
  return !(props.donationOnly && selectedPreset.value === 'custom' && isCustomEmpty.value);
});

const donation = computed(() => {
  if (!props.allowDonation) return 0;
  if (selectedPreset.value !== 'custom') return selectedPreset.value;
  if (customAmountError.value) return 0;
  return Number(customAmount.value) || 0;
});

watch(donation, value => emit('update:modelValue', value), { immediate: true });
watch(isValid, valid => emit('update:valid', valid), { immediate: true });

function formatAmount(amount) {
  return Number(amount || 0).toFixed(2);
}
</script>

<style scoped>
.charity-card :deep(.v-card-text) {
  color: #2c3e50;
}

.charity-description {
  white-space: pre-line;
}

.charity-total-note {
  background-color: rgba(255, 255, 255, 0.7);
}
</style>
