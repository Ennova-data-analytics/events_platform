<template>
  <v-form>
    <h3 class="text-h6 font-weight-medium mb-4">Personal Information</h3>
    <v-text-field
      label="Full Name"
      variant="outlined"
      class="mb-4"
      prepend-inner-icon="mdi-account-outline"
    ></v-text-field>
    <v-text-field
      label="Degree"
      variant="outlined"
      class="mb-4"
      prepend-inner-icon="mdi-briefcase-outline"
    ></v-text-field>
    <v-text-field
      label="Year of Study"
      variant="outlined"
      class="mb-4"
      prepend-inner-icon="mdi-school-outline"
    ></v-text-field>
    
    <v-divider class="my-4"></v-divider>

    <h3 class="text-h6 font-weight-medium mb-4">Your Documents</h3>
    <v-file-input
      label="Upload new CV (optional)"
      variant="outlined"
      prepend-icon=""
      prepend-inner-icon="mdi-paperclip"
    ></v-file-input>
    
    <v-divider class="my-4"></v-divider>
    
    <h3 class="text-h6 font-weight-medium mb-4">Change Password</h3>
    <v-text-field
      label="New Password"
      type="password"
      variant="outlined"
      class="mb-4"
      prepend-inner-icon="mdi-lock-outline"
    ></v-text-field>
    <v-text-field
      label="Confirm New Password"
      type="password"
      variant="outlined"
      class="mb-4"
      prepend-inner-icon="mdi-lock-outline"
    ></v-text-field>
    
    <v-btn color="primary" size="large" class="mt-4">
      Save Changes
    </v-btn>
  </v-form>
</template>