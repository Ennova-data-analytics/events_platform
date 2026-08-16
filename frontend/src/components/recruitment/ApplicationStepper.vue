<template>
  <div>
    <v-stepper v-model="step" alt-labels flat>
      <v-stepper-header>
        <v-stepper-item :value="1" title="Basic info" :complete="step > 1" :editable="step > 1" />
        <v-divider />
        <v-stepper-item :value="2" title="Department" :complete="step > 2" :editable="step > 2" />
        <v-divider />
        <v-stepper-item :value="3" title="Documents" :complete="step > 3" :editable="step > 3" />
        <v-divider />
        <v-stepper-item :value="4" title="Match" :complete="step > 4" :editable="step > 4" />
        <v-divider />
        <v-stepper-item :value="5" title="Other teams" :editable="step > 4" />
      </v-stepper-header>

      <v-stepper-window>

        <!-- ────────────────────────────────────────────── Step 1: Basic info -->
        <v-stepper-window-item :value="1">
          <v-form ref="form1" class="pa-2">
            <p class="text-body-2 text-medium-emphasis mb-4">
              👋 Great to have you here. You won't need an account - we'll email you a private link to track your application.
            </p>
            <v-text-field
              v-model="form.full_name"
              label="Full name *"
              variant="outlined"
              class="mb-4"
              prepend-inner-icon="mdi-account-outline"
              :rules="[v => !!v || 'Full name is required']"
            />
            <v-row>
              <v-col cols="12" sm="7">
                <v-text-field
                  v-model="form.email"
                  label="Esade email *"
                  type="email"
                  variant="outlined"
                  class="mb-4"
                  prepend-inner-icon="mdi-email-outline"
                  placeholder="name.surname@alumni.esade.edu"
                  hint="Use your Esade email (esade.edu or alumni.esade.edu)"
                  :rules="emailRules"
                />
              </v-col>
              <v-col cols="12" sm="5">
                <v-text-field
                  v-model="form.phone"
                  label="Phone (optional)"
                  variant="outlined"
                  class="mb-4"
                  prepend-inner-icon="mdi-phone-outline"
                />
              </v-col>
            </v-row>
            <v-row>
              <v-col cols="12" sm="8">
                <v-select
                  v-model="form.degree"
                  :items="degrees"
                  label="Degree / programme *"
                  variant="outlined"
                  class="mb-4"
                  prepend-inner-icon="mdi-school-outline"
                  :rules="[v => !!v || 'Please select your programme']"
                />
              </v-col>
              <v-col cols="12" sm="4">
                <v-select
                  v-model="form.year"
                  :items="years"
                  label="Year *"
                  variant="outlined"
                  class="mb-4"
                  prepend-inner-icon="mdi-calendar-account"
                  :rules="[v => !!v || 'Required']"
                />
              </v-col>
            </v-row>
            <v-row>
              <v-col cols="12" sm="7">
                <v-text-field
                  v-model="form.links.linkedin"
                  label="LinkedIn *"
                  variant="outlined"
                  prepend-inner-icon="mdi-linkedin"
                  placeholder="linkedin.com/in/…"
                  hint="Recommended - it really helps us get to know you"
                  persistent-hint
                  :rules="[v => !!v || 'Please add your LinkedIn - it helps us get to know you']"
                />
              </v-col>
              <v-col cols="12" sm="5">
                <v-select
                  v-model="form.source"
                  :items="sources"
                  label="Where did you hear about us?"
                  variant="outlined"
                  prepend-inner-icon="mdi-bullhorn-outline"
                />
              </v-col>
            </v-row>
          </v-form>
        </v-stepper-window-item>

        <!-- ─────────────────────────────────────────────── Step 2: Department -->
        <v-stepper-window-item :value="2">
          <div class="pa-2">
            <p class="text-body-2 text-medium-emphasis mb-4">
              Which department would you like to apply to? There's no wrong choice - every team is a great place to grow. ✨
            </p>
            <v-row>
              <v-col v-for="dep in departments" :key="dep.id" cols="12" sm="6">
                <v-card
                  :variant="form.department_applied_id === dep.id ? 'tonal' : 'outlined'"
                  :color="form.department_applied_id === dep.id ? 'primary' : undefined"
                  class="cursor-pointer h-100"
                  @click="selectDepartment(dep.id)"
                >
                  <v-card-text class="pa-4">
                    <div class="d-flex align-center mb-2">
                      <v-icon :icon="form.department_applied_id === dep.id ? 'mdi-radiobox-marked' : 'mdi-radiobox-blank'" class="mr-2" />
                      <span class="text-subtitle-2 font-weight-bold">{{ dep.name }}</span>
                      <v-chip v-if="dep.has_case_stage" size="x-small" color="deep-purple" variant="tonal" class="ml-2">Case study</v-chip>
                    </div>
                    <div class="text-caption text-medium-emphasis mb-2">{{ dep.description }}</div>
                    <v-chip
                      v-for="skill in dep.skills_sought.slice(0, 4)"
                      :key="skill"
                      size="x-small"
                      variant="outlined"
                      class="mr-1 mb-1"
                    >
                      {{ skill }}
                    </v-chip>
                  </v-card-text>
                </v-card>
              </v-col>
            </v-row>
            <v-alert v-if="!form.department_applied_id" type="info" variant="tonal" density="compact" class="mt-4">
              Select a department to continue.
            </v-alert>
          </div>
        </v-stepper-window-item>

        <!-- ──────────────────────────────────────────────── Step 3: Documents -->
        <v-stepper-window-item :value="3">
          <div class="pa-2">
            <div class="text-subtitle-2 font-weight-bold mb-3">CV & cover letter</div>
            <v-file-input
              v-model="cvFile"
              label="CV (PDF, max 10 MB) *"
              variant="outlined"
              prepend-icon=""
              prepend-inner-icon="mdi-file-pdf-box"
              accept="application/pdf"
              class="mb-3"
              :rules="cvRules"
              @update:model-value="onCvSelected"
            />
            <v-file-input
              v-model="form.cover_letter"
              label="Cover letter (optional)"
              variant="outlined"
              prepend-icon=""
              prepend-inner-icon="mdi-file-document-outline"
              accept="application/pdf"
              class="mb-2"
            />
            <v-alert v-if="parsing" type="info" variant="tonal" density="compact" class="mb-2">
              <v-icon start size="small">mdi-auto-fix</v-icon>
              Reading your CV to prefill a few fields…
            </v-alert>
            <v-alert v-else-if="cvFile" type="success" variant="tonal" density="compact" class="mb-2">
              <v-icon start size="small">mdi-check</v-icon>
              Nice - that's the hard part done. 💪
            </v-alert>

            <v-text-field
              v-model="form.links.youtube"
              label="Video intro - YouTube"
              variant="outlined"
              class="mt-3"
              prepend-inner-icon="mdi-youtube"
              placeholder="youtu.be/…"
              hint="Optional but recommended - a 60-second hello goes a long way"
              persistent-hint
            />

            <!-- Department custom questions -->
            <template v-if="customQuestions.length">
              <v-divider class="my-4" />
              <div class="text-subtitle-2 font-weight-bold mb-1">A few questions from the {{ appliedDepartmentName }} team</div>
              <p class="text-caption text-medium-emphasis mb-3">Quick ones - just to get a feel for you.</p>
              <template v-for="q in customQuestions" :key="q.id">
                <v-select
                  v-if="q.type === 'select'"
                  v-model="form.custom_answers[q.id]"
                  :items="q.options"
                  :label="q.label + (q.required ? ' *' : '')"
                  variant="outlined"
                  class="mb-3"
                  :rules="q.required ? [v => !!v || 'Required'] : []"
                />
                <v-textarea
                  v-else-if="q.type === 'textarea'"
                  v-model="form.custom_answers[q.id]"
                  :label="q.label + (q.required ? ' *' : '')"
                  variant="outlined"
                  rows="3"
                  class="mb-3"
                  :rules="q.required ? [v => !!v || 'Required'] : []"
                />
                <v-text-field
                  v-else
                  v-model="form.custom_answers[q.id]"
                  :label="q.label + (q.required ? ' *' : '')"
                  variant="outlined"
                  class="mb-3"
                  :rules="q.required ? [v => !!v || 'Required'] : []"
                />
              </template>
            </template>

            <v-divider class="my-4" />

            <!-- Additional files -->
            <div class="d-flex align-center justify-space-between mb-2">
              <div class="text-subtitle-2 font-weight-bold">Additional files <span class="text-caption font-weight-regular text-medium-emphasis">(optional)</span></div>
              <v-btn size="small" variant="text" color="primary" prepend-icon="mdi-paperclip-plus" @click="addMaterial">Add file</v-btn>
            </div>
            <v-card v-for="(m, idx) in form.materials" :key="`mat-${idx}`" variant="outlined" class="mb-2">
              <v-card-text class="pa-3">
                <div class="d-flex align-center mb-2">
                  <span class="text-caption text-medium-emphasis flex-grow-1">Attachment {{ idx + 1 }}</span>
                  <v-btn icon="mdi-close" size="x-small" variant="text" color="error" @click="form.materials.splice(idx, 1)" />
                </div>
                <v-file-input v-model="m.file" label="File" variant="outlined" density="compact" prepend-icon="" prepend-inner-icon="mdi-file-outline" hide-details class="mb-2" />
                <v-text-field v-model="m.note" label="What is this? (context)" variant="outlined" density="compact" hide-details placeholder="e.g. A campaign I designed for a student event" />
              </v-card-text>
            </v-card>

            <!-- Additional links -->
            <div class="d-flex align-center justify-space-between mb-2 mt-4">
              <div class="text-subtitle-2 font-weight-bold">Links <span class="text-caption font-weight-regular text-medium-emphasis">(optional)</span></div>
              <v-btn size="small" variant="text" color="primary" prepend-icon="mdi-link-plus" @click="addLink">Add link</v-btn>
            </div>
            <v-row v-for="(l, idx) in form.links_list" :key="`lnk-${idx}`" dense class="align-center">
              <v-col cols="4" sm="3">
                <v-text-field v-model="l.label" label="Label" variant="outlined" density="compact" hide-details placeholder="Portfolio" />
              </v-col>
              <v-col cols="7" sm="8">
                <v-text-field v-model="l.url" label="URL" variant="outlined" density="compact" hide-details placeholder="https://…" prepend-inner-icon="mdi-link-variant" />
              </v-col>
              <v-col cols="1" class="text-center">
                <v-btn icon="mdi-close" size="x-small" variant="text" color="error" @click="form.links_list.splice(idx, 1)" />
              </v-col>
            </v-row>
          </div>
        </v-stepper-window-item>

        <!-- ─────────────────────────────────────────────────── Step 4: Match -->
        <v-stepper-window-item :value="4">
          <div class="pa-2">
            <div class="text-center py-4">
              <template v-if="aiLoading">
                <v-progress-circular indeterminate color="primary" size="56" class="mb-4" />
                <div class="text-body-1">Looking at your profile…</div>
              </template>

              <template v-else-if="aiResult">
                <v-icon :color="band.color" size="52" class="mb-2">{{ band.icon }}</v-icon>
                <h3 class="text-h6 mb-1">{{ band.title }}</h3>
                <p class="text-body-2 text-medium-emphasis mx-auto mb-2" style="max-width: 460px">{{ band.message }}</p>

                <!-- Top-2 recommendations -->
                <div class="d-flex justify-center flex-wrap ga-2 my-4">
                  <v-chip color="primary" variant="flat">
                    <v-icon start size="small">mdi-star</v-icon>
                    Top fit: {{ aiResult.top.department.name }}
                  </v-chip>
                  <v-chip v-if="aiResult.second" color="primary" variant="tonal">
                    <v-icon start size="small">mdi-star-outline</v-icon>
                    Also great: {{ aiResult.second.department.name }}
                  </v-chip>
                </div>

                <!-- Hidden numeric score behind a "view more" -->
                <v-btn variant="text" size="small" color="primary" @click="showScore = !showScore">
                  {{ showScore ? 'Hide details' : 'See my score & how it works' }}
                  <v-icon end>{{ showScore ? 'mdi-chevron-up' : 'mdi-chevron-down' }}</v-icon>
                </v-btn>
                <v-expand-transition>
                  <div v-if="showScore" class="mt-3 text-left mx-auto" style="max-width: 500px">
                    <v-card variant="tonal" color="surface-variant">
                      <v-card-text>
                        <div class="d-flex align-center justify-space-between mb-2">
                          <span class="text-body-2">Estimated fit with {{ appliedDepartmentName }}</span>
                          <span class="text-h6 font-weight-bold">{{ Math.round(aiResult.chosen_score * 100) }}%</span>
                        </div>
                        <div class="text-caption text-medium-emphasis mb-2">
                          <strong>How it works:</strong> we compare your answers and CV against what each department typically looks for
                          and estimate a fit. It's a rough first-pass signal that improves over time.
                        </div>
                        <v-alert type="info" variant="tonal" density="compact" class="mb-0">
                          This number does <strong>not</strong> decide your application. A real person reviews every applicant, and
                          plenty of brilliant members scored modestly here. Whatever it says - we're genuinely glad you applied. 🚀
                        </v-alert>
                      </v-card-text>
                    </v-card>
                  </div>
                </v-expand-transition>
              </template>
            </div>

            <!-- Change department, or proceed happily -->
            <v-card variant="tonal" color="surface-variant" class="mb-2">
              <v-card-text>
                <div class="text-body-2 font-weight-medium mb-2">Happy to continue, or want to change department?</div>
                <v-select
                  v-model="form.department_applied_id"
                  :items="departmentSelectItems"
                  label="Applying for"
                  variant="outlined"
                  density="compact"
                  hide-details
                  style="min-width: 240px; max-width: 320px"
                  @update:model-value="onDepartmentChanged"
                />
                <div class="text-caption text-medium-emphasis mt-2">
                  You apply to whichever department you choose - the score is only guidance.
                </div>
              </v-card-text>
            </v-card>
          </div>
        </v-stepper-window-item>

        <!-- ───────────────────────────────────────────────── Step 5: Other teams -->
        <v-stepper-window-item :value="5">
          <div class="pa-2">
            <p class="text-body-2 text-medium-emphasis mb-3">Almost there! 🎉 A couple of last things.</p>

            <v-switch
              v-model="form.applying_other_departments"
              color="primary"
              hide-details
              density="compact"
              label="Do you wish to apply to any other Ennova department too?"
              @update:model-value="syncRanking"
            />
            <v-select
              v-if="form.applying_other_departments"
              v-model="form.other_departments"
              :items="otherDepartmentItems"
              label="Which other departments?"
              variant="outlined"
              multiple
              chips
              closable-chips
              class="mt-3 mb-2"
              prepend-inner-icon="mdi-shuffle-variant"
              @update:model-value="syncRanking"
            />

            <!-- Ranking of the departments they're applying to -->
            <template v-if="rankingDepartments.length > 1">
              <div class="text-subtitle-2 font-weight-bold mt-3 mb-1">Rank your choices</div>
              <p class="text-caption text-medium-emphasis mb-2">Put your first choice at the top - recruiters see this order.</p>
              <v-list class="rank-list py-0" density="compact">
                <v-list-item
                  v-for="(dep, idx) in rankingDepartments"
                  :key="dep.id"
                  class="rank-item mb-1"
                >
                  <template #prepend>
                    <v-avatar size="26" :color="idx === 0 ? 'primary' : 'grey-lighten-1'" class="mr-2">
                      <span class="text-caption font-weight-bold">{{ idx + 1 }}</span>
                    </v-avatar>
                  </template>
                  <v-list-item-title class="text-body-2">{{ dep.name }}</v-list-item-title>
                  <template #append>
                    <v-btn icon="mdi-arrow-up" size="x-small" variant="text" :disabled="idx === 0" @click="moveRank(idx, -1)" />
                    <v-btn icon="mdi-arrow-down" size="x-small" variant="text" :disabled="idx === rankingDepartments.length - 1" @click="moveRank(idx, 1)" />
                  </template>
                </v-list-item>
              </v-list>
            </template>

            <v-text-field
              v-model="form.other_associations"
              label="Have you applied to any other department or association? (optional)"
              variant="outlined"
              class="mt-4"
              prepend-inner-icon="mdi-account-group-outline"
              placeholder="e.g. ESADE Consulting Club, another department last year…"
              hint="Context only - it never counts against you"
              persistent-hint
            />

            <v-divider class="my-4" />

            <div class="text-subtitle-2 font-weight-bold mb-3">Data & consent</div>
            <v-checkbox v-model="form.gdpr_consent" color="primary" hide-details="auto" class="mb-2">
              <template #label>
                <span class="text-body-2">
                  I consent to Ennova storing and processing my application data for this recruitment cycle.
                  Data is retained for up to 6 months after the cycle closes and then deleted. *
                </span>
              </template>
            </v-checkbox>
            <v-checkbox v-model="form.talent_pool_consent" color="primary" hide-details="auto" class="mb-4">
              <template #label>
                <span class="text-body-2">Keep my details in your talent pool for future cycles (optional).</span>
              </template>
            </v-checkbox>

            <v-alert v-if="!cvFile" type="warning" variant="tonal" density="compact" class="mb-4">
              You still need to attach a CV in the Documents step.
            </v-alert>
            <v-alert v-if="submitError" type="error" variant="tonal" class="mb-4">{{ submitError }}</v-alert>

            <v-btn color="primary" size="large" block :loading="isSubmitting" :disabled="!canSubmit" @click="handleSubmit">
              Submit application
            </v-btn>
          </div>
        </v-stepper-window-item>

      </v-stepper-window>
    </v-stepper>

    <!-- Navigation -->
    <div class="d-flex justify-space-between mt-4 px-2">
      <v-btn v-if="step > 1" variant="text" @click="step--">Back</v-btn>
      <v-spacer />
      <v-btn v-if="step < 5" color="primary" :disabled="!stepValid" @click="nextStep">Next</v-btn>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { RecruitmentService } from '@/services/RecruitmentService.js';
import { ESADE_DEGREES, ESADE_YEARS } from '@/data/recruitmentMock.js';

const props = defineProps({
  departments: { type: Array, default: () => [] },
});
const emit = defineEmits(['submit']);

const step = ref(1);
const form1 = ref(null);
const cvFile = ref(null);
const parsing = ref(false);
const isSubmitting = ref(false);
const submitError = ref(null);

const aiLoading = ref(false);
const aiResult = ref(null);
const showScore = ref(false);

const degrees = ESADE_DEGREES;
const years = ESADE_YEARS;
const sources = ['Class announcement', 'Instagram', 'Referral', 'Careers fair', 'Poster', 'Other'];

const form = ref({
  full_name: '',
  email: '',
  phone: '',
  degree: null,
  year: null,
  source: null,
  links: { linkedin: '', youtube: '' },
  department_applied_id: null,
  custom_answers: {},
  cover_letter: null,
  materials: [],
  links_list: [],
  applying_other_departments: false,
  other_departments: [],
  department_ranking: [],
  other_associations: '',
  gdpr_consent: false,
  talent_pool_consent: false,
});

// Accept any esade.edu address, including subdomains like alumni.esade.edu.
const ESADE_EMAIL = /@([a-z0-9-]+\.)*esade\.edu\s*$/i;
const emailRules = [
  (v) => !!v || 'Email is required',
  (v) => /.+@.+\..+/.test(v) || 'Enter a valid email',
  (v) => ESADE_EMAIL.test(v || '') || 'Please use your Esade email (esade.edu or alumni.esade.edu)',
];

const cvRules = [
  (v) => !!v || 'Please attach your CV',
  (v) => !v || v.size < 10 * 1024 * 1024 || 'File must be under 10 MB',
  (v) => !v || v.type === 'application/pdf' || 'PDF only',
];

const appliedDepartment = computed(() => props.departments.find((d) => d.id === form.value.department_applied_id));
const appliedDepartmentName = computed(() => appliedDepartment.value?.name || 'this team');
const customQuestions = computed(() => appliedDepartment.value?.custom_questions || []);

const departmentSelectItems = computed(() => props.departments.map((d) => ({ title: d.name, value: d.id })));
const otherDepartmentItems = computed(() =>
  props.departments.filter((d) => d.id !== form.value.department_applied_id).map((d) => ({ title: d.name, value: d.id }))
);
const rankingDepartments = computed(() =>
  form.value.department_ranking.map((id) => props.departments.find((d) => d.id === id)).filter(Boolean)
);

// Qualitative, encouraging band derived from the (hidden) numeric score.
const band = computed(() => {
  const s = aiResult.value?.chosen_score || 0;
  if (s >= 0.85) return { title: 'Excellent fit! 🌟', color: 'success', icon: 'mdi-check-decagram', message: `Your profile lines up beautifully with ${appliedDepartmentName.value}. We'd love to see your application.` };
  if (s >= 0.7) return { title: 'Strong fit 👍', color: 'success', icon: 'mdi-thumb-up-outline', message: `You look like a great match for ${appliedDepartmentName.value}. Go for it!` };
  if (s >= 0.55) return { title: 'Good potential ✨', color: 'info', icon: 'mdi-lightbulb-on-outline', message: `There's real potential here for ${appliedDepartmentName.value}. Applications are about more than a score.` };
  return { title: 'Worth a shot 💛', color: 'info', icon: 'mdi-hand-heart-outline', message: `Every application is reviewed by a person - and enthusiasm counts for a lot. We're glad you're here.` };
});

function addMaterial() {
  form.value.materials.push({ file: null, note: '' });
}
function addLink() {
  form.value.links_list.push({ label: '', url: '' });
}

function selectDepartment(id) {
  form.value.department_applied_id = id;
  // Keep custom-question answers relevant to the chosen department.
  form.value.custom_answers = {};
  syncRanking();
}

function onDepartmentChanged() {
  form.value.custom_answers = {};
  syncRanking();
  runAiPreview();
}

// Keep the ranking list in sync with the chosen departments, preserving order.
function syncRanking() {
  const ids = [form.value.department_applied_id, ...(form.value.applying_other_departments ? form.value.other_departments : [])]
    .filter((v) => v != null);
  const uniq = [...new Set(ids)];
  const kept = form.value.department_ranking.filter((id) => uniq.includes(id));
  const added = uniq.filter((id) => !kept.includes(id));
  form.value.department_ranking = [...kept, ...added];
}

function moveRank(idx, dir) {
  const arr = form.value.department_ranking;
  const j = idx + dir;
  if (j < 0 || j >= arr.length) return;
  [arr[idx], arr[j]] = [arr[j], arr[idx]];
}

const stepValid = computed(() => {
  switch (step.value) {
    case 1:
      return !!form.value.full_name?.trim()
        && ESADE_EMAIL.test(form.value.email || '')
        && !!form.value.degree && !!form.value.year
        && !!form.value.links.linkedin?.trim();
    case 2:
      return !!form.value.department_applied_id;
    case 3:
      return !!cvFile.value && cvFile.value.size < 10 * 1024 * 1024;
    default:
      return true;
  }
});

const canSubmit = computed(
  () => !!cvFile.value && form.value.gdpr_consent && cvFile.value.size < 10 * 1024 * 1024
);

async function runAiPreview() {
  if (!form.value.department_applied_id) return;
  aiLoading.value = true;
  aiResult.value = null;
  showScore.value = false;
  try {
    aiResult.value = await RecruitmentService.previewMatch({
      department_applied_id: form.value.department_applied_id,
      degree: form.value.degree,
    });
  } finally {
    aiLoading.value = false;
  }
}

async function nextStep() {
  if (step.value === 1 && form1.value) {
    const { valid } = await form1.value.validate();
    if (!valid) return;
  }
  step.value++;
  if (step.value === 4) runAiPreview();
  if (step.value === 5) syncRanking();
}

async function onCvSelected(file) {
  if (!file || (Array.isArray(file) && !file.length)) return;
  parsing.value = true;
  try {
    const prefill = await RecruitmentService.parseCv();
    if (prefill.full_name && !form.value.full_name) form.value.full_name = prefill.full_name;
    if (prefill.email && !form.value.email) form.value.email = prefill.email;
  } finally {
    parsing.value = false;
  }
}

async function handleSubmit() {
  isSubmitting.value = true;
  submitError.value = null;
  try {
    // Pass the raw File objects through; the service uploads them when live
    // (form.value already carries cover_letter + materials[].file).
    const result = await RecruitmentService.submitApplication({
      ...form.value,
      cv_file: cvFile.value,
    });
    emit('submit', result);
  } catch {
    submitError.value = 'Something went wrong submitting your application. Please try again.';
    isSubmitting.value = false;
  }
}
</script>

<style scoped>
.cursor-pointer {
  cursor: pointer;
}
.h-100 {
  height: 100%;
}
.rank-item {
  border: 1px solid rgba(var(--v-theme-on-surface), 0.12);
  border-radius: 8px;
}
</style>
