import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { AuthService } from '@/services/AuthService';
import router from '@/router';
import { UserService } from '@/services/UserService';

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('authToken') || null);
  const user = ref(JSON.parse(localStorage.getItem('authUser')) || null); 
  const error = ref(null); 
  


  const isAuthenticated = computed(() => !!token.value);
  const isOrganiser = computed(() => {
    return user.value?.roles?.some(role => role.role_name === 'organiser' || role.role_name === 'super_admin');
  });

  const isSuperAdmin = computed(() => {
    return user.value?.roles?.some(role => role.role_name === 'super_admin');
  });

  async function register(userData, cvFile = null) {
    error.value = null;
    try {
      await AuthService.register(userData);
      await login({ email: userData.email, password: userData.password });
      if (cvFile) {
        await UserService.uploadCv(cvFile);
        user.value = response.data;
        localStorage.setItem('authUser', JSON.stringify(user.value));
      }
    } catch (err) {
      console.error('Registration failed:', err.response.data);
      error.value = err.response.data.detail || 'Registration failed.';
    }
  }

  async function login(credentials) {
    error.value = null;
    try {
      const response = await AuthService.login(credentials);
      token.value = response.data.access_token;
      user.value = response.data.user;

      localStorage.setItem('authToken', token.value);
      localStorage.setItem('authUser', JSON.stringify(user.value));

      const redirectPath = router.currentRoute.value.query.redirect || '/profile';
      router.push(redirectPath);
    } catch (err) {
      console.error('Login failed:', err.response.data);
      error.value = err.response.data.detail || 'Login failed.';
    }
  }

  function setAuthFromResponse(tokenValue, userData) {
    token.value = tokenValue;
    user.value = userData;
    localStorage.setItem('authToken', tokenValue);
    localStorage.setItem('authUser', JSON.stringify(userData));
  }

  async function fetchCurrentUser() {
    try {
      const response = await AuthService.getMe();
      user.value = response.data;
      localStorage.setItem('authUser', JSON.stringify(user.value));
    } catch (err) {
      console.error("Failed to fetch current user", err);
    }
  }

  function logout() {
    token.value = null;
    user.value = null;
    localStorage.removeItem('authToken');
    localStorage.removeItem('authUser');
    router.push('/login');
  }

  return { token, user, error, isAuthenticated, isOrganiser, isSuperAdmin, register, login, logout, fetchCurrentUser, setAuthFromResponse };
});