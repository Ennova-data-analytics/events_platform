<template>
  <div class="confirmation-page d-flex align-center justify-center">
    <v-container>
      <v-row justify="center">
        <v-col cols="12" sm="10" md="6" lg="5">
          <v-card class="ennova-card pa-8 pa-md-12" flat rounded="xl">
            <div class="text-center">
              <v-icon size="80" :color="isPending ? 'info' : 'success'" class="mb-4">
                {{ isPending ? 'mdi-clock-outline' : 'mdi-check-circle' }}
              </v-icon>
              <h1 class="form-title mb-2">{{ title }}</h1>
              <p class="form-subtitle mb-6">{{ subtitle }}</p>
              <v-btn color="primary" variant="flat" size="large" :to="`/event/${$route.params.id}`">
                View Event Details
              </v-btn>
            </div>
          </v-card>
        </v-col>
      </v-row>
    </v-container>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { useAuthStore } from '@/stores/auth.store.js';

const route = useRoute();
const authStore = useAuthStore();

onMounted(async () => {
  if (authStore.isAuthenticated) {
    await authStore.fetchCurrentUser();
  }
});

const registrationStatus = computed(() => {
  const eventId = parseInt(route.params.id);
  const registration = authStore.user?.registrations?.find(
    reg => reg.event.event_id === eventId
  );
  return registration?.status || null;
});

const isPending = computed(() => registrationStatus.value === 'Pending Approval');
const isPaidConfirmation = computed(() => route.query.payment === 'success');

const title = computed(() => {
  if (isPaidConfirmation.value) return "You're In!";
  if (isPending.value) return 'Application Submitted';
  return "You're In!";
});

const subtitle = computed(() => {
  if (isPaidConfirmation.value) return 'Payment successful! Your registration is confirmed.';
  if (isPending.value) return 'Your application is pending review by the organiser. You will be notified once a decision has been made.';
  return 'Your registration has been submitted successfully.';
});
</script>

<style scoped>
.confirmation-page {
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
