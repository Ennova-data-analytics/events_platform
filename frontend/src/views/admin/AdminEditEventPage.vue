<template>
  <div>
    <h1 class="text-h5 mb-4">Edit Event: {{ event.event_name }}</h1>
    <v-card>
      <v-card-text>
        <EventForm :initial-data="event" @submit="handleUpdateEvent" />
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import EventForm from '@/components/forms/EventForm.vue';
import { useEventStore } from '@/stores/events.store.js';
import { EventService } from '@/services/EventService.js';

const route = useRoute();
const eventStore = useEventStore();

const event = ref({});

onMounted(async () => {
  const eventId = route.params.id;
  try {
    const response = await EventService.getEventById(eventId);
    event.value = response.data;
  } catch (error) {
    console.error("Failed to fetch event for editing:", error);
  }
});

const handleUpdateEvent = (eventData) => {
  const eventId = route.params.id;
  eventStore.updateEvent(eventId, eventData);
};
</script>