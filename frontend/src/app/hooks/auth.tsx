'use client';

import { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';

// Типы данных
interface User {
  id: number;
  username: string;
  email: string;
  roles: string[];
  is_active: boolean;
}

interface UserPermissions {
  roles: string[];
  permissions: string[];
  is_admin: boolean;
  is_moderator: boolean;
  is_seller: boolean;
  highest_role: string;
}

interface UIPermissions {
  [key: string]: boolean;
}

interface AuthContextType {
  user: User | null;
  userPermissions: UserPermissions | null;
  uiPermissions: UIPermissions | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  login: (credentials: { email: string; password: string }) => Promise<void>;
  logout: () => Promise<void>;
  register: (userData: RegisterUserData) => Promise<void>;
  refreshToken: () => Promise<boolean>;
}

// Создаем интерфейс для данных регистрации
interface RegisterUserData {
  username: string;
  email: string;
  password: string;
  [key: string]: string; // Для поддержки дополнительных полей
}

// Создаем контекст для аутентификации
const AuthContext = createContext<AuthContextType | undefined>(undefined);

// API URL
const API_URL = process.env.NEXT_PUBLIC_AUTH_URL || 'http://localhost:8000';
console.log('API_URL', API_URL)
console.log('NEXT_PUBLIC_AUTH_URL', process.env.NEXT_PUBLIC_AUTH_URL)
console.log('NEXT_PUBLIC_API_URL', process.env.NEXT_PUBLIC_API_URL)
// Provider компонент
export const AuthProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<User | null>(null);
  const [userPermissions, setUserPermissions] = useState<UserPermissions | null>(null);
  const [uiPermissions, setUIPermissions] = useState<UIPermissions | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  // Оборачиваем fetchUserData в useCallback
  const fetchUserData = useCallback(async () => {
    const token = localStorage.getItem('accessToken');
    
    if (!token) {
      setIsAuthenticated(false);
      setUser(null);
      setIsLoading(false);
      return;
    }
    
    setIsLoading(true);
    
    try {
      const response = await fetch(`${API_URL}/account/me`, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      });
      
      if (!response.ok) {
        // Если токен не валиден, пробуем обновить
        const refreshed = await refreshToken();
        
        if (!refreshed) {
          setIsAuthenticated(false);
          setUser(null);
          return;
        }
        
        // Повторяем запрос с новым токеном
        const newToken = localStorage.getItem('accessToken');
        const retryResponse = await fetch(`${API_URL}/account/me`, {
          headers: {
            Authorization: `Bearer ${newToken}`
          }
        });
        
        if (!retryResponse.ok) {
          throw new Error('Failed to fetch user data');
        }
        
        const userData = await retryResponse.json();
        setUser(userData);
        setIsAuthenticated(true);
      } else {
        const userData = await response.json();
        setUser(userData);
        setIsAuthenticated(true);
      }
      
      // Загружаем разрешения пользователя
      await fetchUserPermissions();
      
    } catch (error) {
      console.error('Error fetching user data:', error);
      setIsAuthenticated(false);
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, [API_URL]); // Добавляем API_URL как зависимость

  // Получение разрешений пользователя
  const fetchUserPermissions = async () => {
    try {
      const token = localStorage.getItem('accessToken');
      if (!token) return;

      // Получаем информацию о разрешениях пользователя
      const permissionsResponse = await fetch(`${API_URL}/account/permissions`, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      });

      if (!permissionsResponse.ok) {
        throw new Error('Failed to fetch user permissions');
      }

      const permissionsData = await permissionsResponse.json();
      setUserPermissions(permissionsData);

      // Получаем информацию о разрешениях для UI
      const uiPermissionsResponse = await fetch(`${API_URL}/account/ui-permissions`, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      });

      if (!uiPermissionsResponse.ok) {
        throw new Error('Failed to fetch UI permissions');
      }

      const uiPermissionsData = await uiPermissionsResponse.json();
      setUIPermissions(uiPermissionsData);

    } catch (error) {
      console.error('Error fetching permissions:', error);
    }
  };

  // Авторизация
  const login = async (credentials: { email: string; password: string }) => {
    setIsLoading(true);

    try {
      const response = await fetch(`${API_URL}/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(credentials)
      });

      if (!response.ok) {
        throw new Error('Login failed');
      }

      const data = await response.json();

      // Сохраняем токены
      localStorage.setItem('accessToken', data.access_token);
      localStorage.setItem('refreshToken', data.refresh_token);

      // Загружаем данные пользователя
      await fetchUserData();

    } catch (error) {
      console.error('Login error:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  // Выход
  const logout = async () => {
    setIsLoading(true);

    try {
      const token = localStorage.getItem('accessToken');
      if (token) {
        // Вызываем API для логаута на сервере
        await fetch(`${API_URL}/logout`, {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${token}`
          }
        });
      }
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      // Очищаем локальное состояние и хранилище
      localStorage.removeItem('accessToken');
      localStorage.removeItem('refreshToken');
      setUser(null);
      setUserPermissions(null);
      setUIPermissions(null);
      setIsAuthenticated(false);
      setIsLoading(false);
    }
  };

  // Регистрация
  const register = async (userData: RegisterUserData) => {
    setIsLoading(true);

    try {
      console.log('Отправка запроса на:', `${API_URL}/auth/register`);
      console.log('С данными:', userData);

      const response = await fetch(`${API_URL}/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(userData)
      });


      if (!response.ok) {
        throw new Error('Registration failed  for url: ' + `${API_URL}/auth/register`);
      }

      const data = await response.json();
      console.log('Registration successful', data);

      // После успешной регистрации можно автоматически авторизовать пользователя
      await login({
        email: userData.email,
        password: userData.password
      });

    } catch (error) {
      console.error('Registration error:', error);
      console.error(API_URL)
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  // Обновление токена
  const refreshToken = async (): Promise<boolean> => {
    try {
      const refresh = localStorage.getItem('refreshToken');
      if (!refresh) {
        return false;
      }

      const response = await fetch(`${API_URL}/refresh`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ refresh_token: refresh })
      });

      if (!response.ok) {
        localStorage.removeItem('accessToken');
        localStorage.removeItem('refreshToken');
        return false;
      }

      const data = await response.json();
      localStorage.setItem('accessToken', data.access_token);
      localStorage.setItem('refreshToken', data.refresh_token);
      return true;

    } catch (error) {
      console.error('Token refresh error:', error);
      localStorage.removeItem('accessToken');
      localStorage.removeItem('refreshToken');
      return false;
    }
  };

  // Загружаем данные пользователя при инициализации приложения
  useEffect(() => {
    fetchUserData();
  }, [fetchUserData]);  // Теперь fetchUserData в зависимостях

  // Значение контекста
  const contextValue: AuthContextType = {
    user,
    userPermissions,
    uiPermissions,
    isLoading,
    isAuthenticated,
    login,
    logout,
    register,
    refreshToken
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
};

// Хук для использования контекста аутентификации
export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
