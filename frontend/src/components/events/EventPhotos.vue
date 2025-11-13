<template>
  <v-row v-if="photos && photos.length > 0" class="mt-8">
    <v-col cols="12">
      <v-card elevation="2" class="pa-8">
        <h2 class="text-h4 font-weight-bold mb-6">Past Events Photo Gallery</h2>
        <v-divider class="mb-6"></v-divider>

        <v-row>
          <v-col
            v-for="photo in photos"
            :key="photo.photo_id"
            cols="12"
            sm="6"
            md="4"
          >
            <v-card @click="openLightbox(photo)" class="cursor-pointer">
              <v-img
                :src="photo.photo_url"
                height="250"
                cover
                class="rounded"
              >
                <template v-slot:placeholder>
                  <v-row class="fill-height ma-0" align="center" justify="center">
                    <v-progress-circular
                      indeterminate
                      color="grey-lighten-4"
                      size="64"
                    ></v-progress-circular>
                  </v-row>
                </template>
              </v-img>
              <v-card-subtitle v-if="photo.caption" class="text-wrap">
                {{ photo.caption }}
              </v-card-subtitle>
            </v-card>
          </v-col>
        </v-row>
      </v-card>
    </v-col>
  </v-row>

  <!-- Lightbox Dialog -->
  <v-dialog v-model="lightbox.show" max-width="1200px">
    <v-card>
      <v-card-text class="pa-0">
        <v-img
          :src="lightbox.photo?.photo_url"
          max-height="80vh"
          contain
        >
          <template v-slot:placeholder>
            <v-row class="fill-height ma-0" align="center" justify="center">
              <v-progress-circular
                indeterminate
                color="primary"
                size="64"
              ></v-progress-circular>
            </v-row>
          </template>
        </v-img>
      </v-card-text>
      <v-card-actions v-if="lightbox.photo?.caption">
        <v-card-subtitle class="text-wrap">
          {{ lightbox.photo.caption }}
        </v-card-subtitle>
        <v-spacer></v-spacer>
        <v-btn icon="mdi-close" @click="lightbox.show = false"></v-btn>
      </v-card-actions>
      <v-card-actions v-else class="justify-end">
        <v-btn icon="mdi-close" @click="lightbox.show = false"></v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, defineProps } from 'vue'

defineProps({
  photos: {
    type: Array,
    default: () => []
  }
})

const lightbox = ref({ show: false, photo: null })

const openLightbox = (photo) => {
  lightbox.value = { show: true, photo }
}
</script>

<style scoped>
.cursor-pointer {
  cursor: pointer;
}
</style>
