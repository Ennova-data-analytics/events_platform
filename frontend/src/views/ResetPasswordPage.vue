<template>
  <div class="reset-page d-flex align-center justify-center">
    <v-container>
      <v-row justify="center">
        <v-col cols="12" sm="10" md="6" lg="5">

          <v-card class="ennova-card pa-8 pa-md-12" flat rounded="xl">
            <div class="text-center mb-8">
              <h1 class="form-title mb-2">Reset Password</h1>
              <p class="form-subtitle">Choose a new password for your account.</p>
            </div>

            <v-alert v-if="successMessage" type="success" variant="tonal" density="compact" class="mb-6">
              {{ successMessage }}
            </v-alert>
            <v-alert v-if="errorMessage" type="error" variant="tonal" density="compact" class="mb-6">
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
                color="primary"
                size="large"
                :loading="isLoading"
                :disabled="!isFormValid"
                class="mt-2"
              >
                Reset Password
              </v-btn>
            </v-form>

            <div v-if="successMessage" class="text-center mt-6">
              <v-btn to="/login" color="primary" variant="outlined" size="large">
                Go to Login
              </v-btn>
            </div>

            <div v-if="!successMessage" class="text-center mt-8">
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

<style scoped>
.reset-page {
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
