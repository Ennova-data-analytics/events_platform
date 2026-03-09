<template>
  <v-form @submit.prevent="handleSubmit">
    <v-text-field
      v-model="editableEvent.event_name"
      label="Event Name"
      variant="outlined"
      class="mb-4"
    />
    
    <v-textarea
      v-model="editableEvent.description"
      label="Description"
      variant="outlined"
      class="mb-4"
      rows="12"
      hint="Supports Markdown: **bold**, *italic*, ## headings, - lists, [links](url)"
      persistent-hint
    />
    
    <v-row>
      <v-col cols="12" sm="6">
        <v-text-field
          v-model="editableEvent.event_date_start"
          label="Date & Time (YYYY-MM-DDTHH:MM:SS)"
          placeholder="e.g., 2025-10-22T18:00:00"
          variant="outlined"
          class="mb-4"
        />
      </v-col>
      <v-col cols="12" sm="6">
        <v-text-field
          v-model="editableEvent.location"
          label="Display Location"
          hint="This is what attendees will see (e.g., 'Building 9, Room 101')"
          persistent-hint
          variant="outlined"
          class="mb-4"
        />
      </v-col>
    </v-row>

    <v-divider class="my-6"></v-divider>
    <h3 class="text-subtitle-1 mb-4 font-weight-medium">
      <v-icon start>mdi-map</v-icon>
      Interactive Map Settings (Optional)
    </h3>

    <v-expansion-panels class="mb-4">
      <v-expansion-panel>
        <v-expansion-panel-title>
          <div class="d-flex align-center">
            <v-icon start color="primary">mdi-map-marker-radius</v-icon>
            <span class="font-weight-medium">Configure Map Display</span>
          </div>
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <v-alert type="info" variant="tonal" density="compact" class="mb-4">
            <v-icon start size="small">mdi-information</v-icon>
            Configure how the event location appears on the interactive map. Choose one option:
            <ul class="mt-2 ml-4">
              <li><strong>Map Address:</strong> Let the system find coordinates automatically</li>
              <li><strong>Manual Coordinates:</strong> Enter exact latitude/longitude</li>
              <li><strong>Leave Empty:</strong> System will try to geocode the display location</li>
            </ul>
          </v-alert>

          <v-radio-group v-model="mapInputMethod" class="mb-4">
            <v-radio label="Use Map Address (Recommended)" value="address"></v-radio>
            <v-radio label="Enter Manual Coordinates" value="coordinates"></v-radio>
            <v-radio label="Auto-detect from Display Location" value="auto"></v-radio>
          </v-radio-group>

          <v-text-field
            v-if="mapInputMethod === 'address'"
            v-model="editableEvent.map_address"
            label="Map Address"
            variant="outlined"
            placeholder="e.g., 'Julianalaan 134, 2628 BL Delft' or 'TU Delft Library, Delft, Netherlands'"
            hint="Enter a detailed address for accurate map placement. The more specific, the better!"
            persistent-hint
            clearable
            prepend-inner-icon="mdi-map-search"
            class="mb-3"
          />

          <v-row v-if="mapInputMethod === 'coordinates'">
            <v-col cols="12" sm="6">
              <v-text-field
                v-model.number="editableEvent.latitude"
                label="Latitude"
                variant="outlined"
                placeholder="e.g., 52.0027"
                type="number"
                step="any"
                hint="Latitude coordinate (-90 to 90)"
                persistent-hint
                prepend-inner-icon="mdi-latitude"
              />
            </v-col>
            <v-col cols="12" sm="6">
              <v-text-field
                v-model.number="editableEvent.longitude"
                label="Longitude"
                variant="outlined"
                placeholder="e.g., 4.3707"
                type="number"
                step="any"
                hint="Longitude coordinate (-180 to 180)"
                persistent-hint
                prepend-inner-icon="mdi-longitude"
              />
            </v-col>
          </v-row>

          <v-alert v-if="mapInputMethod === 'auto'" type="info" variant="tonal" density="compact">
            <v-icon start size="small">mdi-auto-fix</v-icon>
            The map will attempt to geocode your display location: <strong>{{ editableEvent.location || 'Not set' }}</strong>
          </v-alert>

          <div v-if="showMapPreviewLink" class="mt-3">
            <v-btn
              :href="mapPreviewUrl"
              target="_blank"
              size="small"
              variant="outlined"
              color="primary"
            >
              <v-icon start>mdi-open-in-new</v-icon>
              Preview on Google Maps
            </v-btn>
          </div>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>

    <v-row>
      <v-col cols="12" sm="6">
        <v-text-field
          v-model.number="editableEvent.price_euros"
          label="Price (€)"
          type="number"
          variant="outlined"
          class="mb-4"
        />
      </v-col>
      <v-col cols="12" sm="6">
        <v-text-field
          v-model.number="editableEvent.capacity"
          label="Capacity"
          type="number"
          variant="outlined"
          class="mb-4"
        />
      </v-col>
    </v-row>

    <!-- Requires Approval Toggle -->
    <v-row>
      <v-col cols="12">
        <v-card variant="outlined" class="mb-4">
          <v-card-text>
            <div class="d-flex align-center justify-space-between">
              <div>
                <div class="text-subtitle-1 font-weight-medium mb-1">
                  Require Admin Approval for Registrations
                </div>
                <div class="text-body-2 text-grey">
                  When enabled, registrations must be manually approved before attendees can proceed to payment.
                  When disabled, registrations are auto-approved and attendees can pay immediately.
                </div>
              </div>
              <v-switch
                v-model="editableEvent.requires_approval"
                color="primary"
                hide-details
                class="ml-4"
              ></v-switch>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Free for Members Toggle -->
    <v-row>
      <v-col cols="12">
        <v-card variant="outlined" class="mb-4">
          <v-card-text>
            <div class="d-flex align-center justify-space-between">
              <div>
                <div class="text-subtitle-1 font-weight-medium mb-1">
                  Free for Ennova Members
                </div>
                <div class="text-body-2 text-grey">
                  When enabled, Ennova association members will automatically bypass payment and be approved for this event.
                  Members are managed in the "Ennova Members" section.
                </div>
              </div>
              <v-switch
                v-model="editableEvent.is_free_for_members"
                color="success"
                hide-details
                class="ml-4"
              ></v-switch>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Team Registration Toggle -->
    <v-row>
      <v-col cols="12">
        <v-card variant="outlined" class="mb-4">
          <v-card-text>
            <div class="d-flex align-center justify-space-between">
              <div>
                <div class="text-subtitle-1 font-weight-medium mb-1">
                  Enable Team Registration
                </div>
                <div class="text-body-2 text-grey">
                  When enabled, attendees can join or create a team when registering.
                  Team selection is optional — attendees without teammates can still register and be assigned later.
                  Only applies to events without ticket types.
                </div>
              </div>
              <v-switch
                v-model="editableEvent.teams_enabled"
                color="primary"
                hide-details
                class="ml-4"
              ></v-switch>
            </div>

            <v-text-field
              v-if="editableEvent.teams_enabled"
              v-model.number="editableEvent.team_max_members"
              label="Default Max Team Size"
              type="number"
              min="1"
              variant="outlined"
              class="mt-4"
              hint="Leave empty for unlimited team size"
              persistent-hint
            />
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-row>
      <v-col cols="12">
        <v-select
          v-model="editableEvent.form_template_id"
          :items="formTemplates"
          item-title="template_name"
          item-value="template_id"
          label="Additional Application Form (Optional)"
          variant="outlined"
          clearable
          no-data-text="No custom forms available"
        ></v-select>
      </v-col>
    </v-row>


    <v-divider class="my-4"></v-divider>
    <h3 class="text-subtitle-1 mb-3">Custom Email Templates (Optional)</h3>

    <v-row>
      <v-col cols="12" sm="6">
        <v-select
          v-model="editableEvent.email_template_approved_id"
          :items="approvedTemplates"
          item-title="template_name"
          item-value="template_id"
          label="Registration Approved Email"
          variant="outlined"
          clearable
          no-data-text="No templates available"
          hint="Sent when registration is approved"
          persistent-hint
        ></v-select>
      </v-col>
      <v-col cols="12" sm="6">
        <v-select
          v-model="editableEvent.email_template_rejected_id"
          :items="rejectedTemplates"
          item-title="template_name"
          item-value="template_id"
          label="Registration Rejected Email"
          variant="outlined"
          clearable
          no-data-text="No templates available"
          hint="Sent when registration is rejected"
          persistent-hint
        ></v-select>
      </v-col>
    </v-row>

    <v-row>
      <v-col cols="12" sm="6">
        <v-select
          v-model="editableEvent.email_template_received_id"
          :items="receivedTemplates"
          item-title="template_name"
          item-value="template_id"
          label="Registration Received Email"
          variant="outlined"
          clearable
          no-data-text="No templates available"
          hint="Sent when registration is first submitted"
          persistent-hint
        ></v-select>
      </v-col>
      <v-col cols="12" sm="6">
        <v-select
          v-model="editableEvent.email_template_payment_id"
          :items="paymentTemplates"
          item-title="template_name"
          item-value="template_id"
          label="Payment Confirmed Email"
          variant="outlined"
          clearable
          no-data-text="No templates available"
          hint="Sent when payment is confirmed"
          persistent-hint
        ></v-select>
      </v-col>
    </v-row>
    
    <v-row>
      <v-col cols="12">
        <v-file-input
          v-model="imageFile"
          label="Event Cover Image"
          variant="outlined"
          prepend-icon=""
          prepend-inner-icon="mdi-camera"
          accept="image/*"
        ></v-file-input>
      </v-col>
    </v-row>
    
    <v-btn type="submit" color="primary" size="large" :loading="isLoading">
      {{ isEditMode ? 'Save Changes' : 'Create Event' }}
    </v-btn>
  </v-form>
</template>

<script setup>
import { ref, watch, computed, onMounted } from 'vue';
import { FormTemplateService } from '@/services/FormTemplateService.js';
import { EmailTemplateService } from '@/services/EmailTemplateService.js';

const props = defineProps({
  initialData: { type: Object, default: () => ({}) },
  isLoading: { type: Boolean, default: false }
});

const emit = defineEmits(['submit']);

const editableEvent = ref({
  requires_approval: true,
  is_free_for_members: false,
  teams_enabled: false,
  team_max_members: null,
  map_address: null,
  latitude: null,
  longitude: null
});
const imageFile = ref([]);
const mapInputMethod = ref('address'); 

const formTemplates = ref([]);
const approvedTemplates = ref([]);
const rejectedTemplates = ref([]);
const receivedTemplates = ref([]);
const paymentTemplates = ref([]);
const isEditMode = computed(() => props.initialData && props.initialData.event_id);

watch(() => props.initialData, (newData) => {
  const dataToEdit = { ...newData };
  if (dataToEdit.event_date_start) {
    dataToEdit.event_date_start = new Date(dataToEdit.event_date_start).toISOString().slice(0, 19);
  }
  if (dataToEdit.requires_approval === undefined) {
    dataToEdit.requires_approval = true;
  }
  if (dataToEdit.is_free_for_members === undefined) {
    dataToEdit.is_free_for_members = false;
  }
  if (dataToEdit.teams_enabled === undefined) {
    dataToEdit.teams_enabled = false;
  }
  if (dataToEdit.team_max_members === undefined) {
    dataToEdit.team_max_members = null;
  }

  if (dataToEdit.latitude && dataToEdit.longitude) {
    mapInputMethod.value = 'coordinates';
  } else if (dataToEdit.map_address) {
    mapInputMethod.value = 'address';
  } else {
    mapInputMethod.value = 'auto';
  }

  editableEvent.value = dataToEdit;
}, { immediate: true, deep: true });

watch(mapInputMethod, (newMethod) => {
  if (newMethod === 'address') {
    editableEvent.value.latitude = null;
    editableEvent.value.longitude = null;
  } else if (newMethod === 'coordinates') {
    editableEvent.value.map_address = null;
  } else if (newMethod === 'auto') {
    editableEvent.value.map_address = null;
    editableEvent.value.latitude = null;
    editableEvent.value.longitude = null;
  }
});

const showMapPreviewLink = computed(() => {
  if (mapInputMethod.value === 'coordinates' && editableEvent.value.latitude && editableEvent.value.longitude) {
    return true;
  }
  if (mapInputMethod.value === 'address' && editableEvent.value.map_address) {
    return true;
  }
  if (mapInputMethod.value === 'auto' && editableEvent.value.location) {
    return true;
  }
  return false;
});

const mapPreviewUrl = computed(() => {
  if (mapInputMethod.value === 'coordinates' && editableEvent.value.latitude && editableEvent.value.longitude) {
    return `https://www.google.com/maps/search/?api=1&query=${editableEvent.value.latitude},${editableEvent.value.longitude}`;
  }
  const address = mapInputMethod.value === 'address' ? editableEvent.value.map_address : editableEvent.value.location;
  if (address) {
    return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(address)}`;
  }
  return '';
});

onMounted(async () => {
  try {
    const [formResponse, emailResponse] = await Promise.all([
      FormTemplateService.getAllTemplates(),
      EmailTemplateService.getAllTemplates(),
    ]);
    formTemplates.value = formResponse.data;

    // Filter email templates by type
    const allEmailTemplates = emailResponse.data;
    approvedTemplates.value = allEmailTemplates.filter(t => t.template_type === 'registration_approved');
    rejectedTemplates.value = allEmailTemplates.filter(t => t.template_type === 'registration_rejected');
    receivedTemplates.value = allEmailTemplates.filter(t => t.template_type === 'registration_received');
    paymentTemplates.value = allEmailTemplates.filter(t => t.template_type === 'payment_confirmed');
  } catch (error) {
    console.error("Failed to fetch templates:", error);
  }
});

const handleSubmit = () => {
  console.log('=== EVENT FORM SUBMIT DEBUG ===');
  console.log('Image File ref value:', imageFile.value);
  console.log('Image File type:', typeof imageFile.value);
  console.log('Is Array?:', Array.isArray(imageFile.value));
  console.log('Length:', imageFile.value?.length);
 
  const fileToSend = imageFile.value;
  console.log('File to send:', fileToSend);


 
  emit('submit', editableEvent.value, fileToSend);
  console.log('Emitted submit event');

};
</script>