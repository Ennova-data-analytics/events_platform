<template>
  <div>
    <div class="d-flex justify-space-between align-center mb-4">
      <h1 class="text-h5">Manage Email Templates</h1>
      <v-btn to="/admin/email-templates/create" color="primary" prepend-icon="mdi-plus">
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
          <template v-slot:item.template_type="{ item }">
            <v-chip size="small" :color="getTypeColor(item.template_type)">
              {{ formatType(item.template_type) }}
            </v-chip>
          </template>
          <template v-slot:item.actions="{ item }">
            <v-btn icon="mdi-pencil" variant="text" size="small" :to="{ name: 'admin-email-template-edit', params: { id: item.template_id } }"></v-btn>
            <v-btn icon="mdi-delete" variant="text" size="small" color="error" @click="handleDelete(item)"></v-btn>
          </template>
        </v-data-table>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { EmailTemplateService } from '@/services/EmailTemplateService.js';

const templates = ref([]);
const isLoading = ref(true);
const headers = ref([
  { title: 'Template Name', key: 'template_name' },
  { title: 'Type', key: 'template_type' },
  { title: 'Description', key: 'description' },
  { title: 'Actions', key: 'actions', sortable: false, align: 'end' },
]);

async function fetchTemplates() {
  isLoading.value = true;
  try {
    const response = await EmailTemplateService.getAllTemplates();
    templates.value = response.data;
  } catch (error) {
    console.error("Failed to fetch email templates:", error);
  } finally {
    isLoading.value = false;
  }
}

async function handleDelete(item) {
  if (confirm(`Are you sure you want to delete the template "${item.template_name}"?`)) {
    try {
      await EmailTemplateService.deleteTemplate(item.template_id);
      await fetchTemplates();
    } catch (error) {
      console.error("Failed to delete template:", error);
    }
  }
}

function formatType(type) {
  return type
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

function getTypeColor(type) {
  const colors = {
    'registration_approved': 'success',
    'registration_rejected': 'error',
    'registration_received': 'info',
    'payment_confirmed': 'primary',
  };
  return colors[type] || 'default';
}

onMounted(fetchTemplates);
</script>
