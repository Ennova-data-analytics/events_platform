<template>
  <v-app>
    <v-layout>
      <AppNavbar />

      <v-main>
        <v-container>
          <router-view />
        </v-container>
      </v-main>
 
      <AppFooter />
    </v-layout>
  </v-app>
</template>

<script setup>
import AppNavbar from './components/layout/AppNavBar.vue';
import AppFooter from './components/layout/AppFooter.vue';
</script>
