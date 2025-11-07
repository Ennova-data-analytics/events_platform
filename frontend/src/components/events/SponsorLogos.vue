<template>
  <v-container v-if="logos && logos.length > 0" class="sponsor-section">
    <v-row justify="center" align="center" class="sponsor-logos">
      <v-col
        v-for="(logo, index) in logos"
        :key="index"
        cols="6"
        sm="4"
        md="3"
        lg="2"
        class="d-flex justify-center"
      >
        <v-img
          :src="logo"
          alt="Sponsor logo"
          max-width="250"
          max-height="150"
          contain
          class="sponsor-logo"
        />
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { defineProps } from 'vue'

defineProps({
  logos: {
    type: Array,
    default: () => []
  }
})
</script>

<style scoped>
.sponsor-section {
  margin-top: 2rem;
  padding: 1.5rem 0;
  border-top: 1px solid #e0e0e0;
}

.sponsor-logos {
  gap: 1rem;
}

.sponsor-logo {
  filter: grayscale(100%);
  opacity: 0.7;
  transition: all 0.3s ease;
}

.sponsor-logo:hover {
  filter: grayscale(0%);
  opacity: 1;
  transform: scale(1.05);
}
</style>
