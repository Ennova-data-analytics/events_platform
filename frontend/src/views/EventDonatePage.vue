<template>
  <!--
    The page behind a charity event's donation QR code: whoever scans it goes
    straight to paying a donation, with no account, no login and no ticket.
  -->
  <div class="donate-page d-flex justify-center">
    <v-container class="py-6 py-md-12">
      <v-row justify="center">
        <v-col cols="12" sm="10" md="7" lg="5">
          <div v-if="loading" class="text-center mt-16">
            <v-progress-circular indeterminate color="pink-darken-1" size="64" />
          </div>

          <!-- Unknown or unpublished event -->
          <v-card v-else-if="loadError" class="donate-card pa-8" flat rounded="xl" data-test="donate-load-error">
            <div class="text-center">
              <v-icon size="64" color="error" class="mb-4">mdi-alert-circle-outline</v-icon>
              <p class="donate-subtitle mb-6">{{ loadError }}</p>
              <v-btn color="primary" variant="flat" to="/">Go to homepage</v-btn>
            </div>
          </v-card>

          <!-- Not a charity event -->
          <v-card v-else-if="!event.is_charitable" class="donate-card pa-8" flat rounded="xl" data-test="donate-not-charitable">
            <div class="text-center">
              <v-icon size="64" color="grey" class="mb-4">mdi-hand-heart-outline</v-icon>
              <h1 class="donate-title mb-2">Donations aren't open</h1>
              <p class="donate-subtitle mb-6">{{ event.event_name }} isn't taking donations.</p>
              <v-btn color="primary" variant="flat" :to="`/event/${eventId}`">View event</v-btn>
            </div>
          </v-card>

          <!-- Back from a paid checkout -->
          <v-card v-else-if="outcome === 'success'" class="donate-card pa-8" flat rounded="xl" data-test="donate-thanks">
            <div class="text-center">
              <v-icon size="64" color="pink-darken-1" class="mb-4">mdi-heart</v-icon>
              <h1 class="donate-title mb-2">Thank you!</h1>
              <p class="donate-subtitle mb-6">
                Your donation to {{ charityLabel }} was received. A confirmation email is on its way.
              </p>
              <div class="d-flex flex-column ga-3">
                <v-btn color="pink-darken-1" variant="flat" size="large" data-test="donate-again" @click="donateAgain">
                  Make another donation
                </v-btn>
                <v-btn variant="text" :to="`/event/${eventId}`">View event</v-btn>
              </div>
            </div>
          </v-card>

          <!-- The donation form -->
          <v-card v-else class="donate-card pa-6 pa-md-10" flat rounded="xl">
            <div class="mb-5">
              <div class="text-overline text-pink-darken-1" data-test="donate-event-name">{{ event.event_name }}</div>
              <div v-if="eventDate" class="donate-subtitle">{{ eventDate }}</div>
            </div>

            <v-alert
              v-if="outcome === 'cancelled'" type="info" variant="tonal" density="compact" class="mb-4"
              closable data-test="donate-cancelled" @click:close="outcome = null"
            >
              Donation cancelled. You have not been charged.
            </v-alert>

            <v-alert
              v-if="errorMessage" type="error" variant="tonal" density="compact" class="mb-4"
              closable data-test="donate-error" @click:close="errorMessage = ''"
            >
              {{ errorMessage }}
            </v-alert>

            <CharityDonationCard
              v-model="amount"
              donation-only
              :charity-name="event.charity_name"
              :charity-description="event.charity_description"
              class="mb-5"
              @update:valid="isAmountValid = $event"
            />

            <v-text-field
              v-model="email"
              label="Your email"
              type="email"
              inputmode="email"
              autocomplete="email"
              placeholder="you@example.com"
              variant="outlined"
              hint="We'll send your donation receipt here."
              persistent-hint
              :error-messages="emailError"
              class="mb-5"
              data-test="donate-email"
              @blur="emailTouched = true"
            />

            <v-btn
              block
              size="x-large"
              color="pink-darken-1"
              variant="flat"
              prepend-icon="mdi-hand-heart"
              :loading="submitting"
              :disabled="!canSubmit"
              data-test="donate-submit"
              @click="submit"
            >
              Donate €{{ amount.toFixed(2) }}
            </v-btn>
            <div class="text-caption text-center text-grey-darken-1 mt-3">
              <v-icon size="14">mdi-lock</v-icon>
              Secure card payment by Stripe. No account needed.
            </div>
          </v-card>
        </v-col>
      </v-row>
    </v-container>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { EventService } from '@/services/EventService.js';
import { useAuthStore } from '@/stores/auth.store.js';
import CharityDonationCard from '@/components/events/CharityDonationCard.vue';
import { goToExternalUrl } from '@/utils/navigation.js';

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

const eventId = route.params.id;
const event = ref(null);
const loading = ref(true);
const loadError = ref('');

// Stripe sends the donor back here with ?donation=success|cancelled.
const outcome = ref(route.query.donation || null);

const amount = ref(0);
const isAmountValid = ref(true);
const email = ref(authStore.user?.email || '');
const emailTouched = ref(false);
const submitting = ref(false);
const errorMessage = ref('');

const charityLabel = computed(() => event.value?.charity_name || 'charity');

const eventDate = computed(() => {
  if (!event.value?.event_date_start) return '';
  return new Date(event.value.event_date_start).toLocaleDateString('en-GB', {
    weekday: 'long', day: 'numeric', month: 'long', year: 'numeric',
  });
});

const isEmailValid = computed(() => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.value.trim()));
const emailError = computed(() => (emailTouched.value && !isEmailValid.value ? 'Enter a valid email address.' : ''));
const canSubmit = computed(() => isAmountValid.value && amount.value > 0 && isEmailValid.value);

onMounted(async () => {
  // Drop ?donation= so a refresh or a shared screenshot of the URL doesn't
  // replay the thank-you or the cancelled notice.
  if (route.query.donation) router.replace({ query: {} });

  try {
    const response = await EventService.getEventById(eventId);
    event.value = response.data;
  } catch (error) {
    console.error('Failed to load event for donation page:', error);
    loadError.value = error.response?.status === 404
      ? "We couldn't find this event. The link may be wrong or the event may have been taken down."
      : "We couldn't load this page. Check your connection and try again.";
  } finally {
    loading.value = false;
  }
});

async function submit() {
  emailTouched.value = true;
  if (!canSubmit.value) return;

  submitting.value = true;
  errorMessage.value = '';
  try {
    const response = await EventService.donateToEvent(eventId, {
      email: email.value.trim(),
      amountEuros: amount.value,
    });
    goToExternalUrl(response.data.checkout_url);
  } catch (error) {
    console.error('Failed to start donation:', error);
    const detail = error.response?.data?.detail;
    errorMessage.value = typeof detail === 'string'
      ? detail
      : 'Could not start the donation. You have not been charged - please try again.';
    submitting.value = false;
  }
}

function donateAgain() {
  outcome.value = null;
  errorMessage.value = '';
}
</script>

<style scoped>
.donate-page {
  background-color: #F8F9FA;
  min-height: 100vh;
}

.donate-card {
  background-color: #FFFFFF !important;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.05) !important;
}

.donate-title {
  color: #001529;
  font-weight: 800;
  font-size: 2rem;
  letter-spacing: -0.02em;
}

.donate-subtitle {
  color: #6B7280;
  font-size: 1rem;
}
</style>
