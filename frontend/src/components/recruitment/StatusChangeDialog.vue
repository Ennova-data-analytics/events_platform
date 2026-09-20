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
          <template v-if="isHighStakes">
            <v-alert type="warning" variant="tonal" density="compact" class="mb-3">
              <v-icon start size="small">mdi-email-fast-outline</v-icon>
              This sends the <strong>{{ isOffer ? 'offer' : 'rejection' }}</strong> email to the candidate. It can't be unsent.
            </v-alert>

            <!-- Offer: the candidate answers it on their status page -->
            <template v-if="isOffer">
              <p class="text-body-2 text-medium-emphasis mb-3">
                The candidate accepts or declines on their status page. Accepting closes and locks
                their applications with other departments.
              </p>
              <v-text-field
                v-model.number="offerDays"
                type="number"
                min="1"
                max="60"
                label="Days to respond"
                variant="outlined"
                density="compact"
                prepend-inner-icon="mdi-calendar-clock"
                :hint="`Deadline ${offerDeadlineLabel}. Overdue offers stay open and are flagged on the board.`"
                persistent-hint
              />
            </template>
          </template>

          <!-- Marketing case send -->
          <template v-else-if="targetStatus === 'case_sent'">
            <v-alert type="info" variant="tonal" density="compact" class="mb-3">
              Sends the Marketing case brief with a <strong>48-hour</strong> deadline.
            </v-alert>

            <v-btn-toggle v-model="briefMode" mandatory density="compact" variant="outlined" class="mb-3">
              <v-btn value="file" size="small" prepend-icon="mdi-file-pdf-box">File</v-btn>
              <v-btn value="link" size="small" prepend-icon="mdi-link-variant">Link</v-btn>
            </v-btn-toggle>

            <template v-if="briefMode === 'file'">
              <!-- The department's saved brief is used unless a different file
                   is picked here, so the common case needs no interaction. -->
              <div
                v-if="departmentBriefName && !caseBriefFile"
                class="d-flex align-center ga-2 mb-2 text-body-2"
              >
                <v-icon size="small" color="deep-purple">mdi-file-pdf-box</v-icon>
                <span class="flex-grow-1">{{ departmentBriefName }}</span>
                <v-chip size="x-small" variant="tonal">Department default</v-chip>
              </div>
              <v-file-input
                v-model="caseBriefFile"
                :label="departmentBriefName ? 'Use a different file for this candidate' : `Case brief (${ACCEPTED_UPLOAD_LABEL})`"
                :accept="ACCEPTED_UPLOAD_MIME"
                variant="outlined"
                density="compact"
                prepend-icon=""
                prepend-inner-icon="mdi-paperclip"
                hide-details
                :loading="uploadingBrief"
              />
              <div v-if="!departmentBriefName && !caseBriefFile" class="text-caption text-medium-emphasis mt-1">
                This department has no default brief saved — attach one, or set it on the Criteria page.
              </div>
            </template>

            <v-text-field
              v-else
              v-model="caseBriefUrl"
              label="Case brief link"
              variant="outlined"
              density="compact"
              prepend-inner-icon="mdi-link-variant"
              placeholder="https://…"
              hide-details
            />
          </template>

          <!-- Interview: the invite always goes out on the move -->
          <template v-else-if="targetStatus === 'interview'">
            <v-alert type="info" variant="tonal" density="compact" class="mb-3">
              <v-icon start size="small">mdi-email-fast-outline</v-icon>
              Sends the interview invite with the booking link below.
            </v-alert>
            <v-text-field
              v-model="calendlyLink"
              label="Booking link *"
              variant="outlined"
              density="compact"
              prepend-inner-icon="mdi-calendar-account"
              placeholder="https://calendly.com/…"
              :hint="defaultCalendly
                ? 'Saved for this department — edit to use a different one.'
                : 'No link saved for this department yet; this one will be saved for next time.'"
              persistent-hint
            />
          </template>

          <p v-else class="text-caption text-medium-emphasis">No email is sent for this move.</p>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" :disabled="uploadingBrief" @click="close">Cancel</v-btn>
          <v-btn
            :color="isHighStakes ? 'warning' : 'primary'"
            variant="flat"
            :loading="uploadingBrief"
            :disabled="!canConfirm"
            @click="onPrimary"
          >
            {{ isHighStakes ? 'Continue' : 'Confirm move' }}
          </v-btn>
        </v-card-actions>
      </template>

      <!-- ── Level 2: high-stakes final confirmation ───────────────────── -->
      <template v-else>
        <v-card-title class="d-flex align-center pt-4">
          <v-icon :color="isOffer ? 'success' : 'error'" class="mr-2">mdi-shield-alert-outline</v-icon>
          Final check
        </v-card-title>
        <v-card-text>
          <p class="text-body-2 mb-3">
            You're about to <strong :class="isOffer ? 'text-success' : 'text-error'">
              {{ isOffer ? 'SEND AN OFFER TO' : 'REJECT' }}</strong>
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
            :color="isOffer ? 'success' : 'error'"
            variant="flat"
            :disabled="!acknowledged"
            @click="onConfirm"
          >
            {{ isOffer ? 'Send offer' : 'Reject & send email' }}
          </v-btn>
        </v-card-actions>
      </template>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { statusMeta, HIGH_STAKES_STATUSES } from '@/data/recruitmentMock.js';
import { RecruitmentService } from '@/services/RecruitmentService.js';
import { ACCEPTED_UPLOAD_MIME, ACCEPTED_UPLOAD_LABEL } from '@/utils/uploadTypes.js';

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  application: { type: Object, default: null },
  targetStatus: { type: String, default: null },
  defaultCalendly: { type: String, default: '' },
  // The department this candidate would receive a case for. Supplies the
  // default brief, which a per-send file or link can override.
  department: { type: Object, default: null },
});
const emit = defineEmits(['update:modelValue', 'confirm', 'error']);

const level = ref(1);
const acknowledged = ref(false);
const calendlyLink = ref('');
const caseBriefUrl = ref('');
const briefMode = ref('file');
const caseBriefFile = ref(null);
const uploadingBrief = ref(false);

const offerDays = ref(7);
const isOffer = computed(() => props.targetStatus === 'offered');
const offerDaysValid = computed(() => Number.isInteger(offerDays.value) && offerDays.value >= 1 && offerDays.value <= 60);
const offerDeadlineLabel = computed(() => {
  if (!offerDaysValid.value) return 'must be 1-60 days away';
  const d = new Date(Date.now() + offerDays.value * 86400000);
  return d.toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' });
});

// Moving to Interview always sends the invite, so a booking link is required.
const canConfirm = computed(() => {
  if (props.targetStatus === 'interview') return !!calendlyLink.value.trim();
  if (isOffer.value) return offerDaysValid.value;
  return true;
});

const departmentBriefName = computed(
  () => props.department?.case_brief_filename || (props.department?.case_brief_s3_key ? 'Saved brief' : '')
);

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
      calendlyLink.value = props.defaultCalendly || '';
      caseBriefUrl.value = '';
      caseBriefFile.value = null;
      briefMode.value = 'file';
      offerDays.value = 7;
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

// Resolve the case brief into what the API expects. A picked file is uploaded
// first; leaving both empty in file mode means "use the department default",
// which the backend resolves.
async function resolveBrief() {
  if (props.targetStatus !== 'case_sent') return {};
  if (briefMode.value === 'link') {
    return { brief_url: caseBriefUrl.value.trim() || null };
  }
  if (caseBriefFile.value) {
    const up = await RecruitmentService.uploadDocument(caseBriefFile.value);
    return { brief_s3_key: up.s3_key, brief_filename: up.filename };
  }
  return {};
}

async function onConfirm() {
  let brief;
  uploadingBrief.value = true;
  try {
    brief = await resolveBrief();
  } catch (err) {
    console.error('Failed to upload case brief:', err);
    emit('error', err.response?.data?.detail || 'Could not upload the case brief');
    return;
  } finally {
    uploadingBrief.value = false;
  }

  emit('confirm', {
    status: props.targetStatus,
    calendlyLink: calendlyLink.value.trim(),
    offerDays: isOffer.value ? offerDays.value : null,
    ...brief,
  });
  close();
}
</script>
