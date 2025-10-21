<template>
  <div>
    <h1 class="text-h5 mb-4">{{ isEditMode ? 'Edit Email Template' : 'Create New Email Template' }}</h1>

    <v-card>
      <v-card-text>
        <v-form @submit.prevent="saveTemplate">
          <v-text-field
            v-model="template.template_name"
            label="Template Name"
            variant="outlined"
            class="mb-4"
            :rules="[v => !!v || 'Template name is required']"
          ></v-text-field>

          <v-textarea
            v-model="template.description"
            label="Description (optional)"
            variant="outlined"
            class="mb-4"
            rows="2"
          ></v-textarea>

          <v-select
            v-model="template.template_type"
            :items="templateTypes"
            item-title="title"
            item-value="value"
            label="Template Type"
            variant="outlined"
            class="mb-4"
            :rules="[v => !!v || 'Template type is required']"
          ></v-select>

          <v-alert type="info" variant="tonal" class="mb-4">
            <strong>Available Variables:</strong>
            <ul class="mt-2">
              <li v-for="variable in getAvailableVariables()" :key="variable">
                <code v-text="'{{ ' + variable + ' }}'"></code>
              </li>
            </ul>
          </v-alert>

          <v-text-field
            v-model="template.subject_template"
            label="Email Subject (optional, uses default if empty)"
            variant="outlined"
            class="mb-4"
            hint="You can use variables in double curly braces"
          ></v-text-field>

          <v-tabs v-model="editorTab" class="mb-4">
            <v-tab value="html">HTML Content</v-tab>
            <v-tab value="text">Plain Text Content</v-tab>
          </v-tabs>

          <v-window v-model="editorTab">
            <v-window-item value="html">
              <v-textarea
                v-model="template.html_content"
                label="HTML Content"
                variant="outlined"
                rows="15"
                class="mb-4"
                hint="Use Jinja2 template syntax with double curly braces and percent signs"
                :rules="[v => !!v || 'HTML content is required']"
              ></v-textarea>
            </v-window-item>

            <v-window-item value="text">
              <v-textarea
                v-model="template.text_content"
                label="Plain Text Content (optional)"
                variant="outlined"
                rows="15"
                class="mb-4"
                hint="Fallback for email clients that don't support HTML"
              ></v-textarea>
            </v-window-item>
          </v-window>

          <v-btn type="submit" color="primary" size="large">Save Template</v-btn>
          <v-btn to="/admin/email-templates" variant="text" class="ml-2">Cancel</v-btn>
        </v-form>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { EmailTemplateService } from '@/services/EmailTemplateService.js';

const route = useRoute();
const router = useRouter();

const template = ref({
  template_name: '',
  description: '',
  template_type: '',
  html_content: '',
  text_content: '',
  subject_template: ''
});

const editorTab = ref('html');

const templateTypes = [
  { title: 'Registration Approved', value: 'registration_approved' },
  { title: 'Registration Rejected', value: 'registration_rejected' },
  { title: 'Registration Received', value: 'registration_received' },
  { title: 'Payment Confirmed', value: 'payment_confirmed' }
];

const templateVariables = {
  registration_approved: ['user_name', 'event_name', 'event_date', 'event_location', 'price', 'event_url', 'header_title'],
  registration_rejected: ['user_name', 'event_name', 'reason', 'header_title'],
  registration_received: ['user_name', 'event_name', 'event_date', 'header_title'],
  payment_confirmed: ['user_name', 'event_name', 'event_date', 'event_location', 'price', 'event_url', 'header_title']
};

const isEditMode = computed(() => !!route.params.id);

function getAvailableVariables() {
  if (!template.value.template_type) return [];
  return templateVariables[template.value.template_type] || [];
}

async function saveTemplate() {
  try {
    if (isEditMode.value) {
      await EmailTemplateService.updateTemplate(route.params.id, template.value);
    } else {
      await EmailTemplateService.createTemplate(template.value);
    }
    router.push({ name: 'admin-email-templates' });
  } catch (error) {
    console.error("Failed to save template:", error);
    alert('Failed to save template. Please check the form and try again.');
  }
}

onMounted(async () => {
  if (isEditMode.value) {
    try {
      const response = await EmailTemplateService.getTemplateById(route.params.id);
      template.value = response.data;
    } catch (error) {
      console.error("Failed to fetch template for editing:", error);
    }
  }
});
</script>

<style scoped>
code {
  background-color: rgba(0, 0, 0, 0.05);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
}
</style>
