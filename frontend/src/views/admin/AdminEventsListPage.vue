<template>
  <div>
    <div class="d-flex justify-space-between align-center mb-4">
      <h1 class="text-h5">Manage Events</h1>
      <v-btn to="/admin/events/create" color="primary" prepend-icon="mdi-plus">
        Create Event
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
          <template v-slot:item.actions="{ item }">
            <v-btn
              icon="mdi-pencil"
              variant="text"
              size="small"
              :to="{ name: 'admin-edit-event', params: { id: item.event_id } }"
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
    <v-dialog v-model="deleteDialog" max-width="500px">
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
import { ref, onMounted } from 'vue';
import { useEventStore } from '@/stores/events.store.js';

const eventStore = useEventStore();

const headers = ref([
  { title: 'Event Name', key: 'event_name', sortable: true },
  { title: 'Date', key: 'event_date_start', sortable: true },
  { title: 'Location', key: 'location', sortable: false },
  { title: 'Price (€)', key: 'price_euros', sortable: true },
  { title: 'Capacity', key: 'capacity', sortable: true },
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
  if (eventToDelete.value) {
    await eventStore.deleteEvent(eventToDelete.value.event_id);
    closeDeleteDialog();
  }
}

onMounted(() => {
  eventStore.fetchAllEvents();
});
</script>