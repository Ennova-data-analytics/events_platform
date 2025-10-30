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
          label="Location"
          variant="outlined"
          class="mb-4"
        />
      </v-col>
    </v-row>
    
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

    <v-row>
      <v-col cols="12">
        <v-select
          v-model="editableEvent.feedback_template_id"
          :items="feedbackTemplates"
          item-title="template_name"
          item-value="template_id"
          label="Feedback Form Template (Optional)"
          variant="outlined"
          clearable
          no-data-text="No feedback templates available"
          hint="Attendees can submit feedback via QR code"
          persistent-hint
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
import { FeedbackTemplateService } from '@/services/FeedbackTemplateService.js';

const props = defineProps({
  initialData: { type: Object, default: () => ({}) },
  isLoading: { type: Boolean, default: false }
});

const emit = defineEmits(['submit']);

const editableEvent = ref({
  requires_approval: true  // Default to true for new events
});
const imageFile = ref([]);

const formTemplates = ref([]);
const feedbackTemplates = ref([]);
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
  // Ensure requires_approval has a default value if not present
  if (dataToEdit.requires_approval === undefined) {
    dataToEdit.requires_approval = true;
  }
  editableEvent.value = dataToEdit;
}, { immediate: true, deep: true });

onMounted(async () => {
  try {
    const [formResponse, emailResponse, feedbackResponse] = await Promise.all([
      FormTemplateService.getAllTemplates(),
      EmailTemplateService.getAllTemplates(),
      FeedbackTemplateService.getAllTemplates()
    ]);
    formTemplates.value = formResponse.data;
    feedbackTemplates.value = feedbackResponse.data;

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