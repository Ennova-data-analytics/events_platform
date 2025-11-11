<template>
  <v-app>
    <v-layout>
      <AppNavbar />

      <v-main>
        <v-container fluid class="pa-2 pa-md-4">
          <router-view />
        </v-container>
      </v-main>

      <AppFooter />

      <v-btn
        icon="mdi-bug-outline"
        color="#ff5252"
        :size="$vuetify.display.mobile ? 'default' : 'large'"
        position="fixed"
        location="bottom right"
        class="support-btn"
        elevation="8"
        @click="openSupportEmail"
      >
        <v-icon>mdi-bug-outline</v-icon>
        <v-tooltip activator="parent" location="left">Report a bug</v-tooltip>
      </v-btn>
    </v-layout>
  </v-app>
</template>

<script setup>
import AppNavbar from './components/layout/AppNavBar.vue';
import AppFooter from './components/layout/AppFooter.vue';

const openSupportEmail = () => {
  const email = 'alanbruno.fijal@alumni.esade.edu'; 
  const subject = 'Bug Report - Ennova Events Platform';
  const body = 'Please describe the bug you encountered:\n\n';

  window.location.href = `mailto:${email}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
};
</script>

<style scoped>
.support-btn {
  margin: 0 24px 24px 0;
  z-index: 1000;
}
</style>
