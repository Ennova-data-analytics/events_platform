<template>
  <div>
    <h1 :class="$vuetify.display.mobile ? 'text-h5 font-weight-bold mb-3' : 'text-h4 font-weight-bold mb-4'">Upcoming Events</h1>
    
    <div v-if="eventStore.isLoading" class="text-center mt-16">
      <v-progress-circular indeterminate color="primary" size="64"></v-progress-circular>
      <p class="mt-4">Loading Events...</p>
    </div>

    <v-alert v-else-if="eventStore.error" type="error" class="mt-4">
      {{ eventStore.error }}
    </v-alert>

    <div v-else-if="!eventStore.events.length" class="text-center mt-16">
      <p>No upcoming events found. Please check back later!</p>
    </div>

    <v-row v-else>
      <v-col 
        v-for="ev in eventStore.events" 
        :key="ev.event_id" 
        cols="12" 
        sm="6" 
        md="4"
      >
        <EventCard :event="{
          id: ev.event_id,
          name: ev.event_name,
          date: ev.event_date_start,
          location: ev.location,
          description: ev.description,
          image_url: ev.image_url || 'https://cdn.vuetifyjs.com/images/cards/docks.jpg',
        }" />
      </v-col>
    </v-row>
  </div>
</template>

<script setup>
import { onMounted } from 'vue';
import { useEventStore } from '@/stores/events.store.js';
import EventCard from '@/components/events/EventCard.vue';

const eventStore = useEventStore();


onMounted(() => {
  console.log('HomePage.vue has been mounted. Fetching events...');
  eventStore.fetchAllEvents();
});
</script>
