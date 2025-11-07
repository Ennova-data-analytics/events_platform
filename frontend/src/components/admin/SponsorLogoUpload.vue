<template>
  <v-card class="mb-4">
    <v-card-title>Sponsor Logos</v-card-title>
    <v-card-text>
      <v-row v-if="logos && logos.length > 0" class="mb-4">
        <v-col
          v-for="(logo, index) in logos"
          :key="index"
          cols="6"
          sm="4"
          md="3"
        >
          <v-card>
            <v-img :src="logo" height="100" contain />
            <v-card-actions>
              <v-btn
                size="small"
                color="error"
                icon="mdi-delete"
                @click="deleteLogo(index)"
              />
            </v-card-actions>
          </v-card>
        </v-col>
      </v-row>

      <v-alert v-else type="info" variant="tonal" class="mb-4">
        No sponsor logos uploaded yet
      </v-alert>

      <v-file-input
        v-model="selectedFiles"
        label="Upload Sponsor Logos"
        multiple
        accept="image/*"
        prepend-icon="mdi-image-multiple"
        variant="outlined"
        show-size
        hint="For best results, upload PNG files with transparent backgrounds"
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

      <v-checkbox
        v-if="processImages"
        v-model="removeBackground"
        label="Remove background with AI (experimental)"
        hint="May produce artifacts - recommended only for logos with solid backgrounds"
        persistent-hint
        color="warning"
        class="ml-4"
      />

      <v-btn
        color="primary"
        :disabled="!selectedFiles || selectedFiles.length === 0 || uploading"
        :loading="uploading"
        @click="uploadLogos"
        class="mt-2"
      >
        <v-icon start>mdi-cloud-upload</v-icon>
        Upload Logos
      </v-btn>

      <v-alert
        v-if="processImages && !removeBackground"
        type="info"
        variant="tonal"
        density="compact"
        class="mt-4"
      >
        <v-icon start size="small">mdi-image-auto-adjust</v-icon>
        Images will be resized and optimized for fast loading
      </v-alert>

      <v-alert
        v-if="processImages && removeBackground"
        type="warning"
        variant="tonal"
        density="compact"
        class="mt-4"
      >
        <v-icon start size="small">mdi-magic-staff</v-icon>
        AI background removal enabled - this may produce artifacts on some images. Best for logos with solid color backgrounds.
      </v-alert>
    </v-card-text>
  </v-card>

  <v-dialog v-model="deleteDialog.show" max-width="400">
    <v-card>
      <v-card-title class="text-h6">Delete Sponsor Logo?</v-card-title>
      <v-card-text>
        Are you sure you want to delete this sponsor logo? This action cannot be undone.
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
import { ref, defineProps, defineEmits } from 'vue'
import apiClient from '@/services/ApiClient'

const props = defineProps({
  eventId: {
    type: Number,
    required: true
  },
  logos: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['updated'])

const selectedFiles = ref(null)
const uploading = ref(false)
const processImages = ref(true)
const removeBackground = ref(false)
const snackbar = ref({ show: false, text: '', color: '' })
const deleteDialog = ref({ show: false, loading: false, logoIndex: null })

const onFilesSelected = () => {
}

const showSnackbar = (text, color = 'success') => {
  snackbar.value = { show: true, text, color }
}

const uploadLogos = async () => {
  if (!selectedFiles.value || selectedFiles.value.length === 0) return

  uploading.value = true
  try {
    const formData = new FormData()
    selectedFiles.value.forEach(file => {
      formData.append('logo_files', file)
    })

    const response = await apiClient.post(
      `/events/${props.eventId}/sponsor-logos`,
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' },
        params: {
          process_images: processImages.value,
          remove_background: removeBackground.value
        }
      }
    )

    emit('updated', response.data)
    selectedFiles.value = null
    showSnackbar('Sponsor logos uploaded and processed successfully!', 'success')
  } catch (error) {
    console.error('Failed to upload sponsor logos:', error)
    const errorMsg = error.response?.data?.detail || 'Failed to upload sponsor logos'
    showSnackbar(errorMsg, 'error')
  } finally {
    uploading.value = false
  }
}

const deleteLogo = (index) => {
  deleteDialog.value = { show: true, loading: false, logoIndex: index }
}

const confirmDelete = async () => {
  deleteDialog.value.loading = true
  try {
    const response = await apiClient.delete(
      `/events/${props.eventId}/sponsor-logos/${deleteDialog.value.logoIndex}`
    )
    emit('updated', response.data)
    showSnackbar('Sponsor logo deleted successfully', 'success')
    deleteDialog.value.show = false
  } catch (error) {
    console.error('Failed to delete sponsor logo:', error)
    showSnackbar('Failed to delete sponsor logo', 'error')
  } finally {
    deleteDialog.value.loading = false
  }
}
</script>
