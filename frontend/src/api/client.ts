import axios from 'axios';

// Базовый URL API
const baseURL = process.env.NEXT_PUBLIC_API_URL || '';

// Создаем экземпляр axios с настройками по умолчанию
export const apiClient = axios.create({
  baseURL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Добавляем перехватчик запросов для подстановки токена авторизации
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Добавляем перехватчик ответов для обработки ошибок
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const { response } = error;
    
    // Обрабатываем 401 ошибку (не авторизован)
    if (response && response.status === 401) {
      // Здесь можно добавить логику для перенаправления на страницу входа
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    
    return Promise.reject(error);
  }
);

export default apiClient; 