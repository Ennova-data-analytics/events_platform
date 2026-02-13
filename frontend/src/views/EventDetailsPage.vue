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
                <v-progress-circular indeterminate color="grey-lighten-4" size="64"></v-progress-circular>
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
          <h1 :class="$vuetify.display.mobile ? 'text-h4 font-weight-bold mt-4' : 'text-h3 font-weight-bold'">
            {{ eventStore.currentEvent.event_name }}
          </h1>
          
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

          <div v-if="hasTicketTypes && registrationStatus === 'not_registered'" class="mt-6 mb-2">
            <h3 class="text-subtitle-1 font-weight-bold text-grey-darken-1 mb-2">Available Tickets</h3>
            <v-card 
              v-for="ticket in eventStore.currentEvent.ticket_types" 
              :key="ticket.ticket_type_id"
              variant="outlined"
              class="mb-2 px-3 py-2 bg-grey-lighten-5 border-thin"
              elevation="0"
            >
              <div class="d-flex justify-space-between align-center">
                <div>
                  <div class="font-weight-medium text-body-2">{{ ticket.name }}</div>
                  <div class="text-caption text-grey">{{ ticket.description }}</div>
                </div>
                <div class="text-body-1 font-weight-bold text-primary">
                  {{ formatPrice(ticket.price_euros) }}
                </div>
              </div>
            </v-card>
          </div>

          <div :class="$vuetify.display.mobile ? 'mt-4' : 'mt-6'">
            <v-btn v-if="!authStore.isAuthenticated" color="primary" :size="$vuetify.display.mobile ? 'default' : 'large'" block @click="goToRegistrationPage">
              Register / Apply
            </v-btn>

            <v-chip v-else-if="registrationStatus === 'Pending Approval'" color="info" variant="tonal" size="large" block>
              <v-icon start>mdi-clock-outline</v-icon>
              Application Pending Review
            </v-chip>

            <v-btn v-else-if="registrationStatus === 'Approved' && eventStore.currentEvent.price_euros > 0" color="warning" size="large" block @click="handlePayment">
              <v-icon start>mdi-credit-card-outline</v-icon>
              Pay Now to Confirm Spot
            </v-btn>

            <v-chip v-else-if="registrationStatus === 'Approved' || registrationStatus === 'Paid'" color="success" variant="tonal" size="large" block>
              <v-icon start>mdi-check-circle</v-icon>
              Registered & Confirmed
            </v-chip>

            <v-chip v-else-if="registrationStatus === 'Rejected'" color="error" variant="tonal" size="large" block>
              <v-icon start>mdi-close-circle</v-icon>
              Application Not Approved
            </v-chip>

            <v-chip v-else-if="!eventStore.currentEvent.signups_enabled" color="warning" variant="tonal" size="large" block>
              <v-icon start>mdi-close-circle-outline</v-icon>
              Signups Closed
            </v-chip>

            <v-btn
              v-else-if="registrationStatus === 'not_registered'"
              color="primary"
              :size="$vuetify.display.mobile ? 'default' : 'large'"
              block
              @click="goToRegistrationPage"
              elevation="3"
            >
              <template v-if="hasTicketTypes">
                <v-icon start>mdi-ticket-account</v-icon>
                Get Tickets
              </template>

              <template v-else-if="!eventStore.currentEvent.requires_approval && eventStore.currentEvent.price_euros > 0">
                <v-icon start>mdi-credit-card-outline</v-icon>
                Register & Pay ({{ formatPrice(eventStore.currentEvent.price_euros) }})
              </template>

              <template v-else>
                Apply to Register ({{ formatPrice(eventStore.currentEvent.price_euros) }})
              </template>
            </v-btn>
          </div>

          <div v-if="registrationStatus === 'Approved' || registrationStatus === 'Paid'" class="mt-4">
            <v-menu>
              <template v-slot:activator="{ props }">
                <v-btn
                  v-bind="props"
                  color="secondary"
                  variant="outlined"
                  size="large"
                  block
                >
                  <v-icon start>mdi-calendar-plus</v-icon>
                  Add to Calendar
                </v-btn>
              </template>
              <v-list>
                <v-list-item @click="addToGoogleCalendar">
                  <template v-slot:prepend>
                    <v-icon color="primary">mdi-google</v-icon>
                  </template>
                  <v-list-item-title>Google Calendar</v-list-item-title>
                </v-list-item>

                <v-list-item @click="downloadIcsFile">
                  <template v-slot:prepend>
                    <v-icon color="secondary">mdi-download</v-icon>
                  </template>
                  <v-list-item-title>Download .ics file</v-list-item-title>
                  <v-list-item-subtitle class="text-caption">
                    For Apple Calendar, Outlook, etc.
                  </v-list-item-subtitle>
                </v-list-item>
              </v-list>
            </v-menu>
          </div>

          <v-alert
            v-if="registrationStatus === 'not_registered' && eventStore.currentEvent.signups_enabled && authStore.isAuthenticated"
            type="info"
            variant="tonal"
            density="compact"
            class="mt-3"
          >
            <template v-if="eventStore.currentEvent.requires_approval">
              <v-icon size="small" start>mdi-information</v-icon>
              <span>Approvals Required: Your spot is not confirmed until the organizer reviews your application.</span>
            </template>
            <template v-else-if="hasTicketTypes">
              <v-icon size="small" start>mdi-flash</v-icon>
              <span>Select a ticket type to secure your spot.</span>
            </template>
            <template v-else>
               <v-icon size="small" start>mdi-flash</v-icon>
               <span>Register now to secure your spot!</span>
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
            <div class="event-description" v-html="parsedDescription"></div>
          </v-card>
        </v-col>
      </v-row>

      <v-row class="mt-8">
        <v-col cols="12">
          <EventLocationMap
            v-if="eventStore.currentEvent?.location"
            :display-location="eventStore.currentEvent.location"
            :map-address="eventStore.currentEvent.map_address"
            :latitude="eventStore.currentEvent.latitude"
            :longitude="eventStore.currentEvent.longitude"
          />
        </v-col>
      </v-row>

      <SponsorLogos v-if="eventStore.currentEvent?.sponsor_logos" :logos="eventStore.currentEvent.sponsor_logos" />
      <EventPhotos v-if="eventStore.currentEvent?.event_photos?.length > 0" :photos="eventStore.currentEvent.event_photos" />

      <v-row v-if="eventStore.currentEvent?.attachments?.length > 0 && (registrationStatus === 'Approved' || registrationStatus === 'Paid')" class="mt-8">
        <v-col cols="12">
          <v-card elevation="2" class="pa-6">
            <h2 class="text-h5 font-weight-bold mb-4">
              <v-icon start color="primary">mdi-paperclip</v-icon>
              Downloads & Resources
            </h2>
            <v-divider class="mb-4"></v-divider>
            <v-list lines="two">
              <v-list-item
                v-for="attachment in eventStore.currentEvent.attachments"
                :key="attachment.attachment_id"
                :href="attachment.file_url"
                target="_blank"
                class="attachment-item rounded mb-2"
                border
              >
                <template v-slot:prepend>
                  <v-avatar :color="getFileColor(attachment.file_type)" variant="tonal">
                    <v-icon :icon="getFileIcon(attachment.file_type)" size="large"></v-icon>
                  </v-avatar>
                </template>
                <v-list-item-title class="font-weight-medium">{{ attachment.file_name }}</v-list-item-title>
                <v-list-item-subtitle class="text-caption mt-1">
                  {{ formatFileSize(attachment.file_size_bytes) }} • Uploaded {{ formatDate(attachment.uploaded_at) }}
                </v-list-item-subtitle>
                <template v-slot:append>
                  <v-btn icon="mdi-download" variant="text" color="primary"></v-btn>
                </template>
              </v-list-item>
            </v-list>
          </v-card>
        </v-col>
      </v-row>
    </div>

  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useEventStore } from '@/stores/events.store.js';
import { useAuthStore } from '@/stores/auth.store.js';
import ApiClient from '@/services/ApiClient.js';
import { marked } from 'marked';
import DOMPurify from 'dompurify';
import SponsorLogos from '@/components/events/SponsorLogos.vue';
import EventPhotos from '@/components/events/EventPhotos.vue';
import EventLocationMap from '@/components/events/EventLocationMap.vue';
import { generateGoogleCalendarUrl, downloadIcsFile as downloadIcs } from '@/utils/calendarHelpers.js';

// --- Markdown Config ---
marked.setOptions({ breaks: true, gfm: true, headerIds: false });

// --- State ---
const route = useRoute();
const router = useRouter();
const eventStore = useEventStore();
const authStore = useAuthStore();

const showSuccess = ref(false);
const successMessage = ref('');
const showError = ref(false);
const isSubmitting = ref(false);

// --- Computed Properties ---

const parsedDescription = computed(() => {
  if (!eventStore.currentEvent?.description) return '';
  return DOMPurify.sanitize(marked.parse(eventStore.currentEvent.description));
});

const registrationStatus = computed(() => {
  if (!authStore.user || !eventStore.currentEvent) return 'loading';
  const registration = authStore.user.registrations?.find(
    reg => reg.event.event_id === eventStore.currentEvent.event_id
  );
  return registration ? registration.status : 'not_registered';
});

// UX Helper: Check if tickets exist
const hasTicketTypes = computed(() => {
  return eventStore.currentEvent?.ticket_types?.length > 0;
});

// --- Lifecycle ---

onMounted(async () => {
  const eventId = route.params.id;
  await eventStore.fetchEventById(eventId);

  if (authStore.isAuthenticated) {
    await authStore.fetchCurrentUser();
  }

  await handleUrlParams();
});

// --- Methods ---

function goToRegistrationPage() {
  const query = route.query.ref ? { ref: route.query.ref } : undefined;
  router.push({ name: 'event-register', params: { id: route.params.id }, query });
}

function formatPrice(price) {
  const num = parseFloat(price);
  return num > 0 ? `€${num.toFixed(2)}` : 'Free';
}

async function handleUrlParams() {
  const urlParams = new URLSearchParams(window.location.search);
  const paymentStatus = urlParams.get('payment');
  console.log('[EventDetails] handleUrlParams called, payment =', paymentStatus, 'url =', window.location.href);

  if (paymentStatus === 'success') {
    showSuccess.value = true;
    successMessage.value = 'Payment successful! Your registration is confirmed.';
    window.history.replaceState({}, '', window.location.pathname);


    for (let attempt = 0; attempt < 5; attempt++) {
      await new Promise(resolve => setTimeout(resolve, 1500));
      await authStore.fetchCurrentUser();
      const registration = authStore.user?.registrations?.find(
        reg => reg.event.event_id === eventStore.currentEvent?.event_id
      );
      if (registration?.status === 'Paid') break;
    }
  } else if (paymentStatus === 'cancelled') {
    showError.value = true;
    eventStore.error = 'Payment was cancelled. Please try again when ready.';
    window.history.replaceState({}, '', window.location.pathname);
  }
}

async function handlePayment() {
  isSubmitting.value = true;
  try {
    const registration = authStore.user.registrations.find(
      r => r.event.event_id === eventStore.currentEvent.event_id && r.status === 'Approved'
    );
    if (!registration) {
        throw new Error('Registration not found');
    }

    const response = await ApiClient.post(
      `/payments/registrations/${registration.registration_id}/create-checkout-session`
    );

    if (response.data.checkout_url) {
      window.location.href = response.data.checkout_url;
    }
  } catch (error) {
    eventStore.error = 'Failed to initiate payment.';
    showError.value = true;
  } finally {
    isSubmitting.value = false;
  }
}

// Helper functions for assets
function getFileIcon(fileType) {
  const map = { pdf: 'mdi-file-pdf-box', doc: 'mdi-file-word', docx: 'mdi-file-word', jpg: 'mdi-file-image', png: 'mdi-file-image' };
  return map[fileType?.toLowerCase()] || 'mdi-file';
}
function getFileColor(fileType) {
  const map = { pdf: 'red', doc: 'blue', docx: 'blue', jpg: 'teal', png: 'teal' };
  return map[fileType?.toLowerCase()] || 'grey';
}
function formatFileSize(bytes) {
  if (!bytes) return '';
  const units = ['B', 'KB', 'MB', 'GB'];
  let size = bytes;
  let i = 0;
  while (size >= 1024 && i < units.length - 1) { size /= 1024; i++; }
  return `${size.toFixed(1)} ${units[i]}`;
}
function formatDate(date) { return new Date(date).toLocaleDateString(); }

// Calendar Integration Methods
function addToGoogleCalendar() {
  if (!eventStore.currentEvent) return;
  const googleCalUrl = generateGoogleCalendarUrl(eventStore.currentEvent);
  window.open(googleCalUrl, '_blank');
}

async function downloadIcsFile() {
  if (!eventStore.currentEvent) return;

  try {
    await downloadIcs(eventStore.currentEvent.event_id);
    successMessage.value = 'Calendar file downloaded successfully!';
    showSuccess.value = true;
  } catch (error) {
    eventStore.error = 'Failed to download calendar file. Please try again.';
    showError.value = true;
  }
}
</script>

<style scoped>
.attachment-item {
  transition: all 0.2s ease;
  cursor: pointer;
}
.attachment-item:hover {
  background-color: rgba(25, 118, 210, 0.04);
  transform: translateX(4px);
}
.event-description {
  font-size: 16px;
  line-height: 1.8;
  color: #2c3e50;
  max-width: 100%;
  overflow-wrap: break-word;
}
/* Basic Markdown Styling */
.event-description :deep(h1) { font-size: 28px; margin-top: 24px; }
.event-description :deep(p) { margin-bottom: 16px; }
.event-description :deep(img) { max-width: 100%; height: auto; border-radius: 8px; margin: 16px 0; }
.event-description :deep(a) { color: #1976d2; text-decoration: none; }
.event-description :deep(a:hover) { text-decoration: underline; }
</style>