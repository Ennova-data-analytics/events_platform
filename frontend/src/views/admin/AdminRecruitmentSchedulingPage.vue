<template>
  <div>
    <v-btn variant="text" prepend-icon="mdi-arrow-left" to="/admin/recruitment" class="mb-3">Back to board</v-btn>

    <h1 :class="$vuetify.display.mobile ? 'text-h6' : 'text-h5'" class="mb-1">Interview scheduling</h1>
    <p class="text-body-2 text-medium-emphasis mb-4">
      Each department has its own Calendly link. When you move a candidate to <strong>Interview</strong> and send the invite,
      the department's link is included in the email so the candidate books a time directly.
    </p>

    <div v-if="isLoading" class="text-center py-12">
      <v-progress-circular indeterminate color="primary" size="64" />
    </div>

    <v-row v-else>
      <!-- Calendly links per department -->
      <v-col cols="12" md="7">
        <v-card>
          <v-card-title class="text-subtitle-1 font-weight-bold">Calendly links</v-card-title>
          <v-card-text>
            <div v-for="dep in departments" :key="dep.id" class="mb-4">
              <div class="d-flex align-center mb-1">
                <span class="text-body-2 font-weight-medium">{{ dep.name }}</span>
                <v-chip
                  :color="dep.calendly_link ? 'success' : 'grey'"
                  size="x-small"
                  variant="tonal"
                  class="ml-2"
                >
                  {{ dep.calendly_link ? 'Configured' : 'Not set' }}
                </v-chip>
                <v-chip v-if="dep.has_case_stage" size="x-small" color="deep-purple" variant="tonal" class="ml-2">
                  Case study + interview
                </v-chip>
              </div>
              <div class="d-flex align-center ga-2">
                <v-text-field
                  v-model="dep.calendly_link"
                  variant="outlined"
                  density="compact"
                  hide-details
                  placeholder="https://calendly.com/…"
                  prepend-inner-icon="mdi-calendar-account"
                  @blur="save(dep)"
                />
                <v-btn
                  v-if="dep.calendly_link"
                  icon="mdi-open-in-new"
                  size="small"
                  variant="text"
                  :href="dep.calendly_link"
                  target="_blank"
                  title="Open link"
                />
              </div>
              <div v-if="dep.has_case_stage" class="text-caption text-medium-emphasis mt-1">
                Marketing runs a case study earlier in the pipeline, then a live interview - so it still uses this link.
              </div>
            </div>
            <v-alert v-if="savedFlash" type="success" variant="tonal" density="compact">
              Saved.
            </v-alert>
          </v-card-text>
        </v-card>
      </v-col>

      <!-- Email preview -->
      <v-col cols="12" md="5">
        <v-card variant="outlined">
          <v-card-title class="text-subtitle-1 font-weight-bold d-flex align-center">
            <v-icon start size="small">mdi-email-outline</v-icon>
            Interview invite preview
          </v-card-title>
          <v-card-text>
            <div class="email-preview">
              <p class="text-body-2 mb-3">Hi {{ '{first_name}' }},</p>
              <p class="text-body-2 mb-3">
                Great news - we'd love to interview you for <strong>{{ previewDept?.name || '{department}' }}</strong> at Ennova.
              </p>
              <p class="text-body-2 mb-3">Pick a time that works for you:</p>
              <div class="text-center my-4">
                <v-btn color="primary" variant="flat" size="small" :href="previewDept?.calendly_link || undefined" target="_blank">
                  Book my interview
                </v-btn>
                <div class="text-caption text-medium-emphasis mt-1">
                  {{ previewDept?.calendly_link || 'https://calendly.com/…' }}
                </div>
              </div>
              <p class="text-body-2 mb-0">See you soon,<br />The Ennova team</p>
            </div>
            <v-select
              v-model="previewDeptId"
              :items="interviewDepartmentItems"
              label="Preview for department"
              variant="outlined"
              density="compact"
              hide-details
              class="mt-3"
            />
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-snackbar v-model="toast.show" :color="toast.color" :timeout="2000" location="top">{{ toast.text }}</v-snackbar>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { RecruitmentService } from '@/services/RecruitmentService.js';

const isLoading = ref(true);
const departments = ref([]);
const previewDeptId = ref(null);
const savedFlash = ref(false);
const toast = ref({ show: false, text: '', color: 'success' });

// Every department runs a live interview (Marketing adds a case study first).
const interviewDepartmentItems = computed(() =>
  departments.value.map((d) => ({ title: d.name, value: d.id }))
);
const previewDept = computed(() => departments.value.find((d) => d.id === previewDeptId.value));

async function save(dep) {
  await RecruitmentService.updateDepartmentCalendly(dep.id, dep.calendly_link || '');
  savedFlash.value = true;
  setTimeout(() => (savedFlash.value = false), 1500);
}

onMounted(async () => {
  try {
    departments.value = await RecruitmentService.getOpenPositions();
    previewDeptId.value = interviewDepartmentItems.value[0]?.value || null;
  } finally {
    isLoading.value = false;
  }
});
</script>

<style scoped>
.email-preview {
  border: 1px solid rgba(var(--v-theme-on-surface), 0.12);
  border-radius: 8px;
  padding: 16px;
  background: rgba(var(--v-theme-on-surface), 0.02);
}
</style>
