<template>
  <v-card>
    <v-card-title class="d-flex justify-space-between align-center">
      <div>
        <v-icon left>mdi-ticket-confirmation</v-icon>
        Ticket Types
      </div>
      <v-btn
        color="primary"
        prepend-icon="mdi-plus"
        @click="openCreateDialog"
        size="small"
      >
        Add Ticket Type
      </v-btn>
    </v-card-title>

    <v-card-text>
      <v-alert
        v-if="ticketTypes.length === 0"
        type="info"
        variant="tonal"
        class="mb-4"
      >
        <v-icon left>mdi-information</v-icon>
        No ticket types configured. This event will use single-tier pricing.
      </v-alert>

      <v-list v-else lines="three">
        <v-list-item v-for="ticketType in ticketTypes" :key="ticketType.ticket_type_id" class="ticket-type-item">
          <template v-slot:prepend>
            <v-avatar
                  :color="ticketType.is_active ? 'primary' : 'grey'"
                  variant="tonal"
                >
                  <v-icon>mdi-ticket</v-icon>
                </v-avatar>
              </template>

              <v-list-item-title class="font-weight-medium">
                {{ ticketType.name }}
                <v-chip
                  v-if="!ticketType.is_active"
                  size="small"
                  color="grey"
                  class="ml-2"
                >
                  Inactive
                </v-chip>
              </v-list-item-title>

              <v-list-item-subtitle>
                {{ ticketType.description }}
              </v-list-item-subtitle>

              <v-list-item-subtitle class="mt-1">
                <v-chip size="small" variant="flat" color="success" class="mr-2">
                  €{{ ticketType.price_euros }}
                </v-chip>
                <v-chip v-if="ticketType.capacity" size="small" variant="flat">
                  {{ ticketType.tickets_sold }}/{{ ticketType.capacity }} sold
                </v-chip>
                <v-chip v-else size="small" variant="flat">
                  Unlimited capacity
                </v-chip>
                <v-chip
                  v-if="ticketType.is_free_for_members"
                  size="small"
                  color="info"
                  class="ml-2"
                >
                  <v-icon start size="x-small">mdi-star</v-icon>
                  Free for members
                </v-chip>
                <v-chip
                  v-if="ticketType.requires_team"
                  size="small"
                  color="purple"
                  class="ml-2"
                >
                  <v-icon start size="x-small">mdi-account-group</v-icon>
                  Team Required
                </v-chip>
              </v-list-item-subtitle>

              <template v-slot:append>
                <v-btn
                  :color="ticketType.is_active ? 'success' : 'grey'"
                  variant="text"
                  @click="toggleActive(ticketType)"
                  size="small"
                  icon
                >
                  <v-icon>{{ ticketType.is_active ? 'mdi-check-circle' : 'mdi-close-circle' }}</v-icon>
                  <v-tooltip activator="parent">
                    {{ ticketType.is_active ? 'Deactivate' : 'Activate' }}
                  </v-tooltip>
                </v-btn>

                <v-btn
                  color="primary"
                  variant="text"
                  @click="openEditDialog(ticketType)"
                  size="small"
                  icon
                >
                  <v-icon>mdi-pencil</v-icon>
                  <v-tooltip activator="parent">Edit</v-tooltip>
                </v-btn>

                <v-btn
                  color="error"
                  variant="text"
                  @click="confirmDelete(ticketType)"
                  size="small"
                  :disabled="ticketType.tickets_sold > 0"
                  icon
                >
                  <v-icon>mdi-delete</v-icon>
                  <v-tooltip activator="parent">
                    {{ ticketType.tickets_sold > 0 ? 'Cannot delete (tickets sold)' : 'Delete' }}
                  </v-tooltip>
                </v-btn>
          </template>
          <v-divider></v-divider>
        </v-list-item>
      </v-list>
    </v-card-text>

    <!-- Create/Edit Dialog -->
    <v-dialog v-model="dialog" max-width="600px" persistent>
      <v-card>
        <v-card-title>
          <span class="text-h5">{{ isEditing ? 'Edit' : 'Create' }} Ticket Type</span>
        </v-card-title>

        <v-card-text>
          <v-form ref="form">
            <v-text-field
              v-model="editedTicketType.name"
              label="Ticket Name *"
              placeholder="e.g., Participant, Spectator"
              variant="outlined"
              :rules="[v => !!v || 'Name is required']"
              class="mb-2"
            ></v-text-field>

            <v-textarea
              v-model="editedTicketType.description"
              label="Description"
              placeholder="Describe what this ticket includes"
              variant="outlined"
              rows="3"
              class="mb-2"
            ></v-textarea>

            <v-text-field
              v-model.number="editedTicketType.price_euros"
              label="Price (€) *"
              type="number"
              min="0"
              step="0.01"
              variant="outlined"
              :rules="[v => (v !== null && v !== undefined && v >= 0) || 'Price must be 0 or greater']"
              class="mb-2"
            ></v-text-field>

            <v-text-field
              v-model.number="editedTicketType.capacity"
              label="Capacity"
              type="number"
              min="1"
              variant="outlined"
              hint="Leave empty for unlimited"
              persistent-hint
              class="mb-2"
            ></v-text-field>

            <v-select
              v-model="editedTicketType.form_template_id"
              :items="formTemplates"
              item-title="template_name"
              item-value="template_id"
              label="Registration Form Template"
              variant="outlined"
              clearable
              hint="Optional: Use a specific form for this ticket type"
              persistent-hint
              class="mb-2"
            ></v-select>

            <v-checkbox
              v-model="editedTicketType.is_free_for_members"
              label="Free for Ennova Members"
              hint="Ennova members can register for free with this ticket type"
              persistent-hint
              color="primary"
            ></v-checkbox>

            <v-divider class="my-4"></v-divider>

            <h3 class="text-subtitle-1 font-weight-bold mb-3">
              <v-icon left color="purple">mdi-account-group</v-icon>
              Team Settings
            </h3>

            <v-checkbox
              v-model="editedTicketType.requires_team"
              label="Require Team Registration"
              hint="Users must join or create a team to register with this ticket type"
              persistent-hint
              color="purple"
              class="mb-2"
            ></v-checkbox>

            <v-text-field
              v-if="editedTicketType.requires_team"
              v-model.number="editedTicketType.team_max_members"
              label="Default Max Team Size"
              type="number"
              min="1"
              variant="outlined"
              hint="Leave empty for unlimited team size"
              persistent-hint
              class="mb-2"
            ></v-text-field>

            <v-divider class="my-4"></v-divider>

            <v-checkbox
              v-model="editedTicketType.is_active"
              label="Active"
              hint="Only active ticket types are available for registration"
              persistent-hint
              color="primary"
            ></v-checkbox>
          </v-form>
        </v-card-text>

        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn text @click="closeDialog">Cancel</v-btn>
          <v-btn
            color="primary"
            @click="saveTicketType"
            :loading="saving"
          >
            {{ isEditing ? 'Update' : 'Create' }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete Confirmation Dialog -->
    <v-dialog v-model="deleteDialog" max-width="400px">
      <v-card>
        <v-card-title>Confirm Deletion</v-card-title>
        <v-card-text>
          Are you sure you want to delete the ticket type "{{ ticketTypeToDelete?.name }}"?
          This action cannot be undone.
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn text @click="deleteDialog = false">Cancel</v-btn>
          <v-btn color="error" @click="deleteTicketType" :loading="deleting">
            Delete
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Snackbar for notifications -->
    <v-snackbar v-model="snackbar" :color="snackbarColor" timeout="3000">
      {{ snackbarText }}
    </v-snackbar>
  </v-card>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import TicketTypeService from '@/services/TicketTypeService.js';
import { FormTemplateService } from '@/services/FormTemplateService.js';

const props = defineProps({
  eventId: {
    type: Number,
    required: true
  }
});

const emit = defineEmits(['ticket-types-updated']);

const ticketTypes = ref([]);
const formTemplates = ref([]);
const dialog = ref(false);
const deleteDialog = ref(false);
const isEditing = ref(false);
const saving = ref(false);
const deleting = ref(false);
const snackbar = ref(false);
const snackbarText = ref('');
const snackbarColor = ref('success');

const defaultTicketType = {
  name: '',
  description: '',
  price_euros: 0,
  capacity: null,
  form_template_id: null,
  is_active: true,
  is_free_for_members: false,
  requires_team: false,
  team_max_members: null,
  display_order: 0
};

const editedTicketType = ref({ ...defaultTicketType });
const ticketTypeToDelete = ref(null);
const form = ref(null);

onMounted(async () => {
  await loadTicketTypes();
  await loadFormTemplates();
});

async function loadTicketTypes() {
  try {
    console.log('Loading ticket types for event:', props.eventId);
    const response = await TicketTypeService.getTicketTypes(props.eventId);
    console.log('Ticket types response:', response);
    ticketTypes.value = response.ticket_types || [];
    console.log('Loaded ticket types:', ticketTypes.value);
  } catch (error) {
    console.error('Failed to load ticket types:', error);
    showSnackbar('Failed to load ticket types', 'error');
  }
}

async function loadFormTemplates() {
  try {
    const response = await FormTemplateService.getAllTemplates();
    formTemplates.value = response.data || [];
  } catch (error) {
    console.error('Failed to load form templates:', error);
  }
}

function openCreateDialog() {
  isEditing.value = false;
  editedTicketType.value = {
    ...defaultTicketType,
    display_order: ticketTypes.value.length
  };
  dialog.value = true;
}

function openEditDialog(ticketType) {
  isEditing.value = true;
  editedTicketType.value = { ...ticketType };
  dialog.value = true;
}

function closeDialog() {
  dialog.value = false;
  editedTicketType.value = { ...defaultTicketType };
}

async function saveTicketType() {
  console.log('Saving ticket type, form ref:', form.value);
  console.log('Current editedTicketType:', editedTicketType.value);

  // Validate form
  const { valid } = await form.value.validate();
  console.log('Form validation result:', valid);
  if (!valid) {
    console.log('Form validation failed');
    return;
  }

  saving.value = true;

  try {
    if (isEditing.value) {
      console.log('Updating ticket type:', editedTicketType.value.ticket_type_id);
      await TicketTypeService.updateTicketType(
        props.eventId,
        editedTicketType.value.ticket_type_id,
        editedTicketType.value
      );
      showSnackbar('Ticket type updated successfully', 'success');
    } else {
      console.log('Creating new ticket type');
      const result = await TicketTypeService.createTicketType(props.eventId, editedTicketType.value);
      console.log('Create result:', result);
      showSnackbar('Ticket type created successfully', 'success');
    }

    await loadTicketTypes();
    emit('ticket-types-updated');
    closeDialog();
  } catch (error) {
    console.error('Failed to save ticket type:', error);
    console.error('Error details:', error.response);
    showSnackbar(error.response?.data?.detail || 'Failed to save ticket type', 'error');
  } finally {
    saving.value = false;
  }
}

async function toggleActive(ticketType) {
  try {
    await TicketTypeService.toggleActive(props.eventId, ticketType.ticket_type_id);
    await loadTicketTypes();
    emit('ticket-types-updated');
    showSnackbar(
      `Ticket type ${ticketType.is_active ? 'deactivated' : 'activated'}`,
      'success'
    );
  } catch (error) {
    console.error('Failed to toggle ticket type:', error);
    showSnackbar('Failed to update ticket type status', 'error');
  }
}

function confirmDelete(ticketType) {
  ticketTypeToDelete.value = ticketType;
  deleteDialog.value = true;
}

async function deleteTicketType() {
  deleting.value = true;

  try {
    await TicketTypeService.deleteTicketType(
      props.eventId,
      ticketTypeToDelete.value.ticket_type_id
    );
    await loadTicketTypes();
    emit('ticket-types-updated');
    showSnackbar('Ticket type deleted successfully', 'success');
    deleteDialog.value = false;
  } catch (error) {
    console.error('Failed to delete ticket type:', error);
    showSnackbar(error.response?.data?.detail || 'Failed to delete ticket type', 'error');
  } finally {
    deleting.value = false;
  }
}

async function handleReorder() {
  try {
    const ticketTypeIds = ticketTypes.value.map(tt => tt.ticket_type_id);
    await TicketTypeService.reorderTicketTypes(props.eventId, ticketTypeIds);
    emit('ticket-types-updated');
    showSnackbar('Ticket types reordered', 'success');
  } catch (error) {
    console.error('Failed to reorder ticket types:', error);
    showSnackbar('Failed to reorder ticket types', 'error');
    await loadTicketTypes(); // Reload to reset order
  }
}

function showSnackbar(text, color = 'success') {
  snackbarText.value = text;
  snackbarColor.value = color;
  snackbar.value = true;
}
</script>

<style scoped>
.ticket-type-item {
  border-left: 4px solid transparent;
  transition: all 0.2s ease;
}

.ticket-type-item:hover {
  border-left-color: #1976d2;
  background-color: rgba(25, 118, 210, 0.04);
}

.drag-handle {
  cursor: move;
  opacity: 0.5;
  transition: opacity 0.2s;
}

.drag-handle:hover {
  opacity: 1;
}
</style>
