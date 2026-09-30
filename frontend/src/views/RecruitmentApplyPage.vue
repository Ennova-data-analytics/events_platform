<template>
  <v-container class="py-6 py-sm-8">
    <v-row justify="center">
      <v-col cols="12" md="10" lg="8">

        <!-- Loading -->
        <v-card v-if="isLoading" class="pa-8 text-center">
          <v-progress-circular indeterminate color="primary" size="64" />
        </v-card>

        <!-- Success -->
        <v-card v-else-if="submission && !submission.already_applied" class="pa-6 pa-sm-8 text-center">
          <v-icon icon="mdi-check-circle" color="success" size="64" class="mb-4" />
          <h2 class="text-h5 mb-3">Application received!</h2>
          <p class="text-body-1 mb-2">
            Thanks for applying to Ennova. We've emailed a confirmation to your inbox.
          </p>
          <p class="text-body-2 text-medium-emphasis mb-6">
            Your application includes a private link to track its progress - no account needed.
          </p>
          <v-btn color="primary" variant="flat" :to="`/join/status/${submission.status_token}`" prepend-icon="mdi-timeline-check-outline">
            View my status page
          </v-btn>
        </v-card>

        <!-- Already applied -->
        <v-card v-else-if="submission && submission.already_applied" class="pa-6 pa-sm-8 text-center">
          <v-icon icon="mdi-information" color="info" size="64" class="mb-4" />
          <h2 class="text-h5 mb-3">You've already applied</h2>
          <p class="text-body-1 mb-6">
            We already have an application from this email for the current cycle. You can pick up where you left off on your status page.
          </p>
          <v-btn color="primary" variant="flat" :to="`/join/status/${submission.status_token}`">
            Go to my status page
          </v-btn>
        </v-card>

        <!-- Couldn't load the cohort: say so rather than show an empty form -->
        <v-card v-else-if="loadError" class="pa-6 pa-sm-8 text-center">
          <v-icon icon="mdi-alert-circle-outline" color="error" size="64" class="mb-4" />
          <h2 class="text-h5 mb-3">We couldn't load the application form</h2>
          <p class="text-body-1 mb-6">{{ loadError }}</p>
          <v-btn color="primary" variant="flat" prepend-icon="mdi-refresh" @click="load">Try again</v-btn>
        </v-card>

        <!-- Closed: no cohort, outside its dates, or every department closed -->
        <v-card v-else-if="closedState" class="pa-6 pa-sm-8 text-center">
          <v-icon :icon="closedState.icon" color="medium-emphasis" size="64" class="mb-4" />
          <h2 class="text-h5 mb-3">{{ closedState.title }}</h2>
          <p class="text-body-1 mb-6">{{ closedState.text }}</p>
          <v-btn color="primary" variant="flat" to="/">See upcoming events</v-btn>
        </v-card>

        <!-- Form -->
        <template v-else>
          <div class="text-center mb-5 mb-sm-6">
            <h1 class="text-h5 text-sm-h4 font-weight-bold mb-2">Join Ennova</h1>
            <p class="text-body-2 text-sm-body-1 text-medium-emphasis">
              <span v-if="cycle">{{ cycle.name }} · applications close {{ formatDate(cycle.closes_at) }}</span>
            </p>
          </div>
          <v-card>
            <v-card-text class="pa-4 pa-sm-6">
              <ApplicationStepper :departments="departments" @submit="onSubmit" />
            </v-card-text>
          </v-card>
        </template>

      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { RecruitmentService } from '@/services/RecruitmentService.js';
import ApplicationStepper from '@/components/recruitment/ApplicationStepper.vue';

const isLoading = ref(true);
const departments = ref([]);
const cycle = ref(null);
const submission = ref(null);
const loadError = ref(null);

// The server rejects out-of-window submissions too, but only at the final
// step - checking here spares candidates filling in a form they can't send.
const closedState = computed(() => {
  const c = cycle.value;
  if (!c) {
    return {
      icon: 'mdi-calendar-remove-outline',
      title: "Recruitment isn't open right now",
      text: "There's no intake running at the moment. Keep an eye on our events - we announce new intakes there.",
    };
  }
  const now = Date.now();
  if (c.opens_at && new Date(c.opens_at).getTime() > now) {
    return {
      icon: 'mdi-calendar-clock-outline',
      title: `Applications open ${formatDate(c.opens_at)}`,
      text: `The ${c.name} hasn't opened yet. Come back on ${formatDate(c.opens_at)} to apply.`,
    };
  }
  if (c.closes_at && new Date(c.closes_at).getTime() < now) {
    return {
      icon: 'mdi-calendar-remove-outline',
      title: 'Applications are closed',
      text: `The ${c.name} closed on ${formatDate(c.closes_at)}. Thanks for your interest - keep an eye on our events for the next intake.`,
    };
  }
  if (!departments.value.length) {
    return {
      icon: 'mdi-calendar-remove-outline',
      title: 'Applications are closed',
      text: `No teams are taking applications for the ${c.name} any more. Keep an eye on our events for the next intake.`,
    };
  }
  return null;
});

function formatDate(iso) {
  if (!iso) return '';
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' });
}

function onSubmit(result) {
  submission.value = result;
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

async function load() {
  isLoading.value = true;
  loadError.value = null;
  try {
    const [deps, activeCycle] = await Promise.all([
      RecruitmentService.getOpenPositions(),
      RecruitmentService.getActiveCycle(),
    ]);
    departments.value = deps;
    cycle.value = activeCycle;
  } catch (err) {
    console.error('Failed to load application form:', err.response?.status, err.response?.data, err);
    loadError.value = err.response
      ? 'Something went wrong on our side. Please try again in a moment.'
      : "We couldn't reach the server. Check your connection and try again.";
  } finally {
    isLoading.value = false;
  }
}

onMounted(load);
</script>
