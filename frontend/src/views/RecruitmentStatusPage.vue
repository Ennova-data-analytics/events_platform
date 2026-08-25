<template>
  <v-container class="py-8">
    <v-row justify="center">
      <v-col cols="12" md="8" lg="7">

        <v-card v-if="isLoading" class="pa-8 text-center">
          <v-progress-circular indeterminate color="primary" size="64" />
        </v-card>

        <template v-else-if="application">
          <!-- Brand strip -->
          <div class="d-flex align-center mb-4">
            <v-avatar color="primary" size="34" class="mr-2">
              <span class="text-body-2 font-weight-bold">E</span>
            </v-avatar>
            <span class="text-subtitle-1 font-weight-bold">Ennova</span>
            <span class="text-caption text-medium-emphasis ml-2">Recruitment</span>
          </div>

          <!-- Header hero -->
          <v-card class="mb-4 status-hero" :style="heroStyle">
            <v-card-text class="pa-6">
              <div class="d-flex align-center justify-space-between flex-wrap ga-3">
                <div>
                  <div class="text-overline text-medium-emphasis">Your application</div>
                  <h1 class="text-h5 font-weight-bold">{{ application.candidate.full_name }}</h1>
                  <div class="text-body-2 text-medium-emphasis d-flex align-center flex-wrap ga-1">
                    <v-icon size="x-small">mdi-account-tie-outline</v-icon>
                    {{ appliedDepartment?.name || 'Team to be confirmed' }}
                    <span class="mx-1">·</span>
                    <span>Ref {{ reference }}</span>
                  </div>
                </div>
                <v-chip :color="meta.color" variant="flat" size="large">
                  <v-icon start :icon="meta.icon" />
                  {{ meta.title }}
                </v-chip>
              </div>
              <div class="text-caption text-medium-emphasis mt-3">
                Submitted {{ formatDate(application.created_at) }} · {{ cycleName }}
              </div>
            </v-card-text>
          </v-card>

          <!-- Current status narrative -->
          <v-card class="mb-4" :color="narrative.tone" variant="tonal">
            <v-card-text class="pa-5 d-flex ga-4">
              <v-icon :icon="narrative.icon" size="32" class="mt-1" />
              <div>
                <div class="text-subtitle-1 font-weight-bold mb-1">{{ narrative.title }}</div>
                <p class="text-body-2 mb-0">{{ narrative.body }}</p>
                <p v-if="narrative.hint" class="text-caption text-medium-emphasis mt-2 mb-0">{{ narrative.hint }}</p>
              </div>
            </v-card-text>
          </v-card>

          <!-- ── Action cards ──────────────────────────────────────────── -->

          <!-- Marketing case: brief + deadline -->
          <v-card v-if="application.case && !application.case.submitted_at" class="mb-4" variant="outlined">
            <v-card-text class="pa-5">
              <div class="d-flex align-center justify-space-between flex-wrap ga-2 mb-2">
                <div class="d-flex align-center">
                  <v-icon color="deep-purple" class="mr-2">mdi-briefcase-clock-outline</v-icon>
                  <span class="text-subtitle-2 font-weight-bold">Your case study</span>
                </div>
                <v-chip :color="caseOverdue ? 'error' : 'deep-purple'" variant="tonal" size="small">
                  <v-icon start size="x-small">mdi-clock-outline</v-icon>
                  {{ caseOverdue ? 'Deadline passed' : caseCountdown + ' left' }}
                </v-chip>
              </div>
              <p class="text-body-2 text-medium-emphasis mb-3">
                Download the brief and submit your response before {{ formatDateTime(application.case.deadline_at) }}.
              </p>
              <div class="d-flex ga-2 flex-wrap">
                <v-btn :href="application.case.brief_url" target="_blank" color="deep-purple" variant="flat" size="small" prepend-icon="mdi-download">
                  Download brief
                </v-btn>
                <v-btn variant="outlined" size="small" prepend-icon="mdi-upload">Submit response</v-btn>
              </div>
            </v-card-text>
          </v-card>

          <!-- Interview booked -->
          <v-card v-if="application.interview" class="mb-4" variant="outlined">
            <v-card-text class="pa-5">
              <div class="d-flex align-center mb-2">
                <v-icon color="success" class="mr-2">mdi-calendar-check</v-icon>
                <span class="text-subtitle-2 font-weight-bold">Interview booked</span>
              </div>
              <div class="text-body-2 mb-1">{{ formatDateTime(application.interview.starts_at) }}</div>
              <div class="text-caption text-medium-emphasis mb-3">with {{ application.interview.interviewer }} · {{ appliedDepartment?.name }}</div>
              <div class="d-flex ga-2 flex-wrap">
                <v-btn :href="application.interview.meeting_link" target="_blank" color="primary" variant="flat" size="small" prepend-icon="mdi-video">Join call</v-btn>
                <v-btn variant="text" size="small" prepend-icon="mdi-calendar-edit">Reschedule</v-btn>
              </div>
            </v-card-text>
          </v-card>

          <!-- Interview invite (book via Calendly) -->
          <v-card v-else-if="application.status === 'interview'" class="mb-4" variant="outlined">
            <v-card-text class="pa-5">
              <div class="d-flex align-center mb-2">
                <v-icon color="purple" class="mr-2">mdi-calendar-clock</v-icon>
                <span class="text-subtitle-2 font-weight-bold">Book your interview</span>
              </div>
              <p class="text-body-2 text-medium-emphasis mb-3">
                Congrats on reaching the interview stage! Pick a slot that works for you - we've also emailed you this link.
              </p>
              <v-btn v-if="calendlyLink" :href="calendlyLink" target="_blank" color="primary" variant="flat" size="small" prepend-icon="mdi-calendar-account">
                Book my interview
              </v-btn>
            </v-card-text>
          </v-card>

          <!-- Accepted -->
          <v-card v-if="application.status === 'accepted'" class="mb-4" color="success" variant="tonal">
            <v-card-text class="pa-5">
              <div class="d-flex align-center mb-2">
                <v-icon class="mr-2">mdi-party-popper</v-icon>
                <span class="text-subtitle-1 font-weight-bold">Welcome to {{ appliedDepartment?.name }}!</span>
              </div>
              <p class="text-body-2 mb-0">
                Check your inbox for your offer and onboarding details. We can't wait to have you on the team.
              </p>
            </v-card-text>
          </v-card>

          <!-- Rejected -->
          <v-card v-if="application.status === 'rejected'" class="mb-4" variant="outlined">
            <v-card-text class="pa-5">
              <div class="text-subtitle-2 font-weight-bold mb-1">A note on your application</div>
              <p class="text-body-2 text-medium-emphasis mb-2">
                After careful consideration we won't be moving forward this time. It was a genuinely close call -
                please don't let it put you off applying again next cycle.
              </p>
              <p v-if="application.candidate.talent_pool_consent" class="text-caption text-medium-emphasis mb-0">
                With your permission we've kept your details in our talent pool and may reach out about future opportunities.
              </p>
            </v-card-text>
          </v-card>

          <!-- ── Progress timeline ─────────────────────────────────────── -->
          <v-card class="mb-4">
            <v-card-title class="text-subtitle-1 font-weight-bold px-6 pt-5">Progress</v-card-title>
            <v-card-text class="px-6 pb-6">
              <v-timeline side="end" density="comfortable" truncate-line="both" align="start">
                <v-timeline-item
                  v-for="stage in stages"
                  :key="stage.value"
                  :dot-color="stage.reached ? meta.color : 'grey-lighten-1'"
                  :icon="stage.reached && !stage.current ? 'mdi-check' : stage.icon"
                  size="small"
                  :fill-dot="stage.reached"
                >
                  <div class="d-flex align-center justify-space-between">
                    <span :class="stage.reached ? 'font-weight-medium' : 'text-medium-emphasis'">{{ stage.label }}</span>
                    <v-chip v-if="stage.current" size="x-small" :color="meta.color" variant="tonal" class="ml-2">Current</v-chip>
                  </div>
                  <div class="text-caption text-medium-emphasis">{{ stage.description }}</div>
                  <div v-if="stageDate(stage.value)" class="text-caption text-disabled mt-1">{{ formatDate(stageDate(stage.value)) }}</div>
                </v-timeline-item>
              </v-timeline>
            </v-card-text>
          </v-card>

          <!-- ── What you submitted ────────────────────────────────────── -->
          <v-card class="mb-4">
            <v-card-title class="text-subtitle-1 font-weight-bold px-6 pt-5">What you submitted</v-card-title>
            <v-card-text class="px-6 pb-6">
              <v-row dense class="mb-2">
                <v-col cols="6" sm="4">
                  <div class="text-caption text-medium-emphasis">Department</div>
                  <div class="text-body-2 font-weight-medium">{{ appliedDepartment?.name || '-' }}</div>
                </v-col>
                <v-col cols="6" sm="4">
                  <div class="text-caption text-medium-emphasis">Programme</div>
                  <div class="text-body-2">{{ application.candidate.degree || '-' }}</div>
                </v-col>
                <v-col cols="6" sm="4">
                  <div class="text-caption text-medium-emphasis">Year</div>
                  <div class="text-body-2">{{ application.candidate.year || '-' }}</div>
                </v-col>
              </v-row>

              <div class="text-caption text-medium-emphasis mb-1 mt-2">Documents</div>
              <div class="d-flex flex-wrap ga-2">
                <v-chip v-if="application.candidate.cv_s3_key" size="small" variant="outlined" prepend-icon="mdi-file-pdf-box">CV</v-chip>
                <v-chip
                  v-for="(m, i) in (application.answers.materials || [])"
                  :key="i"
                  size="small"
                  variant="outlined"
                  prepend-icon="mdi-paperclip"
                >
                  {{ m.filename || 'Attachment' }}
                </v-chip>
                <v-chip
                  v-for="(l, i) in (application.answers.links || [])"
                  :key="`l-${i}`"
                  size="small"
                  variant="tonal"
                  color="primary"
                  prepend-icon="mdi-link-variant"
                  :href="l.url"
                  target="_blank"
                >
                  {{ l.label }}
                </v-chip>
              </div>

              <div v-if="application.other_departments?.length" class="mt-3 text-caption text-medium-emphasis">
                Also being considered by: {{ application.other_departments.map(d => d.name).join(', ') }}.
              </div>
            </v-card-text>
          </v-card>

          <!-- ── Help / footer ─────────────────────────────────────────── -->
          <v-expansion-panels variant="accordion" class="mb-4">
            <v-expansion-panel title="What happens next?">
              <template #text>
                <p class="text-body-2 text-medium-emphasis mb-2">
                  Every application is reviewed by a real member of our team. You'll get an email at each step, and this page
                  always shows your latest status. Typical timeline from application to final decision is 1–2 weeks.
                </p>
                <p class="text-body-2 text-medium-emphasis mb-0">
                  Questions? Reply to any of our emails or reach us at
                  <a href="mailto:recruitment@ennova.com">recruitment@ennova.com</a>.
                </p>
              </template>
            </v-expansion-panel>
          </v-expansion-panels>

          <p class="text-caption text-medium-emphasis text-center">
            <v-icon size="x-small">mdi-lock-outline</v-icon>
            This page is private to you. Bookmark it - the link stays valid throughout the process.
          </p>
        </template>

        <v-card v-else class="pa-8 text-center">
          <v-icon icon="mdi-link-off" color="error" size="64" class="mb-4" />
          <h2 class="text-h6 mb-2">Link not valid</h2>
          <p class="text-body-2 text-medium-emphasis">This status link is invalid or has expired.</p>
        </v-card>

      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { RecruitmentService } from '@/services/RecruitmentService.js';
import { statusMeta } from '@/data/recruitmentMock.js';

const route = useRoute();
const isLoading = ref(true);
const application = ref(null);

const meta = computed(() => statusMeta(application.value?.status));
const appliedDepartment = computed(
  () => application.value?.final_department || application.value?.applied_department || null
);
const cycleName = computed(() => 'Autumn 2026 Intake');

// A friendly, human reference the candidate can quote in emails.
const reference = computed(() => {
  const id = application.value?.id ?? 0;
  return `EN26-${String(id).padStart(4, '0')}`;
});

const calendlyLink = computed(
  () => application.value?.final_department?.calendly_link || application.value?.applied_department?.calendly_link || ''
);

// Status-specific narrative shown in the banner.
const NARRATIVES = {
  applied: { tone: 'info', icon: 'mdi-inbox-arrow-down', title: 'Application received', body: 'Thanks for applying! Your application is in the queue and a member of our team will review it personally.', hint: 'No action needed right now - we\'ll email you as soon as there\'s an update.' },
  in_review: { tone: 'info', icon: 'mdi-file-search-outline', title: 'Under review', body: 'The team is reviewing your application right now. Hang tight - this usually takes a few days.', hint: '' },
  case_sent: { tone: 'deep-purple', icon: 'mdi-briefcase-clock-outline', title: 'Case study sent', body: 'You\'ve been invited to complete a short case study. Details and your deadline are below.', hint: '' },
  case_submitted: { tone: 'indigo', icon: 'mdi-briefcase-check-outline', title: 'Case received', body: 'Thanks - we\'ve got your case submission. The team is reviewing it and will be in touch about interviews.', hint: '' },
  interview: { tone: 'purple', icon: 'mdi-account-voice', title: 'You\'re through to interviews', body: 'Great news - we\'d love to meet you. Book a time using the link below.', hint: '' },
  decision: { tone: 'amber-darken-2', icon: 'mdi-scale-balance', title: 'Final decision in progress', body: 'Interviews are wrapped up and the team is making their final call. You\'ll hear from us very soon.', hint: '' },
  accepted: { tone: 'success', icon: 'mdi-check-decagram', title: 'You\'re in!', body: 'Congratulations - your application was successful. Details are below.', hint: '' },
  rejected: { tone: 'grey', icon: 'mdi-emoticon-sad-outline', title: 'Application closed', body: 'Thank you for taking the time to apply. See the note below.', hint: '' },
  withdrawn: { tone: 'grey', icon: 'mdi-account-off-outline', title: 'Application withdrawn', body: 'This application has been withdrawn. If that\'s a mistake, get in touch and we\'ll sort it out.', hint: '' },
};
const narrative = computed(() => NARRATIVES[application.value?.status] || NARRATIVES.applied);

const heroStyle = computed(() => ({
  borderLeft: `4px solid rgb(var(--v-theme-${meta.value.color}))`,
}));

// ── Case countdown ──────────────────────────────────────────────────────
const caseOverdue = computed(
  () => application.value?.case && new Date(application.value.case.deadline_at) < new Date()
);
const caseCountdown = computed(() => {
  if (!application.value?.case) return '';
  const diff = new Date(application.value.case.deadline_at).getTime() - Date.now();
  if (diff <= 0) return '0h';
  const hrs = Math.round(diff / 3600000);
  return hrs < 24 ? `${hrs}h` : `${Math.round(hrs / 24)}d`;
});

// ── Journey with descriptions + dates ───────────────────────────────────
const STAGE_DESC = {
  applied: 'We received your application.',
  in_review: 'A team member reviews your profile.',
  case: 'Complete and submit the case study.',
  interview: 'Meet the team.',
  decision: 'Final call and outcome email.',
};

const stages = computed(() => {
  const isMarketing = !!application.value?.case;
  const journey = [
    { value: 'applied', label: 'Application received', icon: 'mdi-inbox-arrow-down' },
    { value: 'in_review', label: 'Under review', icon: 'mdi-file-search-outline' },
    ...(isMarketing ? [{ value: 'case', label: 'Case study', icon: 'mdi-briefcase-clock-outline' }] : []),
    { value: 'interview', label: 'Interview', icon: 'mdi-account-voice' },
    { value: 'decision', label: 'Final decision', icon: 'mdi-flag-checkered' },
  ];
  const order = journey.map((s) => s.value);
  const status = application.value?.status;
  let reachedIdx;
  if (['accepted', 'rejected'].includes(status)) reachedIdx = order.indexOf('decision');
  else if (['case_sent', 'case_submitted'].includes(status)) reachedIdx = order.indexOf('case');
  else reachedIdx = order.indexOf(status);
  return journey.map((s, idx) => ({
    ...s,
    description: STAGE_DESC[s.value] || '',
    reached: idx <= reachedIdx,
    current: idx === reachedIdx,
  }));
});

// Pull the date a stage was reached from the event timeline, when available.
function stageDate(stageValue) {
  const tl = application.value?.timeline || [];
  const targets = stageValue === 'case' ? ['case_sent', 'case_submitted'] : [stageValue];
  const ev = tl.find((e) => e.type === 'status_change' && targets.includes(e.payload?.to));
  return ev?.created_at || null;
}

function formatDate(iso) {
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
}
function formatDateTime(iso) {
  return new Date(iso).toLocaleString('en-GB', { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
}

onMounted(async () => {
  try {
    application.value = await RecruitmentService.getStatusByToken(route.params.token);
  } catch {
    application.value = null;
  } finally {
    isLoading.value = false;
  }
});
</script>

<style scoped>
.status-hero {
  overflow: hidden;
}
a {
  color: rgb(var(--v-theme-primary));
  text-decoration: none;
}
</style>
