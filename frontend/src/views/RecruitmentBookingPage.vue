<template>
  <v-container class="py-8">
    <v-row justify="center">
      <v-col cols="12" md="8" lg="7">

        <v-card v-if="isLoading" class="pa-8 text-center">
          <v-progress-circular indeterminate color="primary" size="64" />
        </v-card>

        <!-- Booked confirmation -->
        <v-card v-else-if="booked" class="pa-8 text-center">
          <v-icon icon="mdi-calendar-check" color="success" size="64" class="mb-4" />
          <h2 class="text-h5 mb-3">You're booked in!</h2>
          <p class="text-body-1 mb-1">
            {{ formatDateTime(booked.slot.starts_at) }}
          </p>
          <p class="text-body-2 text-medium-emphasis mb-6">
            with {{ booked.slot.interviewer }} · a calendar invite (.ics) is on its way to your inbox.
          </p>
          <v-btn color="primary" variant="flat" :to="`/join/status/${$route.params.token}`">
            Back to my status page
          </v-btn>
        </v-card>

        <!-- Slot picker -->
        <template v-else>
          <div class="text-center mb-6">
            <h1 class="text-h5 font-weight-bold mb-2">Book your interview</h1>
            <p class="text-body-2 text-medium-emphasis">Choose one of the available slots below.</p>
          </div>

          <v-alert v-if="conflict" type="warning" variant="tonal" class="mb-4">
            That slot was just taken - please pick another.
          </v-alert>

          <v-card v-if="slots.length === 0" class="pa-8 text-center">
            <v-icon icon="mdi-calendar-remove" color="grey" size="48" class="mb-3" />
            <p class="text-body-2 text-medium-emphasis">No slots are open right now. We'll email you when more are added.</p>
          </v-card>

          <template v-else>
            <v-card
              v-for="(daySlots, day) in slotsByDay"
              :key="day"
              class="mb-4"
            >
              <v-card-title class="text-subtitle-2 font-weight-bold px-5 pt-4">{{ day }}</v-card-title>
              <v-card-text class="px-5 pb-4">
                <div class="d-flex flex-wrap ga-2">
                  <v-btn
                    v-for="slot in daySlots"
                    :key="slot.id"
                    :variant="selected?.id === slot.id ? 'flat' : 'outlined'"
                    :color="selected?.id === slot.id ? 'primary' : undefined"
                    @click="selected = slot"
                  >
                    {{ formatTime(slot.starts_at) }}
                    <span class="text-caption ml-1">· {{ slot.interviewer }}</span>
                  </v-btn>
                </div>
              </v-card-text>
            </v-card>

            <v-btn
              color="primary"
              size="large"
              block
              class="mt-2"
              :disabled="!selected"
              :loading="isBooking"
              @click="confirmBooking"
            >
              {{ selected ? `Confirm ${formatDateTime(selected.starts_at)}` : 'Select a slot' }}
            </v-btn>
          </template>
        </template>

      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { RecruitmentService } from '@/services/RecruitmentService.js';

const route = useRoute();
const isLoading = ref(true);
const isBooking = ref(false);
const slots = ref([]);
const selected = ref(null);
const booked = ref(null);
const conflict = ref(false);

const slotsByDay = computed(() => {
  const groups = {};
  for (const slot of slots.value) {
    const day = new Date(slot.starts_at).toLocaleDateString('en-GB', { weekday: 'long', day: 'numeric', month: 'long' });
    (groups[day] ||= []).push(slot);
  }
  return groups;
});

function formatTime(iso) {
  return new Date(iso).toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
}
function formatDateTime(iso) {
  return new Date(iso).toLocaleString('en-GB', { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
}

async function loadSlots() {
  slots.value = await RecruitmentService.getBookableSlotsByToken(route.params.token);
}

async function confirmBooking() {
  if (!selected.value) return;
  isBooking.value = true;
  conflict.value = false;
  try {
    booked.value = await RecruitmentService.bookSlot(route.params.token, selected.value.id);
  } catch (e) {
    if (e.code === 'slot_taken') {
      conflict.value = true;
      selected.value = null;
      await loadSlots();
    }
  } finally {
    isBooking.value = false;
  }
}

onMounted(async () => {
  try {
    await loadSlots();
  } finally {
    isLoading.value = false;
  }
});
</script>
