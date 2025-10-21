<template>
  <v-footer class="d-flex flex-column" app>
    <div class="footer-content px-3 py-2 text-center w-100">
      <div class="social-links mb-2">
        <a
          href="https://www.instagram.com/ennova.esade/?hl=en"
          target="_blank"
          rel="noopener noreferrer"
          class="social-icon"
          aria-label="Instagram"
        >
          <v-icon size="20">mdi-instagram</v-icon>
        </a>
        <a
          href="https://www.linkedin.com/company/ennovaesade/posts/?feedView=all"
          target="_blank"
          rel="noopener noreferrer"
          class="social-icon"
          aria-label="LinkedIn"
        >
          <v-icon size="20">mdi-linkedin</v-icon>
        </a>
      </div>
      <div class="copyright">
        &copy; {{ new Date().getFullYear() }} <strong>Ennova Events Platform</strong>
      </div>
    </div>
  </v-footer>
</template>

<script setup>
</script>

<style scoped>
.footer-content {
  background: #13182e;
}

.social-links {
  display: flex;
  justify-content: center;
  gap: 16px;
}

.social-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
  color: #ffffff;
  transition: all 0.3s ease;
  text-decoration: none;
}

.social-icon:hover {
  background: rgba(255, 255, 255, 0.2);
  transform: translateY(-2px);
  box-shadow: 0 4px 8px rgba(255, 255, 255, 0.15);
}

.social-icon:active {
  transform: translateY(-1px);
}

.copyright {
  font-size: 12px;
  color: #ffffff;
}
</style>