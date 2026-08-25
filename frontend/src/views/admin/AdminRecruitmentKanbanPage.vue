<template>
  <div>
    <div class="d-flex justify-space-between align-center mb-4 flex-wrap ga-2">
      <h1 :class="$vuetify.display.mobile ? 'text-h6' : 'text-h5'">Recruitment</h1>
      <div class="d-flex ga-2">
        <v-btn-toggle v-if="!listForced" v-model="viewMode" density="comfortable" variant="outlined" divided mandatory @update:model-value="persist">
          <v-btn value="kanban" size="small"><v-icon>mdi-view-column</v-icon></v-btn>
          <v-btn value="table" size="small"><v-icon>mdi-table</v-icon></v-btn>
        </v-btn-toggle>
        <v-btn v-if="authStore.isSuperAdmin" to="/admin/recruitment/cohorts" variant="outlined" size="small" prepend-icon="mdi-cog-outline">
          <span class="d-none d-sm-inline">Cohorts</span>
        </v-btn>
        <v-btn to="/admin/recruitment/scheduling" variant="outlined" size="small" prepend-icon="mdi-calendar-account">
          <span class="d-none d-sm-inline">Scheduling</span>
        </v-btn>
        <v-btn to="/admin/recruitment/criteria" variant="outlined" size="small" prepend-icon="mdi-tune-variant">
          <span class="d-none d-sm-inline">Criteria</span>
        </v-btn>
        <v-btn to="/admin/recruitment/analytics" variant="outlined" size="small" prepend-icon="mdi-chart-box-outline">
          <span class="d-none d-sm-inline">Analytics</span>
        </v-btn>
      </div>
    </div>

    <!-- Filters -->
    <v-card class="mb-4">
      <v-card-text class="py-3">
        <v-row dense align="center">
          <v-col cols="12" sm="6" md="3">
            <v-select
              v-model="filters.cycle_id"
              :items="cycles"
              item-title="name"
              item-value="id"
              label="Cycle"
              variant="outlined"
              density="compact"
              hide-details
            />
          </v-col>
          <v-col cols="12" sm="6" md="3">
            <v-select
              v-model="filters.department_id"
              :items="departmentItems"
              label="Department"
              variant="outlined"
              density="compact"
              clearable
              hide-details
              @update:model-value="persist"
            >
              <template #append-inner>
                <v-icon v-if="filters.department_id" size="x-small" color="primary" title="Locked to your account">mdi-lock-outline</v-icon>
              </template>
            </v-select>
          </v-col>
          <v-col cols="12" sm="6" md="3">
            <v-select
              v-model="filters.stage"
              :items="stageItems"
              label="Stage"
              variant="outlined"
              density="compact"
              clearable
              hide-details
            />
          </v-col>
          <v-col cols="12" sm="6" md="3">
            <v-text-field
              v-model="filters.search"
              label="Search name or email"
              variant="outlined"
              density="compact"
              prepend-inner-icon="mdi-magnify"
              clearable
              hide-details
            />
          </v-col>
        </v-row>
        <div v-if="anyFilterActive" class="d-flex align-center mt-2">
          <v-chip size="x-small" variant="tonal" class="mr-2">{{ filtered.length }} shown</v-chip>
          <span v-if="listForced" class="text-caption text-medium-emphasis">Filtered - showing detailed list.</span>
          <span v-else-if="showMarketingStages" class="text-caption text-medium-emphasis">Marketing pipeline - case stages shown.</span>
          <v-spacer />
          <v-btn size="x-small" variant="text" @click="clearFilters">Clear filters</v-btn>
        </div>
      </v-card-text>
    </v-card>

    <v-progress-linear v-if="isLoading" indeterminate color="primary" class="mb-2" />

    <!-- Filtered → rich list with inline documents -->
    <ApplicantList v-if="listForced" :applications="filtered" @open="openCandidate" />

    <!-- Kanban -->
    <KanbanBoard
      v-else-if="viewMode === 'kanban'"
      :applications="filtered"
      :show-marketing-stages="showMarketingStages"
      @open="openCandidate"
      @status-change="requestStatusChange"
    />

    <!-- Plain table -->
    <v-card v-else>
      <v-card-text>
        <v-data-table
          :headers="headers"
          :items="filtered"
          :loading="isLoading"
          item-key="id"
          @click:row="(_, { item }) => openCandidate(item.id)"
        >
          <template #item.candidate="{ item }">
            <div class="font-weight-medium">{{ item.candidate.full_name }}</div>
            <div class="text-caption text-medium-emphasis">{{ item.candidate.email }}</div>
          </template>
          <template #item.department="{ item }">
            <v-chip v-if="item.final_department" size="small" color="primary" variant="flat">{{ item.final_department.name }}</v-chip>
            <v-chip v-else-if="item.applied_department" size="small" variant="tonal">{{ item.applied_department.name }}</v-chip>
          </template>
          <template #item.status="{ item }">
            <v-chip :color="statusMeta(item.status).color" size="small" variant="tonal">
              <v-icon start :icon="statusMeta(item.status).icon" size="x-small" />
              {{ statusMeta(item.status).title }}
            </v-chip>
          </template>
          <template #item.created_at="{ item }">
            {{ new Date(item.created_at).toLocaleDateString('en-GB') }}
          </template>
        </v-data-table>
      </v-card-text>
    </v-card>

    <!-- Status-change confirmation -->
    <StatusChangeDialog
      v-model="confirmDialog"
      :application="pendingApp"
      :target-status="pendingStatus"
      :default-calendly="pendingCalendly"
      @confirm="applyStatusChange"
    />

    <v-snackbar v-model="toast.show" :color="toast.color" :timeout="3200" location="top">{{ toast.text }}</v-snackbar>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth.store';
import { RecruitmentService } from '@/services/RecruitmentService.js';
import { statusMeta, APPLICATION_STATUSES } from '@/data/recruitmentMock.js';
import { loadPrefs, savePrefs, getCalendlyLink } from '@/utils/recruitmentPrefs.js';
import KanbanBoard from '@/components/recruitment/KanbanBoard.vue';
import ApplicantList from '@/components/recruitment/ApplicantList.vue';
import StatusChangeDialog from '@/components/recruitment/StatusChangeDialog.vue';

const router = useRouter();
const authStore = useAuthStore();
const userId = computed(() => authStore.user?.id || authStore.user?.email || 'anon');

const isLoading = ref(false);
const viewMode = ref('kanban');
const applications = ref([]);
const cycles = ref([]);
const departments = ref([]);

const filters = reactive({ cycle_id: 1, department_id: null, stage: null, search: '' });
const toast = reactive({ show: false, text: '', color: 'success' });

// Status-change dialog state
const confirmDialog = ref(false);
const pendingApp = ref(null);
const pendingStatus = ref(null);
const pendingCalendly = ref('');

const departmentItems = computed(() => departments.value.map((d) => ({ title: d.name, value: d.id })));
const stageItems = APPLICATION_STATUSES.map((s) => ({ title: s.title, value: s.value }));

const headers = [
  { title: 'Candidate', key: 'candidate', sortable: false },
  { title: 'Department', key: 'department', sortable: false },
  { title: 'Status', key: 'status' },
  { title: 'Year', key: 'candidate.year' },
  { title: 'Source', key: 'source' },
  { title: 'Applied', key: 'created_at' },
];

// Client-side filtering keeps the mockup snappy and the list/kanban in sync.
const filtered = computed(() =>
  applications.value.filter((a) => {
    if (filters.department_id && a.final_department_id !== filters.department_id && a.answers.department_applied_id !== filters.department_id) return false;
    if (filters.stage && a.status !== filters.stage) return false;
    if (filters.search) {
      const q = filters.search.toLowerCase();
      if (!a.candidate.full_name.toLowerCase().includes(q) && !a.candidate.email.toLowerCase().includes(q)) return false;
    }
    return true;
  })
);

const anyFilterActive = computed(() => !!(filters.department_id || filters.stage || filters.search));
// When filtering, the rich list is the most useful view (spec: show list format).
// Stage/search switch to the detailed list; a department filter keeps the
// kanban so its columns (including the Marketing case stages) stay visible.
const listForced = computed(() => !!(filters.stage || filters.search));

const marketingId = computed(() => departments.value.find((d) => d.name === 'Marketing')?.id);

// The Marketing-only case columns appear ONLY when the board is filtered to
// Marketing - the case study is particular to that department.
const showMarketingStages = computed(() => !!filters.department_id && filters.department_id === marketingId.value);

function notify(text, color = 'success') {
  toast.text = text;
  toast.color = color;
  toast.show = true;
}

function openCandidate(id) {
  router.push({ name: 'admin-recruitment-candidate', params: { id } });
}

function clearFilters() {
  filters.department_id = null;
  filters.stage = null;
  filters.search = '';
  persist();
}

// Persist locked department filter + view mode per user (spec: don't reset each session).
function persist() {
  savePrefs(userId.value, { departmentFilter: filters.department_id, viewMode: viewMode.value });
}

async function load() {
  isLoading.value = true;
  try {
    applications.value = await RecruitmentService.getApplications({ cycle_id: filters.cycle_id });
  } finally {
    isLoading.value = false;
  }
}

// Drag/drop asks to change status - we confirm first (no accidental moves).
function requestStatusChange({ id, to }) {
  const app = applications.value.find((a) => a.id === id);
  if (!app) return;
  pendingApp.value = app;
  pendingStatus.value = to;
  pendingCalendly.value = getCalendlyLink(userId.value, app.final_department_id || app.answers.department_applied_id, app.final_department?.calendly_link || '');
  confirmDialog.value = true;
}

async function applyStatusChange({ status, sendInterviewInvite, calendlyLink, caseBriefUrl }) {
  const app = pendingApp.value;
  if (!app) return;

  if (status === 'case_sent') {
    await RecruitmentService.sendMarketingCase(app.id, { brief_url: caseBriefUrl });
    app.status = 'case_sent';
    notify(`Case brief sent to ${app.candidate.full_name} · 48h to submit`);
  } else {
    await RecruitmentService.updateStatus(app.id, status);
    app.status = status;
    if (status === 'interview' && sendInterviewInvite) {
      await RecruitmentService.sendInterviewInvite(app.id, { calendly_link: calendlyLink });
      app.interview_invite_sent = true;
      notify(`Moved to Interview · invite sent with Calendly link`);
    } else if (status === 'interview') {
      notify(`Moved to Interview · invite not sent yet (send from applicant screen)`, 'info');
    } else if (status === 'accepted') {
      notify(`${app.candidate.full_name} accepted · offer email sent`);
    } else if (status === 'rejected') {
      notify(`${app.candidate.full_name} rejected · outcome email sent`, 'warning');
    } else {
      notify(`Moved to ${statusMeta(status).title}`);
    }
  }
  pendingApp.value = null;
  pendingStatus.value = null;
}

let searchTimer;
watch(() => filters.search, () => { clearTimeout(searchTimer); });
watch(() => filters.cycle_id, load);

onMounted(async () => {
  const prefs = loadPrefs(userId.value);
  filters.department_id = prefs.departmentFilter;
  viewMode.value = prefs.viewMode || 'kanban';
  [cycles.value, departments.value] = await Promise.all([
    RecruitmentService.getCycles(),
    RecruitmentService.getOpenPositions(),
  ]);
  await load();
});
</script>
