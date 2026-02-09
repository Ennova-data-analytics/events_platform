<template>
  <v-hover v-slot="{ isHovering, props: hoverProps }">
    <v-card
      v-bind="hoverProps"
      :elevation="isHovering ? 8 : 2"
      class="event-card rounded-lg transition-swing cursor-pointer"
      :to="{ name: 'event-details', params: { id: event.id } }"
      height="100%"
    >
      <div class="image-container">
        <v-img
          :src="event.image_url || '/placeholder-event.jpg'"
          :lazy-src="event.image_url ? undefined : '/placeholder-event.jpg'"
          cover
          height="200"
          class="align-end event-image"
          :class="{ 'zoom-effect': isHovering }"
        >
          <div class="image-overlay"></div>

          <v-chip
            v-if="event.category"
            color="white"
            variant="flat"
            size="small"
            class="category-chip text-uppercase font-weight-bold"
            label
          >
            {{ event.category }}
          </v-chip>
        </v-img>

        <div class="date-badge elevation-3 text-center rounded">
          <div class="month text-caption font-weight-bold bg-primary text-white py-1">
            {{ eventDate.month }}
          </div>
          <div class="day text-h6 font-weight-black bg-white text-primary py-1">
            {{ eventDate.day }}
          </div>
        </div>
      </div>

      <v-card-item class="pt-4">
        <v-card-title class="text-h6 font-weight-bold text-truncate mb-1">
          {{ event.name }}
        </v-card-title>

        <v-card-subtitle class="d-flex flex-column gap-1">
          <div class="d-flex align-center">
            <v-icon icon="mdi-calendar-outline" size="small" class="mr-1 text-medium-emphasis"></v-icon>
            <span class="text-caption">{{ eventDate.fullDate }}</span>
          </div>
          <div class="d-flex align-center mt-1">
            <v-icon icon="mdi-map-marker-outline" size="small" class="mr-1 text-medium-emphasis"></v-icon>
            <span class="text-caption text-truncate">{{ event.location || 'Online Event' }}</span>
          </div>
        </v-card-subtitle>
      </v-card-item>

      <v-card-text class="text-body-2 text-medium-emphasis text-truncate-2-lines">
        {{ stripMarkdown(event.description) }}
      </v-card-text>

      <v-divider></v-divider>

      <v-card-actions class="px-4 py-3 d-flex justify-space-between align-center bg-grey-lighten-5">
        <div class="d-flex align-center">
          <v-icon icon="mdi-ticket-outline" color="primary" class="mr-2"></v-icon>
          <span class="font-weight-bold text-primary">{{ priceDisplay }}</span>
        </div>

        <v-btn
          variant="flat"
          color="primary"
          size="small"
          class="text-none font-weight-bold px-4"
          :class="{ 'v-btn--active': isHovering }"
        >
          View Details
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-hover>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  event: {
    type: Object,
    required: true,
    default: () => ({
      id: 0,
      name: 'Default Event Title',
      date: new Date().toISOString(),
      location: 'Default Location',
      description: 'This is a default description for an event.',
      image_url: 'https://cdn.vuetifyjs.com/images/cards/docks.jpg',
    })
  }
});

// Format Date for the Badge (e.g., "OCT" "24")
const eventDate = computed(() => {
  const date = new Date(props.event.date);
  return {
    month: date.toLocaleString('default', { month: 'short' }).toUpperCase(),
    day: date.getDate(),
    time: date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    fullDate: date.toLocaleDateString('en-GB', {
      weekday: 'short',
      day: 'numeric',
      month: 'short',
      year: 'numeric'
    }),
  };
});

// Strip HTML and markdown tags for clean preview text
function stripMarkdown(text) {
  if (!text) return '';
  return text
    .replace(/<[^>]*>/g, '')         // Remove HTML tags
    .replace(/[#*_~`>\-|]/g, '')     // Remove markdown syntax characters
    .replace(/\[([^\]]*)\]\([^)]*\)/g, '$1') // Convert links to just text
    .replace(/!\[([^\]]*)\]\([^)]*\)/g, '')  // Remove images
    .replace(/&amp;/g, '&')          // Decode HTML entities
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/\s+/g, ' ')            // Collapse whitespace
    .trim();
}

// Price Formatting
const priceDisplay = computed(() => {
  // Check if event has ticket types with varying prices
  if (props.event.ticket_types && props.event.ticket_types.length > 0) {
    const prices = props.event.ticket_types
      .filter(t => t.is_active)
      .map(t => parseFloat(t.price_euros));

    if (prices.length === 0) return 'Free';

    const minPrice = Math.min(...prices);
    const maxPrice = Math.max(...prices);

    if (minPrice === 0 && maxPrice === 0) return 'Free';
    if (minPrice === maxPrice) return `€${minPrice.toFixed(2)}`;
    return `€${minPrice.toFixed(2)} - €${maxPrice.toFixed(2)}`;
  }

  // Fall back to base event price
  const price = parseFloat(props.event.price_euros);
  if (!price || price === 0) return 'Free';
  return `€${price.toFixed(2)}`;
});
</script>

<style scoped>
.event-card {
  overflow: hidden; /* Ensures zoomed image stays within rounded corners */
  display: flex;
  flex-direction: column;
}

.image-container {
  position: relative;
  overflow: hidden;
}

/* Date Badge Styles */
.date-badge {
  position: absolute;
  top: 16px;
  left: 16px;
  width: 50px;
  overflow: hidden;
  z-index: 2;
  border: 1px solid rgba(0,0,0,0.05);
}

.category-chip {
  position: absolute;
  top: 16px;
  right: 16px;
  z-index: 2;
  opacity: 0.9;
}

/* Hover Zoom Effect */
.event-image {
  transition: transform 0.4s ease;
}

.zoom-effect {
  transform: scale(1.05);
}

.text-truncate-2-lines {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  height: 40px; /* Adjust based on line-height */
}
</style>
