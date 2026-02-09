<template>
  <div class="forgot-page d-flex align-center justify-center">
    <v-container>
      <v-row justify="center">
        <v-col cols="12" sm="10" md="6" lg="5">

          <v-card class="ennova-card pa-8 pa-md-12" flat rounded="xl">
            <div class="text-center mb-8">
              <h1 class="form-title mb-2">Forgot Password</h1>
              <p class="form-subtitle">Enter your email and we'll send you a reset link.</p>
            </div>

            <v-alert v-if="successMessage" type="success" variant="tonal" density="compact" class="mb-6">
              {{ successMessage }}
            </v-alert>
            <v-alert v-if="errorMessage" type="error" variant="tonal" density="compact" class="mb-6">
              {{ errorMessage }}
            </v-alert>

            <v-form v-if="!successMessage" @submit.prevent="handleSubmit">
              <v-text-field
                v-model="email"
                label="Email Address"
                type="email"
                prepend-inner-icon="mdi-email-outline"
                variant="outlined"
                :rules="[rules.required, rules.email]"
                class="mb-2"
              ></v-text-field>
              <v-btn
                type="submit"
                block
                color="primary"
                size="large"
                :loading="isLoading"
                class="mt-2"
              >
                Send Reset Link
              </v-btn>
            </v-form>

            <div class="text-center mt-8">
              <p class="page-footer">
                Remember your password?
                <router-link to="/login" class="page-link">Log in</router-link>
              </p>
            </div>
          </v-card>

        </v-col>
      </v-row>
    </v-container>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { AuthService } from '@/services/AuthService';

const email = ref('');
const isLoading = ref(false);
const successMessage = ref('');
const errorMessage = ref('');

const rules = {
  required: value => !!value || 'Email is required',
  email: value => {
    const pattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return pattern.test(value) || 'Invalid email address';
  }
};

const handleSubmit = async () => {
  if (!email.value) return;

  isLoading.value = true;
  errorMessage.value = '';
  successMessage.value = '';

  try {
    await AuthService.requestPasswordReset(email.value);
    successMessage.value = 'If an account exists with that email, a password reset link has been sent. Please check your inbox.';
    email.value = '';
  } catch (error) {
    errorMessage.value = error.response?.data?.detail || 'Failed to send reset email. Please try again.';
  } finally {
    isLoading.value = false;
  }
};
</script>

<style scoped>
.forgot-page {
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

.page-footer {
  color: #6B7280;
  font-size: 0.9rem;
}

.page-link {
  color: #001529;
  font-weight: 700;
  text-decoration: none;
}
</style>
