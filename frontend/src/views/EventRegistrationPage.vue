<template>
  <div class="registration-page d-flex align-center justify-center">
    <v-container>
      <v-row justify="center">
        <v-col cols="12" sm="10" md="8" lg="6">

          <!-- Loading State -->
          <div v-if="isLoadingEvent" class="text-center mt-16">
            <v-progress-circular indeterminate color="primary" size="64"></v-progress-circular>
            <p class="mt-4">Loading...</p>
          </div>

          <!-- Error State -->
          <v-alert v-else-if="loadError" type="error" class="mt-4">
            {{ loadError }}
            <template v-slot:append>
              <v-btn variant="text" :to="`/event/${route.params.id}`">Back to Event</v-btn>
            </template>
          </v-alert>

          <!-- Already Registered -->
          <v-card v-else-if="isAlreadyRegistered" class="ennova-card pa-8 pa-md-12" flat rounded="xl">
            <div class="text-center">
              <v-icon size="64" color="success" class="mb-4">mdi-check-circle</v-icon>
              <h2 class="form-title mb-2">Already Registered</h2>
              <p class="form-subtitle mb-6">You are already registered for this event.</p>
              <v-btn color="primary" variant="flat" :to="`/event/${event.event_id}`">
                Back to Event
              </v-btn>
            </div>
          </v-card>

          <!-- Registration Form -->
          <v-card v-else-if="event" class="ennova-card pa-8 pa-md-12" flat rounded="xl">
            <!-- Header -->
            <div class="mb-6">
              <v-btn variant="text" size="small" :to="`/event/${event.event_id}`" class="mb-4 px-0">
                <v-icon start>mdi-arrow-left</v-icon>
                Back to event
              </v-btn>
              <h1 class="form-title mb-1">{{ event.event_name }}</h1>
              <p class="form-subtitle">
                <v-icon size="small">mdi-calendar</v-icon>
                {{ new Date(event.event_date_start).toLocaleDateString('en-GB') }}
                &nbsp;&bull;&nbsp;
                <v-icon size="small">mdi-map-marker</v-icon>
                {{ event.location }}
              </p>
            </div>

            <v-alert v-if="errorMessage" type="error" variant="tonal" density="compact" class="mb-4" closable @click:close="errorMessage = ''">
              {{ errorMessage }}
            </v-alert>

            <!-- Account Details (Guest Only) -->
            <div v-if="!authStore.isAuthenticated">
              <h3 class="text-subtitle-1 font-weight-bold mb-3">Account Details</h3>

              <v-text-field
                v-model="userForm.full_name"
                label="Full Name"
                placeholder="John Doe"
                variant="outlined"
                class="mb-2"
              ></v-text-field>

              <v-text-field
                v-model="userForm.email"
                label="Email"
                placeholder="john.doe@esade.edu"
                type="email"
                variant="outlined"
                class="mb-2"
              ></v-text-field>

              <v-row>
                <v-col cols="6" class="py-0">
                  <v-text-field
                    v-model="userForm.degree"
                    label="Degree"
                    placeholder="BBA"
                    variant="outlined"
                    class="mb-2"
                  ></v-text-field>
                </v-col>
                <v-col cols="6" class="py-0">
                  <v-text-field
                    v-model="userForm.study_year"
                    label="Years of Study"
                    placeholder="1"
                    variant="outlined"
                    class="mb-2"
                  ></v-text-field>
                </v-col>
              </v-row>

              <v-text-field
                v-model="userForm.password"
                label="Password"
                type="password"
                placeholder="Minimum 6 characters"
                variant="outlined"
                class="mb-2"
              ></v-text-field>

              <v-text-field
                v-model="userForm.confirmPassword"
                label="Confirm Password"
                type="password"
                placeholder="Re-enter your password"
                variant="outlined"
                class="mb-4"
              ></v-text-field>

              <v-divider class="mb-4"></v-divider>
            </div>

            <!-- Event Registration Section -->
            <h3 class="text-subtitle-1 font-weight-bold mb-3">Event Registration</h3>

            <TicketTypeSelector
              v-if="hasTicketTypes"
              v-model="selectedTicketTypeId"
              :ticket-types="event.ticket_types"
              @ticket-type-selected="handleTicketTypeSelected"
              class="mb-6"
            />

            <TeamSelector
              v-if="selectedTicketType?.requires_team || (!hasTicketTypes && event.teams_enabled)"
              :event-id="event.event_id"
              :ticket-type-id="selectedTicketType?.ticket_type_id ?? null"
              :ticket-type-max-members="selectedTicketType?.team_max_members ?? null"
              :event-max-members="!hasTicketTypes && event.teams_enabled ? event.team_max_members : null"
              :group-payment-mode="selectedTicketType?.group_payment_mode ?? null"
              :group-size="selectedTicketType?.group_size ?? null"
              @update:teamSelection="handleTeamSelection"
              class="mb-6"
            />

            <v-form ref="customFormRef" v-if="customForm.fields.length > 0">
              <h3 class="text-subtitle-1 font-weight-bold mb-3">Additional Details</h3>
              <div v-for="field in customForm.fields" :key="field.name" class="mb-2">
                <v-text-field v-if="field.type === 'text'" v-model="formResponses[field.name]" :label="field.label" :required="field.required" variant="outlined"></v-text-field>
                <v-textarea v-if="field.type === 'textarea'" v-model="formResponses[field.name]" :label="field.label" :required="field.required" variant="outlined"></v-textarea>
                <v-select v-if="field.type === 'select'" v-model="formResponses[field.name]" :items="field.options" :label="field.label" :required="field.required" variant="outlined"></v-select>
                <v-radio-group v-if="field.type === 'radio'" v-model="formResponses[field.name]" :label="field.label" :required="field.required" inline>
                  <v-radio v-for="option in field.options" :key="option" :label="option" :value="option"></v-radio>
                </v-radio-group>
                <v-file-input v-if="field.type === 'file'" v-model="formFiles[field.name]" :label="field.label" :required="field.required" variant="outlined"></v-file-input>
                <v-checkbox v-if="field.type === 'checkbox'" v-model="formResponses[field.name]" :label="field.label" :required="field.required"></v-checkbox>
              </div>
            </v-form>

            <div class="mt-4">
              <DiscountCodeInput
                v-if="shouldShowDiscountInput"
                :event-id="event.event_id"
                @discount-applied="handleDiscountApplied"
                @discount-removed="handleDiscountRemoved"
              />
            </div>

            <!-- Login prompt for guests -->
            <div v-if="!authStore.isAuthenticated" class="text-center mt-4 mb-2">
              <span class="text-body-2 text-grey-darken-1">
                Already have an account?
                <router-link :to="{ path: '/login', query: { redirect: `/event/${event.event_id}/register` } }" class="auth-link font-weight-bold">
                  Log in
                </router-link>
              </span>
            </div>

            <!-- Submit Button -->
            <v-btn
              color="primary"
              variant="flat"
              block
              size="x-large"
              class="mt-4"
              :loading="isSubmitting"
              @click="submitRegistration"
            >
              {{ authStore.isAuthenticated ? 'Confirm Registration' : 'Create Account & Register' }}
            </v-btn>
          </v-card>

        </v-col>
      </v-row>
    </v-container>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useEventStore } from '@/stores/events.store.js';
import { useAuthStore } from '@/stores/auth.store.js';
import { AuthService } from '@/services/AuthService.js';
import { FormTemplateService } from '@/services/FormTemplateService.js';
import { UploadService } from '@/services/UploadService.js';
import { EventService } from '@/services/EventService.js';
import TicketTypeSelector from '@/components/events/TicketTypeSelector.vue';
import TeamSelector from '@/components/events/TeamSelector.vue';
import DiscountCodeInput from '@/components/DiscountCodeInput.vue';

const route = useRoute();
const router = useRouter();
const eventStore = useEventStore();
const authStore = useAuthStore();

// Event data
const event = ref(null);
const isLoadingEvent = ref(true);
const loadError = ref(null);

// Guest account fields
const userForm = ref({
  full_name: '',
  email: '',
  password: '',
  confirmPassword: '',
  degree: '',
  study_year: ''
});

// Event registration fields
const selectedTicketTypeId = ref(null);
const selectedTicketType = ref(null);
const teamSelection = ref(null);
const customForm = ref({ fields: [] });
const formResponses = ref({});
const formFiles = ref({});
const appliedDiscountCode = ref(null);
const referralCode = ref(null);

// UI state
const isSubmitting = ref(false);
const errorMessage = ref('');

// Computed
const hasTicketTypes = computed(() => event.value?.ticket_types?.length > 0);

const shouldShowDiscountInput = computed(() => {
  if (selectedTicketType.value) {
    // Leader-pays group tickets: no individual discount (fixed group price)
    if (selectedTicketType.value.group_payment_mode === 'leader') return false;
    if (parseFloat(selectedTicketType.value.price_euros) > 0) return true;
  }
  if (!hasTicketTypes.value && event.value?.price_euros > 0) return true;
  return false;
});

const registrationStatus = computed(() => {
  if (!authStore.user || !event.value) return 'not_registered';
  const registration = authStore.user.registrations?.find(
    reg => reg.event.event_id === event.value.event_id
  );
  return registration ? registration.status : 'not_registered';
});

const isAlreadyRegistered = computed(() => {
  return registrationStatus.value !== 'not_registered';
});

// Lifecycle
onMounted(async () => {
  const eventId = route.params.id;
  referralCode.value = route.query.ref || null;
  isLoadingEvent.value = true;
  try {
    await eventStore.fetchEventById(eventId);
    event.value = eventStore.currentEvent;

    if (!event.value) {
      loadError.value = 'Event not found.';
      return;
    }

    if (!event.value.signups_enabled) {
      loadError.value = 'Signups are currently closed for this event.';
      return;
    }

    if (authStore.isAuthenticated) {
      await authStore.fetchCurrentUser();
    }

    await loadInitialForm();
  } catch (e) {
    loadError.value = 'Failed to load event details.';
  } finally {
    isLoadingEvent.value = false;
  }
});

// Methods
async function loadInitialForm() {
  if (!event.value) return;

  if (event.value.form_template_id && !hasTicketTypes.value) {
    try {
      const response = await FormTemplateService.getTemplateById(event.value.form_template_id);
      customForm.value = response.data;
    } catch (e) {
      console.error(e);
      customForm.value = { fields: [] };
    }
  } else {
    customForm.value = { fields: [] };
  }
}

async function handleTicketTypeSelected(ticketType) {
  selectedTicketType.value = ticketType;
  selectedTicketTypeId.value = ticketType.ticket_type_id;
  teamSelection.value = null;

  if (ticketType?.form_template_id) {
    try {
      const response = await FormTemplateService.getTemplateById(ticketType.form_template_id);
      customForm.value = response.data;
      formResponses.value = {};
      formFiles.value = {};
    } catch (error) {
      console.error("Failed to load ticket form", error);
    }
  } else if (event.value?.form_template_id) {
    try {
      const response = await FormTemplateService.getTemplateById(event.value.form_template_id);
      customForm.value = response.data;
    } catch (e) { console.error(e); }
  } else {
    customForm.value = { fields: [] };
  }
}

function handleTeamSelection(selection) {
  teamSelection.value = selection;
}

function handleDiscountApplied(data) {
  appliedDiscountCode.value = data.code;
}

function handleDiscountRemoved() {
  appliedDiscountCode.value = null;
}

function validate() {
  errorMessage.value = '';

  // Guest account validation
  if (!authStore.isAuthenticated) {
    if (!userForm.value.email) {
      errorMessage.value = 'Email is required.';
      return false;
    }
    if (!userForm.value.password) {
      errorMessage.value = 'Password is required.';
      return false;
    }
    if (userForm.value.password.length < 6) {
      errorMessage.value = 'Password must be at least 6 characters.';
      return false;
    }
    if (userForm.value.password !== userForm.value.confirmPassword) {
      errorMessage.value = 'Passwords do not match.';
      return false;
    }
  }

  // Event field validation
  if (hasTicketTypes.value && !selectedTicketTypeId.value) {
    errorMessage.value = 'Please select a ticket type.';
    return false;
  }
  if (selectedTicketType.value?.requires_team && !teamSelection.value) {
    errorMessage.value = 'Please join or create a team for this ticket type.';
    return false;
  }
  for (const field of customForm.value.fields) {
    if (field.required) {
      const textResponse = formResponses.value[field.name];
      const fileResponse = formFiles.value[field.name];
      const isTextFilled = textResponse !== undefined && textResponse !== null && textResponse !== '';
      const isFileFilled = fileResponse !== undefined && fileResponse !== null;
      if (!isTextFilled && !isFileFilled) {
        errorMessage.value = `The field "${field.label}" is required.`;
        return false;
      }
    }
  }
  return true;
}

async function uploadFiles() {
  const fileResponses = {};
  for (const fieldName in formFiles.value) {
    const file = formFiles.value[fieldName];
    if (file) {
      const response = await UploadService.uploadFile(file);
      fileResponses[fieldName] = response.data.file_key;
    }
  }
  return fileResponses;
}

function hasFiles() {
  return Object.values(formFiles.value).some(f => f);
}

async function submitRegistration() {
  if (!validate()) return;

  isSubmitting.value = true;
  errorMessage.value = '';

  try {
    let result;

    if (authStore.isAuthenticated) {
      // Authenticated user flow — upload files first (user already has a token)
      const finalFormResponses = { ...formResponses.value, ...(await uploadFiles()) };

      const registrationData = {
        form_responses: finalFormResponses,
        discount_code: appliedDiscountCode.value,
        referral_code: referralCode.value,
        ticket_type_id: selectedTicketTypeId.value,
        team_selection: teamSelection.value
      };

      result = await eventStore.registerForEvent(event.value.event_id, registrationData);
    } else {
      // Guest flow: create account + register first, then upload files with the new token
      const payload = {
        email: userForm.value.email,
        full_name: userForm.value.full_name,
        password: userForm.value.password,
        degree: userForm.value.degree,
        study_year: userForm.value.study_year,
        ticket_type_id: selectedTicketTypeId.value,
        form_responses: { ...formResponses.value },
        discount_code: appliedDiscountCode.value,
        referral_code: referralCode.value,
        team_selection: teamSelection.value
      };

      const response = await AuthService.registerAndApply(event.value.event_id, payload);
      authStore.setAuthFromResponse(response.data.access_token, response.data.user);
      result = response.data;

      // Now authenticated — upload files and patch the registration
      if (hasFiles()) {
        const fileResponses = await uploadFiles();
        await EventService.updateRegistrationFormResponses(event.value.event_id, fileResponses);
      }
    }

    // Handle Stripe redirect if needed
    if (result.requires_immediate_payment && result.checkout_url) {
      window.location.href = result.checkout_url;
      return;
    }

    // Success - redirect to confirmation page
    await authStore.fetchCurrentUser();
    router.push({ name: 'event-registered', params: { id: event.value.event_id } });

  } catch (error) {
    console.error('Registration failed:', error);
    if (error.response?.data?.detail) {
      errorMessage.value = error.response.data.detail;
    } else {
      errorMessage.value = 'Something went wrong. Please try again.';
    }
  } finally {
    isSubmitting.value = false;
  }
}
</script>

<style scoped>
.registration-page {
  background-color: #F8F9FA;
  min-height: 100vh;
}

.ennova-card {
  background-color: #FFFFFF !important;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.05) !important;
}

.form-title {
  color: #001529;
  font-weight: 800;
  font-size: 2rem;
  letter-spacing: -0.02em;
}

.form-subtitle {
  color: #6B7280;
  font-size: 1rem;
}

.auth-link {
  color: #001529;
  text-decoration: none;
}

.auth-link:hover {
  text-decoration: underline;
}
</style>
