<template>
  <v-form ref="form" @submit.prevent="handleSubmit">
    <v-alert
      v-if="errorMessage"
      type="error"
      variant="tonal"
      closable
      class="mb-4"
      @click:close="errorMessage = ''"
    >
      {{ errorMessage }}
    </v-alert>

    <v-alert
      v-if="successMessage"
      type="success"
      variant="tonal"
      closable
      class="mb-4"
      @click:close="successMessage = ''"
    >
      {{ successMessage }}
    </v-alert>

    <h3 class="text-h6 font-weight-medium mb-4">Personal Information</h3>
    <v-text-field
      v-model="formData.full_name"
      label="Full Name"
      variant="outlined"
      class="mb-4"
      prepend-inner-icon="mdi-account-outline"
      :rules="[rules.required]"
      :disabled="isLoading"
    ></v-text-field>
    <v-text-field
      v-model="formData.degree"
      label="Degree"
      variant="outlined"
      class="mb-4"
      prepend-inner-icon="mdi-briefcase-outline"
      :disabled="isLoading"
    ></v-text-field>
    <v-text-field
      v-model="formData.study_year"
      label="Year of Study"
      variant="outlined"
      class="mb-4"
      prepend-inner-icon="mdi-school-outline"
      :disabled="isLoading"
    ></v-text-field>

    <v-btn
      type="submit"
      color="primary"
      size="large"
      class="mt-4"
      :loading="isLoading"
      :disabled="isLoading"
    >
      Save Changes
    </v-btn>
    <v-btn
      variant="outlined"
      size="large"
      class="mt-4 ml-2"
      :disabled="isLoading"
      @click="handleCancel"
    >
      Cancel
    </v-btn>
  </v-form>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useAuthStore } from '@/stores/auth.store.js';
import { useRouter } from 'vue-router';
import ApiClient from '@/services/ApiClient.js';

const authStore = useAuthStore();
const router = useRouter();

const form = ref(null);
const isLoading = ref(false);
const errorMessage = ref('');
const successMessage = ref('');

const formData = ref({
  full_name: '',
  degree: '',
  study_year: ''
});

const rules = {
  required: value => !!value || 'This field is required'
};

onMounted(async () => {
  if (authStore.user) {
    formData.value.full_name = authStore.user.full_name || '';
    formData.value.degree = authStore.user.degree || '';
    formData.value.study_year = authStore.user.study_year || '';
  }
});

const handleSubmit = async () => {
  // Validate form
  const { valid } = await form.value.validate();
  if (!valid) {
    return;
  }

  isLoading.value = true;
  errorMessage.value = '';
  successMessage.value = '';

  try {
    await ApiClient.patch('/users/me', formData.value);

    await authStore.fetchCurrentUser();

    successMessage.value = 'Profile updated successfully!';

    setTimeout(() => {
      router.push('/profile');
    }, 1500);
  } catch (error) {
    errorMessage.value = error.response?.data?.detail || 'Failed to update profile. Please try again.';
  } finally {
    isLoading.value = false;
  }
};

const handleCancel = () => {
  router.push('/profile');
};
</script>