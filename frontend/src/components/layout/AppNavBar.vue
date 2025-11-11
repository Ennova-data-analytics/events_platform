<template>
  <v-app-bar color="primary" density="default" app class="px-4 px-md-6">
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

    <template v-if="$vuetify.display.mobile">
      <v-app-bar-nav-icon @click="drawer = !drawer"></v-app-bar-nav-icon>
    </template>

    <template v-else>
      <v-btn to="/" text class="mx-1">Events</v-btn>
      <template v-if="!authStore.isAuthenticated">
        <v-btn to="/login" text class="mx-1">Login</v-btn>
        <v-btn to="/register" text class="mx-1">Sign Up</v-btn>
      </template>
      <template v-else>
        <NotificationBell class="mx-1" />
        <v-btn to="/profile" text class="mx-1">Profile</v-btn>
        <v-btn v-if="authStore.isOrganiser" to="/admin" text class="mx-1">Admin</v-btn>
        <v-btn @click="authStore.logout()" text class="mx-1">Logout</v-btn>
      </template>
    </template>
  </v-app-bar>

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