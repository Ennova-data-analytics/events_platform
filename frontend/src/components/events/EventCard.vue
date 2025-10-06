<template>
  <v-card class="mx-auto" hover>
    <v-img
      class="align-end text-white"
      height="200"
      :src="event.image_url"
      cover
    >
      <v-card-title>{{ event.name }}</v-card-title>
    </v-img>

    <v-card-subtitle class="pt-4">
      {{ new Date(event.date).toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' }) }}
    </v-card-subtitle>

    <v-card-text>
      <div>
        <v-icon size="small" class="mr-1">mdi-map-marker-outline</v-icon>
        {{ event.location }}
      </div>
      <div class="mt-2 text-truncate">
        {{ event.description }}
      </div>
    </v-card-text>

    <v-card-actions>
      <v-spacer></v-spacer>
      <v-btn
        color="primary"
        variant="text"
        :to="{ name: 'event-details', params: { id: event.id } }"
      >
        Details
      </v-btn>
    </v-card-actions>
  </v-card>
</template>

<script setup>
defineProps({
  event: {
    type: Object,
    required: true,
    default: () => ({
      id: 0,
      name: 'Default Event Title',
      date: new Date().toISOString(),
      location: 'Default Location',
      description: 'This is a default description for an event.',
      imageUrl: 'https://cdn.vuetifyjs.com/images/cards/docks.jpg', 
    })
  }
})
</script>

<style scoped>
.text-truncate {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>