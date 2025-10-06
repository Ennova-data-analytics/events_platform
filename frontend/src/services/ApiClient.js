import axios from 'axios';
import { useAuthStore } from '@/stores/auth.store';

const ApiClient = axios.create({
    baseURL: '/api'
});

ApiClient.interceptors.request.use(
    (config) => {
        const authStore = useAuthStore();
        const token = authStore.token;

        if (!config.headers) config.headers = {};

        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        
        console.log('Sending request with headers:', config.headers);


        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

export default ApiClient;

