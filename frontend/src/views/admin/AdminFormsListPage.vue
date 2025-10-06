<template>
  <div>
    <div class="d-flex justify-space-between align-center mb-4">
      <h1 class="text-h5">Manage Form Templates</h1>
      <v-btn to="/admin/forms/create" color="primary" prepend-icon="mdi-plus">
        Create Template
      </v-btn>
    </div>
    
    <v-card>
      <v-card-text>
        <v-data-table
          :headers="headers"
          :items="templates"
          :loading="isLoading"
        >
          <template v-slot:item.actions="{ item }">
            <v-btn icon="mdi-pencil" variant="text" size="small" :to="{ name: 'admin-form-edit', params: { id: item.template_id } }"></v-btn>
            <v-btn icon="mdi-delete" variant="text" size="small" color="error" @click="handleDelete(item)"></v-btn>
          </template>
        </v-data-table>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { FormTemplateService } from '@/services/FormTemplateService.js';

const templates = ref([]);
const isLoading = ref(true);
const headers = ref([
  { title: 'Template Name', key: 'template_name' },
  { title: 'Actions', key: 'actions', sortable: false, align: 'end' },
]);

async function fetchTemplates() {
  isLoading.value = true;
  try {
    const response = await FormTemplateService.getAllTemplates();
    templates.value = response.data;
  } catch (error) {
    console.error("Failed to fetch form templates:", error);
  } finally {
    isLoading.value = false;
  }
}

async function handleDelete(item) {
  if (confirm(`Are you sure you want to delete the template "${item.template_name}"?`)) {
    try {
      await FormTemplateService.deleteTemplate(item.template_id);
      await fetchTemplates(); 
    } catch (error) {
      console.error("Failed to delete template:", error);
    }
  }
}

onMounted(fetchTemplates);
</script>