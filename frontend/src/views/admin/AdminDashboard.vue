<template>
  <v-layout>
    <v-navigation-drawer permanent>
      <v-list-item
        prepend-avatar="https://randomuser.me/api/portraits/men/85.jpg"
        title="Admin Panel"
        subtitle="Event Organiser"
      ></v-list-item>
      <v-divider></v-divider>
      <v-list density="compact" nav>
        <v-list-item prepend-icon="mdi-view-dashboard" title="Dashboard" to="/admin"></v-list-item>
        <v-list-item prepend-icon="mdi-calendar-multiple" title="Manage Events" to="/admin/events"></v-list-item>
        <v-list-item prepend-icon="mdi-form-select" title="Form Templates" to="/admin/forms"></v-list-item>
        <v-list-item prepend-icon="mdi-email-edit" title="Email Templates" to="/admin/email-templates"></v-list-item>

      </v-list>
    </v-navigation-drawer>

    <v-main style="min-height: 300px;">
      <v-container>
        <router-view />
      </v-container>
    </v-main>
  </v-layout>
</template>