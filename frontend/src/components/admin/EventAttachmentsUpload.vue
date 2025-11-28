<template>
  <v-card class="mb-4">
    <v-card-title>
      Event Attachments
      <v-chip v-if="attachments && attachments.length > 0" size="small" class="ml-2">
        {{ attachments.length }} file{{ attachments.length !== 1 ? 's' : '' }}
      </v-chip>
    </v-card-title>
    <v-card-text>
      <v-alert type="info" variant="tonal" density="compact" class="mb-4">
        <v-icon start size="small">mdi-paperclip</v-icon>
        Upload files (presentations, guides, worksheets) for participants to download
      </v-alert>

      <!-- Existing Attachments List -->
      <v-list v-if="attachments && attachments.length > 0" class="mb-4">
        <v-list-item
          v-for="(attachment, index) in localAttachments"
          :key="attachment.attachment_id"
          class="attachment-item mb-2 pa-3"
          border
          rounded
        >
          <template v-slot:prepend>
            <v-icon :color="getFileIconColor(attachment.file_type)" size="large">
              {{ getFileIcon(attachment.file_type) }}
            </v-icon>
          </template>

          <v-list-item-title class="font-weight-medium">
            {{ attachment.file_name }}
          </v-list-item-title>

          <v-list-item-subtitle v-if="attachment.description" class="mt-1">
            {{ attachment.description }}
          </v-list-item-subtitle>

          <v-list-item-subtitle class="text-caption mt-1">
            {{ formatFileSize(attachment.file_size_bytes) }} •
            {{ formatDate(attachment.uploaded_at) }}
          </v-list-item-subtitle>

          <template v-slot:append>
            <div class="d-flex gap-2">
              <v-btn
                icon="mdi-pencil"
                size="small"
                variant="text"
                @click="editAttachment(attachment)"
              />
              <v-btn
                icon="mdi-download"
                size="small"
                variant="text"
                color="primary"
                :href="attachment.file_url"
                target="_blank"
              />
              <v-btn
                icon="mdi-delete"
                size="small"
                variant="text"
                color="error"
                @click="deleteAttachment(attachment.attachment_id)"
              />
            </div>
          </template>
        </v-list-item>
      </v-list>

      <v-alert v-else type="info" variant="tonal" class="mb-4">
        No attachments uploaded yet
      </v-alert>

      <!-- Upload Section -->
      <v-divider class="my-4"></v-divider>

      <v-file-input
        v-model="selectedFile"
        label="Upload Attachment"
        accept=".pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.txt,.csv,.zip,.rar,.7z,.jpg,.jpeg,.png,.gif,.svg"
        prepend-icon="mdi-file-upload"
        variant="outlined"
        show-size
        hint="Allowed: PDF, Office files, images, archives (max 50MB)"
        persistent-hint
        @update:model-value="onFileSelected"
      />

      <v-text-field
        v-model="description"
        label="Description (Optional)"
        variant="outlined"
        placeholder="e.g., Day 1 Presentation, Workshop Guide"
        class="mt-4"
        hint="Add a brief description to help participants identify the file"
        persistent-hint
      />

      <v-btn
        color="primary"
        :disabled="!selectedFile || uploading"
        :loading="uploading"
        @click="uploadAttachment"
        class="mt-4"
      >
        <v-icon start>mdi-cloud-upload</v-icon>
        Upload Attachment
      </v-btn>
    </v-card-text>
  </v-card>

  <!-- Edit Dialog -->
  <v-dialog v-model="editDialog.show" max-width="500">
    <v-card>
      <v-card-title class="text-h6">Edit Attachment</v-card-title>
      <v-card-text>
        <v-text-field
          v-model="editDialog.description"
          label="Description"
          variant="outlined"
          placeholder="e.g., Day 1 Presentation"
        />
      </v-card-text>
      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn color="grey" variant="text" @click="editDialog.show = false">
          Cancel
        </v-btn>
        <v-btn color="primary" variant="text" @click="saveEdit" :loading="editDialog.loading">
          Save
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <!-- Delete Dialog -->
  <v-dialog v-model="deleteDialog.show" max-width="400">
    <v-card>
      <v-card-title class="text-h6">Delete Attachment?</v-card-title>
      <v-card-text>
        Are you sure you want to delete this attachment? Participants will no longer be able to download it.
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
  attachments: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits(['updated'])

const selectedFile = ref(null)
const description = ref('')
const uploading = ref(false)
const snackbar = ref({ show: false, text: '', color: '' })
const deleteDialog = ref({ show: false, loading: false, attachmentId: null })
const editDialog = ref({ show: false, loading: false, attachmentId: null, description: '' })

const localAttachments = ref([])

watch(() => props.attachments, (newAttachments) => {
  if (newAttachments) {
    localAttachments.value = [...newAttachments].sort((a, b) => a.display_order - b.display_order)
  }
}, { immediate: true })

const onFileSelected = () => {
  // File selected
}

const showSnackbar = (text, color = 'success') => {
  snackbar.value = { show: true, text, color }
}

const uploadAttachment = async () => {
  if (!selectedFile.value) return

  uploading.value = true
  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    if (description.value) {
      formData.append('description', description.value)
    }

    await apiClient.post(
      `/events/${props.eventId}/attachments`,
      formData,
      {
        headers: { 'Content-Type': 'multipart/form-data' }
      }
    )

    // Refresh event data
    const response = await apiClient.get(`/events/${props.eventId}`)
    emit('updated', response.data)

    selectedFile.value = null
    description.value = ''
    showSnackbar('Attachment uploaded successfully!', 'success')
  } catch (error) {
    console.error('Failed to upload attachment:', error)
    const errorMsg = error.response?.data?.detail || 'Failed to upload attachment'
    showSnackbar(errorMsg, 'error')
  } finally {
    uploading.value = false
  }
}

const editAttachment = (attachment) => {
  editDialog.value = {
    show: true,
    loading: false,
    attachmentId: attachment.attachment_id,
    description: attachment.description || ''
  }
}

const saveEdit = async () => {
  editDialog.value.loading = true
  try {
    await apiClient.patch(
      `/events/${props.eventId}/attachments/${editDialog.value.attachmentId}`,
      { description: editDialog.value.description }
    )

    const response = await apiClient.get(`/events/${props.eventId}`)
    emit('updated', response.data)

    showSnackbar('Attachment updated successfully', 'success')
    editDialog.value.show = false
  } catch (error) {
    console.error('Failed to update attachment:', error)
    showSnackbar('Failed to update attachment', 'error')
  } finally {
    editDialog.value.loading = false
  }
}

const deleteAttachment = (attachmentId) => {
  deleteDialog.value = { show: true, loading: false, attachmentId }
}

const confirmDelete = async () => {
  deleteDialog.value.loading = true
  try {
    await apiClient.delete(
      `/events/${props.eventId}/attachments/${deleteDialog.value.attachmentId}`
    )

    const response = await apiClient.get(`/events/${props.eventId}`)
    emit('updated', response.data)

    showSnackbar('Attachment deleted successfully', 'success')
    deleteDialog.value.show = false
  } catch (error) {
    console.error('Failed to delete attachment:', error)
    showSnackbar('Failed to delete attachment', 'error')
  } finally {
    deleteDialog.value.loading = false
  }
}

const getFileIcon = (fileType) => {
  const iconMap = {
    pdf: 'mdi-file-pdf-box',
    doc: 'mdi-file-word',
    docx: 'mdi-file-word',
    ppt: 'mdi-file-powerpoint',
    pptx: 'mdi-file-powerpoint',
    xls: 'mdi-file-excel',
    xlsx: 'mdi-file-excel',
    txt: 'mdi-file-document',
    csv: 'mdi-file-delimited',
    zip: 'mdi-folder-zip',
    rar: 'mdi-folder-zip',
    '7z': 'mdi-folder-zip',
    jpg: 'mdi-file-image',
    jpeg: 'mdi-file-image',
    png: 'mdi-file-image',
    gif: 'mdi-file-image',
    svg: 'mdi-file-image'
  }
  return iconMap[fileType?.toLowerCase()] || 'mdi-file'
}

const getFileIconColor = (fileType) => {
  const colorMap = {
    pdf: 'red',
    doc: 'blue',
    docx: 'blue',
    ppt: 'orange',
    pptx: 'orange',
    xls: 'green',
    xlsx: 'green',
    zip: 'purple',
    rar: 'purple',
    '7z': 'purple'
  }
  return colorMap[fileType?.toLowerCase()] || 'grey'
}

const formatFileSize = (bytes) => {
  if (!bytes) return ''
  const units = ['B', 'KB', 'MB', 'GB']
  let size = bytes
  let unitIdx = 0
  while (size >= 1024 && unitIdx < units.length - 1) {
    size /= 1024
    unitIdx++
  }
  return `${size.toFixed(1)} ${units[unitIdx]}`
}

const formatDate = (dateString) => {
  return new Date(dateString).toLocaleDateString()
}
</script>

<style scoped>
.attachment-item {
  transition: all 0.2s ease;
}

.attachment-item:hover {
  background-color: rgba(0, 0, 0, 0.02);
}
</style>
