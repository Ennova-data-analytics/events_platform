<template>
  <div>
    <div v-if="isLoading" class="text-center mt-16">
      <v-progress-circular indeterminate color="primary" size="64"></v-progress-circular>
      <p class="mt-4">Loading Profile...</p>
    </div>

    <div v-else-if="authStore.user">
      <h1 class="text-h4 font-weight-bold mb-4">My Profile</h1>
      <v-row>
        
        <!-- Left Column: Profile Card -->
        <v-col cols="12" md="4">
          <v-card>
            <v-card-text class="text-center">
              <v-avatar color="surface" size="150" class="mb-4">
                <v-icon size="90">mdi-account-circle</v-icon>
              </v-avatar>
              <h2 class="text-h5">{{ authStore.user.full_name }}</h2>
              <p class="text-medium-emphasis">{{ authStore.user.email }}</p>
            </v-card-text>
          </v-card>
        </v-col>

        <v-col cols="12" md="8">
          
          <v-card class="mb-4">
            <v-card-title>Your Information</v-card-title>
            <v-divider></v-divider>
            <v-list lines="one">
              <v-list-item 
                prepend-icon="mdi-briefcase-outline" 
                title="Degree" 
                :subtitle="authStore.user.degree || 'Not specified'"
              ></v-list-item>
              <v-list-item 
                prepend-icon="mdi-school-outline" 
                title="Year of Study" 
                :subtitle="authStore.user.study_year || 'Not specified'"
              ></v-list-item>
            </v-list>
            <v-divider></v-divider>
            <v-card-actions>
              <v-spacer></v-spacer>
              <v-btn color="primary" to="/profile/edit" prepend-icon="mdi-pencil">
                Edit Profile
              </v-btn>
            </v-card-actions>
          </v-card>

          <v-card class="mb-4">
            <v-card-title>My Applications</v-card-title>
            <v-divider></v-divider>
            <v-card-text v-if="!applicationEvents.length">
              You have no pending or recently decided applications.
            </v-card-text>
            <v-list v-else lines="two">
              <v-list-item
                v-for="registration in applicationEvents"
                :key="registration.registration_id"
                :title="registration.event.event_name"
                :subtitle="`Applied on: ${new Date(registration.registration_date).toLocaleDateString('en-GB')}`"
              >
                <template v-slot:append>
                  <v-chip :color="getStatusColor(registration.status)" size="small">
                    {{ registration.status }}
                  </v-chip>
                </template>
              </v-list-item>
            </v-list>
          </v-card>

          <v-card class="mb-4">
            <v-card-title>Upcoming Confirmed Events</v-card-title>
            <v-divider></v-divider>
            <v-card-text v-if="!upcomingEvents.length">
              You have no confirmed upcoming events.
            </v-card-text>
            <v-list v-else lines="two">
              <v-list-item
                v-for="registration in upcomingEvents"
                :key="registration.registration_id"
                :title="registration.event.event_name"
                :subtitle="new Date(registration.event.event_date_start).toLocaleDateString('en-GB')"
              >
                <template v-slot:append>
                   <v-chip v-if="registration.status === 'Approved'" color="warning" size="small">
                      Awaiting Payment
                   </v-chip>
                   <div v-else-if="registration.status === 'Paid'" class="d-flex align-center gap-2">
                     <v-chip color="success" size="small">Confirmed</v-chip>
                     <v-btn
                       size="small"
                       variant="tonal"
                       color="primary"
                       prepend-icon="mdi-ticket-outline"
                       :to="{ name: 'my-ticket', params: { id: registration.event.event_id, registrationId: registration.registration_id } }"
                     >
                       View Ticket
                     </v-btn>
                   </div>
                </template>
              </v-list-item>
            </v-list>
          </v-card>

          <v-card>
            <v-card-title>Past Events Attended</v-card-title>
            <v-divider></v-divider>
            <v-card-text v-if="!pastEvents.length">
              You have not attended any past events yet.
            </v-card-text>
            <v-list v-else lines="two">
              <v-list-item
                v-for="registration in pastEvents"
                :key="registration.registration_id"
                :title="registration.event.event_name"
                :subtitle="new Date(registration.event.event_date_start).toLocaleDateString('en-GB')"
              >
                <template v-slot:append>
                  <v-menu>
                    <template v-slot:activator="{ props }">
                      <v-btn icon="mdi-dots-vertical" variant="text" v-bind="props"></v-btn>
                    </template>
                    <v-list>
                      <v-list-item prepend-icon="mdi-comment-edit-outline" title="Give Feedback"></v-list-item>
                    </v-list>
                  </v-menu>
                </template>
              </v-list-item>
            </v-list>
          </v-card>
        </v-col>
      </v-row>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useAuthStore } from '@/stores/auth.store.js';

const authStore = useAuthStore();
const isLoading = ref(true);


const applicationEvents = computed(() => {
  if (!authStore.user?.registrations) return [];
  return authStore.user.registrations.filter(
    reg => ['Pending Approval', 'Rejected'].includes(reg.status)
  );
});

const upcomingEvents = computed(() => {
  if (!authStore.user?.registrations) return [];
  const now = new Date();
  return authStore.user.registrations.filter(
    reg => ['Approved', 'Paid'].includes(reg.status) && new Date(reg.event.event_date_start) >= now
  );
});

const pastEvents = computed(() => {
  if (!authStore.user?.registrations) return [];
  const now = new Date();
  return authStore.user.registrations.filter(
    reg => ['Paid', 'Attended'].includes(reg.status) && new Date(reg.event.event_date_start) < now
  );
});

const getStatusColor = (status) => {
  if (status === 'Pending Approval') return 'info';
  if (status === 'Rejected') return 'error';
  return 'grey';
};

onMounted(async () => {
  await authStore.fetchCurrentUser();
  isLoading.value = false;
});
</script>