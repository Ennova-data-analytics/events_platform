<template>
  <v-card class="mb-4">
    <v-card-title>
      Event Photo Gallery
      <v-chip v-if="photos && photos.length > 0" size="small" class="ml-2">
        {{ photos.length }} photo{{ photos.length !== 1 ? 's' : '' }}
      </v-chip>
    </v-card-title>
    <v-card-text>
      <v-alert v-if="photos && photos.length > 0" type="info" variant="tonal" density="compact" class="mb-4">
        <v-icon start size="small">mdi-drag</v-icon>
        Drag and drop photos to reorder them
      </v-alert>

      <v-row v-if="photos && photos.length > 0" class="mb-4">
        <v-col
          v-for="(photo, index) in localPhotos"
          :key="photo.photo_id"
          cols="12"
          sm="6"
          md="4"
        >
          <v-card
            class="photo-card"
            :class="{ 'dragging': draggedIndex === index }"
            draggable="true"
            @dragstart="handleDragStart(index, $event)"
            @dragend="handleDragEnd"
            @dragover.prevent="handleDragOver(index)"
            @drop.prevent="handleDrop(index)"
          >
            <v-img :src="photo.photo_url" height="200" cover>
              <div class="drag-handle">
                <v-icon color="white" size="large">mdi-drag</v-icon>
              </div>
            </v-img>
            <v-card-subtitle v-if="photo.caption" class="text-wrap">
              {{ photo.caption }}
            </v-card-subtitle>
            <v-card-actions>
              <v-chip size="small" variant="outlined">{{ index + 1 }}</v-chip>
              <v-spacer></v-spacer>
              <v-btn
                size="small"
                color="error"
                icon="mdi-delete"
                @click="deletePhoto(photo.photo_id)"
              />
            </v-card-actions>
          </v-card>
        </v-col>
      </v-row>

      <v-alert v-else type="info" variant="tonal" class="mb-4">
        No event photos uploaded yet
      </v-alert>

      <v-file-input
        v-model="selectedFiles"
        label="Upload Event Photos"
        multiple
        accept="image/*"
        prepend-icon="mdi-image-multiple"
        variant="outlined"
        show-size
        hint="Upload photos from past events to showcase in the photo gallery"
        persistent-hint
        @update:model-value="onFilesSelected"
      />

      <v-checkbox
        v-model="processImages"
        label="Auto-process images (resize and optimize)"
        hint="Resize and optimize images for web display"
        persistent-hint
        class="mt-2"
      />

      <v-btn
        color="primary"
        :disabled="!selectedFiles || selectedFiles.length === 0 || uploading || reordering"
        :loading="uploading"
        @click="uploadPhotos"
        class="mt-2"
      >
        <v-icon start>mdi-cloud-upload</v-icon>
        Upload Photos
      </v-btn>

      <v-progress-linear
        v-if="reordering"
        indeterminate
        color="primary"
        class="mt-2"
      ></v-progress-linear>

      <v-alert
        v-if="processImages"
        type="info"
        variant="tonal"
        density="compact"
        class="mt-4"
      >
        <v-icon start size="small">mdi-image-auto-adjust</v-icon>
        Images will be resized and optimized for fast loading
      </v-alert>
    </v-card-text>
  </v-card>

  <v-dialog v-model="deleteDialog.show" max-width="400">
    <v-card>
      <v-card-title class="text-h6">Delete Event Photo?</v-card-title>
      <v-card-text>
        Are you sure you want to delete this photo? This action cannot be undone.
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn color="grey" variant="text" @click="deleteDialog.show = false">
          Cancel
        </v-btn>
        <v-btn color="error" variant="text" @click="confirmDelete" :loading="deleteDialog.loading">
          Delete
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <v-snackbar v-model="snackbar.show" :color="snackbar.color" timeout="4000">
    {{ snackbar.text }}
  </v-snackbar>
</template>

<script setup>
import { ref, watch, defineProps, defineEmits } from 'vue'
import apiClient from '@/services/ApiClient'

const props = defineProps({
  eventId: {
    type: Number,
    required: true
  },
  photos: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['updated'])

const selectedFiles = ref(null)
const uploading = ref(false)
const processImages = ref(true)
const snackbar = ref({ show: false, text: '', color: '' })
const deleteDialog = ref({ show: false, loading: false, photoId: null })

const localPhotos = ref([])
const draggedIndex = ref(null)
const reordering = ref(false)

watch(() => props.photos, (newPhotos) => {
  if (newPhotos) {
    localPhotos.value = [...newPhotos].sort((a, b) => a.display_order - b.display_order)
  }
}, { immediate: true })

const onFilesSelected = () => {
}

const showSnackbar = (text, color = 'success') => {
  snackbar.value = { show: true, text, color }
}

const uploadPhotos = async () => {
  if (!selectedFiles.value || selectedFiles.value.length === 0) return

  uploading.value = true
  const fileCount = selectedFiles.value.length
  try {
    const formData = new FormData()
    selectedFiles.value.forEach(file => {
      formData.append('photo_files', file)
    })

    const response = await apiClient.post(
      `/events/${props.eventId}/photos`,
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
        params: {
          process_images: processImages.value
        }
      }
    )

    emit('updated', response.data)
    selectedFiles.value = null
    showSnackbar(`${fileCount} photo(s) uploaded successfully!`, 'success')
  } catch (error) {
    console.error('Failed to upload event photos:', error)
    const errorMsg = error.response?.data?.detail || 'Failed to upload event photos'
    showSnackbar(errorMsg, 'error')
  } finally {
    uploading.value = false
  }
}

const deletePhoto = (photoId) => {
  deleteDialog.value = { show: true, loading: false, photoId }
}

const confirmDelete = async () => {
  deleteDialog.value.loading = true
  try {
    await apiClient.delete(
      `/events/${props.eventId}/photos/${deleteDialog.value.photoId}`
    )

    const response = await apiClient.get(`/events/${props.eventId}`)
    emit('updated', response.data)

    showSnackbar('Event photo deleted successfully', 'success')
    deleteDialog.value.show = false
  } catch (error) {
    console.error('Failed to delete event photo:', error)
    showSnackbar('Failed to delete event photo', 'error')
  } finally {
    deleteDialog.value.loading = false
  }
}

const handleDragStart = (index, event) => {
  draggedIndex.value = index
  event.dataTransfer.effectAllowed = 'move'
  event.dataTransfer.setData('text/html', event.target.innerHTML)
}

const handleDragEnd = () => {
  draggedIndex.value = null
}

const handleDragOver = (index) => {
  if (draggedIndex.value !== null && draggedIndex.value !== index) {
    const draggedItem = localPhotos.value[draggedIndex.value]
    const newPhotos = [...localPhotos.value]
    newPhotos.splice(draggedIndex.value, 1)
    newPhotos.splice(index, 0, draggedItem)
    localPhotos.value = newPhotos
    draggedIndex.value = index
  }
}

const handleDrop = async () => {
  if (draggedIndex.value === null) return

  await savePhotoOrder()
}

const savePhotoOrder = async () => {
  if (reordering.value) return

  reordering.value = true
  try {
    const photoIds = localPhotos.value.map(photo => photo.photo_id)

    await apiClient.post(
      `/events/${props.eventId}/photos/reorder`,
      photoIds
    )

    const eventResponse = await apiClient.get(`/events/${props.eventId}`)
    emit('updated', eventResponse.data)

    showSnackbar('Photos reordered successfully', 'success')
  } catch (error) {
    console.error('Failed to reorder photos:', error)
    showSnackbar('Failed to reorder photos', 'error')

    localPhotos.value = [...props.photos].sort((a, b) => a.display_order - b.display_order)
  } finally {
    reordering.value = false
  }
}
</script>

<style scoped>
.photo-card {
  cursor: move;
  transition: all 0.3s ease;
}

.photo-card:hover {
  transform: scale(1.02);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2);
}

.photo-card.dragging {
  opacity: 0.5;
  transform: scale(0.95);
}

.drag-handle {
  position: absolute;
  top: 8px;
  right: 8px;
  background: rgba(0, 0, 0, 0.6);
  border-radius: 50%;
  padding: 4px;
  cursor: move;
  display: none;
}

.photo-card:hover .drag-handle {
  display: block;
}
</style>
