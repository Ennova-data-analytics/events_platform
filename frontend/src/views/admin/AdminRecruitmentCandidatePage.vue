<template>
  <div>
    <v-btn variant="text" prepend-icon="mdi-arrow-left" to="/admin/recruitment" class="mb-3">Back to board</v-btn>

    <div v-if="isLoading" class="text-center py-12">
      <v-progress-circular indeterminate color="primary" size="64" />
    </div>

    <template v-else-if="app">
      <!-- Header -->
      <v-card class="mb-4">
        <v-card-text class="pa-5">
          <div class="d-flex align-center flex-wrap ga-3">
            <v-avatar size="56" color="primary" variant="tonal">
              <span class="text-h6">{{ initials(app.candidate.full_name) }}</span>
            </v-avatar>
            <div class="flex-grow-1" style="min-width: 220px">
              <h1 class="text-h5 font-weight-bold">{{ app.candidate.full_name }}</h1>
              <div class="text-body-2 text-medium-emphasis">
                <a :href="`mailto:${app.candidate.email}`">{{ app.candidate.email }}</a>
                <span v-if="app.candidate.phone"> · {{ app.candidate.phone }}</span>
              </div>
              <div class="text-caption text-medium-emphasis">
                {{ app.candidate.degree }} · {{ app.candidate.year }}
              </div>
              <div class="d-flex ga-3 mt-1">
                <a v-if="app.candidate.links.linkedin" :href="`https://${app.candidate.links.linkedin}`" target="_blank" class="text-caption"><v-icon size="x-small">mdi-linkedin</v-icon> LinkedIn</a>
                <a v-if="app.candidate.links.github" :href="`https://${app.candidate.links.github}`" target="_blank" class="text-caption"><v-icon size="x-small">mdi-github</v-icon> GitHub</a>
                <a v-if="app.candidate.links.youtube" :href="app.candidate.links.youtube" target="_blank" class="text-caption"><v-icon size="x-small">mdi-youtube</v-icon> Video intro</a>
              </div>
            </div>
            <div class="text-right d-flex flex-column ga-2 align-end">
              <v-chip :color="statusMeta(app.status).color" variant="flat">
                <v-icon start :icon="statusMeta(app.status).icon" size="small" />
                {{ statusMeta(app.status).title }}
              </v-chip>
              <v-menu>
                <template #activator="{ props: menuProps }">
                  <v-btn v-bind="menuProps" size="small" variant="outlined" append-icon="mdi-menu-down">Change stage</v-btn>
                </template>
                <v-list density="compact">
                  <v-list-item
                    v-for="s in stageOptions"
                    :key="s.value"
                    @click="requestStatus(s.value)"
                  >
                    <template #prepend><v-icon :icon="s.icon" :color="s.color" size="small" /></template>
                    <v-list-item-title>{{ s.title }}</v-list-item-title>
                  </v-list-item>
                </v-list>
              </v-menu>
            </div>
          </div>
        </v-card-text>
      </v-card>

      <!-- Marketing case panel -->
      <v-card v-if="app.case" class="mb-4" variant="tonal" color="deep-purple">
        <v-card-text class="py-3">
          <div class="d-flex align-center flex-wrap ga-3">
            <v-icon>mdi-briefcase-clock-outline</v-icon>
            <div class="flex-grow-1">
              <div class="text-subtitle-2 font-weight-bold">Marketing case study</div>
              <div class="text-caption" v-if="app.case.submitted_at">
                Submitted {{ formatDateTime(app.case.submitted_at) }}
              </div>
              <div class="text-caption" v-else :class="caseOverdue ? 'text-error' : ''">
                Sent {{ formatDateTime(app.case.sent_at) }} · deadline {{ formatDateTime(app.case.deadline_at) }} ({{ caseCountdown }})
              </div>
            </div>
            <v-btn v-if="app.case.brief_url" size="small" variant="text" :href="app.case.brief_url" target="_blank" prepend-icon="mdi-file-document-outline">Brief</v-btn>
            <v-btn v-if="app.case.submission_url" size="small" variant="flat" color="deep-purple" :href="app.case.submission_url" target="_blank" prepend-icon="mdi-briefcase-check-outline">Open submission</v-btn>
          </div>
        </v-card-text>
      </v-card>

      <!-- Interview invite (selective send) -->
      <v-card v-if="app.status === 'interview'" class="mb-4" variant="outlined">
        <v-card-text class="py-3">
          <div class="d-flex align-center flex-wrap ga-3">
            <v-icon :color="app.interview_invite_sent ? 'success' : 'purple'">
              {{ app.interview_invite_sent ? 'mdi-email-check-outline' : 'mdi-email-fast-outline' }}
            </v-icon>
            <div class="flex-grow-1" style="min-width: 200px">
              <div class="text-subtitle-2 font-weight-bold">Interview invitation</div>
              <div class="text-caption text-medium-emphasis">
                {{ app.interview_invite_sent ? 'Invite sent - candidate can book via the Calendly link.' : 'Not sent yet. Send when you\'re ready (selective).' }}
              </div>
            </div>
            <v-text-field
              v-if="!app.interview_invite_sent"
              v-model="calendlyLink"
              label="Calendly link"
              variant="outlined"
              density="compact"
              hide-details
              style="max-width: 280px"
              prepend-inner-icon="mdi-calendar-account"
              placeholder="https://calendly.com/…"
            />
            <v-btn
              v-if="!app.interview_invite_sent"
              color="primary"
              variant="flat"
              size="small"
              :disabled="!calendlyLink"
              @click="sendInterviewInvite"
            >
              Send invite
            </v-btn>
          </div>
        </v-card-text>
      </v-card>

      <v-row>
        <!-- Left column -->
        <v-col cols="12" md="7">
          <!-- AI match -->
          <v-card class="mb-4">
            <v-card-title class="text-subtitle-1 font-weight-bold d-flex align-center">
              <v-icon start color="info">mdi-robot-outline</v-icon>
              AI department match
            </v-card-title>
            <v-card-text>
              <div class="text-caption text-medium-emphasis mb-2">
                Candidate applied for
                <v-chip size="x-small" variant="tonal" class="ml-1">{{ app.applied_department?.name || '-' }}</v-chip>
              </div>
              <template v-if="app.match_pending">
                <v-alert type="warning" variant="tonal" density="compact">
                  <v-icon start size="small">mdi-timer-sand</v-icon>
                  Matching pending - the model hasn't returned yet.
                  <span v-if="app.match_flags?.includes('cv_unreadable')"> CV could not be parsed; matching will run on answers only.</span>
                </v-alert>
                <v-btn size="small" variant="text" color="info" class="mt-2" prepend-icon="mdi-refresh">Retry matching</v-btn>
              </template>
              <template v-else>
                <div class="d-flex align-center mb-2">
                  <span class="text-h6 font-weight-bold mr-2">{{ app.suggested_department?.name }}</span>
                  <v-chip size="small" :color="confidenceColor" variant="flat">{{ Math.round(app.match_confidence * 100) }}% confidence</v-chip>
                  <v-chip v-if="app.suggested_department_id !== app.answers.department_applied_id" size="x-small" color="deep-orange" variant="tonal" class="ml-2">
                    differs from candidate's choice
                  </v-chip>
                </div>
                <p class="text-body-2 text-medium-emphasis mb-4">{{ app.match_rationale }}</p>

                <div class="text-caption text-medium-emphasis mb-1">Confirm or override placement</div>
                <div class="d-flex ga-2 align-center flex-wrap">
                  <v-select
                    v-model="finalDepartmentId"
                    :items="departmentItems"
                    variant="outlined"
                    density="compact"
                    hide-details
                    style="max-width: 260px"
                  />
                  <v-btn
                    color="primary"
                    variant="flat"
                    size="small"
                    :disabled="finalDepartmentId === app.final_department_id"
                    @click="saveDepartment"
                  >
                    {{ finalDepartmentId === app.suggested_department_id ? 'Confirm' : 'Override' }}
                  </v-btn>
                  <v-chip v-if="app.final_department_id" size="small" color="success" variant="tonal">
                    <v-icon start size="x-small">mdi-check</v-icon>
                    Final: {{ app.final_department?.name }}
                  </v-chip>
                </div>
              </template>
            </v-card-text>
          </v-card>

          <!-- Answers -->
          <v-card class="mb-4">
            <v-card-title class="text-subtitle-1 font-weight-bold">Application answers</v-card-title>
            <v-card-text>
              <div class="mb-4">
                <div class="text-caption text-medium-emphasis mb-1">Background</div>
                <div class="text-body-2">{{ app.answers.background }}</div>
              </div>
              <div class="mb-4">
                <div class="text-caption text-medium-emphasis mb-1">Motivation</div>
                <div class="text-body-2">{{ app.answers.motivation }}</div>
              </div>
              <!-- Candidate's ranked department preferences -->
              <div v-if="app.ranked_departments?.length" class="mb-4">
                <div class="text-caption text-medium-emphasis mb-1">Department preference (candidate's ranking)</div>
                <div class="d-flex flex-wrap ga-1">
                  <v-chip
                    v-for="(d, i) in app.ranked_departments"
                    :key="d.id"
                    size="small"
                    :color="i === 0 ? 'primary' : undefined"
                    :variant="i === 0 ? 'flat' : 'outlined'"
                  >
                    <span class="font-weight-bold mr-1">{{ i + 1 }}.</span> {{ d.name }}
                  </v-chip>
                </div>
              </div>

              <!-- Department custom-question answers -->
              <div v-if="customAnswers.length" class="mb-4">
                <div class="text-caption text-medium-emphasis mb-1">Department questions</div>
                <div v-for="qa in customAnswers" :key="qa.label" class="mb-2">
                  <div class="text-body-2 font-weight-medium">{{ qa.label }}</div>
                  <div class="text-body-2 text-medium-emphasis">{{ qa.value }}</div>
                </div>
              </div>

              <v-row>
                <v-col cols="12" sm="6">
                  <div class="text-caption text-medium-emphasis mb-1">Other associations</div>
                  <div class="text-body-2">{{ app.answers.other_associations || '-' }}</div>
                </v-col>
                <v-col cols="6" sm="3">
                  <div class="text-caption text-medium-emphasis mb-1">Availability</div>
                  <div class="text-body-2">{{ app.answers.availability || '-' }}</div>
                </v-col>
                <v-col cols="6" sm="3">
                  <div class="text-caption text-medium-emphasis mb-1">Source</div>
                  <div class="text-body-2">{{ app.source }}</div>
                </v-col>
              </v-row>
            </v-card-text>
          </v-card>

          <!-- Video intro -->
          <v-card v-if="app.candidate.links.youtube" class="mb-4">
            <v-card-title class="text-subtitle-1 font-weight-bold d-flex align-center">
              <v-icon start color="red-darken-1">mdi-youtube</v-icon>
              Video intro
            </v-card-title>
            <v-card-text class="pt-0">
              <YoutubeEmbed :video-id="app.candidate.links.youtube" :title="`${app.candidate.full_name} - video intro`" />
            </v-card-text>
          </v-card>

          <!-- Documents: CV + materials + links -->
          <v-card class="mb-4">
            <v-card-title class="text-subtitle-1 font-weight-bold">Documents</v-card-title>
            <v-card-text>
              <div class="d-flex align-center ga-3 mb-3">
                <v-icon size="40" :color="app.candidate.cv_s3_key ? 'red-darken-1' : 'grey'">mdi-file-pdf-box</v-icon>
                <div class="flex-grow-1">
                  <div class="text-body-2 font-weight-medium">{{ app.candidate.cv_s3_key ? app.candidate.cv_s3_key.split('/').pop() : 'No CV on file' }}</div>
                  <div class="text-caption text-medium-emphasis">{{ app.candidate.cv_s3_key ? 'Curriculum vitae' : 'Extraction failed or none uploaded' }}</div>
                </div>
                <v-btn v-if="app.candidate.cv_s3_key" size="small" variant="outlined" prepend-icon="mdi-open-in-new" href="#mock-cv" target="_blank">Open</v-btn>
              </div>

              <template v-if="app.answers.materials?.length">
                <v-divider class="my-2" />
                <div class="text-caption text-medium-emphasis mb-2">Additional materials</div>
                <div v-for="(m, i) in app.answers.materials" :key="i" class="d-flex align-center ga-2 mb-2">
                  <v-icon size="small" color="grey-darken-1">mdi-paperclip</v-icon>
                  <div class="flex-grow-1">
                    <div class="text-body-2">{{ m.filename }}</div>
                    <div class="text-caption text-medium-emphasis">{{ m.note }}</div>
                  </div>
                  <v-btn size="x-small" variant="text" href="#mock-material" target="_blank">Open</v-btn>
                </div>
              </template>

              <template v-if="app.answers.links?.length">
                <v-divider class="my-2" />
                <div class="text-caption text-medium-emphasis mb-2">Links</div>
                <v-btn
                  v-for="(l, i) in app.answers.links"
                  :key="i"
                  size="x-small"
                  variant="tonal"
                  color="primary"
                  class="mr-2 mb-1"
                  :href="l.url"
                  target="_blank"
                  prepend-icon="mdi-link-variant"
                >
                  {{ l.label }}
                </v-btn>
              </template>
            </v-card-text>
          </v-card>

          <!-- Scorecard - uses the department's configured criteria -->
          <v-card>
            <v-card-title class="text-subtitle-1 font-weight-bold d-flex align-center justify-space-between">
              <span>Scorecard</span>
              <v-chip size="x-small" variant="tonal">{{ scoreDepartmentName }} rubric</v-chip>
            </v-card-title>
            <v-card-text>
              <div v-for="crit in scorecard" :key="crit.id" class="mb-3">
                <div class="d-flex align-center justify-space-between mb-1">
                  <span class="text-body-2">{{ crit.label }} <span class="text-caption text-medium-emphasis">· {{ crit.weight }}%</span></span>
                  <span class="text-caption text-medium-emphasis">{{ crit.score || '-' }}/5</span>
                </div>
                <v-rating v-model="crit.score" length="5" size="small" color="amber" density="compact" hover />
              </div>
              <div class="d-flex align-center justify-space-between mb-3">
                <span class="text-body-2 font-weight-medium">Weighted total</span>
                <span class="text-subtitle-2 font-weight-bold">{{ weightedScore }}/5</span>
              </div>
              <v-textarea
                v-model="scorecardComment"
                label="Overall comment"
                variant="outlined"
                rows="2"
                density="compact"
                hide-details
                class="mt-2"
              />
              <v-btn color="primary" variant="tonal" size="small" class="mt-3" prepend-icon="mdi-content-save-outline" @click="notify('Scorecard saved')">Save scorecard</v-btn>
            </v-card-text>
          </v-card>
        </v-col>

        <!-- Right column: timeline + notes -->
        <v-col cols="12" md="5">
          <v-card class="mb-4">
            <v-card-title class="text-subtitle-1 font-weight-bold">Timeline</v-card-title>
            <v-card-text>
              <v-timeline side="end" density="compact" truncate-line="both">
                <v-timeline-item
                  v-for="(ev, i) in app.timeline"
                  :key="i"
                  :dot-color="eventColor(ev.type)"
                  :icon="eventIcon(ev.type)"
                  size="x-small"
                >
                  <div class="d-flex justify-space-between align-center">
                    <span class="text-body-2">{{ eventLabel(ev) }}</span>
                  </div>
                  <div class="text-caption text-medium-emphasis">
                    {{ ev.actor }} · {{ formatDateTime(ev.created_at) }}
                  </div>
                </v-timeline-item>
              </v-timeline>
            </v-card-text>
          </v-card>

          <v-card>
            <v-card-title class="text-subtitle-1 font-weight-bold">Notes</v-card-title>
            <v-card-text>
              <v-textarea
                v-model="newNote"
                label="Add an internal note"
                variant="outlined"
                rows="2"
                density="compact"
                hide-details
                class="mb-2"
              />
              <v-btn color="primary" variant="tonal" size="small" :disabled="!newNote.trim()" @click="addNote">Add note</v-btn>

              <v-list v-if="notes.length" density="compact" class="mt-3">
                <v-list-item v-for="(n, i) in notes" :key="i" class="px-0">
                  <template #prepend><v-icon size="small" class="mr-2">mdi-note-text-outline</v-icon></template>
                  <v-list-item-title class="text-body-2 text-wrap">{{ n.text }}</v-list-item-title>
                  <v-list-item-subtitle class="text-caption">{{ n.actor }} · just now</v-list-item-subtitle>
                </v-list-item>
              </v-list>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </template>

    <!-- Status-change confirmation (2-level for accept/reject) -->
    <StatusChangeDialog
      v-model="confirmDialog"
      :application="app"
      :target-status="pendingStatus"
      :default-calendly="calendlyLink"
      @confirm="applyStatusChange"
    />

    <v-snackbar v-model="toast.show" :color="toast.color" :timeout="2800" location="top">{{ toast.text }}</v-snackbar>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { useAuthStore } from '@/stores/auth.store';
import { RecruitmentService } from '@/services/RecruitmentService.js';
import { APPLICATION_STATUSES, statusMeta } from '@/data/recruitmentMock.js';
import { getCalendlyLink, setCalendlyLink } from '@/utils/recruitmentPrefs.js';
import YoutubeEmbed from '@/components/media/YoutubeEmbed.vue';
import StatusChangeDialog from '@/components/recruitment/StatusChangeDialog.vue';

const route = useRoute();
const authStore = useAuthStore();
const userId = computed(() => authStore.user?.id || authStore.user?.email || 'anon');

const isLoading = ref(true);
const app = ref(null);
const departments = ref([]);
const finalDepartmentId = ref(null);
const newNote = ref('');
const notes = ref([]);
const scorecardComment = ref('');
const calendlyLink = ref('');
const toast = reactive({ show: false, text: '', color: 'success' });

const confirmDialog = ref(false);
const pendingStatus = ref(null);

// Scorecard is built from the department's configured rubric (Criteria page).
const scorecard = ref([]);

const departmentItems = computed(() => departments.value.map((d) => ({ title: d.name, value: d.id })));

// Resolve the candidate's department custom-question answers to {label, value}.
const customAnswers = computed(() => {
  const dep = app.value?.applied_department;
  const answers = app.value?.answers?.custom_answers || {};
  if (!dep?.custom_questions) return [];
  return dep.custom_questions
    .filter((q) => answers[q.id] != null && answers[q.id] !== '')
    .map((q) => ({ label: q.label, value: answers[q.id] }));
});

const scoreDepartmentName = computed(
  () => (app.value?.final_department || app.value?.applied_department)?.name || 'Default'
);

// Weighted average of the rubric scores (out of 5).
const weightedScore = computed(() => {
  const rows = scorecard.value.filter((c) => c.score);
  const totalW = rows.reduce((s, c) => s + (Number(c.weight) || 0), 0);
  if (!totalW) return '0.0';
  const sum = rows.reduce((s, c) => s + c.score * (Number(c.weight) || 0), 0);
  return (sum / totalW).toFixed(1);
});

// Stage options offered in the menu - exclude current, and hide the Marketing
// case stages unless this is a Marketing application.
const stageOptions = computed(() => {
  const isMarketing = app.value?.applied_department?.has_case_stage;
  return APPLICATION_STATUSES.filter(
    (s) => s.value !== app.value?.status && (!s.marketing_only || isMarketing)
  );
});

const confidenceColor = computed(() => {
  const c = app.value?.match_confidence || 0;
  if (c >= 0.75) return 'success';
  if (c >= 0.5) return 'amber-darken-2';
  return 'error';
});

const caseOverdue = computed(
  () => app.value?.case && !app.value.case.submitted_at && new Date(app.value.case.deadline_at) < new Date()
);
const caseCountdown = computed(() => {
  if (!app.value?.case) return '';
  const diff = new Date(app.value.case.deadline_at).getTime() - Date.now();
  if (diff <= 0) return 'overdue';
  const hrs = Math.round(diff / 3600000);
  return hrs < 24 ? `${hrs}h left` : `${Math.round(hrs / 24)}d left`;
});

function initials(name) {
  return name.split(' ').map((n) => n[0]).slice(0, 2).join('').toUpperCase();
}
function notify(text, color = 'success') {
  toast.text = text; toast.color = color; toast.show = true;
}
function formatDateTime(iso) {
  return new Date(iso).toLocaleString('en-GB', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
}

const EVENT_STYLE = {
  status_change: { icon: 'mdi-swap-horizontal', color: 'primary' },
  email_sent: { icon: 'mdi-email-outline', color: 'teal' },
  ai_match: { icon: 'mdi-robot-outline', color: 'info' },
  override: { icon: 'mdi-gesture-tap', color: 'deep-orange' },
  note: { icon: 'mdi-note-text-outline', color: 'grey' },
};
const eventIcon = (t) => EVENT_STYLE[t]?.icon || 'mdi-circle-small';
const eventColor = (t) => EVENT_STYLE[t]?.color || 'grey';
function eventLabel(ev) {
  switch (ev.type) {
    case 'status_change': return `Status → ${statusMeta(ev.payload.to).title}`;
    case 'email_sent': return `Email sent: ${ev.payload.template}`;
    case 'ai_match': return `AI matched ${ev.payload.department} (${Math.round(ev.payload.confidence * 100)}%)`;
    case 'override': return `Department set to ${ev.payload.department}`;
    case 'note': return ev.payload.text;
    default: return ev.type;
  }
}

// All stage changes route through the confirmation dialog.
function requestStatus(status) {
  pendingStatus.value = status;
  confirmDialog.value = true;
}

async function applyStatusChange({ status, sendInterviewInvite: doSend, calendlyLink: link, caseBriefUrl }) {
  if (status === 'case_sent') {
    const res = await RecruitmentService.sendMarketingCase(app.value.id, { brief_url: caseBriefUrl });
    app.value.status = 'case_sent';
    app.value.case = res.case;
    pushEvent('status_change', { to: 'case_sent' });
    pushEvent('email_sent', { template: 'Marketing case brief (48h)' });
    notify('Case brief sent · 48h to submit');
  } else {
    await RecruitmentService.updateStatus(app.value.id, status);
    app.value.status = status;
    pushEvent('status_change', { to: status });
    if (status === 'interview' && doSend) {
      await RecruitmentService.sendInterviewInvite(app.value.id, { calendly_link: link });
      app.value.interview_invite_sent = true;
      pushEvent('email_sent', { template: 'Interview invitation (Calendly)' });
      notify('Moved to Interview · invite sent');
    } else if (status === 'accepted') {
      pushEvent('email_sent', { template: 'Offer' });
      notify('Accepted · offer email sent');
    } else if (status === 'rejected') {
      pushEvent('email_sent', { template: 'Rejection' });
      notify('Rejected · outcome email sent', 'warning');
    } else {
      notify(`Moved to ${statusMeta(status).title}`);
    }
  }
  pendingStatus.value = null;
}

function pushEvent(type, payload) {
  app.value.timeline.push({ type, payload, actor: 'You', created_at: new Date().toISOString() });
}

async function sendInterviewInvite() {
  await RecruitmentService.sendInterviewInvite(app.value.id, { calendly_link: calendlyLink.value });
  app.value.interview_invite_sent = true;
  setCalendlyLink(userId.value, app.value.final_department_id || app.value.answers.department_applied_id, calendlyLink.value);
  pushEvent('email_sent', { template: 'Interview invitation (Calendly)' });
  notify('Interview invite sent with Calendly link');
}

async function saveDepartment() {
  const isOverride = finalDepartmentId.value !== app.value.suggested_department_id;
  await RecruitmentService.setFinalDepartment(app.value.id, finalDepartmentId.value);
  app.value.final_department_id = finalDepartmentId.value;
  app.value.final_department = departments.value.find((d) => d.id === finalDepartmentId.value);
  pushEvent('override', { department: app.value.final_department.name });
  notify(isOverride ? 'Department overridden (logged)' : 'Suggestion confirmed');
}

async function addNote() {
  const text = newNote.value.trim();
  await RecruitmentService.addNote(app.value.id, text);
  notes.value.unshift({ text, actor: 'You' });
  pushEvent('note', { text });
  newNote.value = '';
}

onMounted(async () => {
  try {
    [app.value, departments.value] = await Promise.all([
      RecruitmentService.getApplication(route.params.id),
      RecruitmentService.getOpenPositions(),
    ]);
    finalDepartmentId.value = app.value.final_department_id || app.value.suggested_department_id;
    const deptId = app.value.final_department_id || app.value.answers.department_applied_id;
    calendlyLink.value = getCalendlyLink(userId.value, deptId, app.value.final_department?.calendly_link || app.value.applied_department?.calendly_link || '');
    buildScorecard();
  } finally {
    isLoading.value = false;
  }
});

// Build the scorecard rows from the (final or applied) department's rubric,
// falling back to a generic rubric if none is configured.
function buildScorecard() {
  const dep = app.value?.final_department || app.value?.applied_department;
  const criteria = dep?.scoring_criteria?.length
    ? dep.scoring_criteria
    : [
        { id: 'motivation', label: 'Motivation', weight: 34 },
        { id: 'skills', label: 'Skills', weight: 33 },
        { id: 'culture', label: 'Culture fit', weight: 33 },
      ];
  scorecard.value = criteria.map((c) => ({ id: c.id, label: c.label, weight: c.weight, score: 0 }));
}
</script>

<style scoped>
a { color: rgb(var(--v-theme-primary)); text-decoration: none; }
</style>
