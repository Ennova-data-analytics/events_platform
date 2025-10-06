<template>
  <v-form @submit.prevent="handleSubmit">
    <v-alert v-if="authStore.error" type="error" density="compact" class="mb-4">
      {{ authStore.error }}
    </v-alert>

    <v-text-field
      v-model="formData.full_name"
      label="Full Name"
      prepend-inner-icon="mdi-account-outline"
      variant="outlined"
      class="mb-2"
    ></v-text-field>

    <v-text-field
      v-model="formData.email"
      label="Professional Email"
      type="email"
      prepend-inner-icon="mdi-email-outline"
      variant="outlined"
      class="mb-2"
    ></v-text-field>

    <v-text-field
      v-model="formData.degree"
      label="Degree"
      prepend-inner-icon="mdi-briefcase-outline"
      variant="outlined"
      class="mb-2"
    ></v-text-field>

    <v-text-field
      v-model="formData.study_year"
      label="Year of Study"
      prepend-inner-icon="mdi-school-outline"
      variant="outlined"
      class="mb-2"
    ></v-text-field>


    <v-text-field
      v-model="formData.password"
      label="Password"
      type="password"
      prepend-inner-icon="mdi-lock-outline"
      variant="outlined"
      class="mb-2"
    ></v-text-field>
    
    
    <v-checkbox
      label="I agree to the terms and conditions."
      class="mt-2"
    ></v-checkbox>

    <v-btn type="submit" block class="mt-2" color="primary" size="large">
      Create Account
    </v-btn>
  </v-form>
</template>

<script setup>
import { ref } from 'vue';
import { useAuthStore } from '@/stores/auth.store.js';

const authStore = useAuthStore();
const cvFile = ref(null);

const formData = ref({
  full_name: '',
  email: '',
  password: '',
  degree: '',
  study_year: '',
});

const handleSubmit = () => {
  console.log('Form submitted in RegistrationForm.vue! Calling authStore.register...');
  console.log('handleSubmit in RegistrationForm.vue');
  console.log('Value of cvFile ref:', cvFile.value);

  authStore.register(formData.value, cvFile.value);
};
</script>