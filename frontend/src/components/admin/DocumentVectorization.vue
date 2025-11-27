<template>
  <v-card>
    <v-card-title class="d-flex align-center pa-4">
      <v-icon class="mr-2" color="primary">mdi-file-document-multiple</v-icon>
      Document Vectorization
    </v-card-title>

    <v-divider></v-divider>

    <v-card-text class="pa-6">
      <!-- Upload Area -->
      <v-file-input
        v-model="selectedFile"
        label="Upload Word Document (.docx)"
        accept=".docx"
        prepend-icon="mdi-paperclip"
        variant="outlined"
        :disabled="uploading"
        @change="onFileSelected"
      >
        <template #selection="{ fileNames }">
          <template v-for="fileName in fileNames" :key="fileName">
            {{ fileName }}
          </template>
        </template>
      </v-file-input>

      <!-- Event Association (Optional) -->
      <v-autocomplete
        v-model="associatedEventId"
        :items="events"
        item-title="event_name"
        item-value="event_id"
        label="Associate with Event (Optional)"
        variant="outlined"
        clearable
        class="mt-4"
        :disabled="uploading || loadingEvents"
        :loading="loadingEvents"
      >
        <template #prepend>
          <v-icon>mdi-calendar</v-icon>
        </template>
      </v-autocomplete>

      <!-- Additional Metadata -->
      <v-text-field
        v-model="documentTitle"
        label="Document Title (Optional)"
        variant="outlined"
        class="mt-4"
        :disabled="uploading"
      >
        <template #prepend>
          <v-icon>mdi-text</v-icon>
        </template>
      </v-text-field>

      <v-textarea
        v-model="documentDescription"
        label="Document Description (Optional)"
        variant="outlined"
        rows="3"
        class="mt-4"
        :disabled="uploading"
      >
        <template #prepend>
          <v-icon>mdi-text-box</v-icon>
        </template>
      </v-textarea>

      <!-- Upload Button -->
      <v-btn
        color="primary"
        size="large"
        :disabled="!selectedFile || uploading"
        :loading="uploading"
        @click="uploadDocument"
        block
        class="mt-4"
      >
        <v-icon left class="mr-2">mdi-upload</v-icon>
        Upload & Vectorize
      </v-btn>

      <!-- Upload Progress -->
      <v-progress-linear
        v-if="uploading"
        indeterminate
        color="primary"
        class="mt-4"
      ></v-progress-linear>

      <!-- Status Messages -->
      <v-alert
        v-if="successMessage"
        type="success"
        variant="tonal"
        class="mt-4"
        closable
        @click:close="successMessage = ''"
      >
        {{ successMessage }}
      </v-alert>

      <v-alert
        v-if="errorMessage"
        type="error"
        variant="tonal"
        class="mt-4"
        closable
        @click:close="errorMessage = ''"
      >
        {{ errorMessage }}
      </v-alert>

      <!-- Info Card -->
      <v-card variant="outlined" class="mt-6 bg-blue-lighten-5">
        <v-card-text>
          <div class="d-flex align-start">
            <v-icon color="info" class="mr-3">mdi-information</v-icon>
            <div>
              <div class="font-weight-bold mb-2">How it works:</div>
              <ul class="text-body-2">
                <li>Upload Word documents (.docx) to make them searchable by the AI chatbot</li>
                <li>Documents are processed, chunked, and stored as vector embeddings</li>
                <li>Users can then ask questions about the content</li>
                <li>Optionally associate documents with specific events for better context</li>
              </ul>
            </div>
          </div>
        </v-card-text>
      </v-card>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { ChatService } from '@/services/ChatService';
import { EventService } from '@/services/EventService';

const selectedFile = ref(null);
const associatedEventId = ref(null);
const documentTitle = ref('');
const documentDescription = ref('');
const uploading = ref(false);
const successMessage = ref('');
const errorMessage = ref('');
const events = ref([]);
const loadingEvents = ref(false);

const onFileSelected = () => {
  if (!selectedFile.value) {
    documentTitle.value = '';
    return;
  }

  // Auto-populate title from filename if empty
  // Handle both array and single file formats from v-file-input
  const file = Array.isArray(selectedFile.value) ? selectedFile.value[0] : selectedFile.value;
  if (!documentTitle.value && file?.name) {
    documentTitle.value = file.name.replace('.docx', '');
  }
};

const uploadDocument = async () => {
  if (!selectedFile.value) {
    errorMessage.value = 'Please select a document to upload';
    return;
  }

  uploading.value = true;
  errorMessage.value = '';
  successMessage.value = '';

  try {
    // v-file-input returns array of files when multiple=false, or single file
    const file = Array.isArray(selectedFile.value) ? selectedFile.value[0] : selectedFile.value;

    if (!file) {
      errorMessage.value = 'Please select a valid document';
      uploading.value = false;
      return;
    }

    const response = await ChatService.vectorizeDocument(
      file,
      associatedEventId.value
    );

    successMessage.value = `Successfully processed ${response.data.chunks_processed} chunks from the document!`;

    // Reset form
    selectedFile.value = null;
    associatedEventId.value = null;
    documentTitle.value = '';
    documentDescription.value = '';
  } catch (error) {
    console.error('Upload failed:', error);
    errorMessage.value = error.response?.data?.detail || 'Failed to upload and vectorize document';
  } finally {
    uploading.value = false;
  }
};

const loadEvents = async () => {
  loadingEvents.value = true;
  try {
    const response = await EventService.fetchEvents();
    events.value = response.data;
  } catch (error) {
    console.error('Failed to load events:', error);
  } finally {
    loadingEvents.value = false;
  }
};

onMounted(() => {
  loadEvents();
});
</script>

<style scoped>
ul {
  list-style-position: inside;
}
</style>
