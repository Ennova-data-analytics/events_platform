<template>
  <v-layout class="admin-layout">
    <v-app-bar v-if="$vuetify.display.mobile" elevation="1">
      <v-app-bar-nav-icon @click="drawer = !drawer"></v-app-bar-nav-icon>
      <v-app-bar-title>Admin Panel</v-app-bar-title>
    </v-app-bar>

    <v-navigation-drawer v-model="drawer" :permanent="!$vuetify.display.mobile">
      <v-list-item
        :prepend-avatar="avatarUrl"
        :title="userName"
        :subtitle="userRole"
      ></v-list-item>
      <v-divider></v-divider>
      <v-list density="compact" nav>
        <v-list-item prepend-icon="mdi-view-dashboard" title="Dashboard" to="/admin" @click="closeDrawerOnMobile"></v-list-item>
        <v-list-item prepend-icon="mdi-calendar-multiple" title="Manage Events" to="/admin/events" @click="closeDrawerOnMobile"></v-list-item>
        <v-list-item prepend-icon="mdi-account-tie" title="Recruitment" to="/admin/recruitment" @click="closeDrawerOnMobile"></v-list-item>
        <v-list-item prepend-icon="mdi-account-group" title="Ennova Members" to="/admin/ennova-members" @click="closeDrawerOnMobile"></v-list-item>
        <v-list-item prepend-icon="mdi-form-select" title="Form Templates" to="/admin/forms" @click="closeDrawerOnMobile"></v-list-item>
        <v-list-item prepend-icon="mdi-email-edit" title="Email Templates" to="/admin/email-templates" @click="closeDrawerOnMobile"></v-list-item>
        <v-list-item prepend-icon="mdi-comment-text-multiple" title="Feedback Templates" to="/admin/feedback-templates" @click="closeDrawerOnMobile"></v-list-item>
        <v-list-item prepend-icon="mdi-robot-happy" title="AI Documents" to="/admin/ai-documents" @click="closeDrawerOnMobile"></v-list-item>
        <v-list-item prepend-icon="mdi-play-circle" title="Tutorials" to="/admin/tutorials" @click="closeDrawerOnMobile"></v-list-item>
        <v-divider v-if="authStore.isSuperAdmin" class="my-2"></v-divider>
        <v-list-item v-if="authStore.isSuperAdmin" prepend-icon="mdi-shield-account" title="User Roles" to="/admin/user-roles" @click="closeDrawerOnMobile"></v-list-item>
      </v-list>
    </v-navigation-drawer>

    <v-main>
      <v-container>
        <router-view />
      </v-container>
    </v-main>
  </v-layout>
</template>

<script setup>
  import { useAuthStore } from '@/stores/auth.store';
  import { computed, ref } from 'vue';
  import { useDisplay } from 'vuetify';

  const authStore = useAuthStore();
  const { mobile } = useDisplay();
  const drawer = ref(true);

  const userName = computed(() => {
    return authStore.user?.full_name || authStore.user?.email || 'Admin Panel';
  });

  const userRole = computed(() => {
    if (!authStore.user?.roles || authStore.user.roles.length === 0) {
      return 'Event Organiser';
    }
    const roles = authStore.user.roles.map(r =>
      r.role_name.charAt(0).toUpperCase() + r.role_name.slice(1)
    );
    return roles.join(', ');
  });

  function closeDrawerOnMobile() {
    if (mobile.value) drawer.value = false;
  }
</script>

<style scoped>
/*
 * This dashboard renders a nested v-layout inside the app's outer layout. A
 * nested v-layout has no intrinsic height, so it collapses to the content
 * height — which made the sidebar track the page content and cut off nav items.
 * Anchor it to the viewport (minus the 80px global app bar) so the drawer always
 * fills the screen regardless of how tall the current page's content is.
 */
.admin-layout {
  min-height: calc(100vh - 80px);
}
</style>