<template>
  <v-row align="center" justify="center" style="height: 70vh;">
    <v-col cols="12" sm="8" md="4">
      <v-card class="elevation-12">
        <v-toolbar color="primary">
          <v-toolbar-title>Reset Your Password</v-toolbar-title>
        </v-toolbar>
        <v-card-text class="pa-6">
          <v-alert v-if="successMessage" type="success" density="compact" class="mb-4">
            {{ successMessage }}
          </v-alert>
          <v-alert v-if="errorMessage" type="error" density="compact" class="mb-4">
            {{ errorMessage }}
          </v-alert>

          <v-form v-if="!successMessage" @submit.prevent="handleSubmit">
            <v-text-field
              v-model="formData.newPassword"
              label="New Password"
              type="password"
              prepend-inner-icon="mdi-lock-outline"
              variant="outlined"
              :rules="[rules.required, rules.minLength]"
              class="mb-2"
            ></v-text-field>

            <v-text-field
              v-model="formData.confirmPassword"
              label="Confirm Password"
              type="password"
              prepend-inner-icon="mdi-lock-check-outline"
              variant="outlined"
              :rules="[rules.required, rules.passwordMatch]"
            ></v-text-field>

            <v-btn
              type="submit"
              block
              class="mt-2"
              color="primary"
              size="large"
              :loading="isLoading"
              :disabled="!isFormValid"
            >
              Reset Password
            </v-btn>
          </v-form>

          <div v-if="successMessage" class="text-center mt-4">
            <v-btn to="/login" color="primary" variant="outlined">
              Go to Login
            </v-btn>
          </div>
        </v-card-text>
      </v-card>
    </v-col>
  </v-row>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { AuthService } from '@/services/AuthService';

const route = useRoute();
const router = useRouter();

const formData = ref({
  newPassword: '',
  confirmPassword: ''
});

const token = ref('');
const isLoading = ref(false);
const successMessage = ref('');
const errorMessage = ref('');

const rules = {
  required: value => !!value || 'This field is required',
  minLength: value => value.length >= 8 || 'Password must be at least 8 characters',
  passwordMatch: value => value === formData.value.newPassword || 'Passwords do not match'
};

const isFormValid = computed(() => {
  return formData.value.newPassword.length >= 8 &&
         formData.value.newPassword === formData.value.confirmPassword;
});

onMounted(() => {
  token.value = route.query.token;

  if (!token.value) {
    errorMessage.value = 'Invalid or missing reset token. Please request a new password reset.';
  }
});

const handleSubmit = async () => {
  if (!isFormValid.value) return;

  isLoading.value = true;
  errorMessage.value = '';

  try {
    await AuthService.confirmPasswordReset(token.value, formData.value.newPassword);
    successMessage.value = 'Password has been successfully reset! You can now log in with your new password.';

    setTimeout(() => {
      router.push('/login');
    }, 2000);
  } catch (error) {
    errorMessage.value = error.response?.data?.detail || 'Failed to reset password. The link may have expired.';
  } finally {
    isLoading.value = false;
  }
};
</script>