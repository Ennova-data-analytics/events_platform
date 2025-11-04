<template>
  <v-container class="tutorial-page">
    <v-row justify="center">
      <v-col cols="12" md="10" lg="8">
        <div class="text-center mb-8">
          <v-icon size="64" color="primary" class="mb-4">mdi-play-circle</v-icon>
          <h1 class="text-h3 mb-2">Platform Tutorial</h1>
          <p class="text-subtitle-1 text-medium-emphasis">
            Learn how to use the Events Platform with our comprehensive video guide
          </p>
        </div>

        <v-card elevation="2" class="mb-8">
          <v-card-title class="text-h5 bg-primary">
            <v-icon start>mdi-school</v-icon>
            Getting Started with the Events Platform
          </v-card-title>

          <v-card-text class="pa-6">
            <YoutubeEmbed
              :videoId="tutorialVideoId"
              title="Events Platform Tutorial"
            />
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref } from 'vue'
import YoutubeEmbed from '@/components/media/YoutubeEmbed.vue'

const tutorialVideoId = ref('ylC1TubJffs')
</script>

<style scoped>
.tutorial-page {
  padding-top: 40px;
  padding-bottom: 60px;
}

.bg-primary {
  background-color: rgb(var(--v-theme-primary));
  color: white;
}
</style>
