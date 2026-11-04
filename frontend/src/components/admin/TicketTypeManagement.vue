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
                  v-if="ticketType.bring_a_friend"
                  size="small"
                  color="pink"
                  class="ml-2"
                  data-test="bring-a-friend-chip"
                >
                  <v-icon start size="x-small">mdi-account-heart</v-icon>
                  Bring a friend: {{ dealLabel(ticketType) }}
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
                <v-chip
                  v-if="ticketType.group_payment_mode === 'leader' && ticketType.group_size"
                  size="small"
                  color="deep-orange"
                  class="ml-2"
                >
                  <v-icon start size="x-small">mdi-account-cash</v-icon>
                  €{{ ticketType.group_price_euros }} for {{ ticketType.group_size }} (lead pays)
                </v-chip>
                <v-chip
                  v-else-if="ticketType.group_payment_mode === 'individual' && ticketType.group_size"
                  size="small"
                  color="teal"
                  class="ml-2"
                >
                  <v-icon start size="x-small">mdi-account-group</v-icon>
                  Group of {{ ticketType.group_size }}, each pays €{{ ticketType.price_euros }}
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
                  data-test="edit-ticket-type"
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
                  icon
                  data-test="delete-ticket-type"
                >
                  <v-icon>mdi-delete</v-icon>
                  <v-tooltip activator="parent">Delete</v-tooltip>
                </v-btn>
          </template>
          <v-divider></v-divider>
        </v-list-item>
      </v-list>

      <v-expansion-panels v-if="deletedTicketTypes.length" variant="accordion" class="mt-4" data-test="deleted-ticket-types">
        <v-expansion-panel>
          <v-expansion-panel-title>
            <v-icon start size="small">mdi-delete-clock</v-icon>
            Deleted ({{ deletedTicketTypes.length }})
          </v-expansion-panel-title>
          <v-expansion-panel-text>
            <p class="text-caption text-medium-emphasis mb-2">
              Off sale and hidden from the event page. Everyone who registered with these keeps their ticket.
            </p>
            <v-list density="compact">
              <v-list-item v-for="ticketType in deletedTicketTypes" :key="ticketType.ticket_type_id">
                <v-list-item-title>{{ ticketType.name }}</v-list-item-title>
                <v-list-item-subtitle>
                  €{{ ticketType.price_euros }} · {{ ticketType.tickets_sold }} sold ·
                  deleted {{ new Date(ticketType.deleted_at).toLocaleDateString('en-GB') }}
                </v-list-item-subtitle>
              </v-list-item>
            </v-list>
          </v-expansion-panel-text>
        </v-expansion-panel>
      </v-expansion-panels>
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

            <v-checkbox
              v-model="editedTicketType.bring_a_friend"
              label="Bring a friend: this price buys 2 tickets"
              :hint="bringAFriendHint"
              persistent-hint
              color="pink"
              :disabled="bringAFriendLocked"
              data-test="bring-a-friend-toggle"
              class="mb-2"
              @update:model-value="onBringAFriendChange"
            ></v-checkbox>

            <v-text-field
              v-model.number="editedTicketType.price_euros"
              :label="editedTicketType.bring_a_friend ? 'Price for both tickets (€) *' : 'Price (€) *'"
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
              v-if="!editedTicketType.bring_a_friend"
              v-model="editedTicketType.is_free_for_members"
              label="Free for Ennova Members"
              hint="Ennova members can register for free with this ticket type"
              persistent-hint
              color="primary"
            ></v-checkbox>

            <v-checkbox
              v-model="editedTicketType.show_availability"
              label="Show Ticket Availability"
              hint="Display remaining ticket count to users (e.g., '48/50 available')"
              persistent-hint
              color="primary"
            ></v-checkbox>

            <v-divider class="my-4"></v-divider>

            <template v-if="!editedTicketType.bring_a_friend">
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

            <!-- Group Pricing -->
            <div v-if="editedTicketType.requires_team" class="mt-2">
              <p class="text-caption text-medium-emphasis mb-2">
                <v-icon size="small">mdi-information-outline</v-icon>
                Group pricing — who pays for the team?
              </p>

              <v-select
                v-model="editedTicketType.group_payment_mode"
                :items="groupPaymentModeOptions"
                item-title="label"
                item-value="value"
                label="Group Payment Mode"
                variant="outlined"
                clearable
                hint="Leave unset for standard per-person pricing"
                persistent-hint
                class="mb-2"
              ></v-select>

              <v-row v-if="editedTicketType.group_payment_mode">
                <v-col cols="6" class="py-0">
                  <v-text-field
                    v-model.number="editedTicketType.group_size"
                    label="Group Size *"
                    type="number"
                    min="2"
                    variant="outlined"
                    hint="How many people in a group"
                    persistent-hint
                    class="mb-2"
                    :rules="[v => !editedTicketType.group_payment_mode || (v >= 2) || 'Must be at least 2']"
                  ></v-text-field>
                </v-col>
                <v-col v-if="editedTicketType.group_payment_mode === 'leader'" cols="6" class="py-0">
                  <v-text-field
                    v-model.number="editedTicketType.group_price_euros"
                    label="Group Total Price (€) *"
                    type="number"
                    min="0"
                    step="0.01"
                    variant="outlined"
                    hint="Total charged to team lead"
                    persistent-hint
                    class="mb-2"
                    :rules="[v => !editedTicketType.group_payment_mode === 'leader' || v >= 0 || 'Required']"
                  ></v-text-field>
                </v-col>
              </v-row>

              <v-alert
                v-if="editedTicketType.group_payment_mode === 'leader' && editedTicketType.group_size >= 2 && editedTicketType.group_price_euros >= 0"
                type="info"
                variant="tonal"
                density="compact"
                class="mb-2"
              >
                Team lead pays <strong>€{{ editedTicketType.group_price_euros }}</strong> for
                {{ editedTicketType.group_size }} people
                (€{{ (editedTicketType.group_price_euros / editedTicketType.group_size).toFixed(2) }}/person).
                The other {{ editedTicketType.group_size - 1 }} teammate(s) receive a free invite by email.
              </v-alert>

              <v-alert
                v-else-if="editedTicketType.group_payment_mode === 'individual' && editedTicketType.group_size >= 2"
                type="info"
                variant="tonal"
                density="compact"
                class="mb-2"
              >
                Each of the {{ editedTicketType.group_size }} team members pays
                <strong>€{{ editedTicketType.price_euros }}</strong> individually (€{{ (editedTicketType.price_euros * editedTicketType.group_size).toFixed(2) }} total).
              </v-alert>
            </div>
            </template>

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
    <v-dialog v-model="deleteDialog" max-width="440px">
      <v-card>
        <v-card-title>Delete "{{ ticketTypeToDelete?.name }}"?</v-card-title>
        <v-card-text data-test="delete-message">
          <template v-if="ticketTypeToDelete?.tickets_sold > 0">
            {{ ticketTypeToDelete.tickets_sold }}
            {{ ticketTypeToDelete.tickets_sold === 1 ? 'person holds' : 'people hold' }} this ticket.
            They keep it. It will be taken off sale and moved to the Deleted section below.
          </template>
          <template v-else>
            It will no longer be on sale. Anyone who already registered with it (for example, awaiting
            approval or payment) keeps it; otherwise it is removed for good.
          </template>
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
import { ref, computed, onMounted } from 'vue';
import TicketTypeService from '@/services/TicketTypeService.js';
import { dealLabel } from '@/utils/friendTickets.js';
import { FormTemplateService } from '@/services/FormTemplateService.js';

const props = defineProps({
  eventId: {
    type: Number,
    required: true
  }
});

const emit = defineEmits(['ticket-types-updated']);

const ticketTypes = ref([]);
const deletedTicketTypes = ref([]);
const formTemplates = ref([]);
const dialog = ref(false);
const deleteDialog = ref(false);
const isEditing = ref(false);
const saving = ref(false);
const deleting = ref(false);
const snackbar = ref(false);
const snackbarText = ref('');
const snackbarColor = ref('success');

const groupPaymentModeOptions = [
  { label: 'Leader pays for the whole group', value: 'leader' },
  { label: 'Each member pays individually', value: 'individual' },
];

const defaultTicketType = {
  name: '',
  description: '',
  price_euros: 0,
  capacity: null,
  form_template_id: null,
  is_active: true,
  is_free_for_members: false,
  show_availability: true,
  requires_team: false,
  team_max_members: null,
  group_payment_mode: null,
  group_size: null,
  group_price_euros: null,
  bring_a_friend: false,
  display_order: 0
};

const editedTicketType = ref({ ...defaultTicketType });

// Switching a type to or from the deal after people bought it would change
// what they paid for, so the backend refuses it; say so up front.
const bringAFriendLocked = computed(() => isEditing.value && (editedTicketType.value.tickets_sold || 0) > 0);
const bringAFriendHint = computed(() => {
  if (bringAFriendLocked.value) return "People already have this ticket, so this can't be changed. Create a new ticket type instead.";
  if (!editedTicketType.value.bring_a_friend) return 'The buyer pays once and names a friend, who gets their own ticket. Uses 2 seats.';
  const price = Number(editedTicketType.value.price_euros) || 0;
  return `Buyers pay €${price.toFixed(2)} for two (€${(price / 2).toFixed(2)} each). Discount codes and member pricing don't apply.`;
});

function onBringAFriendChange(on) {
  if (!on) return;
  // The deal doesn't mix with team or member pricing.
  Object.assign(editedTicketType.value, {
    is_free_for_members: false,
    requires_team: false,
    team_max_members: null,
    group_payment_mode: null,
    group_size: null,
    group_price_euros: null,
  });
}
const ticketTypeToDelete = ref(null);
const form = ref(null);

onMounted(async () => {
  await loadTicketTypes();
  await loadFormTemplates();
});

async function loadTicketTypes() {
  try {
    const response = await TicketTypeService.getTicketTypes(props.eventId, false, true);
    ticketTypes.value = response.ticket_types || [];
    deletedTicketTypes.value = response.deleted_ticket_types || [];
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
    const result = await TicketTypeService.deleteTicketType(
      props.eventId,
      ticketTypeToDelete.value.ticket_type_id
    );
    deleteDialog.value = false;
    showSnackbar(
      result.outcome === 'hidden'
        ? `Ticket type taken off sale. ${result.holders} ${result.holders === 1 ? 'registration keeps' : 'registrations keep'} it.`
        : 'Ticket type deleted',
      'success'
    );
    emit('ticket-types-updated');
    await loadTicketTypes();
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
