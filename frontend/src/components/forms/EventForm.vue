<template>
  <v-form @submit.prevent="handleSubmit">
    <v-text-field
      v-model="editableEvent.event_name"
      label="Event Name"
      variant="outlined"
      class="mb-4"
    />
    
    <v-textarea
      v-model="editableEvent.description"
      label="Description"
      variant="outlined"
      class="mb-4"
    />
    
    <v-row>
      <v-col cols="12" sm="6">
        <v-text-field
          v-model="editableEvent.event_date_start"
          label="Date & Time (YYYY-MM-DDTHH:MM:SS)"
          placeholder="e.g., 2025-10-22T18:00:00"
          variant="outlined"
          class="mb-4"
        />
      </v-col>
      <v-col cols="12" sm="6">
        <v-text-field
          v-model="editableEvent.location"
          label="Location"
          variant="outlined"
          class="mb-4"
        />
      </v-col>
    </v-row>
    
    <v-row>
      <v-col cols="12" sm="6">
        <v-text-field
          v-model.number="editableEvent.price_euros"
          label="Price (€)"
          type="number"
          variant="outlined"
          class="mb-4"
        />
      </v-col>
      <v-col cols="12" sm="6">
        <v-text-field
          v-model.number="editableEvent.capacity"
          label="Capacity"
          type="number"
          variant="outlined"
          class="mb-4"
        />
      </v-col>
    </v-row>

    <v-row>
      <v-col cols="12">
        <v-select
          v-model="editableEvent.form_template_id"
          :items="formTemplates"
          item-title="template_name"
          item-value="template_id"
          label="Additional Application Form (Optional)"
          variant="outlined"
          clearable
          no-data-text="No custom forms available"
        ></v-select>
      </v-col>
    </v-row>
    
    <v-row>
      <v-col cols="12">
        <v-file-input
          v-model="imageFile"
          label="Event Cover Image"
          variant="outlined"
          prepend-icon=""
          prepend-inner-icon="mdi-camera"
          accept="image/*"
        ></v-file-input>
      </v-col>
    </v-row>
    
    <v-btn type="submit" color="primary" size="large" :loading="isLoading">
      {{ isEditMode ? 'Save Changes' : 'Create Event' }}
    </v-btn>
  </v-form>
</template>

<script setup>
import { ref, watch, computed, onMounted } from 'vue';
import { FormTemplateService } from '@/services/FormTemplateService.js';

const props = defineProps({
  initialData: { type: Object, default: () => ({}) },
  isLoading: { type: Boolean, default: false }
});

const emit = defineEmits(['submit']);

const editableEvent = ref({});
const imageFile = ref([]); 

const formTemplates = ref([]);
const isEditMode = computed(() => props.initialData && props.initialData.event_id);

watch(() => props.initialData, (newData) => {
  const dataToEdit = { ...newData };
  if (dataToEdit.event_date_start) {
    dataToEdit.event_date_start = new Date(dataToEdit.event_date_start).toISOString().slice(0, 19);
  }
  editableEvent.value = dataToEdit;
}, { immediate: true, deep: true });

onMounted(async () => {
  try {
    const response = await FormTemplateService.getAllTemplates();
    formTemplates.value = response.data;
  } catch (error) {
    console.error("Failed to fetch form templates:", error);
  }
});

const handleSubmit = () => {
 
  const fileToSend = imageFile.value;

 
  emit('submit', editableEvent.value, fileToSend);
};
</script>