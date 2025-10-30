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
            :height="$vuetify.display.mobile ? '250px' : '400px'"
            cover
            class="rounded-lg"
            :gradient="'to top, rgba(0,0,0,.3), rgba(0,0,0,0)'"
          >
            <template v-slot:placeholder>
              <v-row class="fill-height ma-0" align="center" justify="center">
                <v-progress-circular
                  indeterminate
                  color="grey-lighten-4"
                  size="64"
                ></v-progress-circular>
              </v-row>
            </template>

            <template v-slot:error>
              <v-row class="fill-height ma-0 bg-grey-lighten-3" align="center" justify="center">
                <div class="text-center">
                  <v-icon size="64" color="grey">mdi-image-broken-variant</v-icon>
                  <p class="text-grey mt-2">Failed to load image</p>
                </div>
              </v-row>
            </template>
          </v-img>
        </v-col>
        
        <v-col cols="12" md="4">
          <h1 :class="$vuetify.display.mobile ? 'text-h4 font-weight-bold mt-4' : 'text-h3 font-weight-bold'">{{ eventStore.currentEvent.event_name }}</h1>
          <div :class="$vuetify.display.mobile ? 'mt-3' : 'mt-4'">
            <p :class="$vuetify.display.mobile ? 'text-body-1 font-weight-regular' : 'text-h6 font-weight-regular'">
              <v-icon>mdi-calendar</v-icon>
              {{ new Date(eventStore.currentEvent.event_date_start).toLocaleDateString('en-GB') }}
            </p>
            <p :class="$vuetify.display.mobile ? 'text-body-1 font-weight-regular mt-2' : 'text-h6 font-weight-regular mt-2'">
              <v-icon>mdi-map-marker</v-icon>
              {{ eventStore.currentEvent.location }}
            </p>
          </div>

          <div :class="$vuetify.display.mobile ? 'mt-4' : 'mt-8'">
            <v-btn v-if="!authStore.isAuthenticated" to="/login" color="primary" :size="$vuetify.display.mobile ? 'default' : 'large'" block>
              Login to Apply
            </v-btn>
            <v-chip v-else-if="registrationStatus === 'Pending Approval'" color="info" variant="tonal" :size="$vuetify.display.mobile ? 'default' : 'large'" block>
              <v-icon start>mdi-clock-outline</v-icon>
              Application Pending Review
            </v-chip>
            <v-btn v-else-if="registrationStatus === 'Approved'" color="warning" :size="$vuetify.display.mobile ? 'default' : 'large'" block @click="handlePayment">
              <v-icon start>mdi-credit-card-outline</v-icon>
              Pay Now to Confirm Spot
            </v-btn>
            <v-chip v-else-if="registrationStatus === 'Paid'" color="success" variant="tonal" :size="$vuetify.display.mobile ? 'default' : 'large'" block>
              <v-icon start>mdi-check-circle</v-icon>
              Registered & Confirmed
            </v-chip>
            <v-chip v-else-if="registrationStatus === 'Rejected'" color="error" variant="tonal" :size="$vuetify.display.mobile ? 'default' : 'large'" block>
              <v-icon start>mdi-close-circle</v-icon>
              Application Not Approved
            </v-chip>
            <v-chip v-else-if="!eventStore.currentEvent.signups_enabled" color="warning" variant="tonal" :size="$vuetify.display.mobile ? 'default' : 'large'" block>
              <v-icon start>mdi-close-circle-outline</v-icon>
              Signups Closed
            </v-chip>
            <v-btn
              v-else-if="registrationStatus === 'not_registered'"
              color="primary"
              :size="$vuetify.display.mobile ? 'default' : 'large'"
              block
              @click="handleRegistration"
              :loading="eventStore.isLoading"
            >
              Apply to Register ({{ eventStore.currentEvent.price_euros > 0 ? `€${eventStore.currentEvent.price_euros}` : 'Free' }})
            </v-btn>
          </div>

          <!-- Approval requirement info -->
          <v-alert
            v-if="registrationStatus === 'not_registered' && eventStore.currentEvent.signups_enabled && authStore.isAuthenticated"
            type="info"
            variant="tonal"
            density="compact"
            class="mt-3"
          >
            <template v-if="eventStore.currentEvent.requires_approval">
              <v-icon size="small">mdi-information</v-icon>
              Your registration will be reviewed by the organizer before you can proceed to payment.
            </template>
            <template v-else>
              <v-icon size="small">mdi-flash</v-icon>
              Register now and pay immediately to secure your spot!
            </template>
          </v-alert>

          <v-snackbar v-model="showSuccess" color="success" timeout="4000">
            {{ successMessage }}
          </v-snackbar>
          <v-snackbar v-model="showError" color="error" timeout="5000">
            {{ eventStore.error }}
          </v-snackbar>

        </v-col>
      </v-row>
      
      <v-row :class="$vuetify.display.mobile ? 'mt-4' : 'mt-8'">
        <v-col cols="12">
          <v-card elevation="2" :class="$vuetify.display.mobile ? 'pa-4' : 'pa-8'">
            <h2 :class="$vuetify.display.mobile ? 'text-h5 font-weight-bold mb-4' : 'text-h4 font-weight-bold mb-6'">About this event</h2>
            <v-divider class="mb-6"></v-divider>
            
            <div 
              class="event-description" 
              v-html="parsedDescription"
            ></div>
          </v-card>
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
import ApiClient from '@/services/ApiClient.js';
import { marked } from 'marked';
import DOMPurify from 'dompurify';

marked.setOptions({
  breaks: true,        
  gfm: true,          
  headerIds: false,   
});

const parsedDescription = computed(() => {
  if (!eventStore.currentEvent?.description) return '';
  
  const rawHtml = marked.parse(eventStore.currentEvent.description);
  
  return DOMPurify.sanitize(rawHtml);
});

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

onMounted(async () => {
  const eventId = route.params.id;
  await eventStore.fetchEventById(eventId);

  if (authStore.isAuthenticated) {
    await authStore.fetchCurrentUser();
  }

  const urlParams = new URLSearchParams(window.location.search);
  const paymentStatus = urlParams.get('payment');

  if (paymentStatus === 'success') {
    showSuccess.value = true;
    successMessage.value = 'Payment successful! Your registration is confirmed.';
    await authStore.fetchCurrentUser();
    window.history.replaceState({}, '', window.location.pathname);
  } else if (paymentStatus === 'cancelled') {
    showError.value = true;
    eventStore.error = 'Payment was cancelled. Please try again when ready.';
    window.history.replaceState({}, '', window.location.pathname);
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

  if (!event.signups_enabled) {
    eventStore.error = "Signups are currently closed for this event.";
    showError.value = true;
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

async function handlePayment() {
  try {
    isSubmitting.value = true;

    const registration = authStore.user.registrations.find(
      r => r.event.event_id === eventStore.currentEvent.event_id && r.status === 'Approved'
    );

    if (!registration) {
      alert('Registration not found or not approved');
      return;
    }

    const response = await ApiClient.post(
      `/payments/registrations/${registration.registration_id}/create-checkout-session`
    );

    if (response.data.checkout_url) {
      window.location.href = response.data.checkout_url;
    }

  } catch (error) {
    console.error('Error creating checkout session:', error);
    eventStore.error = 'Failed to initiate payment. Please try again.';
    showError.value = true;
  } finally {
    isSubmitting.value = false;
  }
}
</script>

<style scoped>
.event-description {
  font-size: 16px;
  line-height: 1.8;
  color: #2c3e50;
  max-width: 100%;
  overflow-wrap: break-word;
}

.event-description :deep(h1) {
  font-size: 28px;
  font-weight: 700;
  margin-top: 32px;
  margin-bottom: 16px;
  color: #1a1a1a;
  line-height: 1.3;
}

.event-description :deep(h2) {
  font-size: 24px;
  font-weight: 600;
  margin-top: 28px;
  margin-bottom: 14px;
  color: #1a1a1a;
  line-height: 1.3;
}

.event-description :deep(h3) {
  font-size: 20px;
  font-weight: 600;
  margin-top: 24px;
  margin-bottom: 12px;
  color: #2a2a2a;
  line-height: 1.4;
}

.event-description :deep(h1:first-child),
.event-description :deep(h2:first-child),
.event-description :deep(h3:first-child) {
  margin-top: 0;
}

.event-description :deep(p) {
  margin-bottom: 16px;
  color: #2c3e50;
}

.event-description :deep(p:first-of-type) {
  font-size: 18px;
  font-weight: 400;
  color: #1a1a1a;
}

.event-description :deep(ul),
.event-description :deep(ol) {
  margin: 16px 0;
  padding-left: 28px;
}

.event-description :deep(li) {
  margin-bottom: 10px;
  line-height: 1.7;
}

.event-description :deep(ul li) {
  list-style-type: disc;
}

.event-description :deep(ol li) {
  list-style-type: decimal;
}

.event-description :deep(ul ul),
.event-description :deep(ol ol),
.event-description :deep(ul ol),
.event-description :deep(ol ul) {
  margin: 8px 0;
}

.event-description :deep(strong) {
  font-weight: 600;
  color: #000;
}

.event-description :deep(em) {
  font-style: italic;
}

/* Links */
.event-description :deep(a) {
  color: #1976d2;
  text-decoration: none;
  font-weight: 500;
  transition: color 0.2s ease;
}

.event-description :deep(a:hover) {
  color: #1565c0;
  text-decoration: underline;
}

.event-description :deep(blockquote) {
  border-left: 4px solid #1976d2;
  padding-left: 16px;
  margin: 20px 0;
  font-style: italic;
  color: #555;
  background-color: #f5f9fc;
  padding: 16px;
  border-radius: 4px;
}

.event-description :deep(code) {
  background-color: #f5f5f5;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Courier New', Consolas, monospace;
  font-size: 14px;
  color: #c7254e;
}

.event-description :deep(pre) {
  background-color: #f5f5f5;
  padding: 16px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 16px 0;
}

.event-description :deep(pre code) {
  background: none;
  padding: 0;
  color: #333;
}

.event-description :deep(hr) {
  border: none;
  border-top: 2px solid #e0e0e0;
  margin: 32px 0;
}

.event-description :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 20px 0;
}

.event-description :deep(th),
.event-description :deep(td) {
  border: 1px solid #ddd;
  padding: 12px;
  text-align: left;
}

.event-description :deep(th) {
  background-color: #f5f5f5;
  font-weight: 600;
}

.event-description :deep(tr:hover) {
  background-color: #fafafa;
}

.event-description :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: 8px;
  margin: 16px 0;
}

@media (max-width: 960px) {
  .event-description {
    font-size: 15px;
  }
  
  .event-description :deep(h1) {
    font-size: 24px;
  }
  
  .event-description :deep(h2) {
    font-size: 20px;
  }
  
  .event-description :deep(h3) {
    font-size: 18px;
  }
  
  .event-description :deep(p:first-of-type) {
    font-size: 16px;
  }
}
</style>