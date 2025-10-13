import ApiClient from './ApiClient';

export const AuthService = {
  register(userData) {
    return ApiClient.post('/users/register', userData);
  },
  
  login(credentials) {
    const formData = new URLSearchParams();
    formData.append('username', credentials.email);
    formData.append('password', credentials.password);


    return ApiClient.post('/auth/token', formData);
  },
  getMe(){
    return ApiClient.get('/users/me');
  },

  requestPasswordReset(email) {
    return ApiClient.post('/auth/password-reset/request', { email });
  },

  confirmPasswordReset(token, newPassword) {
    return ApiClient.post('/auth/password-reset/confirm', {
      token,
      new_password: newPassword
    });
  }
};