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

    <div class="input-group mb-4">
      <label class="custom-label">Confirm Email</label>
      <v-text-field
        v-model="confirmEmail"
        placeholder="john.doe@esade.edu"
        type="email"
        variant="solo-filled"
        flat
        :bg-color="emailMismatch ? '#FEF2F2' : '#F3F4F6'"
        rounded="lg"
        hide-details
      ></v-text-field>
      <p v-if="emailMismatch" class="mismatch-hint">Emails do not match</p>
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
      <div v-if="formData.password.length > 0" class="password-strength mt-2">
        <div class="strength-bars">
          <div class="bar" :class="{ active: passwordStrength >= 1, weak: passwordStrength === 1, medium: passwordStrength === 2, strong: passwordStrength === 3 }"></div>
          <div class="bar" :class="{ active: passwordStrength >= 2, medium: passwordStrength === 2, strong: passwordStrength === 3 }"></div>
          <div class="bar" :class="{ active: passwordStrength >= 3, strong: passwordStrength === 3 }"></div>
        </div>
        <span class="strength-label" :class="passwordStrengthClass">{{ passwordStrengthLabel }}</span>
      </div>
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
import { ref, computed } from 'vue';
import { useAuthStore } from '@/stores/auth.store.js';

const authStore = useAuthStore();
const cvFile = ref(null);
const confirmEmail = ref('');

const formData = ref({
  full_name: '',
  email: '',
  password: '',
  degree: '',
  study_year: '',
});

const emailMismatch = computed(() =>
  confirmEmail.value.length > 0 && formData.value.email !== confirmEmail.value
);

const passwordStrength = computed(() => {
  const p = formData.value.password;
  if (!p) return 0;
  let score = 0;
  if (p.length >= 8) score++;
  if (/[A-Z]/.test(p) && /[a-z]/.test(p)) score++;
  if (/[0-9]/.test(p) && /[^A-Za-z0-9]/.test(p)) score++;
  return score;
});

const passwordStrengthLabel = computed(() => {
  return ['', 'Weak', 'Medium', 'Strong'][passwordStrength.value];
});

const passwordStrengthClass = computed(() => {
  return ['', 'label-weak', 'label-medium', 'label-strong'][passwordStrength.value];
});

const handleSubmit = () => {
  if (emailMismatch.value || !confirmEmail.value) return;

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

.mismatch-hint {
  color: #DC2626;
  font-size: 0.75rem;
  margin-top: 4px;
  margin-left: 2px;
}

.password-strength {
  display: flex;
  align-items: center;
  gap: 8px;
}

.strength-bars {
  display: flex;
  gap: 4px;
  flex: 1;
}

.bar {
  height: 4px;
  flex: 1;
  border-radius: 2px;
  background-color: #E5E7EB;
  transition: background-color 0.3s ease;
}

.bar.active.weak   { background-color: #EF4444; }
.bar.active.medium { background-color: #F59E0B; }
.bar.active.strong { background-color: #10B981; }

.strength-label {
  font-size: 0.75rem;
  font-weight: 600;
  min-width: 44px;
  text-align: right;
}

.label-weak   { color: #EF4444; }
.label-medium { color: #F59E0B; }
.label-strong { color: #10B981; }
</style>