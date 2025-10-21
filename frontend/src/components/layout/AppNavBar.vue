<template>
  <v-app-bar color="primary" density="compact" app>
    <div class="d-flex align-center" style="cursor: pointer;" @click="$router.push('/')">
      <v-img
        :src="logoUrl"
        :height="$vuetify.display.mobile ? 32 : 48"
        :width="$vuetify.display.mobile ? 130 : 200"
        contain
        :class="$vuetify.display.mobile ? 'mr-1' : 'mr-3'"
      ></v-img>
    </div>

    <v-spacer></v-spacer>

    <!-- Mobile Menu -->
    <template v-if="$vuetify.display.mobile">
      <v-app-bar-nav-icon @click="drawer = !drawer"></v-app-bar-nav-icon>
    </template>

    <!-- Desktop Menu -->
    <template v-else>
      <v-btn to="/" text>Events</v-btn>
      <template v-if="!authStore.isAuthenticated">
        <v-btn to="/login" text>Login</v-btn>
        <v-btn to="/register" text>Sign Up</v-btn>
      </template>
      <template v-else>
        <NotificationBell />
        <v-btn to="/profile" text>Profile</v-btn>
        <v-btn v-if="authStore.isOrganiser" to="/admin" text>Admin</v-btn>
        <v-btn @click="authStore.logout()" text>Logout</v-btn>
      </template>
    </template>
  </v-app-bar>

  <!-- Mobile Navigation Drawer -->
  <v-navigation-drawer v-model="drawer" location="right" temporary>
    <v-list>
      <v-list-item to="/" prepend-icon="mdi-calendar-multiple">
        <v-list-item-title>Events</v-list-item-title>
      </v-list-item>

      <template v-if="!authStore.isAuthenticated">
        <v-list-item to="/login" prepend-icon="mdi-login">
          <v-list-item-title>Login</v-list-item-title>
        </v-list-item>
        <v-list-item to="/register" prepend-icon="mdi-account-plus">
          <v-list-item-title>Sign Up</v-list-item-title>
        </v-list-item>
      </template>

      <template v-else>
        <v-list-item>
          <NotificationBell />
        </v-list-item>
        <v-list-item to="/profile" prepend-icon="mdi-account">
          <v-list-item-title>Profile</v-list-item-title>
        </v-list-item>
        <v-list-item v-if="authStore.isOrganiser" to="/admin" prepend-icon="mdi-shield-crown">
          <v-list-item-title>Admin</v-list-item-title>
        </v-list-item>
        <v-list-item @click="authStore.logout()" prepend-icon="mdi-logout">
          <v-list-item-title>Logout</v-list-item-title>
        </v-list-item>
      </template>
    </v-list>
  </v-navigation-drawer>
</template>

<script setup>
import { ref } from 'vue'
import logoUrl from '@/assets/ennova-logo-white.png';
import { useAuthStore } from '@/stores/auth.store'
import NotificationBell from '@/components/NotificationBell.vue'

const authStore = useAuthStore();
const drawer = ref(false);
</script>

<style scoped>
</style>