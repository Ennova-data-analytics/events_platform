<template>
  <div>
    <div v-if="eventStore.isLoading && !eventStore.currentEvent" class="text-center mt-16">
      <v-progress-circular indeterminate color="primary" size="64"></v-progress-circular>
      <p class="mt-4">Loading Event Details...</p>
    </div>
    <v-alert v-else-if="eventStore.error && !eventStore.currentEvent" type="error" class="mt-4">
      {{ eventStore.error }}
    </v-alert>

    <div v-else-if="eventStore.currentEvent">
      <v-row>
        <v-col cols="12" md="8">
          <v-img 
            :src="eventStore.currentEvent.image_url || 'https://cdn.vuetifyjs.com/images/cards/docks.jpg'" 
            height="400px" 
            cover 
            class="rounded-lg"
          ></v-img>
        </v-col>
        
        <v-col cols="12" md="4">
          <h1 class="text-h3 font-weight-bold">{{ eventStore.currentEvent.event_name }}</h1>
          <div class="mt-4">
            <p class="text-h6 font-weight-regular">
              <v-icon>mdi-calendar</v-icon>
              {{ new Date(eventStore.currentEvent.event_date_start).toLocaleString('en-GB') }}
            </p>
            <p class="text-h6 font-weight-regular mt-2">
              <v-icon>mdi-map-marker</v-icon>
              {{ eventStore.currentEvent.location }}
            </p>
          </div>

          <div class="mt-8">
            <v-btn v-if="!authStore.isAuthenticated" to="/login" color="primary" size="large" block>
              Login to Apply
            </v-btn>
            <v-btn
              v-else-if="registrationStatus === 'not_registered'"
              color="primary"
              size="large"
              block
              @click="handleRegistration"
              :loading="eventStore.isLoading"
            >
              Apply to Register ({{ eventStore.currentEvent.price_euros > 0 ? `€${eventStore.currentEvent.price_euros}` : 'Free' }})
            </v-btn>
            <v-chip v-else-if="registrationStatus === 'Pending Approval'" color="info" variant="tonal" size="large" block>
              <v-icon start>mdi-clock-outline</v-icon>
              Application Pending Review
            </v-chip>
            <v-btn v-else-if="registrationStatus === 'Approved'" color="warning" size="large" block @click="handlePayment">
              <v-icon start>mdi-credit-card-outline</v-icon>
              Pay Now to Confirm Spot
            </v-btn>
            <v-chip v-else-if="registrationStatus === 'Paid'" color="success" variant="tonal" size="large" block>
              <v-icon start>mdi-check-circle</v-icon>
              Registered & Confirmed
            </v-chip>
            <v-chip v-else-if="registrationStatus === 'Rejected'" color="error" variant="tonal" size="large" block>
              <v-icon start>mdi-close-circle</v-icon>
              Application Not Approved
            </v-chip>
          </div>

          <v-snackbar v-model="showSuccess" color="success" timeout="4000">
            {{ successMessage }}
          </v-snackbar>
          <v-snackbar v-model="showError" color="error" timeout="5000">
            {{ eventStore.error }}
          </v-snackbar>

        </v-col>
      </v-row>
      
      <v-row class="mt-8">
        <v-col>
          <h2 class="text-h5">About this event</h2>
          <p class="mt-4" style="white-space: pre-wrap;">{{ eventStore.currentEvent.description }}</p>
        </v-col>
      </v-row>
    </div>

    <v-dialog v-model="isFormModalVisible" max-width="600px" persistent>
      <v-card>
        <v-card-title>
          <span class="text-h5">Additional Information Required</span>
        </v-card-title>
        <v-card-text>
          <p class="mb-4">Please answer the following questions to complete your application.</p>
          <v-alert
              v-if="validationError"
              type="error"
              variant="tonal"
              density="compact"
              class="mb-4"
            >
              {{ validationError }}
          </v-alert>
          <v-form ref="customFormRef">
            <div v-for="field in customForm.fields" :key="field.name" class="mb-2">
              <v-text-field
                v-if="field.type === 'text'"
                v-model="formResponses[field.name]"
                :label="field.label"
                :required="field.required"
                variant="outlined"
              ></v-text-field>
              <v-textarea
                v-if="field.type === 'textarea'"
                v-model="formResponses[field.name]"
                :label="field.label"
                :required="field.required"
                variant="outlined"
              ></v-textarea>
          <v-select
            v-if="field.type === 'select'"
            v-model="formResponses[field.name]"
            :items="field.options"
            :label="field.label"
            :required="field.required"
            variant="outlined"
          ></v-select>

          <v-radio-group
            v-if="field.type === 'radio'"
            v-model="formResponses[field.name]"
            :label="field.label"
            :required="field.required"
            inline
          >
          <v-radio
              v-for="option in field.options"
              :key="option"
              :label="option"
              :value="option"
            ></v-radio>
          </v-radio-group>
          <v-file-input
                v-if="field.type === 'file'"
                v-model="formFiles[field.name]"
                :label="field.label"
                :required="field.required"
                variant="outlined"
          ></v-file-input>
          <v-checkbox
            v-if="field.type === 'checkbox'"
            v-model="formResponses[field.name]"
            :label="field.label"
            :required="field.required"
          ></v-checkbox>

          </div>
        </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn text @click="isFormModalVisible = false">Cancel</v-btn>
          <v-btn color="primary" @click="submitApplicationWithForm">Submit Application</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue';
import { useRoute } from 'vue-router';
import { useEventStore } from '@/stores/events.store.js';
import { useAuthStore } from '@/stores/auth.store.js';
import { FormTemplateService } from '@/services/FormTemplateService.js';
import { UploadService } from '@/services/UploadService.js';


const route = useRoute();
const eventStore = useEventStore();
const authStore = useAuthStore();
    
const showSuccess = ref(false);
const successMessage = ref('');
const showError = ref(false);

const isFormModalVisible = ref(false);
const customForm = ref({ fields: [] });
const formResponses = ref({});
const formFiles = ref({}); 
const isSubmitting = ref(false); 
const validationError = ref('');


watch(() => eventStore.currentEvent, (newEvent) => {
  console.log('EventDetailsPage: currentEvent updated:', newEvent);
});
watch(isFormModalVisible, (isVisible) => {
  if (!isVisible) {
    validationError.value = '';
  }
});

const registrationStatus = computed(() => {
  if (!authStore.user || !eventStore.currentEvent) return 'loading';
  const registration = authStore.user.registrations?.find(
    reg => reg.event.event_id === eventStore.currentEvent.event_id
  );
  return registration ? registration.status : 'not_registered';
});

onMounted(() => {
  const eventId = route.params.id;
  eventStore.fetchEventById(eventId);
  if (authStore.isAuthenticated) {
    authStore.fetchCurrentUser();
  }
});

function validateForm() {
  for (const field of customForm.value.fields) {
    if (field.required) {
      const textResponse = formResponses.value[field.name];
      const fileResponse = formFiles.value[field.name];

      const isTextFilled = textResponse !== undefined && textResponse !== null && textResponse !== '';
      const isFileFilled = fileResponse !== undefined && fileResponse !== null;

      if (!isTextFilled && !isFileFilled) {
        validationError.value = `The field "${field.label}" is required. Please fill it out.`;
        return false;
      }
    }
  }
  validationError.value = ''; 
  return true;
}

async function handleRegistration() {
  const event = eventStore.currentEvent;
  console.log('handleRegistration called. Event object:', event);
  
  if (!event) {
    console.error('handleRegistration: No current event found.');
    return;
  }

  console.log(`Checking for form_template_id: ${event.form_template_id}`);
  if (event.form_template_id) {
    console.log('Form template found. Attempting to open modal...');
    try {
      const response = await FormTemplateService.getTemplateById(event.form_template_id);
      customForm.value = response.data;
      formResponses.value = {}; 
      formFiles.value = {};
      isFormModalVisible.value = true;
      console.log('Modal should now be visible.');
    } catch (error) {
      console.error("Failed to load custom form", error);
      eventStore.error = "Could not load the application form.";
      showError.value = true;
    }
  } else {
    console.log('No form template found. Submitting application directly...');
    submitApplicationWithForm();
  }
}

async function submitApplicationWithForm() {
  if (!validateForm()) {
    return;
  }
  isSubmitting.value = true;
  const finalFormResponses = { ...formResponses.value };

  try {
    for (const fieldName in formFiles.value) {
      const file = formFiles.value[fieldName];
      if (file) {
        const response = await UploadService.uploadFile(file);
        finalFormResponses[fieldName] = response.data.file_key;
      }
    }

    if (eventStore.currentEvent) {
      await eventStore.registerForEvent(eventStore.currentEvent.event_id, { form_responses: finalFormResponses });
      successMessage.value = 'Application submitted successfully!';
      showSuccess.value = true;
      await authStore.fetchCurrentUser();
    }
  } catch (error) {
    showError.value = true;
  } finally {
    isSubmitting.value = false;
    isFormModalVisible.value = false;
  }
}

function handlePayment() {
  console.log('Redirecting to payment...');
  alert('Payment flow is not yet implemented.');
}
</script>