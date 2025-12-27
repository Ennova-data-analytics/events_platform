<template>
  <div>
    <h1 class="text-h5 mb-4">Create New Event</h1>
    <v-card>
      <v-card-text>
        <EventForm @submit="handleCreateEvent" />
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup>
import EventForm from '@/components/forms/EventForm.vue';
import { useEventStore } from '@/stores/events.store.js';
import { useRouter } from 'vue-router';

const eventStore = useEventStore();
const router = useRouter();



const handleCreateEvent = async (eventData, imageFile) => {
  console.log("handleCreateEvent received imageFile:", imageFile);
  try {
    console.log("Calling eventStore.createEvent...");
    const newEvent = await eventStore.createEvent(eventData);
    console.log("...createEvent finished. Received new event object:", newEvent);

    if (newEvent && newEvent.event_id && imageFile) {
      console.log(`Uploading image for new event ID: ${newEvent.event_id}`);
      await eventStore.uploadEventImage(newEvent.event_id, imageFile);
      console.log("...image upload finished.");
    }

    // Redirect to edit page where ticket types can be configured
    if (newEvent && newEvent.event_id) {
      router.push({ name: 'admin-edit-event', params: { id: newEvent.event_id } });
    } else {
      router.push({ name: 'admin-events' });
    }
  } catch (error) {
    console.error("An error occurred during the creation process:", error);
  }
};
</script>