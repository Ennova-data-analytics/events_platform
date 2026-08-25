<template>
  <v-dialog :model-value="modelValue" :max-width="$vuetify.display.mobile ? '92vw' : '540px'" @update:model-value="close" persistent>
    <v-card v-if="application">
      <!-- ── Level 1: standard confirmation ────────────────────────────── -->
      <template v-if="level === 1">
        <v-card-title class="d-flex align-center pt-4">
          <v-icon :color="toMeta.color" class="mr-2">{{ toMeta.icon }}</v-icon>
          Move to {{ toMeta.title }}?
        </v-card-title>
        <v-card-text>
          <p class="text-body-2 mb-3">
            <strong>{{ application.candidate.full_name }}</strong> will move from
            <v-chip size="x-small" :color="fromMeta.color" variant="tonal">{{ fromMeta.title }}</v-chip>
            to
            <v-chip size="x-small" :color="toMeta.color" variant="tonal">{{ toMeta.title }}</v-chip>.
          </p>

          <!-- Email side-effect notice -->
          <v-alert v-if="isHighStakes" type="warning" variant="tonal" density="compact" class="mb-3">
            <v-icon start size="small">mdi-email-fast-outline</v-icon>
            This sends the <strong>{{ targetStatus === 'accepted' ? 'offer' : 'rejection' }}</strong> email to the candidate. It can't be unsent.
          </v-alert>

          <!-- Marketing case send -->
          <template v-else-if="targetStatus === 'case_sent'">
            <v-alert type="info" variant="tonal" density="compact" class="mb-3">
              Sends the Marketing case brief with a <strong>48-hour</strong> deadline.
            </v-alert>
            <v-text-field
              v-model="caseBriefUrl"
              label="Case brief link"
              variant="outlined"
              density="compact"
              prepend-inner-icon="mdi-link-variant"
              hide-details
            />
          </template>

          <!-- Interview: selective email + Calendly -->
          <template v-else-if="targetStatus === 'interview'">
            <v-checkbox
              v-model="sendInterviewInvite"
              color="primary"
              hide-details
              density="compact"
              class="mb-1"
              label="Send interview invite email now"
            />
            <div class="text-caption text-medium-emphasis mb-2 ml-8">
              Leave off to move the card now and send the invite later from the applicant screen.
            </div>
            <v-text-field
              v-if="sendInterviewInvite"
              v-model="calendlyLink"
              label="Calendly link (sent in the email)"
              variant="outlined"
              density="compact"
              prepend-inner-icon="mdi-calendar-account"
              placeholder="https://calendly.com/…"
              hide-details
              class="ml-8"
            />
          </template>

          <p v-else class="text-caption text-medium-emphasis">No email is sent for this move.</p>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="close">Cancel</v-btn>
          <v-btn :color="isHighStakes ? 'warning' : 'primary'" variant="flat" @click="onPrimary">
            {{ isHighStakes ? 'Continue' : 'Confirm move' }}
          </v-btn>
        </v-card-actions>
      </template>

      <!-- ── Level 2: high-stakes final confirmation ───────────────────── -->
      <template v-else>
        <v-card-title class="d-flex align-center pt-4">
          <v-icon :color="targetStatus === 'accepted' ? 'success' : 'error'" class="mr-2">mdi-shield-alert-outline</v-icon>
          Final check
        </v-card-title>
        <v-card-text>
          <p class="text-body-2 mb-3">
            You're about to <strong :class="targetStatus === 'accepted' ? 'text-success' : 'text-error'">
              {{ targetStatus === 'accepted' ? 'ACCEPT' : 'REJECT' }}</strong>
            {{ application.candidate.full_name }} for
            {{ (application.final_department || application.applied_department)?.name }}.
          </p>
          <v-checkbox
            v-model="acknowledged"
            color="error"
            hide-details="auto"
            :label="`I understand this emails the candidate and is final.`"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="level = 1">Back</v-btn>
          <v-btn
            :color="targetStatus === 'accepted' ? 'success' : 'error'"
            variant="flat"
            :disabled="!acknowledged"
            @click="onConfirm"
          >
            {{ targetStatus === 'accepted' ? 'Accept & send offer' : 'Reject & send email' }}
          </v-btn>
        </v-card-actions>
      </template>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { statusMeta, HIGH_STAKES_STATUSES } from '@/data/recruitmentMock.js';

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  application: { type: Object, default: null },
  targetStatus: { type: String, default: null },
  defaultCalendly: { type: String, default: '' },
  defaultCaseBrief: { type: String, default: 'https://ennova.com/cases/marketing-autumn26.pdf' },
});
const emit = defineEmits(['update:modelValue', 'confirm']);

const level = ref(1);
const acknowledged = ref(false);
const sendInterviewInvite = ref(false);
const calendlyLink = ref('');
const caseBriefUrl = ref('');

const fromMeta = computed(() => statusMeta(props.application?.status));
const toMeta = computed(() => statusMeta(props.targetStatus));
const isHighStakes = computed(() => HIGH_STAKES_STATUSES.includes(props.targetStatus));

// Reset transient state whenever the dialog (re)opens.
watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      level.value = 1;
      acknowledged.value = false;
      sendInterviewInvite.value = false;
      calendlyLink.value = props.defaultCalendly || '';
      caseBriefUrl.value = props.defaultCaseBrief || '';
    }
  }
);

function close() {
  emit('update:modelValue', false);
}

function onPrimary() {
  if (isHighStakes.value) {
    level.value = 2; // escalate to the second confirmation
  } else {
    onConfirm();
  }
}

function onConfirm() {
  emit('confirm', {
    status: props.targetStatus,
    sendInterviewInvite: sendInterviewInvite.value,
    calendlyLink: calendlyLink.value,
    caseBriefUrl: caseBriefUrl.value,
  });
  close();
}
</script>
