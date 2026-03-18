<template>
  <div>
    <div class="d-flex align-center flex-wrap gap-3 mb-4">
      <h1 :class="$vuetify.display.mobile ? 'text-h5 font-weight-bold' : 'text-h4 font-weight-bold'">Events</h1>
      <v-btn-toggle v-model="filter" mandatory density="compact" rounded="lg" class="ml-auto filter-toggle">
        <v-btn value="upcoming" size="small">Upcoming</v-btn>
        <v-btn value="past" size="small">Past</v-btn>
        <v-btn value="all" size="small">All</v-btn>
      </v-btn-toggle>
    </div>

    <div v-if="eventStore.isLoading" class="text-center mt-16">
      <v-progress-circular indeterminate color="primary" size="64"></v-progress-circular>
      <p class="mt-4">Loading Events...</p>
    </div>

    <v-alert v-else-if="eventStore.error" type="error" class="mt-4">
      {{ eventStore.error }}
    </v-alert>

    <div v-else-if="!filteredEvents.length" class="text-center mt-16">
      <p>No {{ filter !== 'all' ? filter : '' }} events found.</p>
    </div>

    <v-row v-else class="mt-2">
      <v-col
        v-for="ev in filteredEvents"
        :key="ev.event_id"
        cols="12"
        sm="6"
        md="4"
        class="mb-4"
      >
        <EventCard :event="{
          id: ev.event_id,
          name: ev.event_name,
          date: ev.event_date_start,
          location: ev.location,
          description: ev.description,
          image_url: ev.image_url || 'https://cdn.vuetifyjs.com/images/cards/docks.jpg',
          price_euros: ev.price_euros,
          ticket_types: ev.ticket_types,
          category: ev.category,
        }" />
      </v-col>
    </v-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useEventStore } from '@/stores/events.store.js';
import EventCard from '@/components/events/EventCard.vue';

const eventStore = useEventStore();
const filter = ref('upcoming');

const filteredEvents = computed(() => {
  const now = new Date();
  return eventStore.events.filter(ev => {
    const eventDate = new Date(ev.event_date_start);
    if (filter.value === 'upcoming') return eventDate >= now;
    if (filter.value === 'past') return eventDate < now;
    return true;
  });
});

onMounted(() => {
  eventStore.fetchAllEvents();
});
</script>

<style scoped>
.filter-toggle {
  border: 1px solid #E5E7EB;
}
</style>
