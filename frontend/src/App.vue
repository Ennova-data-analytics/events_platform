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

      <v-btn
        icon="mdi-bug-outline"
        color="primary"
        size="large"
        position="fixed"
        location="bottom right"
        class="support-btn"
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
  margin: 0 16px 80px 0;
}
</style>
