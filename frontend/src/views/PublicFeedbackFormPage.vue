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
              <div v-for="(field, index) in template.fields" :key="index" class="mb-8">
                <!-- Text input -->
                <div v-if="field.type === 'text'" class="field-wrapper">
                  <label class="text-body-1 font-weight-medium mb-2 d-block">
                    {{ field.label }}
                    <span v-if="field.required" class="text-error">*</span>
                  </label>
                  <v-text-field
                    v-model="formData[field.name]"
                    :placeholder="`Enter ${field.label.toLowerCase()}`"
                    :required="field.required"
                    :rules="field.required ? [v => !!v || `${field.label} is required`] : []"
                    variant="outlined"
                    density="comfortable"
                    hide-details="auto"
                  ></v-text-field>
                </div>

                <!-- Textarea -->
                <div v-else-if="field.type === 'textarea'" class="field-wrapper">
                  <label class="text-body-1 font-weight-medium mb-2 d-block">
                    {{ field.label }}
                    <span v-if="field.required" class="text-error">*</span>
                  </label>
                  <v-textarea
                    v-model="formData[field.name]"
                    :placeholder="`Enter your response`"
                    :required="field.required"
                    :rules="field.required ? [v => !!v || `${field.label} is required`] : []"
                    variant="outlined"
                    rows="4"
                    density="comfortable"
                    hide-details="auto"
                  ></v-textarea>
                </div>

                <!-- Number input -->
                <div v-else-if="field.type === 'number'" class="field-wrapper">
                  <label class="text-body-1 font-weight-medium mb-2 d-block">
                    {{ field.label }}
                    <span v-if="field.required" class="text-error">*</span>
                  </label>
                  <v-text-field
                    v-model.number="formData[field.name]"
                    :placeholder="`Enter a number`"
                    :required="field.required"
                    :rules="field.required ? [v => v !== null && v !== '' || `${field.label} is required`] : []"
                    type="number"
                    variant="outlined"
                    density="comfortable"
                    hide-details="auto"
                  ></v-text-field>
                </div>

                <!-- Rating -->
                <div v-else-if="field.type === 'rating'" class="field-wrapper">
                  <label class="text-body-1 font-weight-medium mb-3 d-block">
                    {{ field.label }}
                    <span v-if="field.required" class="text-error">*</span>
                  </label>
                  <v-rating
                    v-model="formData[field.name]"
                    color="warning"
                    length="5"
                    hover
                    size="large"
                  ></v-rating>
                </div>

                <!-- Select dropdown -->
                <div v-else-if="field.type === 'select'" class="field-wrapper">
                  <label class="text-body-1 font-weight-medium mb-2 d-block">
                    {{ field.label }}
                    <span v-if="field.required" class="text-error">*</span>
                  </label>
                  <v-select
                    v-model="formData[field.name]"
                    :placeholder="`Select an option`"
                    :items="field.options"
                    :required="field.required"
                    :rules="field.required ? [v => !!v || `${field.label} is required`] : []"
                    variant="outlined"
                    density="comfortable"
                    hide-details="auto"
                  ></v-select>
                </div>

                <!-- Radio buttons -->
                <div v-else-if="field.type === 'radio'" class="field-wrapper">
                  <label class="text-body-1 font-weight-medium mb-3 d-block">
                    {{ field.label }}
                    <span v-if="field.required" class="text-error">*</span>
                  </label>
                  <v-radio-group
                    v-model="formData[field.name]"
                    :required="field.required"
                    :rules="field.required ? [v => !!v || `${field.label} is required`] : []"
                    hide-details="auto"
                  >
                    <v-radio
                      v-for="option in field.options"
                      :key="option"
                      :label="option"
                      :value="option"
                      class="mb-2"
                    ></v-radio>
                  </v-radio-group>
                </div>
              </div>

              <v-alert v-if="!invitationToken" type="info" variant="tonal" class="mb-4">
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

        <v-card v-else-if="tokenError" class="pa-8 text-center">
          <v-icon icon="mdi-link-off" color="error" size="64" class="mb-4"></v-icon>
          <h2 class="text-h5 mb-4">Link Unavailable</h2>
          <p class="text-body-1">{{ tokenError }}</p>
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

// Support both ?token= (invitation-based) and ?template_id= (QR-based)
const invitationToken = route.query.token || null;
const templateId = route.query.template_id ? parseInt(route.query.template_id) : null;

const template = ref(null);
const formData = ref({});
const isLoading = ref(true);
const isSubmitting = ref(false);
const submitted = ref(false);
const formRef = ref(null);
const tokenError = ref(null);

async function loadTemplate() {
  isLoading.value = true;
  try {
    const response = await FeedbackService.getFeedbackTemplate(eventId, templateId);
    template.value = response.data;

    template.value.fields.forEach(field => {
      formData.value[field.name] = field.type === 'rating' ? 0 : '';
    });
  } catch (error) {
    console.error('Failed to load feedback template:', error);
    if (error.response?.status === 400 || error.response?.status === 404) {
      tokenError.value = error.response?.data?.detail || 'Feedback form not available.';
    }
  } finally {
    isLoading.value = false;
  }
}

async function submitFeedback() {
  const { valid } = await formRef.value.validate();
  if (!valid) return;

  isSubmitting.value = true;
  try {
    if (invitationToken) {
      // Token-based submission (invitation link — registered or external)
      await FeedbackService.submitFeedbackViaToken(eventId, invitationToken, formData.value);
    } else {
      // Anonymous public QR submission
      await FeedbackService.submitFeedback(eventId, {
        form_responses: formData.value,
        is_anonymous: true,
      });
    }
    submitted.value = true;
  } catch (error) {
    console.error('Failed to submit feedback:', error);
    const detail = error.response?.data?.detail || '';
    if (detail.includes('already submitted') || detail.includes('expired') || detail.includes('Invalid')) {
      tokenError.value = detail;
      template.value = null;
    } else {
      alert('Failed to submit feedback. Please try again.');
    }
  } finally {
    isSubmitting.value = false;
  }
}

onMounted(loadTemplate);
</script>
