<template>
  <v-container fluid>
    <v-row>
      <v-col cols="12">
        <h1 :class="$vuetify.display.mobile ? 'text-h5 mb-2' : 'text-h4 mb-2'">Organiser Role Management</h1>
        <p class="text-subtitle-1 mb-6">
          Grant or revoke the organiser role for users. Organisers can create events, manage registrations, and access the admin panel.
        </p>
      </v-col>
    </v-row>

    <!-- Search -->
    <v-row class="mb-4">
      <v-col cols="12" md="6">
        <v-text-field
          v-model="searchQuery"
          prepend-inner-icon="mdi-magnify"
          label="Search users by name or email"
          variant="outlined"
          density="compact"
          clearable
          @input="debouncedSearch"
        ></v-text-field>
      </v-col>
      <v-col cols="12" md="6" class="d-flex align-center">
        <v-chip-group v-model="roleFilter" mandatory>
          <v-chip value="all" filter>All Users</v-chip>
          <v-chip value="organisers" filter color="primary">Organisers Only</v-chip>
        </v-chip-group>
      </v-col>
    </v-row>

    <!-- Users Table -->
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title>
            <span class="text-h6">Users ({{ filteredUsers.length }} of {{ totalCount }})</span>
          </v-card-title>
          <v-card-text>
            <v-data-table
              :headers="headers"
              :items="filteredUsers"
              :loading="loading"
              :items-per-page="25"
              class="elevation-1"
            >
              <template v-slot:item.roles="{ item }">
                <v-chip
                  v-for="role in item.roles"
                  :key="role.role_id"
                  :color="roleColor(role.role_name)"
                  size="small"
                  class="mr-1"
                >
                  {{ formatRoleName(role.role_name) }}
                </v-chip>
                <span v-if="item.roles.length === 0" class="text-medium-emphasis text-caption">No roles</span>
              </template>

              <template v-slot:item.is_active="{ item }">
                <v-icon :color="item.is_active ? 'success' : 'error'" size="small">
                  {{ item.is_active ? 'mdi-check-circle' : 'mdi-close-circle' }}
                </v-icon>
              </template>

              <template v-slot:item.created_at="{ item }">
                {{ formatDate(item.created_at) }}
              </template>

              <template v-slot:item.actions="{ item }">
                <template v-if="!isSuperAdmin(item)">
                  <v-btn
                    v-if="!hasOrganiserRole(item)"
                    size="small"
                    color="primary"
                    variant="tonal"
                    prepend-icon="mdi-shield-account-outline"
                    @click="confirmGrant(item)"
                    :loading="actionLoading === item.user_id"
                  >
                    Grant Organiser
                  </v-btn>
                  <v-btn
                    v-else
                    size="small"
                    color="error"
                    variant="tonal"
                    prepend-icon="mdi-shield-off-outline"
                    @click="confirmRevoke(item)"
                    :loading="actionLoading === item.user_id"
                  >
                    Revoke Organiser
                  </v-btn>
                </template>
                <v-chip v-else color="warning" size="small" prepend-icon="mdi-shield-crown">
                  Super Admin
                </v-chip>
              </template>

              <template v-slot:no-data>
                <v-alert type="info" variant="tonal" class="ma-4">
                  No users found.
                </v-alert>
              </template>
            </v-data-table>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Grant Confirmation Dialog -->
    <v-dialog v-model="grantDialog" :max-width="$vuetify.display.mobile ? '90vw' : '480px'">
      <v-card>
        <v-card-title class="text-h5">Grant Organiser Role</v-card-title>
        <v-card-text>
          Grant the organiser role to <strong>{{ targetUser?.full_name || targetUser?.email }}</strong>?
          <br><br>
          They will be able to create events, manage registrations, send bulk emails, and access the admin panel.
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="grey" variant="text" @click="grantDialog = false">Cancel</v-btn>
          <v-btn color="primary" :loading="actionLoading === targetUser?.user_id" @click="grantOrganiser">Grant</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Revoke Confirmation Dialog -->
    <v-dialog v-model="revokeDialog" :max-width="$vuetify.display.mobile ? '90vw' : '480px'">
      <v-card>
        <v-card-title class="text-h5">Revoke Organiser Role</v-card-title>
        <v-card-text>
          Revoke the organiser role from <strong>{{ targetUser?.full_name || targetUser?.email }}</strong>?
          <br><br>
          They will lose access to the admin panel and all organiser capabilities.
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="grey" variant="text" @click="revokeDialog = false">Cancel</v-btn>
          <v-btn color="error" :loading="actionLoading === targetUser?.user_id" @click="revokeOrganiser">Revoke</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-snackbar v-model="snackbar" :color="snackbarColor" :timeout="3000">
      {{ snackbarMessage }}
    </v-snackbar>
  </v-container>
</template>

<script>
import { UserRoleService } from '@/services/UserRoleService';

export default {
  name: 'AdminUserRolesPage',
  data() {
    return {
      users: [],
      totalCount: 0,
      loading: false,
      searchQuery: '',
      roleFilter: 'all',
      searchTimeout: null,

      grantDialog: false,
      revokeDialog: false,
      targetUser: null,
      actionLoading: null,

      snackbar: false,
      snackbarMessage: '',
      snackbarColor: 'success',

      headers: [
        { title: 'Email', key: 'email', sortable: true },
        { title: 'Full Name', key: 'full_name', sortable: true },
        { title: 'Roles', key: 'roles', sortable: false },
        { title: 'Active', key: 'is_active', sortable: false, align: 'center' },
        { title: 'Joined', key: 'created_at', sortable: true },
        { title: 'Actions', key: 'actions', sortable: false, align: 'end' }
      ]
    };
  },
  computed: {
    filteredUsers() {
      if (this.roleFilter === 'organisers') {
        return this.users.filter(u => this.hasOrganiserRole(u) || this.isSuperAdmin(u));
      }
      return this.users;
    }
  },
  mounted() {
    this.loadUsers();
  },
  methods: {
    async loadUsers() {
      this.loading = true;
      try {
        const response = await UserRoleService.listUsers(this.searchQuery || null, 0, 200);
        this.users = response.data.users;
        this.totalCount = response.data.total_count;
      } catch (error) {
        this.showSnackbar('Failed to load users', 'error');
        console.error('Error loading users:', error);
      } finally {
        this.loading = false;
      }
    },

    debouncedSearch() {
      clearTimeout(this.searchTimeout);
      this.searchTimeout = setTimeout(() => this.loadUsers(), 400);
    },

    hasOrganiserRole(user) {
      return user.roles.some(r => r.role_name === 'organiser');
    },

    isSuperAdmin(user) {
      return user.roles.some(r => r.role_name === 'super_admin');
    },

    roleColor(roleName) {
      if (roleName === 'super_admin') return 'warning';
      if (roleName === 'organiser') return 'primary';
      return 'default';
    },

    formatRoleName(roleName) {
      return roleName.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase());
    },

    confirmGrant(user) {
      this.targetUser = user;
      this.grantDialog = true;
    },

    confirmRevoke(user) {
      this.targetUser = user;
      this.revokeDialog = true;
    },

    async grantOrganiser() {
      if (!this.targetUser) return;
      this.actionLoading = this.targetUser.user_id;
      try {
        const response = await UserRoleService.grantOrganiser(this.targetUser.user_id);
        const idx = this.users.findIndex(u => u.user_id === this.targetUser.user_id);
        if (idx !== -1) this.users[idx] = response.data;
        this.showSnackbar(`Organiser role granted to ${this.targetUser.full_name || this.targetUser.email}`, 'success');
        this.grantDialog = false;
      } catch (error) {
        this.showSnackbar(error.response?.data?.detail || 'Failed to grant role', 'error');
      } finally {
        this.actionLoading = null;
        this.targetUser = null;
      }
    },

    async revokeOrganiser() {
      if (!this.targetUser) return;
      this.actionLoading = this.targetUser.user_id;
      try {
        const response = await UserRoleService.revokeOrganiser(this.targetUser.user_id);
        const idx = this.users.findIndex(u => u.user_id === this.targetUser.user_id);
        if (idx !== -1) this.users[idx] = response.data;
        this.showSnackbar(`Organiser role revoked from ${this.targetUser.full_name || this.targetUser.email}`, 'success');
        this.revokeDialog = false;
      } catch (error) {
        this.showSnackbar(error.response?.data?.detail || 'Failed to revoke role', 'error');
      } finally {
        this.actionLoading = null;
        this.targetUser = null;
      }
    },

    formatDate(dateString) {
      if (!dateString) return 'N/A';
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric', month: 'short', day: 'numeric'
      });
    },

    showSnackbar(message, color = 'success') {
      this.snackbarMessage = message;
      this.snackbarColor = color;
      this.snackbar = true;
    }
  }
};
</script>
