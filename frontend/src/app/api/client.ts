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

// Состояние для предотвращения бесконечных циклов редиректа
let isRefreshing = false;
let failedQueue: {
  resolve: (token: string) => void;
  reject: (error: any) => void;
}[] = [];

// Функция для обработки запросов из очереди
const processQueue = (error: any, token: string | null) => {
  failedQueue.forEach(promise => {
    if (error) {
      promise.reject(error);
    } else if (token) {
      promise.resolve(token);
    }
  });
  
  failedQueue = [];
};

// Добавляем перехватчик запросов для подстановки токена авторизации
apiClient.interceptors.request.use(
  (config) => {
    // Пробуем получить токен сначала как 'token', затем как 'accessToken'
    let token = localStorage.getItem('token');
    
    // Если токен не найден как 'token', пробуем 'accessToken'
    if (!token) {
      token = localStorage.getItem('accessToken');
    }
    
    if (token) {
      // Убедимся, что заголовок Authorization установлен правильно
      config.headers.Authorization = `Bearer ${token}`;
      
      // Для отладки
      console.log('Sending request with token:', config.url);
    } else {
      console.warn('No auth token available for request:', config.url);
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Перехватчик ответов для обработки ошибок аутентификации
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    // Не обрабатываем ошибки, если мы не в браузере (SSR)
    if (typeof window === 'undefined') {
      return Promise.reject(error);
    }
    
    const originalRequest = error.config;
    console.log('API Error:', {
      url: originalRequest?.url,
      method: originalRequest?.method,
      status: error.response?.status,
      retried: originalRequest?._retry || false,
      hasAuthHeader: !!originalRequest?.headers?.Authorization,
      hasRefreshToken: !!localStorage.getItem('refreshToken'),
      errorMessage: error.message
    });
    
    // Проверяем, что ошибка 401 и запрос не является уже повторным
    if (error.response?.status === 401 && !originalRequest._retry) {
      // Предотвращаем бесконечный цикл запросов
      if (isRefreshing) {
        console.log('Token refresh already in progress, adding request to queue');
        // Если уже идет обновление токена, добавляем запрос в очередь
        try {
          const token = await new Promise<string>((resolve, reject) => {
            failedQueue.push({ resolve, reject });
          });
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return apiClient(originalRequest);
        } catch (err) {
          // Если не удалось обновить токен, перенаправляем на страницу входа
          console.error('Token refresh failed in queue:', err);
          return Promise.reject(error);
        }
      }
      
      // Помечаем запрос как повторный
      originalRequest._retry = true;
      isRefreshing = true;
      
      try {
        // Пытаемся обновить токен
        const refreshToken = localStorage.getItem('refreshToken');
        
        if (!refreshToken) {
          console.warn('No refresh token available, authentication required');
          throw new Error('No refresh token available');
        }
        
        console.log('Attempting to refresh token...');
        
        // Создаем новый экземпляр axios для запроса обновления токена
        // чтобы избежать рекурсивного перехвата
        const response = await axios.post(
          `${process.env.NEXT_PUBLIC_AUTH_URL || 'http://localhost:8000'}/refresh`,
          { refresh_token: refreshToken },
          { headers: { 'Content-Type': 'application/json' } }
        );
        
        if (response.status === 200) {
          console.log('Token refreshed successfully');
          const { access_token, refresh_token } = response.data;
          
          // Сохраняем новые токены
          localStorage.setItem('accessToken', access_token);
          localStorage.setItem('refreshToken', refresh_token);
          localStorage.setItem('token', access_token); // Дублируем для совместимости
          
          // Обрабатываем очередь запросов
          processQueue(null, access_token);
          
          // Повторяем оригинальный запрос с новым токеном
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return apiClient(originalRequest);
        } else {
          console.error('Non-200 response from refresh token endpoint:', response.status);
          throw new Error('Failed to refresh token');
        }
      } catch (refreshError) {
        // Обрабатываем ошибку обновления токена
        console.error('Token refresh error:', refreshError);
        
        // Очищаем токены
        localStorage.removeItem('accessToken');
        localStorage.removeItem('refreshToken');
        localStorage.removeItem('token');
        
        // Обрабатываем очередь запросов с ошибкой
        processQueue(refreshError, null);
        
        // Если пользователь пытался получить кошельки или другие приватные ресурсы,
        // перенаправляем с параметром, указывающим причину
        const privateUrlPatterns = ['/wallets', '/profile', '/account', '/orders', '/sales', '/payments'];
        
        const originalUrl = originalRequest.url || '';
        const isPrivateEndpoint = privateUrlPatterns.some(pattern => originalUrl.includes(pattern));
        
        if (isPrivateEndpoint) {
          console.log('Redirecting to login due to auth failure on private endpoint:', originalUrl);
          window.location.href = '/login?redirected=true&from=' + encodeURIComponent(originalUrl);
        } else {
          console.log('Auth failure on public endpoint, not redirecting:', originalUrl);
        }
        
        return Promise.reject(error);
      } finally {
        isRefreshing = false;
      }
    }
    
    return Promise.reject(error);
  }
);

// Добавьте константы базовых URL для сервисов:
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '';
export const AUTH_API_URL = `${API_BASE_URL}/auth`;
export const MARKETPLACE_API_URL = `${API_BASE_URL}/marketplace`;
export const PAYMENTS_API_URL = `${API_BASE_URL}/payments`;
export const CHAT_API_URL = `${API_BASE_URL}/chat`;

export default apiClient; 