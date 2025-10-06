<template>
  <div>
    <h1 class="text-h5 mb-4">{{ isEditMode ? 'Edit Form Template' : 'Create New Form Template' }}</h1>
    
    <v-card>
      <v-card-text>
        <v-form @submit.prevent="saveTemplate">
          <v-text-field
            v-model="template.template_name"
            label="Template Name"
            variant="outlined"
            class="mb-6"
            :rules="[v => !!v || 'Template name is required']"
          ></v-text-field>

          <h2 class="text-h6 mb-4">Fields</h2>
          
          <div v-for="(field, index) in template.fields" :key="index" class="field-row mb-6 pb-4">
            <v-text-field v-model="field.label" label="Question / Label" variant="outlined" density="compact"></v-text-field>
            <v-text-field v-model="field.name" label="Unique Name (e.g., team_name)" variant="outlined" density="compact" hint="No spaces, lowercase"></v-text-field>
            
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
            <v-btn icon="mdi-delete" variant="text" color="error" @click="removeField(index)"></v-btn>

            <div v-if="['select', 'radio'].includes(field.type)" class="options-input">
              <v-text-field
                v-model="field.options"
                label="Options (comma-separated)"
                hint="e.g., Option A, Option B, Option C"
                variant="outlined"
                density="compact"
              ></v-text-field>
            </div>
          </div>
          
          <v-btn @click="addField" prepend-icon="mdi-plus" class="mb-6">Add Field</v-btn>
          <v-divider class="mb-6"></v-divider>
          
          <v-btn type="submit" color="primary" size="large">Save Template</v-btn>
          <v-btn to="/admin/forms" variant="text" class="ml-2">Cancel</v-btn>
        </v-form>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { FormTemplateService } from '@/services/FormTemplateService.js';

const route = useRoute();
const router = useRouter();

const template = ref({
  template_name: '',
  fields: []
});

const fieldTypes = [
  {
    title: 'Short Answer (single line)',
    value: 'text'
  },
  {
    title: 'Paragraph (multiline)',
    value: 'textarea'
  },
  {
    title: 'Dropdown Menu',
    value: 'select'
  },
  {
    title: 'Multiple choice (select one)',
    value: 'radio'
  },
  {
    title: 'Checkboxes (select many)',
    value: 'checkbox'
  },
  {
    title: 'File',
    value: 'file'
  }
]

const isEditMode = computed(() => !!route.params.id);

function addField() {
  template.value.fields.push({
    name: '',
    label: '',
    type: 'text',
    required: false,
    options: [] 
  });
}

function removeField(index) {
  template.value.fields.splice(index, 1);
}

async function saveTemplate() {
  const payload = JSON.parse(JSON.stringify(template.value)); 
  payload.fields.forEach(field => {
    if (typeof field.options === 'string') {
      field.options = field.options.split(',').map(opt => opt.trim()).filter(Boolean);
    }
  });

  try {
    if (isEditMode.value) {
      await FormTemplateService.updateTemplate(route.params.id, payload);
    } else {
      await FormTemplateService.createTemplate(payload);
    }
    router.push({ name: 'admin-forms' });
  } catch (error) {
    console.error("Failed to save template:", error);
  }
}

onMounted(async () => {
  if (isEditMode.value) {
    try {
      const response = await FormTemplateService.getTemplateById(route.params.id);
      const data = response.data;
      data.fields.forEach(field => {
        if (Array.isArray(field.options)) {
          field.options = field.options.join(', ');
        }
      });
      template.value = data;
    } catch (error) {
      console.error("Failed to fetch template for editing:", error);
    }
  }
});
</script>

<style scoped>
.field-row {
  display: grid;
  grid-template-columns: repeat(5, 1fr); 
  gap: 16px;
  align-items: start;
  border-bottom: 1px solid rgba(128, 128, 128, 0.2);
  padding-bottom: 16px;
}

.options-input {
  grid-column: 1 / -1; 
}
</style>