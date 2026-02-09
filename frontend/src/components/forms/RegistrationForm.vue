<template>
  <v-form @submit.prevent="handleSubmit">
    <v-alert v-if="authStore.error" type="error" density="compact" class="mb-6" rounded="lg">
      {{ authStore.error }}
    </v-alert>

    <div class="input-group mb-4">
      <label class="custom-label">Full Name</label>
      <v-text-field
        v-model="formData.full_name"
        placeholder="John Doe"
        variant="solo-filled"
        flat
        bg-color="#F3F4F6"
        rounded="lg"
        hide-details
      ></v-text-field>
    </div>

    <div class="input-group mb-4">
      <label class="custom-label">Professional Email</label>
      <v-text-field
        v-model="formData.email"
        placeholder="john.doe@esade.edu"
        type="email"
        variant="solo-filled"
        flat
        bg-color="#F3F4F6"
        rounded="lg"
        hide-details
      ></v-text-field>
    </div>

    <v-row class="mb-4">
      <v-col cols="6" class="py-0">
        <div class="input-group">
          <label class="custom-label">Degree</label>
          <v-text-field
            v-model="formData.degree"
            placeholder="BBA"
            variant="solo-filled"
            flat
            bg-color="#F3F4F6"
            rounded="lg"
            hide-details
          ></v-text-field>
        </div>
      </v-col>
      <v-col cols="6" class="py-0">
        <div class="input-group">
          <label class="custom-label">Years of Study</label>
          <v-text-field
            v-model="formData.study_year"
            placeholder="1"
            variant="solo-filled"
            flat
            bg-color="#F3F4F6"
            rounded="lg"
            hide-details
          ></v-text-field>
        </div>
      </v-col>
    </v-row>

    <div class="input-group mb-6">
      <label class="custom-label">Password</label>
      <v-text-field
        v-model="formData.password"
        type="password"
        placeholder="••••••••"
        variant="solo-filled"
        flat
        bg-color="#F3F4F6"
        rounded="lg"
        hide-details
      ></v-text-field>
    </div>

    <v-checkbox class="terms-checkbox mb-4" hide-details>
      <template v-slot:label>
        <span class="text-caption">
          I agree to the <a href="#" class="link">Terms and Conditions</a> and <a href="#" class="link">Privacy Policy</a>.
        </span>
      </template>
    </v-checkbox>

    <v-btn
      type="submit"
      block
      color="#001529"
      size="x-large"
      rounded="lg"
      class="signup-btn"
    >
      SIGN UP
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

<style scoped>
.custom-label {
  display: block;
  font-size: 0.85rem;
  font-weight: 700;
  color: #001529;
  margin-bottom: 6px;
}

.signup-btn {
  color: white !important;
  font-weight: 800;
  letter-spacing: 0.05em;
  height: 56px !important;
}

.link {
  color: #001529;
  font-weight: 700;
  text-decoration: underline;
}

:deep(.v-checkbox .v-selection-control) {
  min-height: 30px;
}
</style>