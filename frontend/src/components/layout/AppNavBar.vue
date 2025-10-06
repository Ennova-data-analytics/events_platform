<template>
  <v-app-bar color="primary" density="compact" app>
    <div class="d-flex align-center" style="cursor: pointer;" @click="$router.push('/')">
      <v-img
        :src="logoUrl"
        height="48"
        width="200"
        contain
        class="mr-3"
      ></v-img>

    </div>

    <v-spacer></v-spacer>

    <v-btn to="/" text>Events</v-btn>
    <template v-if="!authStore.isAuthenticated">
      <v-btn to="/login" text>Login</v-btn>
      <v-btn to="/register" text>Sign Up</v-btn>
    </template>
    <template v-else>
      <v-btn to="/profile" text>Profile</v-btn>
      <v-btn v-if="authStore.isOrganiser" to="/admin" text>Admin</v-btn>
      <v-btn @click="authStore.logout()" text>Logout</v-btn>
    </template>
  </v-app-bar>
</template>

<script setup>
import logoUrl from '@/assets/ennova-logo-white.png';
import { useAuthStore } from '@/stores/auth.store'

const authStore = useAuthStore();
</script>

<style scoped>
</style>