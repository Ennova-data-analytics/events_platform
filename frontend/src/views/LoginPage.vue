<template>
  <div class="login-page d-flex align-center justify-center">
    <v-container>
      <v-row justify="center">
        <v-col cols="12" sm="10" md="6" lg="5">

          <v-card class="ennova-card pa-8 pa-md-12" flat rounded="xl">
            <div class="text-center mb-8">
              <h1 class="form-title mb-2">Welcome Back</h1>
              <p class="form-subtitle">Log in to your Ennova account.</p>
            </div>

            <LoginForm />
          </v-card>

        </v-col>
      </v-row>
    </v-container>
  </div>
</template>

<script setup>
import LoginForm from '../components/forms/LoginForm.vue';
</script>

<style scoped>
.login-page {
  background-color: #F8F9FA;
  min-height: 100vh;
}

.ennova-card {
  background-color: #FFFFFF !important;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.05) !important;
}

.form-title {
  color: #001529;
  font-weight: 800;
  font-size: 2rem;
  letter-spacing: -0.02em;
}

.form-subtitle {
  color: #6B7280;
  font-size: 1rem;
}
</style>
