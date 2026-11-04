<template>
  <v-card v-if="friendTicket" variant="outlined" rounded="lg" class="pa-4" data-test="friend-ticket-card">
    <div class="d-flex align-center mb-2">
      <v-icon start color="primary">mdi-account-heart</v-icon>
      <span class="font-weight-bold">{{ COPY.cardTitle }}</span>
    </div>

    <v-alert :color="message.color" variant="tonal" density="compact" class="mb-3" data-test="friend-ticket-status">
      {{ message.text }}
    </v-alert>

    <v-alert
      v-if="errorMessage"
      type="error" variant="tonal" density="compact" class="mb-3"
      closable data-test="friend-ticket-error"
      @click:close="errorMessage = ''"
    >
      {{ errorMessage }}
    </v-alert>
    <v-alert v-if="notice" type="success" variant="tonal" density="compact" class="mb-3" data-test="friend-ticket-notice">
      {{ notice }}
    </v-alert>

    <div v-if="editing">
      <v-text-field
        v-model="newEmail"
        :label="COPY.friendFieldLabel"
        :hint="COPY.friendFieldHint"
        :error-messages="emailError ? [emailError] : []"
        persistent-hint
        type="email"
        variant="outlined"
        data-test="friend-ticket-new-email"
      />
      <div class="d-flex justify-end mt-2" style="gap: 8px">
        <v-btn variant="text" @click="editing = false">Cancel</v-btn>
        <v-btn
          color="primary" variant="flat" :loading="busy" :disabled="!!emailError"
          data-test="friend-ticket-save" @click="save"
        >
          {{ COPY.saveButton }}
        </v-btn>
      </div>
    </div>

    <div v-else class="d-flex flex-wrap" style="gap: 8px">
      <v-btn
        v-if="friendTicket.can_change" variant="tonal" size="small" prepend-icon="mdi-pencil"
        data-test="friend-ticket-change" @click="startEditing"
      >
        {{ COPY.changeButton }}
      </v-btn>
      <v-btn
        v-if="friendTicket.can_resend && friendTicket.status !== 'claimed'"
        variant="tonal" size="small" prepend-icon="mdi-email-fast" :loading="busy"
        data-test="friend-ticket-resend" @click="resend"
      >
        {{ COPY.resendButton }}
      </v-btn>
    </div>
  </v-card>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { EventService } from '@/services/EventService.js';
import { BRING_A_FRIEND as COPY } from '@/content/bringAFriend.js';
import { apiErrorMessage, friendEmailError, friendTicketMessage } from '@/utils/friendTickets.js';

const props = defineProps({
  eventId: { type: [Number, String], required: true },
  buyerEmail: { type: String, default: '' },
});

const friendTicket = ref(null);
const editing = ref(false);
const newEmail = ref('');
const busy = ref(false);
const errorMessage = ref('');
const notice = ref('');

const message = computed(() => friendTicketMessage(friendTicket.value));
const emailError = computed(() => friendEmailError(newEmail.value, props.buyerEmail));

onMounted(async () => {
  try {
    const response = await EventService.getMyFriendTicket(props.eventId);
    friendTicket.value = response.data;
  } catch (error) {
    // 404: this registration didn't come with a friend's ticket.
    if (error?.response?.status !== 404) {
      console.error('Failed to load the friend ticket', error);
    }
  }
});

function startEditing() {
  newEmail.value = '';
  notice.value = '';
  editing.value = true;
}

async function run(action, doneMessage) {
  busy.value = true;
  errorMessage.value = '';
  notice.value = '';
  try {
    const response = await action();
    friendTicket.value = response.data;
    notice.value = doneMessage;
    return true;
  } catch (error) {
    console.error('Friend ticket action failed', error);
    errorMessage.value = apiErrorMessage(error, 'Something went wrong. Please try again.');
    return false;
  } finally {
    busy.value = false;
  }
}

async function save() {
  const ok = await run(() => EventService.changeFriendEmail(props.eventId, newEmail.value.trim()), COPY.changedMessage);
  if (ok) editing.value = false;
}

function resend() {
  return run(() => EventService.resendFriendTicket(props.eventId), COPY.resentMessage);
}
</script>
