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


// const handleCreateEvent = (eventData) => {
//   eventStore.createEvent(eventData);
// };

const handleCreateEvent = async (eventData, imageFile) => {
  console.log("handleCreateEvent received imageFile:", imageFile); 
  try {
    console.log("Calling eventStore.createEvent...");
    const newEvent = await eventStore.createEvent(eventData); // This works
    console.log("...createEvent finished. Received new event object:", newEvent);

    // --- THE PROBLEM IS ALMOST CERTAINLY HERE ---
    if (newEvent && newEvent.event_id && imageFile) {
      console.log(`Uploading image for new event ID: ${newEvent.event_id}`);
      await eventStore.uploadEventImage(newEvent.event_id, imageFile);
      console.log("...image upload finished.");
    }
    // --- END PROBLEM AREA ---
    
    router.push({ name: 'admin-events' });
  } catch (error) {
    console.error("An error occurred during the creation process:", error);
  }
};
</script>