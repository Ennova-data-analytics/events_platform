<template>
  <v-card
    class="mx-auto"
    hover
    :to="{ name: 'event-details', params: { id: event.id } }"
    style="cursor: pointer;"
    elevation="2"
  >
    <v-img
      class="align-end text-white"
      :height="$vuetify.display.mobile ? 150 : 200"
      :src="event.image_url"
      cover
    >
      <v-card-title :class="$vuetify.display.mobile ? 'text-body-1' : ''">{{ event.name }}</v-card-title>
    </v-img>

    <v-card-subtitle :class="$vuetify.display.mobile ? 'pt-2 text-caption' : 'pt-4'">
      {{ new Date(event.date).toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' }) }}
    </v-card-subtitle>

    <v-card-text :class="$vuetify.display.mobile ? 'py-2' : ''">
      <div :class="$vuetify.display.mobile ? 'text-caption' : ''">
        <v-icon size="small" class="mr-1">mdi-map-marker-outline</v-icon>
        {{ event.location }}
      </div>
      <div :class="['mt-2', 'text-truncate', $vuetify.display.mobile ? 'text-caption' : '']">
        {{ event.description }}
      </div>
    </v-card-text>

    <v-card-actions>
      <v-spacer></v-spacer>
      <v-btn
        color="primary"
        variant="text"
        :size="$vuetify.display.mobile ? 'small' : 'default'"
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