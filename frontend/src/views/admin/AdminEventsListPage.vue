<template>
  <div>
    <div class="d-flex justify-space-between align-center mb-4">
      <h1 :class="$vuetify.display.mobile ? 'text-h6' : 'text-h5'">Manage Events</h1>
      <v-btn to="/admin/events/create" color="primary" prepend-icon="mdi-plus" :size="$vuetify.display.mobile ? 'small' : 'default'">
        <span class="d-none d-sm-inline">Create Event</span>
        <span class="d-sm-none">Create</span>
      </v-btn>
    </div>
    
    <v-card>
      <v-card-text>
        <v-data-table
          :headers="headers"
          :items="eventStore.events"
          :loading="eventStore.isLoading"
          item-key="event_id"
          class="elevation-1"
        >
          <template v-slot:item.requires_approval="{ item }">
            <v-chip
              :color="item.requires_approval ? 'warning' : 'success'"
              variant="tonal"
              size="small"
            >
              <v-icon start :icon="item.requires_approval ? 'mdi-account-check' : 'mdi-check-circle'"></v-icon>
              {{ item.requires_approval ? 'Manual' : 'Auto' }}
            </v-chip>
          </template>

          <template v-slot:item.status="{ item }">
            <v-chip :color="statusColor(item.status)" variant="tonal" size="small" label>
              {{ item.status }}
            </v-chip>
          </template>

          <template v-slot:item.actions="{ item }">
            <v-btn
              icon="mdi-pencil"
              variant="text"
              size="small"
              :to="{ name: 'admin-edit-event', params: { id: item.event_id } }"
            ></v-btn>
            <v-btn
              icon="mdi-content-copy"
              variant="text"
              size="small"
              title="Duplicate for a re-run"
              @click="openDuplicateDialog(item)"
            ></v-btn>
            <v-btn
              icon="mdi-account-group"
              variant="text"
              size="small"
              :to="{ name: 'admin-view-event', params: { id: item.event_id } }"
            ></v-btn>
            <v-btn
              icon="mdi-delete-outline"
              variant="text"
              color="error"
              size="small"
              @click="openDeleteDialog(item)"
            ></v-btn>
          </template>

          <template v-slot:item.event_date_start="{ item }">
            {{ new Date(item.event_date_start).toLocaleString('en-GB') }}
          </template>

        </v-data-table>
      </v-card-text>
    </v-card>
    <v-dialog v-model="duplicateDialog" :max-width="$vuetify.display.mobile ? '92vw' : '520px'" persistent>
      <v-card>
        <v-card-title class="text-h6 pt-4">Duplicate event</v-card-title>
        <v-card-text>
          <p class="text-body-2 text-medium-emphasis mb-4">
            Creates an unpublished copy of "{{ eventToDuplicate?.event_name }}" with its details,
            media and ticket types. Registrations, feedback and attendance are not carried over.
          </p>
          <v-text-field
            v-model="duplicateDraft.event_name"
            label="Name *"
            variant="outlined"
            density="comfortable"
            class="mb-2"
          />
          <DateTimeField
            v-model="duplicateDraft.event_date_start"
            label="Starts"
            density="comfortable"
            prepend-inner-icon="mdi-calendar-start"
          />
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="text" :disabled="duplicating" @click="closeDuplicateDialog">Cancel</v-btn>
          <v-btn
            color="primary"
            variant="flat"
            :disabled="!duplicateDraft.event_name.trim()"
            :loading="duplicating"
            @click="confirmDuplicate"
          >
            Duplicate
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-snackbar v-model="snackbar.show" :color="snackbar.color" :timeout="3000" location="top">
      {{ snackbar.text }}
    </v-snackbar>

    <v-dialog v-model="deleteDialog" :max-width="$vuetify.display.mobile ? '90vw' : '500px'">
      <v-card>
        <v-card-title class="text-h5">Are you sure?</v-card-title>
        <v-card-text>
          Do you really want to delete the event "{{ eventToDelete?.event_name }}"? This action cannot be undone.
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn variant="text" @click="closeDeleteDialog">Cancel</v-btn>
          <v-btn color="error" variant="flat" @click="confirmDelete">Delete</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { useDisplay } from 'vuetify';
import { useRouter } from 'vue-router';
import { useEventStore } from '@/stores/events.store.js';
import { statusColor } from '@/utils/eventStatus.js';
import DateTimeField from '@/components/common/DateTimeField.vue';

const eventStore = useEventStore();
const router = useRouter();

const { mobile } = useDisplay();
const headers = computed(() => mobile.value ? [
  { title: 'Event Name', key: 'event_name', sortable: true },
  { title: 'Date', key: 'event_date_start', sortable: true },
  { title: 'Status', key: 'status', sortable: true },
  { title: 'Actions', key: 'actions', sortable: false, align: 'end' },
] : [
  { title: 'Event Name', key: 'event_name', sortable: true },
  { title: 'Date', key: 'event_date_start', sortable: true },
  { title: 'Status', key: 'status', sortable: true },
  { title: 'Location', key: 'location', sortable: false },
  { title: 'Price (€)', key: 'price_euros', sortable: true },
  { title: 'Capacity', key: 'capacity', sortable: true },
  { title: 'Approval', key: 'requires_approval', sortable: true },
  { title: 'Actions', key: 'actions', sortable: false, align: 'end' },
]);
const deleteDialog = ref(false);
const eventToDelete = ref(null);

function openDeleteDialog(event) {
  eventToDelete.value = event;
  deleteDialog.value = true;
}

function closeDeleteDialog() {
  eventToDelete.value = null;
  deleteDialog.value = false;
}

async function confirmDelete() {
  if (!eventToDelete.value) return;
  try {
    await eventStore.deleteEvent(eventToDelete.value.event_id);
    closeDeleteDialog();
  } catch (err) {
    console.error('Failed to delete event:', err);
    // The store re-throws; without this the dialog just sat there on failure.
    snackbar.text = err.response?.data?.detail || 'Could not delete the event';
    snackbar.color = 'error';
    snackbar.show = true;
  }
}

// ── Duplicate ─────────────────────────────────────────────────────────────
const duplicateDialog = ref(false);
const duplicating = ref(false);
const eventToDuplicate = ref(null);
const duplicateDraft = reactive({ event_name: '', event_date_start: '' });
const snackbar = reactive({ show: false, text: '', color: 'success' });

// "Summer Gala 2026" → "Summer Gala 2027". Falls back to a "(Copy)" suffix when
// the name carries no year to bump.
function nextYearName(name) {
  const match = name?.match(/(.*)(\b(?:19|20)\d{2}\b)(.*)/);
  if (!match) return `${name} (Copy)`;
  return `${match[1]}${Number(match[2]) + 1}${match[3]}`;
}

// DateTimeField expects a "YYYY-MM-DDTHH:mm" local string.
function toLocalInput(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  const pad = n => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function nextYearDate(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  d.setFullYear(d.getFullYear() + 1);
  return toLocalInput(d.toISOString());
}

function openDuplicateDialog(event) {
  eventToDuplicate.value = event;
  duplicateDraft.event_name = nextYearName(event.event_name);
  duplicateDraft.event_date_start = nextYearDate(event.event_date_start);
  duplicateDialog.value = true;
}

function closeDuplicateDialog() {
  eventToDuplicate.value = null;
  duplicateDialog.value = false;
}

async function confirmDuplicate() {
  duplicating.value = true;
  try {
    const created = await eventStore.duplicateEvent(eventToDuplicate.value.event_id, {
      event_name: duplicateDraft.event_name.trim(),
      event_date_start: duplicateDraft.event_date_start
        ? new Date(duplicateDraft.event_date_start).toISOString()
        : null,
    });
    duplicateDialog.value = false;
    router.push({ name: 'admin-edit-event', params: { id: created.event_id } });
  } catch {
    snackbar.text = eventStore.error || 'Could not duplicate the event';
    snackbar.color = 'error';
    snackbar.show = true;
  } finally {
    duplicating.value = false;
  }
}

onMounted(() => {
  // Admins see drafts too, which the public event list never returns.
  eventStore.fetchAllEvents({ includeUnpublished: true });
});
</script>