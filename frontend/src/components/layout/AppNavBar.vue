<template>
  <v-app-bar app class="px-4 px-md-10 ennova-navbar" elevation="0" height="80">
    <div class="d-flex align-center" style="cursor: pointer;" @click="$router.push('/')">
      <v-img
        :src="logoUrl"
        height="40"
        width="160"
        contain
        class="mr-3"
      ></v-img>
    </div>

    <v-spacer></v-spacer>

    <div v-if="!$vuetify.display.mobile" class="d-flex align-center ga-4">
      <v-btn to="/" variant="text" class="nav-link">EVENTS</v-btn>

      <template v-if="!authStore.isAuthenticated">
        <v-btn to="/login" variant="text" class="nav-link">LOGIN</v-btn>
        <v-btn to="/register" color="white" rounded="pill" class="signup-btn px-6">
          SIGN UP
        </v-btn>
      </template>

      <template v-else>
        <NotificationBell />
        <v-btn to="/profile" variant="text" class="nav-link">PROFILE</v-btn>
        <v-btn v-if="authStore.isOrganiser" to="/admin" variant="text" class="nav-link">ADMIN</v-btn>
        <v-btn @click="authStore.logout()" variant="text" class="nav-link">LOGOUT</v-btn>
      </template>
    </div>

    <v-app-bar-nav-icon v-else color="white" @click="drawer = !drawer"></v-app-bar-nav-icon>
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
.ennova-navbar {
  background-color: #001529 !important;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.nav-link {
  color: white !important;
  font-size: 12px !important;
  font-weight: 700 !important;
  letter-spacing: 0.1em !important;
  text-transform: uppercase;
}

.signup-btn {
  background-color: white !important;
  color: #001529 !important;
  font-size: 12px !important;
  font-weight: 800 !important;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}
</style>