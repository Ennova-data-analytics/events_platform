<template>
  <v-row align="center" justify="center" style="min-height: 70vh;">
    <v-col cols="12" sm="10" md="6">
      
      <v-card class="elevation-12">
        <v-toolbar color="primary">
          <v-toolbar-title>Create a New Account</v-toolbar-title>
        </v-toolbar>
        
        <v-card-text class="pa-6">
          <p class="mb-4">
            Join our community to get access to exclusive events. An account allows for one-click registration in the future!
          </p>
          <RegistrationForm />
        </v-card-text>
      </v-card>

    </v-col>
  </v-row>
</template>

<script setup>
import RegistrationForm from '../components/forms/RegistrationForm.vue';
</script>
