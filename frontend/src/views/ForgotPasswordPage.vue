<template>
  <v-row align="center" justify="center" style="height: 70vh;">
    <v-col cols="12" sm="8" md="4">
      <v-card class="elevation-12">
        <v-toolbar color="primary">
          <v-toolbar-title>Forgot Password</v-toolbar-title>
        </v-toolbar>
        <v-card-text class="pa-6">
          <v-alert v-if="successMessage" type="success" density="compact" class="mb-4">
            {{ successMessage }}
          </v-alert>
          <v-alert v-if="errorMessage" type="error" density="compact" class="mb-4">
            {{ errorMessage }}
          </v-alert>

          <p class="mb-4" v-if="!successMessage">
            Enter your email address below and we will send you a link to reset your password.
          </p>

          <v-form v-if="!successMessage" @submit.prevent="handleSubmit">
            <v-text-field
              v-model="email"
              label="Email Address"
              type="email"
              prepend-inner-icon="mdi-email-outline"
              variant="outlined"
              :rules="[rules.required, rules.email]"
            ></v-text-field>
            <v-btn
              type="submit"
              block
              class="mt-2"
              color="primary"
              size="large"
              :loading="isLoading"
            >
              Send Reset Link
            </v-btn>
          </v-form>

          <div class="text-center mt-4">
            <router-link to="/login" class="text-primary" style="text-decoration: none;">
              Back to Login
            </router-link>
          </div>
        </v-card-text>
      </v-card>
    </v-col>
  </v-row>
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