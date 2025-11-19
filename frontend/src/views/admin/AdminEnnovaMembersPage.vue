<template>
  <v-container fluid>
    <v-row>
      <v-col cols="12">
        <h1 class="text-h4 mb-4">Ennova Members Management</h1>
        <p class="text-subtitle-1 mb-6">
          Manage Ennova association members. Members marked here will automatically bypass payment for events marked as "Free for Members".
        </p>
      </v-col>
    </v-row>

    <!-- Action Buttons -->
    <v-row class="mb-4">
      <v-col cols="12" md="6">
        <v-text-field
          v-model="searchQuery"
          prepend-inner-icon="mdi-magnify"
          label="Search members"
          variant="outlined"
          density="compact"
          clearable
          @input="debouncedSearch"
        ></v-text-field>
      </v-col>
      <v-col cols="12" md="6" class="d-flex justify-end align-center">
        <v-btn
          color="primary"
          prepend-icon="mdi-account-plus"
          class="mr-2"
          @click="openAddMemberDialog"
        >
          Add Member
        </v-btn>
        <v-btn
          color="success"
          prepend-icon="mdi-file-excel"
          @click="openExcelImportDialog"
        >
          Import from Excel
        </v-btn>
      </v-col>
    </v-row>

    <!-- Members Table -->
    <v-row>
      <v-col cols="12">
        <v-card>
          <v-card-title>
            <span class="text-h6">Current Members ({{ totalMembers }})</span>
          </v-card-title>
          <v-card-text>
            <v-data-table
              :headers="headers"
              :items="members"
              :loading="loading"
              :items-per-page="itemsPerPage"
              class="elevation-1"
            >
              <template v-slot:item.created_at="{ item }">
                {{ formatDate(item.created_at) }}
              </template>
              <template v-slot:item.actions="{ item }">
                <v-btn
                  size="small"
                  color="error"
                  variant="text"
                  icon="mdi-delete"
                  @click="confirmRemoveMember(item)"
                ></v-btn>
              </template>
              <template v-slot:no-data>
                <v-alert type="info" variant="tonal" class="ma-4">
                  No Ennova members found. Use the "Add Member" or "Import from Excel" buttons to get started.
                </v-alert>
              </template>
            </v-data-table>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- Add Member Dialog -->
    <v-dialog v-model="addMemberDialog" max-width="600px">
      <v-card>
        <v-card-title>
          <span class="text-h5">Add Ennova Member</span>
        </v-card-title>
        <v-card-text>
          <v-text-field
            v-model="userSearchQuery"
            prepend-inner-icon="mdi-magnify"
            label="Search users by email or name"
            variant="outlined"
            @input="searchUsersDebounced"
            :loading="searchingUsers"
          ></v-text-field>

          <v-list v-if="searchResults.length > 0" class="mt-4" max-height="300" style="overflow-y: auto;">
            <v-list-item
              v-for="user in searchResults"
              :key="user.user_id"
              @click="selectUserToAdd(user)"
              :disabled="user.is_ennova_member"
            >
              <v-list-item-title>{{ user.full_name || user.email }}</v-list-item-title>
              <v-list-item-subtitle>{{ user.email }}</v-list-item-subtitle>
              <template v-slot:append>
                <v-chip v-if="user.is_ennova_member" color="primary" size="small">Already a member</v-chip>
                <v-icon v-else color="success">mdi-plus-circle</v-icon>
              </template>
            </v-list-item>
          </v-list>

          <v-alert v-else-if="userSearchQuery && !searchingUsers" type="info" variant="tonal" class="mt-4">
            No users found. Try a different search term.
          </v-alert>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="grey" variant="text" @click="addMemberDialog = false">Cancel</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Excel Import Dialog -->
    <v-dialog v-model="excelImportDialog" max-width="700px">
      <v-card>
        <v-card-title>
          <span class="text-h5">Import Members from Excel</span>
        </v-card-title>
        <v-card-text>
          <v-alert type="info" variant="tonal" class="mb-4">
            Upload an Excel file (.xlsx, .xls) or CSV file containing a column with member emails.
            The file should have a column named "email" or "Esade email".
          </v-alert>

          <v-file-input
            v-model="excelFile"
            label="Select Excel or CSV file"
            accept=".xlsx,.xls,.csv"
            prepend-icon="mdi-file-excel"
            variant="outlined"
            :disabled="uploading"
          ></v-file-input>

          <v-progress-linear v-if="uploading" indeterminate color="primary" class="mb-4"></v-progress-linear>

          <!-- Import Results -->
          <v-card v-if="importResults" class="mt-4" variant="outlined">
            <v-card-title class="text-h6">Import Results</v-card-title>
            <v-card-text>
              <v-row>
                <v-col cols="6">
                  <v-list-item>
                    <v-list-item-title class="text-subtitle-2">Added</v-list-item-title>
                    <v-list-item-subtitle class="text-h6 text-success">{{ importResults.added_count }}</v-list-item-subtitle>
                  </v-list-item>
                </v-col>
                <v-col cols="6">
                  <v-list-item>
                    <v-list-item-title class="text-subtitle-2">Already Members</v-list-item-title>
                    <v-list-item-subtitle class="text-h6 text-info">{{ importResults.already_members.length }}</v-list-item-subtitle>
                  </v-list-item>
                </v-col>
                <v-col cols="6">
                  <v-list-item>
                    <v-list-item-title class="text-subtitle-2">Matched</v-list-item-title>
                    <v-list-item-subtitle class="text-h6">{{ importResults.matched_count }}</v-list-item-subtitle>
                  </v-list-item>
                </v-col>
                <v-col cols="6">
                  <v-list-item>
                    <v-list-item-title class="text-subtitle-2">Not Found</v-list-item-title>
                    <v-list-item-subtitle class="text-h6 text-warning">{{ importResults.unmatched_count }}</v-list-item-subtitle>
                  </v-list-item>
                </v-col>
              </v-row>

              <v-expansion-panels v-if="importResults.unmatched_emails.length > 0" class="mt-4">
                <v-expansion-panel>
                  <v-expansion-panel-title>
                    <v-icon class="mr-2">mdi-alert-circle</v-icon>
                    Unmatched Emails ({{ importResults.unmatched_emails.length }})
                  </v-expansion-panel-title>
                  <v-expansion-panel-text>
                    <v-chip
                      v-for="(email, index) in importResults.unmatched_emails"
                      :key="index"
                      class="ma-1"
                      size="small"
                      color="warning"
                    >
                      {{ email }}
                    </v-chip>
                  </v-expansion-panel-text>
                </v-expansion-panel>
              </v-expansion-panels>
            </v-card-text>
          </v-card>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="grey" variant="text" @click="closeExcelImportDialog">Close</v-btn>
          <v-btn
            color="primary"
            :loading="uploading"
            :disabled="!excelFile || uploading"
            @click="uploadExcelFile"
          >
            Import
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Remove Member Confirmation Dialog -->
    <v-dialog v-model="removeConfirmDialog" max-width="500px">
      <v-card>
        <v-card-title class="text-h5">Confirm Removal</v-card-title>
        <v-card-text>
          Are you sure you want to remove <strong>{{ memberToRemove?.full_name || memberToRemove?.email }}</strong> from Ennova members?
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="grey" variant="text" @click="removeConfirmDialog = false">Cancel</v-btn>
          <v-btn color="error" :loading="removing" @click="removeMember">Remove</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Snackbar for notifications -->
    <v-snackbar v-model="snackbar" :color="snackbarColor" :timeout="3000">
      {{ snackbarMessage }}
    </v-snackbar>
  </v-container>
</template>

<script>
import { EnnovaMemberService } from '@/services/EnnovaMemberService';

export default {
  name: 'AdminEnnovaMembersPage',
  data() {
    return {
      members: [],
      totalMembers: 0,
      loading: false,
      searchQuery: '',
      itemsPerPage: 25,

      // Add member dialog
      addMemberDialog: false,
      userSearchQuery: '',
      searchResults: [],
      searchingUsers: false,
      searchTimeout: null,

      // Excel import
      excelImportDialog: false,
      excelFile: null,
      uploading: false,
      importResults: null,

      // Remove member
      removeConfirmDialog: false,
      memberToRemove: null,
      removing: false,

      // Snackbar
      snackbar: false,
      snackbarMessage: '',
      snackbarColor: 'success',

      headers: [
        { title: 'Email', key: 'email', sortable: true },
        { title: 'Full Name', key: 'full_name', sortable: true },
        { title: 'Degree', key: 'degree', sortable: false },
        { title: 'Study Year', key: 'study_year', sortable: false },
        { title: 'Member Since', key: 'created_at', sortable: true },
        { title: 'Actions', key: 'actions', sortable: false, align: 'end' }
      ]
    };
  },
  mounted() {
    this.loadMembers();
  },
  methods: {
    async loadMembers() {
      this.loading = true;
      try {
        const response = await EnnovaMemberService.getMembers(0, 1000, this.searchQuery || null);
        this.members = response.data.members;
        this.totalMembers = response.data.total_count;
      } catch (error) {
        this.showSnackbar('Failed to load members', 'error');
        console.error('Error loading members:', error);
      } finally {
        this.loading = false;
      }
    },

    debouncedSearch() {
      clearTimeout(this.searchTimeout);
      this.searchTimeout = setTimeout(() => {
        this.loadMembers();
      }, 500);
    },

    openAddMemberDialog() {
      this.addMemberDialog = true;
      this.userSearchQuery = '';
      this.searchResults = [];
    },

    async searchUsersDebounced() {
      clearTimeout(this.searchTimeout);
      if (!this.userSearchQuery || this.userSearchQuery.length < 2) {
        this.searchResults = [];
        return;
      }

      this.searchTimeout = setTimeout(async () => {
        await this.searchUsers();
      }, 500);
    },

    async searchUsers() {
      if (!this.userSearchQuery || this.userSearchQuery.length < 2) return;

      this.searchingUsers = true;
      try {
        const response = await EnnovaMemberService.searchUsers(this.userSearchQuery);
        this.searchResults = response.data.users;
      } catch (error) {
        this.showSnackbar('Failed to search users', 'error');
        console.error('Error searching users:', error);
      } finally {
        this.searchingUsers = false;
      }
    },

    async selectUserToAdd(user) {
      if (user.is_ennova_member) return;

      try {
        await EnnovaMemberService.addMember(user.user_id);
        this.showSnackbar(`${user.full_name || user.email} added to Ennova members`, 'success');
        this.addMemberDialog = false;
        this.loadMembers();
      } catch (error) {
        this.showSnackbar('Failed to add member', 'error');
        console.error('Error adding member:', error);
      }
    },

    openExcelImportDialog() {
      this.excelImportDialog = true;
      this.excelFile = null;
      this.importResults = null;
    },

    closeExcelImportDialog() {
      this.excelImportDialog = false;
      this.excelFile = null;
      this.importResults = null;
      this.loadMembers();
    },

    async uploadExcelFile() {
      if (!this.excelFile) return;

      this.uploading = true;
      try {
        const response = await EnnovaMemberService.importFromExcel(this.excelFile);
        this.importResults = response.data;
        this.showSnackbar(
          `Successfully imported ${response.data.added_count} new members`,
          'success'
        );
      } catch (error) {
        this.showSnackbar(
          error.response?.data?.detail || 'Failed to import Excel file',
          'error'
        );
        console.error('Error importing Excel:', error);
      } finally {
        this.uploading = false;
      }
    },

    confirmRemoveMember(member) {
      this.memberToRemove = member;
      this.removeConfirmDialog = true;
    },

    async removeMember() {
      if (!this.memberToRemove) return;

      this.removing = true;
      try {
        await EnnovaMemberService.removeMember(this.memberToRemove.user_id);
        this.showSnackbar(
          `${this.memberToRemove.full_name || this.memberToRemove.email} removed from Ennova members`,
          'success'
        );
        this.removeConfirmDialog = false;
        this.memberToRemove = null;
        this.loadMembers();
      } catch (error) {
        this.showSnackbar('Failed to remove member', 'error');
        console.error('Error removing member:', error);
      } finally {
        this.removing = false;
      }
    },

    formatDate(dateString) {
      if (!dateString) return 'N/A';
      const date = new Date(dateString);
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
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

<style scoped>
.v-list-item:hover {
  background-color: rgba(0, 0, 0, 0.04);
  cursor: pointer;
}
</style>
