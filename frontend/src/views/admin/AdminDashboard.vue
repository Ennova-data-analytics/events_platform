<template>
  <v-layout>
    <v-navigation-drawer permanent>
      <v-list-item
        :prepend-avatar="avatarUrl"
        :title="userName"
        :subtitle="userRole"
      ></v-list-item>
      <v-divider></v-divider>
      <v-list density="compact" nav>
        <v-list-item prepend-icon="mdi-view-dashboard" title="Dashboard" to="/admin"></v-list-item>
        <v-list-item prepend-icon="mdi-calendar-multiple" title="Manage Events" to="/admin/events"></v-list-item>
        <v-list-item prepend-icon="mdi-account-group" title="Ennova Members" to="/admin/ennova-members"></v-list-item>
        <v-list-item prepend-icon="mdi-form-select" title="Form Templates" to="/admin/forms"></v-list-item>
        <v-list-item prepend-icon="mdi-email-edit" title="Email Templates" to="/admin/email-templates"></v-list-item>
        <v-list-item prepend-icon="mdi-comment-text-multiple" title="Feedback Templates" to="/admin/feedback-templates"></v-list-item>
        <v-list-item prepend-icon="mdi-robot-happy" title="AI Documents" to="/admin/ai-documents"></v-list-item>
        <v-list-item prepend-icon="mdi-play-circle" title="Tutorials" to="/admin/tutorials"></v-list-item>

      </v-list>
    </v-navigation-drawer>

    <v-main style="min-height: 300px;">
      <v-container>
        <router-view />
      </v-container>
    </v-main>
  </v-layout>
</template>

<script setup>
  import { useAuthStore } from '@/stores/auth.store';
  import { computed } from 'vue';

  const authStore = useAuthStore();

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
</script>