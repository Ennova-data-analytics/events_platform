<template>
  <v-row align="center" justify="center" style="height: 70vh;">
    <v-col cols="12" sm="8" md="4">
      
      <v-card class="elevation-12">
        <v-toolbar color="primary">
          <v-toolbar-title>Login to your Account</v-toolbar-title>
        </v-toolbar>
        
        <v-card-text class="pa-6">
          <LoginForm />
        </v-card-text>
      </v-card>

    </v-col>
  </v-row>
</template>

<script setup>
import LoginForm from '../components/forms/LoginForm.vue';
</script>
