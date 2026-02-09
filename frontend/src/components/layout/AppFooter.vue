<template>
  <v-footer class="ennova-footer py-10 px-4 px-md-10" app>
    <v-container fluid class="pa-0">
      <v-row align="center">
        <v-col cols="12" md="6" class="text-center text-md-left">
          <h3 class="footer-logo mb-2">Ennova</h3>
          <p class="copyright-text">
            &copy; {{ new Date().getFullYear() }} Ennova Events Platform. All rights reserved.
          </p>
        </v-col>

        <v-col cols="12" md="6" class="text-center text-md-right">
          <div class="d-flex justify-center justify-md-end ga-4">
            <v-btn
              href="https://www.instagram.com/ennova.esade/?hl=en"
              target="_blank"
              rel="noopener noreferrer"
              icon="mdi-instagram"
              variant="text"
              color="white"
              density="comfortable"
              aria-label="Instagram"
            ></v-btn>
            <v-btn
              href="https://www.linkedin.com/company/ennovaesade/posts/?feedView=all"
              target="_blank"
              rel="noopener noreferrer"
              icon="mdi-linkedin"
              variant="text"
              color="white"
              density="comfortable"
              aria-label="LinkedIn"
            ></v-btn>
          </div>
        </v-col>
      </v-row>
    </v-container>
  </v-footer>
</template>

<script setup>
</script>

<style scoped>
.ennova-footer {
  background-color: #001529 !important;
  color: white !important;
}

.footer-logo {
  font-weight: 800;
  font-size: 1.25rem;
  letter-spacing: -0.02em;
}

.copyright-text {
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.6);
}
</style>