<template>
  <v-container class="py-8">
    <v-row justify="center">
      <v-col cols="12" md="10" lg="8">

        <!-- Loading -->
        <v-card v-if="isLoading" class="pa-8 text-center">
          <v-progress-circular indeterminate color="primary" size="64" />
        </v-card>

        <!-- Success -->
        <v-card v-else-if="submission && !submission.already_applied" class="pa-8 text-center">
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
        <v-card v-else-if="submission && submission.already_applied" class="pa-8 text-center">
          <v-icon icon="mdi-information" color="info" size="64" class="mb-4" />
          <h2 class="text-h5 mb-3">You've already applied</h2>
          <p class="text-body-1 mb-6">
            We already have an application from this email for the current cycle. You can pick up where you left off on your status page.
          </p>
          <v-btn color="primary" variant="flat" :to="`/join/status/${submission.status_token}`">
            Go to my status page
          </v-btn>
        </v-card>

        <!-- Form -->
        <template v-else>
          <div class="text-center mb-6">
            <h1 class="text-h4 font-weight-bold mb-2">Join Ennova</h1>
            <p class="text-body-1 text-medium-emphasis">
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
import { ref, onMounted } from 'vue';
import { RecruitmentService } from '@/services/RecruitmentService.js';
import ApplicationStepper from '@/components/recruitment/ApplicationStepper.vue';

const isLoading = ref(true);
const departments = ref([]);
const cycle = ref(null);
const submission = ref(null);

function formatDate(iso) {
  if (!iso) return '';
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' });
}

function onSubmit(result) {
  submission.value = result;
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

onMounted(async () => {
  try {
    const [deps, activeCycle] = await Promise.all([
      RecruitmentService.getOpenPositions(),
      RecruitmentService.getActiveCycle(),
    ]);
    departments.value = deps;
    cycle.value = activeCycle;
  } finally {
    isLoading.value = false;
  }
});
</script>
