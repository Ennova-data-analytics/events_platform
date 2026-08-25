<template>
  <div>
    <v-btn variant="text" prepend-icon="mdi-arrow-left" to="/admin/recruitment" class="mb-3">Back to board</v-btn>

    <div class="d-flex justify-space-between align-center mb-1 flex-wrap ga-2">
      <h1 :class="$vuetify.display.mobile ? 'text-h6' : 'text-h5'">Recruitment cohorts</h1>
      <v-btn color="primary" prepend-icon="mdi-plus" @click="openCreate">New cohort</v-btn>
    </div>
    <p class="text-body-2 text-medium-emphasis mb-4">
      A cohort is one recruitment round. Pick which departments recruit, set the dates, and activate it —
      the public application form and the whole panel key off the active cohort.
    </p>

    <div v-if="isLoading" class="text-center py-12">
      <v-progress-circular indeterminate color="primary" size="64" />
    </div>

    <template v-else>
      <!-- Cohort list -->
      <v-card v-for="c in cycles" :key="c.id" class="mb-3" :variant="c.is_active ? 'tonal' : 'elevated'" :color="c.is_active ? 'primary' : undefined">
        <v-card-text class="pa-4">
          <div class="d-flex align-center flex-wrap ga-3">
            <div class="flex-grow-1" style="min-width: 220px">
              <div class="d-flex align-center ga-2">
                <span class="text-subtitle-1 font-weight-bold">{{ c.name }}</span>
                <v-chip v-if="c.is_active" size="x-small" color="success" variant="flat">Active</v-chip>
              </div>
              <div class="text-caption text-medium-emphasis">
                {{ formatDate(c.opens_at) }} – {{ formatDate(c.closes_at) }}
              </div>
              <div class="d-flex flex-wrap ga-1 mt-2">
                <v-chip
                  v-for="cd in c.cycle_departments"
                  :key="cd.department_id"
                  size="x-small"
                  :color="cd.is_open ? 'primary' : undefined"
                  :variant="cd.is_open ? 'tonal' : 'outlined'"
                >
                  {{ cd.department?.name || 'Department' }}
                  <span v-if="!cd.is_open" class="ml-1 text-medium-emphasis">(closed)</span>
                </v-chip>
                <span v-if="!c.cycle_departments?.length" class="text-caption text-medium-emphasis">No departments yet</span>
              </div>
            </div>
            <div class="d-flex ga-1">
              <v-btn v-if="!c.is_active" size="small" variant="tonal" color="success" prepend-icon="mdi-flag-checkered" @click="activate(c)">Activate</v-btn>
              <v-btn icon="mdi-pencil" size="small" variant="text" @click="openEdit(c)" />
              <v-btn icon="mdi-delete-outline" size="small" variant="text" color="error" @click="askDelete(c)" />
            </div>
          </div>
        </v-card-text>
      </v-card>

      <v-alert v-if="!cycles.length" type="info" variant="tonal">
        No cohorts yet. Create one to open recruitment.
      </v-alert>

      <!-- Department catalog -->
      <v-expansion-panels class="mt-4" variant="accordion">
        <v-expansion-panel>
          <v-expansion-panel-title>
            <v-icon start size="small">mdi-account-tie-outline</v-icon>
            Department catalog ({{ departments.length }})
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <p class="text-caption text-medium-emphasis mb-3">
              The stable list of teams cohorts pick from. Scoring criteria & questions are edited on the Criteria page.
            </p>
            <div v-for="d in departments" :key="d.id" class="d-flex align-center ga-2 mb-2">
              <v-icon size="small" :color="d.is_active ? 'primary' : 'grey'">mdi-circle-medium</v-icon>
              <span class="text-body-2 flex-grow-1">{{ d.name }}</span>
              <v-chip v-if="d.has_case_stage" size="x-small" color="deep-purple" variant="tonal">Case study</v-chip>
              <v-switch
                :model-value="d.is_active"
                color="primary"
                density="compact"
                hide-details
                @update:model-value="toggleDepartmentActive(d, $event)"
              />
            </div>
            <v-btn size="small" variant="text" color="primary" prepend-icon="mdi-plus" @click="deptDialog = true">Add department</v-btn>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>
    </template>

    <!-- Create / edit cohort dialog -->
    <v-dialog v-model="dialog" :max-width="$vuetify.display.mobile ? '94vw' : '600px'" persistent>
      <v-card>
        <v-card-title class="text-h6 pt-4">{{ editing ? 'Edit cohort' : 'New cohort' }}</v-card-title>
        <v-card-text>
          <v-text-field v-model="draft.name" label="Cohort name *" variant="outlined" density="comfortable" class="mb-3" placeholder="e.g. Autumn 2026 Intake" />
          <v-row dense>
            <v-col cols="12" sm="6">
              <DateTimeField v-model="draft.opens_at" label="Opens" density="comfortable" prepend-inner-icon="mdi-calendar-start" />
            </v-col>
            <v-col cols="12" sm="6">
              <DateTimeField
                v-model="draft.closes_at"
                label="Closes"
                density="comfortable"
                prepend-inner-icon="mdi-calendar-end"
                :min-date="draft.opens_at || null"
                :start-date="draft.opens_at || null"
                :default-time="{ hours: 23, minutes: 59 }"
              />
            </v-col>
          </v-row>

          <div class="text-subtitle-2 font-weight-bold mt-2 mb-1">Departments recruiting</div>
          <p class="text-caption text-medium-emphasis mb-2">Tick the teams taking part. Untick "open" to keep a team in the cohort but paused.</p>
          <v-card variant="outlined">
            <v-list density="compact">
              <v-list-item v-for="d in departments" :key="d.id" class="px-2">
                <template #prepend>
                  <v-checkbox-btn :model-value="isSelected(d.id)" color="primary" @update:model-value="toggleSelected(d.id, $event)" />
                </template>
                <v-list-item-title class="text-body-2">{{ d.name }}</v-list-item-title>
                <template #append>
                  <v-switch
                    v-if="isSelected(d.id)"
                    :model-value="isOpen(d.id)"
                    color="primary"
                    density="compact"
                    hide-details
                    :label="isOpen(d.id) ? 'Open' : 'Paused'"
                    @update:model-value="setOpen(d.id, $event)"
                  />
                </template>
              </v-list-item>
            </v-list>
          </v-card>
          <v-alert v-if="!departments.length" type="warning" variant="tonal" density="compact" class="mt-2">
            Add a department first (in the catalog below) before creating a cohort.
          </v-alert>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="dialog = false">Cancel</v-btn>
          <v-btn color="primary" variant="flat" :disabled="!draft.name.trim()" :loading="saving" @click="save">
            {{ editing ? 'Save' : 'Create' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- New department dialog -->
    <v-dialog v-model="deptDialog" :max-width="$vuetify.display.mobile ? '92vw' : '480px'">
      <v-card>
        <v-card-title class="text-h6 pt-4">New department</v-card-title>
        <v-card-text>
          <v-text-field v-model="deptDraft.name" label="Name *" variant="outlined" density="comfortable" class="mb-3" />
          <v-textarea v-model="deptDraft.description" label="Description" variant="outlined" density="comfortable" rows="2" class="mb-2" hint="Used as context for AI matching" persistent-hint />
          <v-switch v-model="deptDraft.has_case_stage" color="deep-purple" density="compact" hide-details label="Runs a case study before interview (like Marketing)" />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="deptDialog = false">Cancel</v-btn>
          <v-btn color="primary" variant="flat" :disabled="!deptDraft.name.trim()" :loading="savingDept" @click="saveDepartment">Add</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete confirm -->
    <v-dialog v-model="deleteDialog" :max-width="$vuetify.display.mobile ? '90vw' : '420px'">
      <v-card>
        <v-card-title class="text-h6">Delete cohort?</v-card-title>
        <v-card-text>
          Delete "{{ toDelete?.name }}"? This removes the cohort and its department setup. Applications in it would be affected — this can't be undone.
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="deleteDialog = false">Cancel</v-btn>
          <v-btn color="error" variant="flat" @click="confirmDelete">Delete</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-snackbar v-model="toast.show" :color="toast.color" :timeout="2200" location="top">{{ toast.text }}</v-snackbar>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import DateTimeField from '@/components/common/DateTimeField.vue';
import { RecruitmentService } from '@/services/RecruitmentService.js';

const isLoading = ref(true);
const saving = ref(false);
const savingDept = ref(false);
const cycles = ref([]);
const departments = ref([]);

const dialog = ref(false);
const editing = ref(null);
const deptDialog = ref(false);
const deleteDialog = ref(false);
const toDelete = ref(null);

const toast = reactive({ show: false, text: '', color: 'success' });
// draft.selection: { [department_id]: is_open }
const draft = reactive({ name: '', opens_at: '', closes_at: '', selection: {} });
const deptDraft = reactive({ name: '', description: '', has_case_stage: false });

function notify(text, color = 'success') { toast.text = text; toast.color = color; toast.show = true; }

function formatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
}
// datetime-local wants "YYYY-MM-DDTHH:mm"; strip trailing seconds/zone.
function toLocalInput(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
function toIso(local) {
  return local ? new Date(local).toISOString() : null;
}

// ── Dialog selection helpers ──────────────────────────────────────────────
const isSelected = (id) => id in draft.selection;
const isOpen = (id) => !!draft.selection[id];
function toggleSelected(id, on) {
  if (on) draft.selection[id] = true;
  else delete draft.selection[id];
}
function setOpen(id, on) { draft.selection[id] = on; }

function resetDraft() {
  draft.name = '';
  draft.opens_at = '';
  draft.closes_at = '';
  draft.selection = {};
}

function openCreate() {
  editing.value = null;
  resetDraft();
  // Default: all active departments selected & open.
  departments.value.filter((d) => d.is_active).forEach((d) => { draft.selection[d.id] = true; });
  dialog.value = true;
}

function openEdit(cycle) {
  editing.value = cycle;
  draft.name = cycle.name;
  draft.opens_at = toLocalInput(cycle.opens_at);
  draft.closes_at = toLocalInput(cycle.closes_at);
  draft.selection = {};
  (cycle.cycle_departments || []).forEach((cd) => { draft.selection[cd.department_id] = cd.is_open; });
  dialog.value = true;
}

function buildPayload() {
  return {
    name: draft.name.trim(),
    opens_at: toIso(draft.opens_at),
    closes_at: toIso(draft.closes_at),
    departments: Object.entries(draft.selection).map(([id, open]) => ({ department_id: Number(id), is_open: open })),
  };
}

async function save() {
  saving.value = true;
  try {
    const payload = buildPayload();
    if (editing.value) {
      const updated = await RecruitmentService.updateCycle(editing.value.id, payload);
      const i = cycles.value.findIndex((c) => c.id === editing.value.id);
      if (i >= 0 && updated) cycles.value[i] = updated;
      notify('Cohort updated');
    } else {
      const created = await RecruitmentService.createCycle(payload);
      cycles.value.unshift(created);
      notify('Cohort created');
    }
    dialog.value = false;
  } finally {
    saving.value = false;
  }
}

async function activate(cycle) {
  await RecruitmentService.activateCycle(cycle.id);
  cycles.value.forEach((c) => { c.is_active = c.id === cycle.id; });
  notify(`${cycle.name} is now the active cohort`);
}

function askDelete(cycle) {
  toDelete.value = cycle;
  deleteDialog.value = true;
}
async function confirmDelete() {
  await RecruitmentService.deleteCycle(toDelete.value.id);
  cycles.value = cycles.value.filter((c) => c.id !== toDelete.value.id);
  deleteDialog.value = false;
  notify('Cohort deleted', 'warning');
}

async function saveDepartment() {
  savingDept.value = true;
  try {
    const dep = await RecruitmentService.createDepartment({ ...deptDraft });
    departments.value.push(dep);
    Object.assign(deptDraft, { name: '', description: '', has_case_stage: false });
    deptDialog.value = false;
    notify('Department added');
  } finally {
    savingDept.value = false;
  }
}

async function toggleDepartmentActive(dep, active) {
  dep.is_active = active;
  await RecruitmentService.updateDepartment(dep.id, { is_active: active });
  notify(`${dep.name} ${active ? 'activated' : 'deactivated'}`);
}

onMounted(async () => {
  try {
    [cycles.value, departments.value] = await Promise.all([
      RecruitmentService.getCycles(),
      RecruitmentService.getHrDepartments(),
    ]);
  } finally {
    isLoading.value = false;
  }
});
</script>
