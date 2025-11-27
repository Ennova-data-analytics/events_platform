<template>
  <v-container fluid class="pa-6">
    <div class="mb-6">
      <h1 class="text-h4 font-weight-bold mb-2">AI Document Management</h1>
      <p class="text-subtitle-1 text-medium-emphasis">
        Upload and manage documents for the Ennova AI chatbot
      </p>
    </div>

    <v-row>
      <v-col cols="12" md="8">
        <DocumentVectorization />
      </v-col>

      <v-col cols="12" md="4">
        <!-- Statistics Card -->
        <v-card class="mb-4">
          <v-card-title class="d-flex align-center pa-4">
            <v-icon class="mr-2" color="primary">mdi-chart-box</v-icon>
            Statistics
          </v-card-title>
          <v-divider></v-divider>
          <v-card-text>
            <div class="d-flex justify-space-between align-center mb-3">
              <span class="text-body-2">Total Documents:</span>
              <v-chip color="primary" variant="flat">-</v-chip>
            </div>
            <div class="d-flex justify-space-between align-center mb-3">
              <span class="text-body-2">Total Chunks:</span>
              <v-chip color="secondary" variant="flat">-</v-chip>
            </div>
            <div class="d-flex justify-space-between align-center">
              <span class="text-body-2">Last Updated:</span>
              <span class="text-caption text-medium-emphasis">-</span>
            </div>
          </v-card-text>
        </v-card>

        <!-- Quick Guide Card -->
        <v-card>
          <v-card-title class="d-flex align-center pa-4">
            <v-icon class="mr-2" color="success">mdi-lightbulb</v-icon>
            Quick Guide
          </v-card-title>
          <v-divider></v-divider>
          <v-card-text>
            <v-timeline density="compact" side="end" align="start">
              <v-timeline-item dot-color="primary" size="small">
                <div class="text-body-2">
                  <strong>Upload Documents</strong>
                  <div class="text-caption text-medium-emphasis">
                    Upload Word documents containing event details, association info, or FAQs
                  </div>
                </div>
              </v-timeline-item>

              <v-timeline-item dot-color="primary" size="small">
                <div class="text-body-2">
                  <strong>Automatic Processing</strong>
                  <div class="text-caption text-medium-emphasis">
                    Documents are automatically chunked and converted to vector embeddings
                  </div>
                </div>
              </v-timeline-item>

              <v-timeline-item dot-color="primary" size="small">
                <div class="text-body-2">
                  <strong>AI Integration</strong>
                  <div class="text-caption text-medium-emphasis">
                    The chatbot uses these documents to provide accurate answers to users
                  </div>
                </div>
              </v-timeline-item>
            </v-timeline>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
import DocumentVectorization from '@/components/admin/DocumentVectorization.vue';
</script>

<style scoped>
/* Add any custom styles here */
</style>
