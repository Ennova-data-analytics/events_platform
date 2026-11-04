<template>
  <v-card variant="tonal" color="primary" class="pa-4" data-test="bring-a-friend-field">
    <div class="d-flex align-center mb-2">
      <v-icon start color="primary">mdi-account-heart</v-icon>
      <span class="font-weight-bold">{{ COPY.friendFieldTitle }}</span>
    </div>
    <v-text-field
      :model-value="modelValue"
      :label="COPY.friendFieldLabel"
      :hint="COPY.friendFieldHint"
      :error-messages="shownError"
      persistent-hint
      type="email"
      variant="outlined"
      bg-color="white"
      placeholder="friend@example.com"
      data-test="friend-email"
      @update:model-value="value => emit('update:modelValue', value)"
      @blur="touched = true"
    />
  </v-card>
</template>

<script setup>
import { computed, ref } from 'vue';
import { BRING_A_FRIEND as COPY } from '@/content/bringAFriend.js';
import { friendEmailError } from '@/utils/friendTickets.js';

const props = defineProps({
  modelValue: { type: String, default: '' },
  // So the buyer is told straight away if they typed their own email.
  buyerEmail: { type: String, default: '' },
  // Set by the page when the buyer presses the checkout button.
  showErrors: { type: Boolean, default: false },
});
const emit = defineEmits(['update:modelValue']);

const touched = ref(false);
const error = computed(() => friendEmailError(props.modelValue, props.buyerEmail));
const shownError = computed(() => ((touched.value || props.showErrors) && error.value ? [error.value] : []));
</script>
