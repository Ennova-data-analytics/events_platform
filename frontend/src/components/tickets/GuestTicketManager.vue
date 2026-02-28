<template>
  <div>
    <div class="d-flex align-center mb-4 pa-4">
      <div>
        <h3 class="text-subtitle-1 font-weight-bold">Guest Tickets</h3>
        <p class="text-caption text-grey">Generate tickets for speakers, invitees, and other guests.</p>
      </div>
      <v-spacer />
      <v-btn color="primary" prepend-icon="mdi-plus" @click="openAddDialog">
        Add Guest
      </v-btn>
    </div>

    <v-data-table
      :headers="headers"
      :items="guests"
      :loading="loading"
      item-value="id"
      no-data-text="No guest tickets yet"
    >
      <template #item.checked_in="{ item }">
        <v-chip :color="item.checked_in ? 'success' : 'default'" size="small" variant="tonal">
          <v-icon start size="14">{{ item.checked_in ? 'mdi-check-circle' : 'mdi-clock-outline' }}</v-icon>
          {{ item.checked_in ? 'Checked in' : 'Not yet' }}
        </v-chip>
      </template>

      <template #item.ticket_token="{ item }">
        <v-btn
          icon
          size="x-small"
          variant="text"
          :href="`/ticket/${item.ticket_token}`"
          target="_blank"
        >
          <v-icon size="18">mdi-open-in-new</v-icon>
        </v-btn>
      </template>

      <template #item.actions="{ item }">
        <v-btn
          icon
          size="x-small"
          variant="text"
          color="primary"
          @click="resend(item)"
          :loading="resendingId === item.id"
        >
          <v-icon size="18">mdi-email-fast</v-icon>
          <v-tooltip activator="parent" location="top">Resend email</v-tooltip>
        </v-btn>
        <v-btn
          icon
          size="x-small"
          variant="text"
          color="error"
          class="ml-1"
          @click="confirmDelete(item)"
        >
          <v-icon size="18">mdi-delete</v-icon>
          <v-tooltip activator="parent" location="top">Delete</v-tooltip>
        </v-btn>
      </template>
    </v-data-table>

    <!-- Add Guest Dialog -->
    <v-dialog v-model="addDialog" max-width="420" persistent>
      <v-card rounded="xl">
        <v-card-title class="pa-6 pb-2 font-weight-bold">Add Guest Ticket</v-card-title>
        <v-card-text class="pa-6 pt-2">
          <v-text-field
            v-model="form.guest_name"
            label="Full name"
            variant="outlined"
            density="compact"
            class="mb-3"
            :error-messages="formErrors.guest_name"
          />
          <v-text-field
            v-model="form.guest_email"
            label="Email address"
            variant="outlined"
            density="compact"
            type="email"
            :error-messages="formErrors.guest_email"
          />
          <v-alert v-if="addError" type="error" variant="tonal" class="mt-3" density="compact">
            {{ addError }}
          </v-alert>
        </v-card-text>
        <v-card-actions class="pa-6 pt-0">
          <v-spacer />
          <v-btn variant="text" @click="closeAddDialog">Cancel</v-btn>
          <v-btn color="primary" :loading="saving" @click="save">
            Create & Send Email
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Confirm Dialog -->
    <v-dialog v-model="deleteDialog" max-width="360">
      <v-card rounded="xl">
        <v-card-title class="pa-6 pb-2">Delete Guest Ticket?</v-card-title>
        <v-card-text class="pa-6 pt-0">
          This will remove the ticket for <strong>{{ deletingGuest?.guest_name }}</strong>. Their QR code will no longer be valid.
        </v-card-text>
        <v-card-actions class="pa-6 pt-0">
          <v-spacer />
          <v-btn variant="text" @click="deleteDialog = false">Cancel</v-btn>
          <v-btn color="error" :loading="deleting" @click="doDelete">Delete</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-snackbar v-model="snackbar.show" :color="snackbar.color" timeout="3000" location="top">
      {{ snackbar.message }}
    </v-snackbar>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { TicketService } from '@/services/TicketService';

const props = defineProps({
  eventId: { type: Number, required: true },
});

const headers = [
  { title: 'Name', key: 'guest_name' },
  { title: 'Email', key: 'guest_email' },
  { title: 'Status', key: 'checked_in', sortable: false },
  { title: 'Ticket', key: 'ticket_token', sortable: false },
  { title: 'Actions', key: 'actions', sortable: false, align: 'end' },
];

const guests = ref([]);
const loading = ref(false);

const addDialog = ref(false);
const saving = ref(false);
const addError = ref(null);
const form = ref({ guest_name: '', guest_email: '' });
const formErrors = ref({});

const deleteDialog = ref(false);
const deletingGuest = ref(null);
const deleting = ref(false);

const resendingId = ref(null);

const snackbar = ref({ show: false, message: '', color: 'success' });

function showSnack(message, color = 'success') {
  snackbar.value = { show: true, message, color };
}

async function fetchGuests() {
  loading.value = true;
  try {
    const res = await TicketService.listGuestTickets(props.eventId);
    guests.value = res.data;
  } catch {
    showSnack('Failed to load guest tickets', 'error');
  } finally {
    loading.value = false;
  }
}

function openAddDialog() {
  form.value = { guest_name: '', guest_email: '' };
  formErrors.value = {};
  addError.value = null;
  addDialog.value = true;
}

function closeAddDialog() {
  addDialog.value = false;
}

async function save() {
  formErrors.value = {};
  if (!form.value.guest_name) formErrors.value.guest_name = ['Required'];
  if (!form.value.guest_email) formErrors.value.guest_email = ['Required'];
  if (Object.keys(formErrors.value).length) return;

  saving.value = true;
  addError.value = null;
  try {
    await TicketService.createGuestTicket(props.eventId, form.value);
    await fetchGuests();
    closeAddDialog();
    showSnack('Guest ticket created and email sent');
  } catch (e) {
    addError.value = e.response?.data?.detail || 'Failed to create guest ticket';
  } finally {
    saving.value = false;
  }
}

function confirmDelete(guest) {
  deletingGuest.value = guest;
  deleteDialog.value = true;
}

async function doDelete() {
  deleting.value = true;
  try {
    await TicketService.deleteGuestTicket(deletingGuest.value.id);
    await fetchGuests();
    deleteDialog.value = false;
    showSnack('Guest ticket deleted');
  } catch {
    showSnack('Failed to delete ticket', 'error');
  } finally {
    deleting.value = false;
  }
}

async function resend(guest) {
  resendingId.value = guest.id;
  try {
    await TicketService.resendGuestTicketEmail(guest.id);
    showSnack(`Ticket email resent to ${guest.guest_email}`);
  } catch {
    showSnack('Failed to resend email', 'error');
  } finally {
    resendingId.value = null;
  }
}

onMounted(fetchGuests);
</script>