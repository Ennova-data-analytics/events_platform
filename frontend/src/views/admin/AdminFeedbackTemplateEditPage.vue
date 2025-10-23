<template>
  <div>
    <h1 class="text-h5 mb-4">{{ isEditMode ? 'Edit Feedback Template' : 'Create New Feedback Template' }}</h1>

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
            rows="2"
            class="mb-6"
          ></v-textarea>

          <h2 class="text-h6 mb-4">Feedback Questions</h2>

          <div v-for="(field, index) in template.fields" :key="index" class="field-row mb-6 pb-4 border-b">
            <v-text-field
              v-model="field.label"
              label="Question / Label"
              variant="outlined"
              density="compact"
            ></v-text-field>

            <v-text-field
              v-model="field.name"
              label="Unique Name (e.g., overall_rating)"
              variant="outlined"
              density="compact"
              hint="No spaces, lowercase"
            ></v-text-field>

            <v-select
              v-model="field.type"
              :items="fieldTypes"
              item-title="title"
              item-value="value"
              label="Field Type"
              variant="outlined"
              density="compact"
            ></v-select>

            <v-checkbox v-model="field.required" label="Required" density="compact"></v-checkbox>

            <v-btn
              icon="mdi-delete"
              variant="text"
              color="error"
              @click="removeField(index)"
            ></v-btn>

            <div v-if="['select', 'radio'].includes(field.type)" class="options-input mt-2">
              <v-text-field
                v-model="field.options"
                label="Options (comma-separated)"
                hint="e.g., Excellent, Good, Fair, Poor"
                variant="outlined"
                density="compact"
              ></v-text-field>
            </div>
          </div>

          <v-btn @click="addField" prepend-icon="mdi-plus" class="mb-6">Add Question</v-btn>
          <v-divider class="mb-6"></v-divider>

          <v-btn type="submit" color="primary" size="large">Save Template</v-btn>
          <v-btn to="/admin/feedback-templates" variant="text" class="ml-2">Cancel</v-btn>
        </v-form>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { FeedbackTemplateService } from '@/services/FeedbackTemplateService.js';

const route = useRoute();
const router = useRouter();

const template = ref({
  template_name: '',
  description: '',
  fields: []
});

const fieldTypes = [
  { title: 'Short Answer (single line)', value: 'text' },
  { title: 'Paragraph (multiline)', value: 'textarea' },
  { title: 'Dropdown Menu', value: 'select' },
  { title: 'Multiple choice (select one)', value: 'radio' },
  { title: 'Number', value: 'number' },
  { title: 'Rating (1-5)', value: 'rating' }
];

const isEditMode = computed(() => !!route.params.id);

function addField() {
  template.value.fields.push({
    name: '',
    label: '',
    type: 'text',
    required: false,
    options: ''
  });
}

function removeField(index) {
  template.value.fields.splice(index, 1);
}

async function saveTemplate() {
  const templateData = {
    template_name: template.value.template_name,
    description: template.value.description,
    fields: template.value.fields.map(field => ({
      name: field.name,
      label: field.label,
      type: field.type,
      required: field.required,
      options: field.options ? field.options.split(',').map(opt => opt.trim()) : null
    }))
  };

  try {
    if (isEditMode.value) {
      await FeedbackTemplateService.updateTemplate(route.params.id, templateData);
    } else {
      await FeedbackTemplateService.createTemplate(templateData);
    }
    router.push({ name: 'admin-feedback-templates' });
  } catch (error) {
    console.error('Failed to save template:', error);
  }
}

async function loadTemplate() {
  if (isEditMode.value) {
    try {
      const response = await FeedbackTemplateService.getTemplateById(route.params.id);
      const data = response.data;
      template.value = {
        template_name: data.template_name,
        description: data.description || '',
        fields: data.fields.map(field => ({
          ...field,
          options: field.options ? field.options.join(', ') : ''
        }))
      };
    } catch (error) {
      console.error('Failed to load template:', error);
    }
  }
}

onMounted(loadTemplate);
</script>

<style scoped>
.border-b {
  border-bottom: 1px solid #e0e0e0;
}
</style>