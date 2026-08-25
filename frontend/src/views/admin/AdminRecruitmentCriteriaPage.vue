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
  } finally {
    saving.value = null;
  }
}
async function saveQuestions(dep) {
  saving.value = `q-${dep.id}`;
  try {
    await RecruitmentService.updateDepartmentQuestions(dep.id, dep.custom_questions);
    notify(`${dep.name} questions saved`);
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
