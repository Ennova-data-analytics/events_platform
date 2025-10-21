<template>
  <v-form @submit.prevent="handleSubmit">
    <v-alert v-if="authStore.error" type="error" density="compact" class="mb-4">
      {{ authStore.error }}
    </v-alert>
    <v-text-field
      v-model="formData.email"
      label="Email"
      type="email"
      prepend-inner-icon="mdi-email-outline"
      variant="outlined"
      :density="$vuetify.display.mobile ? 'compact' : 'default'"
      class="mb-2"
    />

    <v-text-field
      v-model="formData.password"
      label="Password"
      type="password"
      prepend-inner-icon="mdi-lock-outline"
      variant="outlined"
      :density="$vuetify.display.mobile ? 'compact' : 'default'"
    />

    <div class="d-flex justify-center mb-4">
      <router-link to="/forgot-password" class="text-caption text-primary" style="text-decoration: none;">
        Forgot your password, you can reset it now!
      </router-link>
    </div>


    <v-btn type="submit" block class="mt-2" color="primary" :size="$vuetify.display.mobile ? 'default' : 'large'">
      Login
    </v-btn>

    <div class="text-center mt-4">
      <span>Don't have an account? </span>
      <router-link to="/register" class="text-primary font-weight-bold" style="text-decoration: none;">
        Sign Up
      </router-link>
    </div>
    
  </v-form>
</template>

<script setup>
import { ref } from 'vue';
import { useAuthStore } from '@/stores/auth.store.js';

const authStore = useAuthStore();

const formData = ref({
  email: '',
  password: '',
});

const handleSubmit = () => {
  authStore.login(formData.value);
};
</script>