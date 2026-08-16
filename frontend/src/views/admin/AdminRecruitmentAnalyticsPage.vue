<template>
  <div>
    <v-btn variant="text" prepend-icon="mdi-arrow-left" to="/admin/recruitment" class="mb-3">Back to board</v-btn>

    <div class="d-flex justify-space-between align-center mb-4 flex-wrap ga-2">
      <h1 :class="$vuetify.display.mobile ? 'text-h6' : 'text-h5'">Recruitment analytics</h1>
      <v-select
        v-model="cycleId"
        :items="cycles"
        item-title="name"
        item-value="id"
        variant="outlined"
        density="compact"
        hide-details
        style="max-width: 260px"
        @update:model-value="load"
      />
    </div>

    <div v-if="isLoading" class="text-center py-12">
      <v-progress-circular indeterminate color="primary" size="64" />
    </div>

    <template v-else-if="funnel">
      <!-- KPI tiles -->
      <v-row class="mb-1" dense>
        <v-col v-for="kpi in kpis" :key="kpi.label" cols="6" md="3">
          <v-card variant="tonal" :color="kpi.color">
            <v-card-text class="py-4">
              <div class="d-flex align-center mb-1">
                <v-icon :icon="kpi.icon" size="small" class="mr-2" />
                <span class="text-caption">{{ kpi.label }}</span>
              </div>
              <div class="text-h5 font-weight-bold">{{ kpi.value }}</div>
              <div class="text-caption text-medium-emphasis">{{ kpi.sub }}</div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <!-- Overall funnel -->
      <v-card class="mb-4 mt-3">
        <v-card-title class="text-subtitle-1 font-weight-bold">Overall funnel</v-card-title>
        <v-card-text>
          <div v-for="stage in funnelStages" :key="stage.key" class="mb-3">
            <div class="d-flex justify-space-between align-center mb-1">
              <span class="text-body-2">{{ stage.label }}</span>
              <span class="text-body-2 font-weight-medium">
                {{ funnel.overall[stage.key] }}
                <span class="text-caption text-medium-emphasis">({{ pct(funnel.overall[stage.key]) }}%)</span>
              </span>
            </div>
            <v-progress-linear
              :model-value="pct(funnel.overall[stage.key])"
              :color="stage.color"
              height="18"
              rounded
            />
          </div>
        </v-card-text>
      </v-card>

      <v-row>
        <!-- By department -->
        <v-col cols="12" md="7">
          <v-card>
            <v-card-title class="text-subtitle-1 font-weight-bold">By department</v-card-title>
            <v-card-text>
              <v-data-table
                :headers="deptHeaders"
                :items="funnel.by_department"
                density="compact"
                hide-default-footer
                :items-per-page="-1"
              >
                <template #item.conversion="{ item }">
                  <v-chip size="x-small" :color="convColor(item)" variant="tonal">
                    {{ item.applied ? Math.round((item.accepted / item.applied) * 100) : 0 }}%
                  </v-chip>
                </template>
              </v-data-table>
            </v-card-text>
          </v-card>
        </v-col>

        <!-- Sources -->
        <v-col cols="12" md="5">
          <v-card>
            <v-card-title class="text-subtitle-1 font-weight-bold">Where candidates come from</v-card-title>
            <v-card-text>
              <div v-for="src in funnel.sources" :key="src.source" class="mb-3">
                <div class="d-flex justify-space-between mb-1">
                  <span class="text-body-2">{{ src.source }}</span>
                  <span class="text-body-2 font-weight-medium">{{ src.count }}</span>
                </div>
                <v-progress-linear
                  :model-value="(src.count / maxSource) * 100"
                  color="primary"
                  height="10"
                  rounded
                />
              </div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <v-row class="mt-1">
        <!-- Median time in stage -->
        <v-col cols="12" md="4">
          <v-card class="h-100">
            <v-card-title class="text-subtitle-1 font-weight-bold">Median time in stage</v-card-title>
            <v-card-text>
              <div v-for="(days, key) in funnel.time_in_stage_days" :key="key" class="d-flex align-center justify-space-between mb-2">
                <span class="text-body-2">{{ statusMeta(key).title }}</span>
                <div class="d-flex align-center" style="width: 60%">
                  <v-progress-linear :model-value="(days / maxStageDays) * 100" color="purple" height="8" rounded class="mr-2" />
                  <span class="text-caption text-medium-emphasis" style="white-space: nowrap">{{ days }}d</span>
                </div>
              </div>
            </v-card-text>
          </v-card>
        </v-col>

        <!-- AI match quality -->
        <v-col cols="12" md="4">
          <v-card class="h-100">
            <v-card-title class="text-subtitle-1 font-weight-bold">AI match quality</v-card-title>
            <v-card-text>
              <div class="text-center mb-3">
                <div class="text-h4 font-weight-bold">{{ aiConfirmRate }}%</div>
                <div class="text-caption text-medium-emphasis">suggestions confirmed without override</div>
              </div>
              <div class="d-flex text-caption">
                <div class="text-center flex-grow-1">
                  <div class="font-weight-bold text-success">{{ funnel.ai_match.confirmed }}</div>
                  <div class="text-medium-emphasis">Confirmed</div>
                </div>
                <div class="text-center flex-grow-1">
                  <div class="font-weight-bold text-deep-orange">{{ funnel.ai_match.overridden }}</div>
                  <div class="text-medium-emphasis">Overridden</div>
                </div>
                <div class="text-center flex-grow-1">
                  <div class="font-weight-bold text-medium-emphasis">{{ funnel.ai_match.pending }}</div>
                  <div class="text-medium-emphasis">Pending</div>
                </div>
              </div>
            </v-card-text>
          </v-card>
        </v-col>

        <!-- By year of study -->
        <v-col cols="12" md="4">
          <v-card class="h-100">
            <v-card-title class="text-subtitle-1 font-weight-bold">Applicants by year</v-card-title>
            <v-card-text>
              <div v-for="y in funnel.by_year" :key="y.year" class="mb-2">
                <div class="d-flex justify-space-between mb-1">
                  <span class="text-body-2">{{ y.year }}</span>
                  <span class="text-caption text-medium-emphasis">{{ y.count }}</span>
                </div>
                <v-progress-linear :model-value="(y.count / maxYear) * 100" color="teal" height="8" rounded />
              </div>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { RecruitmentService } from '@/services/RecruitmentService.js';
import { statusMeta } from '@/data/recruitmentMock.js';

const isLoading = ref(true);
const funnel = ref(null);
const cycles = ref([]);
const cycleId = ref(1);

const aiConfirmRate = computed(() => {
  const m = funnel.value?.ai_match;
  if (!m) return 0;
  const decided = m.confirmed + m.overridden;
  return decided ? Math.round((m.confirmed / decided) * 100) : 0;
});
const maxStageDays = computed(() => Math.max(...Object.values(funnel.value?.time_in_stage_days || { a: 1 })));
const maxYear = computed(() => Math.max(...(funnel.value?.by_year.map((y) => y.count) || [1])));

const kpis = computed(() => {
  const o = funnel.value?.overall || {};
  const acceptRate = o.applied ? Math.round((o.accepted / o.applied) * 100) : 0;
  const interviewRate = o.applied ? Math.round((o.interview / o.applied) * 100) : 0;
  return [
    { label: 'Applications', value: o.applied ?? 0, sub: 'this cycle', icon: 'mdi-inbox-multiple', color: 'blue-grey' },
    { label: 'Interview rate', value: `${interviewRate}%`, sub: `${o.interview ?? 0} interviewed`, icon: 'mdi-account-voice', color: 'purple' },
    { label: 'Accept rate', value: `${acceptRate}%`, sub: `${o.accepted ?? 0} accepted`, icon: 'mdi-check-decagram', color: 'success' },
    { label: 'Avg. to decision', value: `${funnel.value?.avg_days_to_decision ?? '-'}d`, sub: 'applied → outcome', icon: 'mdi-timer-outline', color: 'amber-darken-2' },
  ];
});

const funnelStages = [
  { key: 'applied', label: 'Applied', color: 'blue-grey' },
  { key: 'in_review', label: 'In review', color: 'info' },
  { key: 'interview', label: 'Interviewed', color: 'purple' },
  { key: 'offered', label: 'Offered', color: 'amber-darken-2' },
  { key: 'accepted', label: 'Accepted', color: 'success' },
];

const deptHeaders = [
  { title: 'Department', key: 'department' },
  { title: 'Applied', key: 'applied' },
  { title: 'Interview', key: 'interview' },
  { title: 'Offered', key: 'offered' },
  { title: 'Accepted', key: 'accepted' },
  { title: 'Conv.', key: 'conversion', sortable: false },
];

const maxSource = computed(() => Math.max(...(funnel.value?.sources.map((s) => s.count) || [1])));

function pct(n) {
  const total = funnel.value?.overall.applied || 1;
  return Math.round((n / total) * 100);
}
function convColor(item) {
  const r = item.applied ? item.accepted / item.applied : 0;
  if (r >= 0.15) return 'success';
  if (r >= 0.08) return 'amber-darken-2';
  return 'error';
}

async function load() {
  isLoading.value = true;
  try {
    funnel.value = await RecruitmentService.getFunnel(cycleId.value);
  } finally {
    isLoading.value = false;
  }
}

onMounted(async () => {
  cycles.value = await RecruitmentService.getCycles();
  await load();
});
</script>

<style scoped>
.h-100 {
  height: 100%;
}
</style>
