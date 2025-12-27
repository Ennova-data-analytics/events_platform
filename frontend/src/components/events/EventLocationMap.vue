<template>
  <v-card elevation="2" class="pa-4">
    <h3 class="text-h6 font-weight-bold mb-3 d-flex align-center">
      <v-icon start color="primary">mdi-map-marker</v-icon>
      Event Location
    </h3>
    <v-divider class="mb-4"></v-divider>

    <div class="location-info mb-3">
      <p class="text-body-1 font-weight-medium mb-1">{{ displayLocation }}</p>
      <v-chip
        v-if="coordinateSource"
        size="x-small"
        variant="tonal"
        color="info"
        class="mb-2"
      >
        <v-icon start size="x-small">mdi-map-check</v-icon>
        {{ coordinateSource }}
      </v-chip>
      <div>
        <v-btn
          :href="googleMapsUrl"
          target="_blank"
          color="primary"
          variant="tonal"
          size="small"
        >
          <v-icon start>mdi-directions</v-icon>
          Get Directions
        </v-btn>
      </div>
    </div>

    <div v-if="isLoading" class="map-container d-flex align-center justify-center">
      <v-progress-circular indeterminate color="primary"></v-progress-circular>
    </div>

    <div v-else-if="coordinates.lat && coordinates.lng" class="map-container">
      <div ref="mapContainer" class="map"></div>
    </div>

    <v-alert v-else type="info" variant="tonal" density="compact" class="mt-2">
      <v-icon start size="small">mdi-information</v-icon>
      Unable to display map. {{ geocodeError || 'No location data available.' }}
      <br>Click "Get Directions" to view in Google Maps.
    </v-alert>
  </v-card>
</template>

<script setup>
import { ref, onMounted, watch, computed } from 'vue';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: markerIcon2x,
  iconUrl: markerIcon,
  shadowUrl: markerShadow,
});

const props = defineProps({
  displayLocation: {
    type: String,
    required: true
  },
  mapAddress: {
    type: String,
    default: null
  },
  latitude: {
    type: Number,
    default: null
  },
  longitude: {
    type: Number,
    default: null
  }
});

const mapContainer = ref(null);
const map = ref(null);
const marker = ref(null);
const coordinates = ref({ lat: null, lng: null });
const isLoading = ref(false);
const geocodeError = ref(null);
const coordinateSource = ref(null); 

const googleMapsUrl = computed(() => {
  if (coordinates.value.lat && coordinates.value.lng) {
    return `https://www.google.com/maps/dir/?api=1&destination=${coordinates.value.lat},${coordinates.value.lng}`;
  }
  const query = encodeURIComponent(props.mapAddress || props.displayLocation);
  return `https://www.google.com/maps/search/?api=1&query=${query}`;
});

async function geocodeLocation() {
  isLoading.value = true;
  geocodeError.value = null;

  if (props.latitude && props.longitude) {
    coordinates.value = { lat: props.latitude, lng: props.longitude };
    coordinateSource.value = 'Manual Coordinates';
    isLoading.value = false;
    return;
  }


  const addressToGeocode = props.mapAddress || props.displayLocation;

  if (!addressToGeocode) {
    geocodeError.value = 'No address provided';
    isLoading.value = false;
    return;
  }

  try {
    const response = await fetch(
      `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(addressToGeocode)}&limit=1`,
      {
        headers: {
          'User-Agent': 'EventsPlatform/1.0' 
        }
      }
    );
    const data = await response.json();

    if (data && data.length > 0) {
      coordinates.value = {
        lat: parseFloat(data[0].lat),
        lng: parseFloat(data[0].lon)
      };
      coordinateSource.value = props.mapAddress ? 'Geocoded from Map Address' : 'Geocoded from Location';
    } else {
      geocodeError.value = 'Location not found. Please verify the address.';
      coordinateSource.value = null;
    }
  } catch (error) {
    console.error('Geocoding failed:', error);
    geocodeError.value = 'Failed to geocode location.';
    coordinateSource.value = null;
  } finally {
    isLoading.value = false;
  }
}

function initMap() {
  if (!mapContainer.value || !coordinates.value.lat || !coordinates.value.lng) return;

  destroyMap();

  map.value = L.map(mapContainer.value).setView(
    [coordinates.value.lat, coordinates.value.lng],
    15
  );

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19
  }).addTo(map.value);

  marker.value = L.marker([coordinates.value.lat, coordinates.value.lng])
    .addTo(map.value)
    .bindPopup(`<b>${props.displayLocation}</b>`)
    .openPopup();
}

function destroyMap() {
  if (map.value) {
    map.value.remove();
    map.value = null;
  }
}

onMounted(async () => {
  await geocodeLocation();
  if (coordinates.value.lat && coordinates.value.lng) {
    setTimeout(() => initMap(), 100);
  }
});

watch([() => props.displayLocation, () => props.mapAddress, () => props.latitude, () => props.longitude], async () => {
  destroyMap();
  await geocodeLocation();
  if (coordinates.value.lat && coordinates.value.lng) {
    setTimeout(() => initMap(), 100);
  }
});
</script>

<style scoped>
.map-container {
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.map {
  width: 100%;
  height: 400px;
  z-index: 1;
}

.location-info {
  background-color: rgba(25, 118, 210, 0.04);
  padding: 12px;
  border-radius: 8px;
  border-left: 4px solid #1976d2;
}
</style>