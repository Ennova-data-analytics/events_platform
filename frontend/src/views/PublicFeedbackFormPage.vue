<template>
  <v-container class="py-8">
    <v-row justify="center">
      <v-col cols="12" md="8" lg="6">
        <v-card v-if="isLoading" class="pa-8 text-center">
          <v-progress-circular indeterminate color="primary" size="64"></v-progress-circular>
        </v-card>

        <v-card v-else-if="submitted" class="pa-8 text-center">
          <v-icon icon="mdi-check-circle" color="success" size="64" class="mb-4"></v-icon>
          <h2 class="text-h5 mb-4">Thank You!</h2>
          <p class="text-body-1">Your feedback has been submitted successfully.</p>
        </v-card>

        <v-card v-else-if="template">
          <v-card-title class="text-h5 pa-6">
            {{ template.template_name }}
          </v-card-title>

          <v-card-text v-if="template.description" class="pb-0">
            <p class="text-body-2 text-grey-darken-1">{{ template.description }}</p>
          </v-card-text>

          <v-card-text class="px-6 pb-6">
            <v-form ref="formRef" @submit.prevent="submitFeedback">
              <div v-for="(field, index) in template.fields" :key="index" class="mb-4">
                <!-- Text input -->
                <v-text-field
                  v-if="field.type === 'text'"
                  v-model="formData[field.name]"
                  :label="field.label"
                  :required="field.required"
                  :rules="field.required ? [v => !!v || `${field.label} is required`] : []"
                  variant="outlined"
                ></v-text-field>

                <!-- Textarea -->
                <v-textarea
                  v-else-if="field.type === 'textarea'"
                  v-model="formData[field.name]"
                  :label="field.label"
                  :required="field.required"
                  :rules="field.required ? [v => !!v || `${field.label} is required`] : []"
                  variant="outlined"
                  rows="4"
                ></v-textarea>

                <!-- Number input -->
                <v-text-field
                  v-else-if="field.type === 'number'"
                  v-model.number="formData[field.name]"
                  :label="field.label"
                  :required="field.required"
                  :rules="field.required ? [v => v !== null && v !== '' || `${field.label} is required`] : []"
                  type="number"
                  variant="outlined"
                ></v-text-field>

                <!-- Rating -->
                <div v-else-if="field.type === 'rating'">
                  <label class="text-body-2 mb-2 d-block">{{ field.label }}</label>
                  <v-rating
                    v-model="formData[field.name]"
                    color="warning"
                    length="5"
                    hover
                  ></v-rating>
                </div>

                <!-- Select dropdown -->
                <v-select
                  v-else-if="field.type === 'select'"
                  v-model="formData[field.name]"
                  :label="field.label"
                  :items="field.options"
                  :required="field.required"
                  :rules="field.required ? [v => !!v || `${field.label} is required`] : []"
                  variant="outlined"
                ></v-select>

                <!-- Radio buttons -->
                <div v-else-if="field.type === 'radio'">
                  <label class="text-body-2 mb-2 d-block">{{ field.label }}</label>
                  <v-radio-group
                    v-model="formData[field.name]"
                    :required="field.required"
                    :rules="field.required ? [v => !!v || `${field.label} is required`] : []"
                  >
                    <v-radio
                      v-for="option in field.options"
                      :key="option"
                      :label="option"
                      :value="option"
                    ></v-radio>
                  </v-radio-group>
                </div>
              </div>

              <v-alert type="info" variant="tonal" class="mb-4">
                All feedback is submitted anonymously to encourage honest responses.
              </v-alert>

              <v-btn
                type="submit"
                color="primary"
                size="large"
                block
                :loading="isSubmitting"
              >
                Submit Feedback
              </v-btn>
            </v-form>
          </v-card-text>
        </v-card>

        <v-alert v-else type="error" class="mb-0">
          Feedback form not available for this event.
        </v-alert>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { FeedbackService } from '@/services/FeedbackService.js';

const route = useRoute();
const eventId = route.params.id;

const template = ref(null);
const formData = ref({});
const isLoading = ref(true);
const isSubmitting = ref(false);
const submitted = ref(false);
const formRef = ref(null);

async function loadTemplate() {
  isLoading.value = true;
  try {
    const response = await FeedbackService.getFeedbackTemplate(eventId);
    template.value = response.data;

    template.value.fields.forEach(field => {
      formData.value[field.name] = field.type === 'rating' ? 0 : '';
    });
  } catch (error) {
    console.error('Failed to load feedback template:', error);
  } finally {
    isLoading.value = false;
  }
}

async function submitFeedback() {
  const { valid } = await formRef.value.validate();

  if (!valid) return;

  isSubmitting.value = true;
  try {
    await FeedbackService.submitFeedback(eventId, {
      form_responses: formData.value,
      is_anonymous: true  
    });
    submitted.value = true;
  } catch (error) {
    console.error('Failed to submit feedback:', error);
    if (error.response?.status === 400 && error.response?.data?.detail?.includes('already submitted')) {
      alert('You have already submitted feedback for this event.');
    } else {
      alert('Failed to submit feedback. Please try again.');
    }
  } finally {
    isSubmitting.value = false;
  }
}

onMounted(loadTemplate);
</script>
