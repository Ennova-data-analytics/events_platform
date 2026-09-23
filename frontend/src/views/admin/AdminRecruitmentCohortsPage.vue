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
                  :color="departmentState(cd).accepting ? 'primary' : undefined"
                  :variant="departmentState(cd).accepting ? 'tonal' : 'outlined'"
                >
                  {{ cd.department?.name || 'Department' }}
                  <span v-if="departmentState(cd).note" class="ml-1 text-medium-emphasis">({{ departmentState(cd).note }})</span>
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
              <div class="flex-grow-1" style="min-width: 0">
                <div class="text-body-2">{{ d.name }}</div>
                <div v-if="d.description" class="text-caption text-medium-emphasis text-truncate">{{ d.description }}</div>
              </div>
              <v-chip v-if="d.has_case_stage" size="x-small" color="deep-purple" variant="tonal">Case study</v-chip>
              <v-btn
                icon="mdi-pencil-outline"
                size="x-small"
                variant="text"
                :title="`Edit ${d.name}`"
                @click="openDeptEdit(d)"
              />
              <v-switch
                :model-value="d.is_active"
                color="primary"
                density="compact"
                hide-details
                @update:model-value="toggleDepartmentActive(d, $event)"
              />
            </div>
            <v-btn size="small" variant="text" color="primary" prepend-icon="mdi-plus" @click="openDeptCreate">Add department</v-btn>
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
          <p class="text-caption text-medium-emphasis mb-2">
            Tick the teams taking part. Untick "open" to keep a team in the cohort but paused.
            Set a close date to stop one team taking applications early while the rest keep recruiting.
          </p>
          <v-card variant="outlined">
            <template v-for="(d, i) in departments" :key="d.id">
              <v-divider v-if="i" />
              <div class="dept-row">
                <div class="d-flex align-center ga-2">
                  <v-checkbox-btn
                    :model-value="isSelected(d.id)"
                    color="primary"
                    class="flex-grow-0"
                    @update:model-value="toggleSelected(d.id, $event)"
                  />
                  <span class="text-body-2 flex-grow-1">{{ d.name }}</span>
                  <v-switch
                    v-if="isSelected(d.id)"
                    :model-value="isOpen(d.id)"
                    color="primary"
                    density="compact"
                    hide-details
                    class="flex-grow-0"
                    :label="isOpen(d.id) ? 'Open' : 'Paused'"
                    @update:model-value="setOpen(d.id, $event)"
                  />
                </div>
                <!-- Indented under the name so it reads as this team's setting. -->
                <DateTimeField
                  v-if="isSelected(d.id) && isOpen(d.id)"
                  :model-value="draft.closes[d.id] || null"
                  label="Closes early (optional)"
                  density="compact"
                  hide-details
                  class="dept-row__close"
                  prepend-inner-icon="mdi-calendar-end"
                  :min-date="draft.opens_at || null"
                  :max-date="draft.closes_at || null"
                  :start-date="draft.opens_at || null"
                  :default-time="{ hours: 23, minutes: 59 }"
                  @update:model-value="setCloses(d.id, $event)"
                />
              </div>
            </template>
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

    <!-- Create / edit department dialog -->
    <v-dialog v-model="deptDialog" :max-width="$vuetify.display.mobile ? '92vw' : '480px'">
      <v-card>
        <v-card-title class="text-h6 pt-4">{{ editingDept ? 'Edit department' : 'New department' }}</v-card-title>
        <v-card-text>
          <v-text-field v-model="deptDraft.name" label="Name *" variant="outlined" density="comfortable" class="mb-3" />
          <v-textarea v-model="deptDraft.description" label="Description" variant="outlined" density="comfortable" rows="2" class="mb-2" hint="Used as context for AI matching" persistent-hint />
          <v-switch v-model="deptDraft.has_case_stage" color="deep-purple" density="compact" hide-details label="Runs a case study before interview (like Marketing)" />
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="deptDialog = false">Cancel</v-btn>
          <v-btn color="primary" variant="flat" :disabled="!deptDraft.name.trim()" :loading="savingDept" @click="saveDepartment">
            {{ editingDept ? 'Save' : 'Add' }}
          </v-btn>
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
const editingDept = ref(null);
const deleteDialog = ref(false);
const toDelete = ref(null);

const toast = reactive({ show: false, text: '', color: 'success' });
// draft.selection: { [department_id]: is_open }
// draft.closes:    { [department_id]: local datetime string } - early close, optional
const draft = reactive({ name: '', opens_at: '', closes_at: '', selection: {}, closes: {} });
const deptDraft = reactive({ name: '', description: '', has_case_stage: false });

function notify(text, color = 'success') { toast.text = text; toast.color = color; toast.show = true; }

// A cohort department's state for its chip: paused, closed early, or closing early.
function departmentState(cd) {
  if (!cd.is_open) return { accepting: false, note: 'paused' };
  if (!cd.closes_at) return { accepting: true, note: null };
  const past = new Date(cd.closes_at).getTime() <= Date.now();
  return past
    ? { accepting: false, note: `closed ${formatDate(cd.closes_at)}` }
    : { accepting: true, note: `closes ${formatDate(cd.closes_at)}` };
}

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
  else {
    delete draft.selection[id];
    delete draft.closes[id];
  }
}
function setOpen(id, on) { draft.selection[id] = on; }
function setCloses(id, local) {
  if (local) draft.closes[id] = local;
  else delete draft.closes[id];
}

function resetDraft() {
  draft.name = '';
  draft.opens_at = '';
  draft.closes_at = '';
  draft.selection = {};
  draft.closes = {};
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
  draft.closes = {};
  (cycle.cycle_departments || []).forEach((cd) => {
    draft.selection[cd.department_id] = cd.is_open;
    if (cd.closes_at) draft.closes[cd.department_id] = toLocalInput(cd.closes_at);
  });
  dialog.value = true;
}

function buildPayload() {
  return {
    name: draft.name.trim(),
    opens_at: toIso(draft.opens_at),
    closes_at: toIso(draft.closes_at),
    departments: Object.entries(draft.selection).map(([id, open]) => ({
      department_id: Number(id),
      is_open: open,
      closes_at: toIso(draft.closes[id]),
    })),
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
  } catch (err) {
    console.error('Failed to save cohort:', err);
    // Dialog stays open so the edits aren't lost; the server names the
    // offending department when a close date falls outside the cohort.
    const detail = err.response?.data?.detail;
    notify(typeof detail === 'string' ? detail : 'Could not save the cohort', 'error');
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

function openDeptCreate() {
  editingDept.value = null;
  Object.assign(deptDraft, { name: '', description: '', has_case_stage: false });
  deptDialog.value = true;
}

function openDeptEdit(dep) {
  editingDept.value = dep;
  Object.assign(deptDraft, {
    name: dep.name || '',
    description: dep.description || '',
    has_case_stage: !!dep.has_case_stage,
  });
  deptDialog.value = true;
}

async function saveDepartment() {
  savingDept.value = true;
  try {
    const payload = {
      name: deptDraft.name.trim(),
      description: deptDraft.description?.trim() || '',
      has_case_stage: deptDraft.has_case_stage,
    };
    if (editingDept.value) {
      const updated = await RecruitmentService.updateDepartment(editingDept.value.id, payload);
      const i = departments.value.findIndex((d) => d.id === editingDept.value.id);
      if (i >= 0) departments.value[i] = updated ?? { ...departments.value[i], ...payload };
      notify('Department updated');
    } else {
      const dep = await RecruitmentService.createDepartment(payload);
      departments.value.push(dep);
      notify('Department added');
    }
    deptDialog.value = false;
  } catch (err) {
    console.error('Failed to save department:', err);
    // Dialog stays open so the entered values aren't lost.
    notify(err.response?.data?.detail || 'Could not save the department', 'error');
  } finally {
    savingDept.value = false;
  }
}

async function toggleDepartmentActive(dep, active) {
  const previous = dep.is_active;
  dep.is_active = active;   // optimistic, reverted below if the save fails
  try {
    await RecruitmentService.updateDepartment(dep.id, { is_active: active });
    notify(`${dep.name} ${active ? 'activated' : 'deactivated'}`);
  } catch (err) {
    console.error('Failed to update department:', err);
    dep.is_active = previous;
    notify(err.response?.data?.detail || `Could not update ${dep.name}`, 'error');
  }
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

<style scoped>
.dept-row {
  padding: 8px 12px;
}
.dept-row__close {
  /* Line up with the department name, past the checkbox. */
  margin: 4px 0 8px 48px;
}
</style>
