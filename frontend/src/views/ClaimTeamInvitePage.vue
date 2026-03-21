<template>
  <div class="claim-invite-page d-flex align-center justify-center">
    <v-container>
      <v-row justify="center">
        <v-col cols="12" sm="10" md="8" lg="5">

          <!-- Loading -->
          <div v-if="loading" class="text-center mt-16">
            <v-progress-circular indeterminate color="primary" size="64"></v-progress-circular>
            <p class="mt-4">Verifying your invite...</p>
          </div>

          <!-- Error -->
          <v-card v-else-if="error" class="ennova-card pa-8" flat rounded="xl">
            <div class="text-center">
              <v-icon size="64" color="error" class="mb-4">mdi-close-circle</v-icon>
              <h2 class="form-title mb-2">Invite Invalid</h2>
              <p class="form-subtitle mb-6">{{ error }}</p>
              <v-btn color="primary" variant="flat" to="/">Go to homepage</v-btn>
            </div>
          </v-card>

          <!-- Success (already claimed) -->
          <v-card v-else-if="claimed" class="ennova-card pa-8" flat rounded="xl">
            <div class="text-center">
              <v-icon size="64" color="success" class="mb-4">mdi-check-circle</v-icon>
              <h2 class="form-title mb-2">You're registered!</h2>
              <p class="form-subtitle mb-6">You've successfully joined the team and registered for <strong>{{ eventName }}</strong>.</p>
              <v-btn color="primary" variant="flat" :to="`/event/${eventId}`">View Event</v-btn>
            </div>
          </v-card>

          <!-- Invite claim form -->
          <v-card v-else-if="invite" class="ennova-card pa-8 pa-md-12" flat rounded="xl">
            <div class="mb-6">
              <v-icon size="48" color="primary" class="mb-3">mdi-account-group</v-icon>
              <h1 class="form-title mb-1">You're invited!</h1>
              <p class="form-subtitle">
                Join team <strong>{{ invite.team_name }}</strong> for <strong>{{ invite.event_name }}</strong>.
                Your spot has already been paid for.
              </p>
            </div>

            <v-alert type="success" variant="tonal" density="compact" class="mb-6">
              <v-icon start>mdi-ticket</v-icon>
              Your spot is <strong>free</strong> — the team lead has covered the cost for the whole group.
            </v-alert>

            <v-alert v-if="errorMessage" type="error" variant="tonal" density="compact" class="mb-4" closable @click:close="errorMessage = ''">
              {{ errorMessage }}
            </v-alert>

            <!-- Not logged in: show login/register choice -->
            <div v-if="!authStore.isAuthenticated">
              <v-tabs v-model="authTab" color="primary" class="mb-6">
                <v-tab value="login">I have an account</v-tab>
                <v-tab value="register">Create account</v-tab>
              </v-tabs>

              <v-tabs-window v-model="authTab">
                <!-- Login tab -->
                <v-tabs-window-item value="login">
                  <v-alert type="info" variant="tonal" density="compact" class="mb-4">
                    <v-icon start size="small">mdi-information</v-icon>
                    Log in with the account linked to <strong>{{ invite?.invited_email }}</strong>.
                    No account yet? Switch to <strong>Create account</strong>.
                  </v-alert>
                  <v-text-field
                    v-model="loginForm.email"
                    label="Email"
                    type="email"
                    variant="outlined"
                    class="mb-2"
                  ></v-text-field>
                  <v-text-field
                    v-model="loginForm.password"
                    label="Password"
                    type="password"
                    variant="outlined"
                    class="mb-4"
                  ></v-text-field>
                </v-tabs-window-item>

                <!-- Register tab -->
                <v-tabs-window-item value="register">
                  <v-text-field
                    v-model="registerForm.full_name"
                    label="Full Name"
                    variant="outlined"
                    class="mb-2"
                  ></v-text-field>
                  <v-text-field
                    v-model="registerForm.email"
                    label="Email"
                    type="email"
                    variant="outlined"
                    class="mb-2"
                    readonly
                    hint="This must match the email the invite was sent to"
                    persistent-hint
                  ></v-text-field>
                  <v-row>
                    <v-col cols="6" class="py-0">
                      <v-text-field
                        v-model="registerForm.degree"
                        label="Degree"
                        placeholder="BBA"
                        variant="outlined"
                        class="mb-2"
                      ></v-text-field>
                    </v-col>
                    <v-col cols="6" class="py-0">
                      <v-text-field
                        v-model="registerForm.study_year"
                        label="Year of Study"
                        placeholder="1"
                        variant="outlined"
                        class="mb-2"
                      ></v-text-field>
                    </v-col>
                  </v-row>
                  <v-text-field
                    v-model="registerForm.password"
                    label="Password"
                    type="password"
                    placeholder="Minimum 6 characters"
                    variant="outlined"
                    class="mb-2"
                  ></v-text-field>
                  <v-text-field
                    v-model="registerForm.confirmPassword"
                    label="Confirm Password"
                    type="password"
                    variant="outlined"
                    class="mb-4"
                  ></v-text-field>
                </v-tabs-window-item>
              </v-tabs-window>
            </div>

            <!-- Already logged in -->
            <div v-else class="mb-4">
              <v-alert type="info" variant="tonal" density="compact">
                <v-icon start>mdi-account</v-icon>
                Claiming invite as <strong>{{ authStore.user?.email }}</strong>
              </v-alert>
            </div>

            <v-btn
              color="primary"
              variant="flat"
              block
              size="x-large"
              class="mt-4"
              :loading="submitting"
              @click="claimInvite"
            >
              Claim My Spot
            </v-btn>
          </v-card>

        </v-col>
      </v-row>
    </v-container>

    <v-snackbar
      v-model="showSuccess"
      color="success"
      location="top"
      timeout="1800"
    >
      <v-icon start>mdi-check-circle</v-icon>
      <strong>Success!</strong> You've claimed your spot and joined the team.
    </v-snackbar>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { useAuthStore } from '@/stores/auth.store.js';
import { EventService } from '@/services/EventService.js';
import { AuthService } from '@/services/AuthService.js';

const route = useRoute();
const authStore = useAuthStore();

const eventId = route.params.id;
const token = route.query.token;

const loading = ref(true);
const error = ref(null);
const invite = ref(null);
const eventName = ref('');
const claimed = ref(false);
const submitting = ref(false);
const errorMessage = ref('');
const authTab = ref('login');
const showSuccess = ref(false);

const loginForm = ref({ email: '', password: '' });
const registerForm = ref({ full_name: '', email: '', password: '', confirmPassword: '', degree: '', study_year: '' });

onMounted(async () => {
  if (!token) {
    error.value = 'No invite token provided.';
    loading.value = false;
    return;
  }

  try {
    const response = await EventService.getTeamInvitePreview(eventId, token);
    invite.value = response.data;
    eventName.value = invite.value.event_name;

    // Pre-fill email fields with the invited email
    loginForm.value.email = invite.value.invited_email;
    registerForm.value.email = invite.value.invited_email;

    if (invite.value.claimed) {
      claimed.value = true;
    }
  } catch (e) {
    error.value = e.response?.data?.detail || 'This invite link is invalid or has already been used.';
  } finally {
    loading.value = false;
  }
});

async function claimInvite() {
  errorMessage.value = '';
  submitting.value = true;

  try {
    // If not authenticated, log in or register first
    if (!authStore.isAuthenticated) {
      if (authTab.value === 'login') {
        // login() expects a credentials object { email, password }
        const response = await AuthService.login({ email: loginForm.value.email, password: loginForm.value.password });
        authStore.setAuthFromResponse(response.data.access_token, response.data.user);
      } else {
        // Validate register form
        if (registerForm.value.password !== registerForm.value.confirmPassword) {
          errorMessage.value = 'Passwords do not match.';
          submitting.value = false;
          return;
        }
        if (registerForm.value.password.length < 6) {
          errorMessage.value = 'Password must be at least 6 characters.';
          submitting.value = false;
          return;
        }
        // Register creates the account, then login to get a token
        await AuthService.register({
          email: registerForm.value.email,
          full_name: registerForm.value.full_name,
          password: registerForm.value.password,
          degree: registerForm.value.degree,
          study_year: registerForm.value.study_year,
        });
        const loginResponse = await AuthService.login({ email: registerForm.value.email, password: registerForm.value.password });
        authStore.setAuthFromResponse(loginResponse.data.access_token, loginResponse.data.user);
      }
    }

    // Claim the invite — registers user for free and joins the team
    await EventService.claimTeamInvite(eventId, token);
    await authStore.fetchCurrentUser();

    // Show success snackbar then flip to success card
    showSuccess.value = true;
    setTimeout(() => {
      claimed.value = true;
    }, 1800);

  } catch (e) {
    if (e.response?.status === 401) {
      errorMessage.value = 'Incorrect password, or no account exists for this email. Try the "Create account" tab.';
    } else {
      errorMessage.value = e.response?.data?.detail || 'Failed to claim invite. Please try again.';
    }
  } finally {
    submitting.value = false;
  }
}
</script>

<style scoped>
.claim-invite-page {
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
