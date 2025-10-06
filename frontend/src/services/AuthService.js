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
  }
};