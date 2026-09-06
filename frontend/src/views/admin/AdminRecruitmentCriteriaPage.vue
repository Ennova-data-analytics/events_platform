<template>
  <div>
    <v-btn variant="text" prepend-icon="mdi-arrow-left" to="/admin/recruitment" class="mb-3">Back to board</v-btn>

    <h1 :class="$vuetify.display.mobile ? 'text-h6' : 'text-h5'" class="mb-1">Criteria & questions</h1>
    <p class="text-body-2 text-medium-emphasis mb-4">
      Each department sets its own scoring rubric and application questions - what you look for varies a lot per team.
    </p>

    <div v-if="isLoading" class="text-center py-12">
      <v-progress-circular indeterminate color="primary" size="64" />
    </div>

    <template v-else>
      <v-tabs v-model="tab" color="primary" class="mb-4" show-arrows>
        <v-tab v-for="dep in departments" :key="dep.id" :value="dep.id">{{ dep.name }}</v-tab>
      </v-tabs>

      <v-window v-model="tab">
        <v-window-item v-for="dep in departments" :key="dep.id" :value="dep.id">
          <v-row>
            <!-- Scoring criteria -->
            <v-col cols="12" md="6">
              <v-card class="h-100">
                <v-card-title class="text-subtitle-1 font-weight-bold d-flex align-center justify-space-between">
                  <span>Scoring criteria</span>
                  <v-chip size="x-small" :color="weightTotal(dep) === 100 ? 'success' : 'warning'" variant="tonal">
                    {{ weightTotal(dep) }}% weighted
                  </v-chip>
                </v-card-title>
                <v-card-text>
                  <!-- Skills sought — fed to the AI matcher alongside the rubric -->
                  <div class="text-caption text-medium-emphasis mb-1">
                    <v-icon size="x-small">mdi-robot-outline</v-icon>
                    Skills sought (used for AI matching)
                  </div>
                  <v-combobox
                    v-model="dep.skills_sought"
                    label="Skills"
                    variant="outlined"
                    density="compact"
                    multiple
                    chips
                    closable-chips
                    hide-details
                    class="mb-4"
                    placeholder="e.g. SQL, Python, Storytelling"
                    hint="Press enter after each skill"
                  />

                  <p class="text-caption text-medium-emphasis mb-3">
                    The rubric reviewers score against — also fed to the AI matcher. Weights ideally sum to 100%.
                  </p>
                  <div v-for="(c, idx) in dep.scoring_criteria" :key="idx" class="d-flex align-center ga-2 mb-2">
                    <v-text-field
                      v-model="c.label"
                      variant="outlined"
                      density="compact"
                      hide-details
                      placeholder="Criterion"
                    />
                    <v-text-field
                      v-model.number="c.weight"
                      variant="outlined"
                      density="compact"
                      hide-details
                      type="number"
                      suffix="%"
                      style="max-width: 96px"
                    />
                    <v-btn icon="mdi-close" size="x-small" variant="text" color="error" @click="dep.scoring_criteria.splice(idx, 1)" />
                  </div>
                  <v-btn size="small" variant="text" color="primary" prepend-icon="mdi-plus" class="mt-1" @click="addCriterion(dep)">
                    Add criterion
                  </v-btn>

                  <!-- Live weight preview -->
                  <div class="mt-4">
                    <div v-for="c in dep.scoring_criteria" :key="c.id || c.label" class="mb-2">
                      <div class="d-flex justify-space-between text-caption mb-1">
                        <span>{{ c.label || 'Untitled' }}</span>
                        <span class="text-medium-emphasis">{{ c.weight || 0 }}%</span>
                      </div>
                      <v-progress-linear :model-value="c.weight || 0" color="primary" height="6" rounded />
                    </div>
                  </div>

                  <v-btn color="primary" variant="flat" size="small" class="mt-3" :loading="saving === `crit-${dep.id}`" @click="saveCriteria(dep)">
                    Save rubric
                  </v-btn>
                </v-card-text>
              </v-card>
            </v-col>

            <!-- Custom questions -->
            <v-col cols="12" md="6">
              <v-card class="h-100">
                <v-card-title class="text-subtitle-1 font-weight-bold">Application questions</v-card-title>
                <v-card-text>
                  <p class="text-caption text-medium-emphasis mb-3">
                    Extra questions shown to applicants who pick this department.
                  </p>
                  <v-card v-for="(q, idx) in dep.custom_questions" :key="idx" variant="outlined" class="mb-2">
                    <v-card-text class="pa-3">
                      <div class="d-flex align-center mb-2">
                        <span class="text-caption text-medium-emphasis flex-grow-1">Question {{ idx + 1 }}</span>
                        <v-btn icon="mdi-close" size="x-small" variant="text" color="error" @click="dep.custom_questions.splice(idx, 1)" />
                      </div>
                      <v-text-field
                        v-model="q.label"
                        label="Question"
                        variant="outlined"
                        density="compact"
                        hide-details
                        class="mb-2"
                      />
                      <div class="d-flex ga-2 align-center">
                        <v-select
                          v-model="q.type"
                          :items="questionTypes"
                          label="Type"
                          variant="outlined"
                          density="compact"
                          hide-details
                          style="max-width: 160px"
                        />
                        <v-checkbox v-model="q.required" label="Required" color="primary" density="compact" hide-details />
                      </div>
                      <v-combobox
                        v-if="q.type === 'select'"
                        v-model="q.options"
                        label="Options"
                        variant="outlined"
                        density="compact"
                        multiple
                        chips
                        closable-chips
                        hide-details
                        class="mt-2"
                        hint="Press enter after each option"
                      />
                    </v-card-text>
                  </v-card>

                  <v-btn size="small" variant="text" color="primary" prepend-icon="mdi-plus" @click="addQuestion(dep)">
                    Add question
                  </v-btn>

                  <div>
                    <v-btn color="primary" variant="flat" size="small" class="mt-3" :loading="saving === `q-${dep.id}`" @click="saveQuestions(dep)">
                      Save questions
                    </v-btn>
                  </div>

                  <v-alert type="info" variant="tonal" density="compact" class="mt-3">
                    Tip: keep it to 1–2 questions so the form stays quick.
                  </v-alert>
                </v-card-text>
              </v-card>
            </v-col>

            <!-- Case stage: the toggle lives here alongside the brief, so this
                 page is self-sufficient. Previously the card was hidden outright
                 for departments without a case stage, and the only toggle was on
                 the Cohorts page - so there was no way in from here. -->
            <v-col cols="12">
              <v-card>
                <v-card-title class="text-subtitle-1 font-weight-bold">Case study stage</v-card-title>
                <v-card-text>
                  <div class="d-flex align-center justify-space-between mb-2">
                    <div>
                      <div class="text-body-2 font-weight-medium">
                        {{ dep.name }} runs a case study before interviews
                      </div>
                      <div class="text-caption text-medium-emphasis">
                        Adds the Case Sent / Case Submitted stages to the board for this department.
                      </div>
                    </div>
                    <v-switch
                      :model-value="dep.has_case_stage"
                      color="deep-purple"
                      density="compact"
                      hide-details
                      :loading="saving === `case-${dep.id}`"
                      class="ml-4 flex-shrink-0"
                      @update:model-value="toggleCaseStage(dep, $event)"
                    />
                  </div>

                  <template v-if="dep.has_case_stage">
                    <v-divider class="my-3" />
                    <div class="text-subtitle-2 font-weight-bold mb-1">Case brief</div>
                    <p class="text-caption text-medium-emphasis mb-3">
                      The file sent to candidates when they move to Case Sent. Saved once here and
                      reused for everyone; a recruiter can still attach a different file for an
                      individual candidate.
                    </p>

                  <div v-if="dep.case_brief_s3_key" class="d-flex align-center ga-3 mb-3">
                    <v-icon size="32" color="red-darken-1">mdi-file-pdf-box</v-icon>
                    <div class="flex-grow-1">
                      <div class="text-body-2 font-weight-medium">
                        {{ dep.case_brief_filename || 'Case brief' }}
                      </div>
                      <div class="text-caption text-medium-emphasis">Currently sent to candidates</div>
                    </div>
                    <v-btn
                      size="small"
                      variant="text"
                      color="error"
                      :loading="saving === `brief-${dep.id}`"
                      @click="removeCaseBrief(dep)"
                    >
                      Remove
                    </v-btn>
                  </div>
                  <v-alert v-else type="warning" variant="tonal" density="compact" class="mb-3">
                    No brief saved. Recruiters will have to attach one on every send.
                  </v-alert>

                  <v-file-input
                    v-model="briefFiles[dep.id]"
                    :label="dep.case_brief_s3_key ? 'Replace with a new file' : `Upload the case brief (${ACCEPTED_UPLOAD_LABEL})`"
                    :accept="ACCEPTED_UPLOAD_MIME"
                    variant="outlined"
                    density="compact"
                    prepend-icon=""
                    prepend-inner-icon="mdi-paperclip"
                    hide-details
                  />
                  <v-btn
                    color="primary"
                    variant="flat"
                    size="small"
                    class="mt-3"
                    :disabled="!briefFiles[dep.id]"
                    :loading="saving === `brief-${dep.id}`"
                    @click="saveCaseBrief(dep)"
                  >
                    Save brief
                  </v-btn>
                  </template>
                </v-card-text>
              </v-card>
            </v-col>
          </v-row>
        </v-window-item>
      </v-window>
    </template>

    <v-snackbar v-model="toast.show" :color="toast.color" :timeout="2000" location="top">{{ toast.text }}</v-snackbar>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { RecruitmentService } from '@/services/RecruitmentService.js';
import { ACCEPTED_UPLOAD_MIME, ACCEPTED_UPLOAD_LABEL } from '@/utils/uploadTypes.js';

const isLoading = ref(true);
const departments = ref([]);
const tab = ref(null);
const saving = ref(null);
const toast = reactive({ show: false, text: '', color: 'success' });

const questionTypes = [
  { title: 'Short text', value: 'text' },
  { title: 'Long text', value: 'textarea' },
  { title: 'Choice', value: 'select' },
];

function notify(text, color = 'success') {
  toast.text = text;
  toast.color = color;
  toast.show = true;
}
function weightTotal(dep) {
  return (dep.scoring_criteria || []).reduce((sum, c) => sum + (Number(c.weight) || 0), 0);
}

function addCriterion(dep) {
  dep.scoring_criteria.push({ id: `c_${Date.now()}`, label: '', weight: 0 });
}
function addQuestion(dep) {
  dep.custom_questions.push({ id: `q_${Date.now()}`, label: '', type: 'text', required: false, options: [] });
}

async function saveCriteria(dep) {
  saving.value = `crit-${dep.id}`;
  try {
    // Persist the rubric + skills together (both feed the AI matcher).
    await RecruitmentService.updateDepartment(dep.id, {
      scoring_criteria: dep.scoring_criteria,
      skills_sought: dep.skills_sought || [],
    });
    notify(`${dep.name} rubric saved`);
  } catch (err) {
    console.error('Failed to save rubric:', err);
    notify(err.response?.data?.detail || 'Could not save the rubric', 'error');
  } finally {
    saving.value = null;
  }
}
// Per-department pending file selections, keyed by department id.
const briefFiles = reactive({});

async function toggleCaseStage(dep, enabled) {
  const previous = dep.has_case_stage;
  dep.has_case_stage = enabled;   // optimistic, reverted below if the save fails
  saving.value = `case-${dep.id}`;
  try {
    await RecruitmentService.updateDepartment(dep.id, { has_case_stage: enabled });
    notify(`${dep.name} ${enabled ? 'now runs' : 'no longer runs'} a case stage`);
  } catch (err) {
    console.error('Failed to update case stage:', err);
    dep.has_case_stage = previous;
    notify(err.response?.data?.detail || 'Could not update the case stage', 'error');
  } finally {
    saving.value = null;
  }
}

async function saveCaseBrief(dep) {
  const file = briefFiles[dep.id];
  if (!file) return;
  saving.value = `brief-${dep.id}`;
  try {
    // Same upload path candidates use for their CVs.
    const up = await RecruitmentService.uploadDocument(file);
    await RecruitmentService.updateDepartment(dep.id, {
      case_brief_s3_key: up.s3_key,
      case_brief_filename: up.filename,
    });
    dep.case_brief_s3_key = up.s3_key;
    dep.case_brief_filename = up.filename;
    briefFiles[dep.id] = null;
    notify(`${dep.name} case brief saved`);
  } catch (err) {
    console.error('Failed to save case brief:', err);
    notify(err.response?.data?.detail || 'Could not save the case brief', 'error');
  } finally {
    saving.value = null;
  }
}

async function removeCaseBrief(dep) {
  saving.value = `brief-${dep.id}`;
  try {
    // Clears the default only. Candidates already sent this brief keep their
    // own copy of the key, so their links go on working.
    await RecruitmentService.updateDepartment(dep.id, {
      case_brief_s3_key: null,
      case_brief_filename: null,
    });
    dep.case_brief_s3_key = null;
    dep.case_brief_filename = null;
    notify(`${dep.name} case brief removed`, 'warning');
  } catch (err) {
    console.error('Failed to remove case brief:', err);
    notify(err.response?.data?.detail || 'Could not remove the case brief', 'error');
  } finally {
    saving.value = null;
  }
}

async function saveQuestions(dep) {
  saving.value = `q-${dep.id}`;
  try {
    await RecruitmentService.updateDepartmentQuestions(dep.id, dep.custom_questions);
    notify(`${dep.name} questions saved`);
  } catch (err) {
    console.error('Failed to save questions:', err);
    notify(err.response?.data?.detail || 'Could not save the questions', 'error');
  } finally {
    saving.value = null;
  }
}

onMounted(async () => {
  try {
    // HR endpoint returns the full config (criteria/skills), unlike the public
    // /positions endpoint which strips the rubric.
    departments.value = await RecruitmentService.getHrDepartments();
    // Ensure editable arrays exist.
    departments.value.forEach((d) => {
      d.scoring_criteria = d.scoring_criteria || [];
      d.custom_questions = d.custom_questions || [];
      d.skills_sought = d.skills_sought || [];
    });
    tab.value = departments.value[0]?.id ?? null;
  } finally {
    isLoading.value = false;
  }
});
</script>

<style scoped>
.h-100 {
  height: 100%;
}
</style>
