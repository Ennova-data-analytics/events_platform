<template>
  <div class="registration-page d-flex align-center justify-center">
    <v-container>
      <v-row justify="center">
        <v-col cols="12" sm="10" md="6" lg="5">

          <v-card class="ennova-card pa-8 pa-md-12" flat rounded="xl">
            <div class="text-center mb-8">
              <h1 class="form-title mb-2">Create Account</h1>
              <p class="form-subtitle">Join the Ennova community today.</p>
            </div>

            <RegistrationForm />

            <div class="text-center mt-8">
              <p class="login-footer">
                Already have an account?
                <router-link to="/login" class="login-link">Log in</router-link>
              </p>
            </div>
          </v-card>

        </v-col>
      </v-row>
    </v-container>
  </div>
</template>

<script setup>
import RegistrationForm from '../components/forms/RegistrationForm.vue';
</script>

<style scoped>
.registration-page {
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

.login-footer {
  color: #6B7280;
  font-size: 0.9rem;
}

.login-link {
  color: #001529;
  font-weight: 700;
  text-decoration: none;
}
</style>
