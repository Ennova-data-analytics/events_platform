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

const handleUpdateEvent = async (eventData, imageFile) => {
  const eventId = route.params.id;

  console.log('=== UPDATE EVENT DEBUG ===');
  console.log('Event ID:', eventId);
  console.log('Event Data:', eventData);
  console.log('Image File (raw):', imageFile);
  console.log('Image File type:', typeof imageFile);
  console.log('Is Array?:', Array.isArray(imageFile));
  console.log('Array length:', imageFile?.length);
  console.log('First element:', imageFile?.[0]);
  
  try {
    await eventStore.updateEvent(eventId, eventData);
    console.log('Event updated successfully');
    console.log('Checking image upload condition...');
    console.log('imageFile exists?', !!imageFile);
    console.log('imageFile.length > 0?', imageFile?.length > 0);
    
    if (imageFile) {
      console.log('ATTEMPTING IMAGE UPLOAD with file:', imageFile);
      await eventStore.uploadEventImage(eventId, imageFile);
      console.log('Image upload completed');
    } else {
      console.log('IMAGE UPLOAD SKIPPED - No file provided');
    }
    
  } catch (error) {
    console.error("Failed to update event:", error);
  }}
</script>