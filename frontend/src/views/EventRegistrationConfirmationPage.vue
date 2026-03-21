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

            <!-- Team progress (leader-pays group tickets) -->
            <template v-if="myTeam">
              <v-divider class="my-6"></v-divider>
              <div class="d-flex align-center justify-space-between mb-1">
                <span class="font-weight-bold">Team: {{ myTeam.team_name }}</span>
                <v-chip size="small" color="deep-orange" variant="tonal">
                  {{ myTeam.members.length }}/{{ myTeam.group_size }} joined
                </v-chip>
              </div>

              <v-progress-linear
                :model-value="(myTeam.members.length / myTeam.group_size) * 100"
                color="deep-orange"
                bg-color="grey-lighten-3"
                rounded
                height="6"
                class="mb-4"
              ></v-progress-linear>

              <v-list density="compact" class="pa-0">
                <v-list-item
                  v-for="member in myTeam.members"
                  :key="member.registration_id"
                  class="px-0"
                >
                  <template v-slot:prepend>
                    <v-icon :color="member.status === 'Paid' ? 'success' : 'warning'" size="18">
                      {{ member.status === 'Paid' ? 'mdi-check-circle' : 'mdi-clock-outline' }}
                    </v-icon>
                  </template>
                  <v-list-item-title class="text-body-2">
                    {{ member.full_name }}
                    <v-chip v-if="member.is_leader" size="x-small" color="deep-orange" class="ml-1">Leader</v-chip>
                  </v-list-item-title>
                  <template v-slot:append>
                    <v-chip size="x-small" :color="member.status === 'Paid' ? 'success' : 'warning'" variant="tonal">
                      {{ member.status }}
                    </v-chip>
                  </template>
                </v-list-item>

                <v-list-item
                  v-for="invite in myTeam.invites.filter(i => !i.claimed)"
                  :key="invite.invite_id"
                  class="px-0"
                >
                  <template v-slot:prepend>
                    <v-icon color="grey" size="18">mdi-email-outline</v-icon>
                  </template>
                  <v-list-item-title class="text-body-2 text-grey">{{ invite.invited_email }}</v-list-item-title>
                  <template v-slot:append>
                    <v-chip size="x-small" color="grey" variant="tonal">Invite pending</v-chip>
                  </template>
                </v-list-item>
              </v-list>

              <v-alert
                v-if="myTeam.members.length < myTeam.group_size"
                type="info"
                variant="tonal"
                density="compact"
                class="mt-4"
              >
                <v-icon start size="small">mdi-email-fast</v-icon>
                Invites have been sent. This panel updates as teammates claim their spots.
              </v-alert>
            </template>
          </v-card>
        </v-col>
      </v-row>
    </v-container>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { useAuthStore } from '@/stores/auth.store.js';
import { EventService } from '@/services/EventService.js';

const route = useRoute();
const authStore = useAuthStore();
const myTeam = ref(null);

onMounted(async () => {
  if (authStore.isAuthenticated) {
    await authStore.fetchCurrentUser();
    try {
      const response = await EventService.getMyTeam(route.params.id);
      myTeam.value = response.data;
    } catch {
      // Not a team registration — ignore
    }
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
