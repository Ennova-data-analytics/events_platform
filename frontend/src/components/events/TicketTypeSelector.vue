<template>
  <div class="ticket-type-selector">
    <v-card v-if="ticketTypes && ticketTypes.length > 0" outlined class="mb-4">
      <v-card-title class="text-h6">
        <v-icon left color="primary">mdi-ticket</v-icon>
        Select Ticket Type
      </v-card-title>

      <v-card-text>
        <v-select
          v-model="selectedTicketTypeId"
          :items="availableTicketTypes"
          item-title="displayText"
          item-value="ticket_type_id"
          label="Choose your ticket type"
          variant="outlined"
          density="comfortable"
          :rules="[v => !!v || 'Please select a ticket type']"
          @update:modelValue="onTicketTypeChange"
        >
          <template v-slot:item="{ props, item }">
            <v-list-item
              v-bind="props"
              :disabled="!item.raw.is_active || (item.raw.capacity && item.raw.tickets_available <= 0)"
            >
              <template v-slot:prepend>
                <v-icon :color="getTicketTypeColor(item.raw)">
                  {{ getTicketTypeIcon(item.raw) }}
                </v-icon>
              </template>

              <v-list-item-title>
                {{ item.raw.name }} - €{{ item.raw.price_euros }}
              </v-list-item-title>

              <v-list-item-subtitle>
                {{ item.raw.description }}
              </v-list-item-subtitle>

              <template v-slot:append>
                <v-chip
                  v-if="item.raw.show_availability && item.raw.capacity"
                  :color="getAvailabilityColor(item.raw)"
                  size="small"
                  variant="flat"
                >
                  {{ item.raw.tickets_available }}/{{ item.raw.capacity }} available
                </v-chip>
                <v-chip v-else-if="item.raw.show_availability && !item.raw.capacity" color="success" size="small" variant="flat">
                  Unlimited
                </v-chip>
              </template>
            </v-list-item>
          </template>
        </v-select>

        <!-- Selected Ticket Type Details -->
        <v-expand-transition>
          <v-card
            v-if="selectedTicketType"
            class="mt-4"
            variant="tonal"
            color="primary"
          >
            <v-card-text>
              <div class="d-flex align-center mb-2">
                <v-icon left color="primary">mdi-check-circle</v-icon>
                <span class="text-h6 ml-2">{{ selectedTicketType.name }}</span>
              </div>

              <p class="text-body-2 mb-3">
                {{ selectedTicketType.description }}
              </p>

              <v-divider class="my-3"></v-divider>

              <div class="d-flex justify-space-between align-center">
                <div>
                  <div class="text-caption text-grey-darken-1">Price</div>
                  <div class="text-h5 text-primary font-weight-bold">
                    €{{ selectedTicketType.price_euros }}
                  </div>
                </div>

                <div v-if="selectedTicketType.show_availability && selectedTicketType.capacity" class="text-right">
                  <div class="text-caption text-grey-darken-1">Availability</div>
                  <div class="text-body-1">
                    <v-chip
                      :color="getAvailabilityColor(selectedTicketType)"
                      size="small"
                    >
                      {{ selectedTicketType.tickets_available }} tickets left
                    </v-chip>
                  </div>
                </div>
              </div>

              <v-alert
                v-if="selectedTicketType.is_free_for_members && !user?.is_ennova_member"
                type="info"
                variant="tonal"
                class="mt-3"
                density="compact"
              >
                <v-icon left>mdi-information</v-icon>
                This ticket is free for Ennova members
              </v-alert>

              <v-alert
                v-if="selectedTicketType.is_free_for_members && user?.is_ennova_member"
                type="success"
                variant="tonal"
                class="mt-3"
                density="compact"
              >
                <v-icon left>mdi-star</v-icon>
                As an Ennova member, this ticket is free for you!
              </v-alert>
            </v-card-text>
          </v-card>
        </v-expand-transition>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { useAuthStore } from '@/stores/auth.store';

const props = defineProps({
  ticketTypes: {
    type: Array,
    default: () => []
  },
  modelValue: {
    type: Number,
    default: null
  }
});

const emit = defineEmits(['update:modelValue', 'ticket-type-selected']);

const authStore = useAuthStore();
const user = computed(() => authStore.user);

const selectedTicketTypeId = ref(props.modelValue);

// Filter out inactive and sold-out ticket types
const availableTicketTypes = computed(() => {
  return props.ticketTypes
    .filter(tt => tt.is_active)
    .map(tt => ({
      ...tt,
      displayText: `${tt.name} - €${tt.price_euros}${tt.show_availability && tt.capacity ? ` (${tt.tickets_available} available)` : ''}`
    }));
});

const selectedTicketType = computed(() => {
  if (!selectedTicketTypeId.value) return null;
  return props.ticketTypes.find(tt => tt.ticket_type_id === selectedTicketTypeId.value);
});

watch(() => props.modelValue, (newValue) => {
  selectedTicketTypeId.value = newValue;
});

function onTicketTypeChange(ticketTypeId) {
  emit('update:modelValue', ticketTypeId);
  emit('ticket-type-selected', selectedTicketType.value);
}

function getTicketTypeColor(ticketType) {
  if (!ticketType.is_active) return 'grey';
  if (ticketType.capacity && ticketType.tickets_available <= 0) return 'error';
  if (ticketType.capacity && ticketType.tickets_available < 10) return 'warning';
  return 'success';
}

function getTicketTypeIcon(ticketType) {
  if (!ticketType.is_active) return 'mdi-ticket-outline';
  if (ticketType.capacity && ticketType.tickets_available <= 0) return 'mdi-close-circle';
  return 'mdi-ticket-confirmation';
}

function getAvailabilityColor(ticketType) {
  if (!ticketType.capacity) return 'success';
  const availabilityPercent = (ticketType.tickets_available / ticketType.capacity) * 100;
  if (availabilityPercent === 0) return 'error';
  if (availabilityPercent < 20) return 'error';
  if (availabilityPercent < 50) return 'warning';
  return 'success';
}
</script>

<style scoped>
.ticket-type-selector {
  width: 100%;
}
</style>
