<template>
  <v-row align="center" justify="center" style="height: 70vh;">
    <v-col cols="12" sm="8" md="4">
      <v-card class="elevation-12">
        <v-toolbar color="primary">
          <v-toolbar-title>Reset Your Password</v-toolbar-title>
        </v-toolbar>
        <v-card-text class="pa-6">
          <p class="mb-4">
            Enter your email address below and we will send you a link to reset your password.
          </p>
          <v-form>
            <v-text-field
              label="Email Address"
              type="email"
              prepend-inner-icon="mdi-email-outline"
              variant="outlined"
            ></v-text-field>
            <v-btn type="submit" block class="mt-2" color="primary" size="large">
              Send Reset Link
            </v-btn>
          </v-form>
        </v-card-text>
      </v-card>
    </v-col>
  </v-row>
</template>