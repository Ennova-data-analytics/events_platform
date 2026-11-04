<template>
  <div class="claim-page d-flex align-center justify-center">
    <v-container>
      <v-row justify="center">
        <v-col cols="12" sm="10" md="8" lg="5">
          <div v-if="loading" class="text-center mt-16">
            <v-progress-circular indeterminate color="primary" size="64" />
          </div>

          <!-- Bad or replaced link -->
          <v-card v-else-if="loadError" class="ennova-card pa-8" flat rounded="xl" data-test="claim-load-error">
            <div class="text-center">
              <v-icon size="64" color="error" class="mb-4">mdi-ticket-confirmation-outline</v-icon>
              <p class="form-subtitle mb-6">{{ loadError }}</p>
              <v-btn color="primary" variant="flat" to="/">Go to homepage</v-btn>
            </div>
          </v-card>

          <!-- Done -->
          <v-card v-else-if="claimed" class="ennova-card pa-8" flat rounded="xl" data-test="claim-done">
            <div class="text-center">
              <v-icon size="64" color="success" class="mb-4">mdi-check-circle</v-icon>
              <h1 class="form-title mb-2">{{ COPY.claimedHeadline }}</h1>
              <p class="form-subtitle mb-6">{{ COPY.claimedSubtitle(preview.event_name) }}</p>
              <v-btn
                color="primary" variant="flat" size="large"
                :to="registrationId ? `/event/${eventId}/ticket/${registrationId}` : `/event/${eventId}`"
              >
                {{ registrationId ? 'View my ticket' : 'View event' }}
              </v-btn>
            </div>
          </v-card>

          <!-- Not available (buyer hasn't paid, or their ticket was cancelled) -->
          <v-card v-else-if="preview.status === 'unavailable'" class="ennova-card pa-8" flat rounded="xl" data-test="claim-unavailable">
            <div class="text-center">
              <v-icon size="64" color="grey" class="mb-4">mdi-ticket-outline</v-icon>
              <h1 class="form-title mb-2">{{ COPY.unavailableHeadline }}</h1>
              <p class="form-subtitle mb-6">{{ COPY.unavailableSubtitle(preview.buyer_name) }}</p>
            </div>
          </v-card>

          <!-- Claim -->
          <v-card v-else class="ennova-card pa-8 pa-md-12" flat rounded="xl">
            <div class="mb-6">
              <v-icon size="48" color="primary" class="mb-3">mdi-account-heart</v-icon>
              <h1 class="form-title mb-1" data-test="claim-headline">{{ COPY.claimHeadline(preview.buyer_name) }}</h1>
              <p class="form-subtitle">{{ COPY.claimSubtitle(preview.event_name) }}</p>
            </div>

            <v-alert
              v-if="errorMessage" type="error" variant="tonal" density="compact" class="mb-4"
              closable data-test="claim-error" @click:close="errorMessage = ''"
            >
              {{ errorMessage }}
            </v-alert>

            <!-- Logged in with the right email -->
            <div v-if="authStore.isAuthenticated && isInvitedAccount" class="mb-2">
              <v-alert type="info" variant="tonal" density="compact">
                Getting your ticket as <strong>{{ authStore.user?.email }}</strong>
              </v-alert>
            </div>

            <!-- Logged in as someone else -->
            <div v-else-if="authStore.isAuthenticated" data-test="claim-wrong-account">
              <v-alert type="warning" variant="tonal" density="compact" class="mb-4">
                You're logged in as <strong>{{ authStore.user?.email }}</strong>, but this ticket is for
                <strong>{{ preview.friend_email }}</strong>. Log out, then open the link from your email again.
              </v-alert>
              <v-btn variant="tonal" block @click="authStore.logout()">Log out</v-btn>
            </div>

            <!-- Not logged in -->
            <div v-else>
              <p class="text-body-2 mb-4">{{ COPY.claimEmailNote(preview.friend_email) }}</p>
              <v-tabs v-model="authTab" color="primary" class="mb-6">
                <v-tab value="register" data-test="tab-register">Create account</v-tab>
                <v-tab value="login" data-test="tab-login">I have an account</v-tab>
              </v-tabs>

              <v-text-field :model-value="preview.friend_email" label="Email" variant="outlined" readonly class="mb-2" />
              <v-text-field
                v-if="authTab === 'register'"
                v-model="fullName" label="Full name" variant="outlined" class="mb-2" data-test="claim-full-name"
              />
              <v-text-field
                v-model="password" label="Password" type="password" variant="outlined" class="mb-2"
                :placeholder="authTab === 'register' ? 'Minimum 6 characters' : ''"
                data-test="claim-password"
              />
              <v-text-field
                v-if="authTab === 'register'"
                v-model="confirmPassword" label="Confirm password" type="password" variant="outlined" class="mb-2"
                data-test="claim-confirm-password"
              />
            </div>

            <v-btn
              v-if="!authStore.isAuthenticated || isInvitedAccount"
              color="primary" variant="flat" block size="x-large" class="mt-4"
              :loading="submitting" data-test="claim-button" @click="claim"
            >
              {{ COPY.claimButton }}
            </v-btn>
          </v-card>
        </v-col>
      </v-row>
    </v-container>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import { useAuthStore } from '@/stores/auth.store.js';
import { EventService } from '@/services/EventService.js';
import { AuthService } from '@/services/AuthService.js';
import { BRING_A_FRIEND as COPY } from '@/content/bringAFriend.js';
import { apiErrorMessage } from '@/utils/friendTickets.js';

const route = useRoute();
const authStore = useAuthStore();
const eventId = route.params.id;
const token = route.query.token;

const loading = ref(true);
const loadError = ref('');
const preview = ref(null);
const claimed = ref(false);
const registrationId = ref(null);
const submitting = ref(false);
const errorMessage = ref('');
const authTab = ref('register');
const fullName = ref('');
const password = ref('');
const confirmPassword = ref('');

const isInvitedAccount = computed(() =>
  (authStore.user?.email || '').toLowerCase() === (preview.value?.friend_email || '').toLowerCase()
);

onMounted(async () => {
  if (!token) {
    loadError.value = 'This link is missing its code. Open it again from your email.';
    loading.value = false;
    return;
  }
  try {
    const response = await EventService.getFriendTicketPreview(eventId, token);
    preview.value = response.data;
    claimed.value = response.data.status === 'claimed';
  } catch (error) {
    console.error('Failed to load the friend ticket link', error);
    loadError.value = apiErrorMessage(error, "We couldn't open this link. Please try again.");
  } finally {
    loading.value = false;
  }
});

async function signIn() {
  const email = preview.value.friend_email;
  if (authTab.value === 'register') {
    if (password.value.length < 6) throw new Error('Your password needs at least 6 characters.');
    if (password.value !== confirmPassword.value) throw new Error("The passwords don't match.");
    await AuthService.register({ email, full_name: fullName.value.trim() || null, password: password.value });
  }
  try {
    const response = await AuthService.login({ email, password: password.value });
    authStore.setAuthFromResponse(response.data.access_token, response.data.user);
  } catch (error) {
    if (error?.response?.status === 401) {
      throw new Error(
        authTab.value === 'login'
          ? 'Wrong password, or there is no account for this email yet. Try "Create account".'
          : 'Your account was created, but we couldn\'t log you in. Try "I have an account".'
      );
    }
    throw error;
  }
}

async function claim() {
  errorMessage.value = '';
  submitting.value = true;
  try {
    if (!authStore.isAuthenticated) await signIn();
    const response = await EventService.claimFriendTicket(eventId, token);
    registrationId.value = response.data.registration_id;
    claimed.value = true;
    await authStore.fetchCurrentUser();
  } catch (error) {
    console.error('Failed to claim the friend ticket', error);
    errorMessage.value = error?.response
      ? apiErrorMessage(error, 'Something went wrong. Please try again.')
      : error.message;
  } finally {
    submitting.value = false;
  }
}
</script>

<style scoped>
.claim-page {
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
</style>
