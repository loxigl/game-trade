import apiClient from './client';
import { UserResponse, ProfileResponse, UsersQueryParams } from '../types/user';

const API_BASE_URL = '/marketplace/users';

// API-клиент для работы с пользователями
export const userApi = {
  // Кэш пользователей для предотвращения лишних запросов
  getUsersMap: new Map<number, UserResponse | ProfileResponse>(),
  
  // Для блокировки повторных запросов к проблемным пользователям
  failedUserRequests: new Set<number>(),
  
  // Максимальное количество повторных попыток запроса
  maxRetries: 2,
  
  // Счетчик попыток запроса по ID пользователя
  retryCounters: new Map<number, number>(),
  
  // Очистка кэша (полезно для тестирования или обновления данных)
  clearCache(): void {
    this.getUsersMap.clear();
    this.failedUserRequests.clear();
    this.retryCounters.clear();
  },
  
  // Проверка, был ли запрос неудачным слишком много раз
  hasExceededRetries(userId: number): boolean {
    const count = this.retryCounters.get(userId) || 0;
    return count >= this.maxRetries;
  },
  
  // Инкремент счетчика попыток
  incrementRetryCounter(userId: number): void {
    const count = this.retryCounters.get(userId) || 0;
    this.retryCounters.set(userId, count + 1);
    
    if (count + 1 >= this.maxRetries) {
      this.failedUserRequests.add(userId);
    }
  },
  
  // Получение списка пользователей по их ID
  async getUsers(ids?: number[]): Promise<UserResponse[]> {
    if (!ids || ids.length === 0) {
      return [];
    }
    
    // Фильтруем ID, к которым не стоит делать запросы из-за предыдущих ошибок
    const validIds = ids.filter(id => !this.failedUserRequests.has(id));
    
    if (validIds.length === 0) {
      return [];
    }
    
    const params: UsersQueryParams = {
      ids: validIds
    };
    
    try {
      const response = await apiClient.get<UserResponse[]>(API_BASE_URL, { params });
      
      // Добавляем пользователей в кэш
      if (response.data && Array.isArray(response.data)) {
        response.data.forEach(user => {
          if (user && user.id) {
            this.getUsersMap.set(user.id, user);
            
            // Сбрасываем счетчик попыток для успешных запросов
            this.retryCounters.delete(user.id);
          }
        });
      }
      
      return response.data || [];
    } catch (error) {
      console.error('Ошибка при получении списка пользователей:', error);
      
      // Инкрементируем счетчики попыток для всех запрошенных ID
      validIds.forEach(id => this.incrementRetryCounter(id));
      
      return [];
    }
  },
  
  // Получение профиля пользователя по ID
  async getUserProfile(userId: number): Promise<ProfileResponse | null> {
    if (!userId || this.failedUserRequests.has(userId)) {
      return null;
    }
    
    try {
      const response = await apiClient.get<ProfileResponse>(`${API_BASE_URL}/${userId}`);
      
      // Добавляем профиль в кэш
      if (response.data && response.data.user_id) {
        this.getUsersMap.set(response.data.user_id, response.data);
        
        // Сбрасываем счетчик попыток
        this.retryCounters.delete(userId);
      }
      
      return response.data;
    } catch (error) {
      console.error(`Ошибка при получении профиля пользователя ${userId}:`, error);
      
      // Инкрементируем счетчик попыток
      this.incrementRetryCounter(userId);
      
      return null;
    }
  },
  
  // Получение пользователя из кэша или с сервера
  async getCachedUser(userId: number): Promise<UserResponse | ProfileResponse | null> {
    if (!userId) {
      return null;
    }
    
    // Проверяем кэш
    if (this.getUsersMap.has(userId)) {
      return this.getUsersMap.get(userId) || null;
    }
    
    // Проверяем, не превышено ли количество попыток
    if (this.failedUserRequests.has(userId)) {
      console.log(`Пропуск запроса для пользователя ${userId} из-за предыдущих ошибок`);
      return this.getFallbackUser(userId);
    }
    
    try {
      // Сначала пробуем получить полный профиль
      const profile = await this.getUserProfile(userId);
      if (profile) {
        return profile;
      }
      
      // Если не получилось, пробуем получить базовую информацию о пользователе
      if (!this.hasExceededRetries(userId)) {
        const users = await this.getUsers([userId]);
        if (users && users.length > 0) {
          return users[0];
        }
      }
      
      // Если и это не получилось, возвращаем заглушку
      return this.getFallbackUser(userId);
    } catch (error) {
      console.error(`Ошибка получения пользователя ${userId}:`, error);
      
      // Добавляем заглушку в кэш, чтобы не делать повторных запросов
      const fallbackUser = this.getFallbackUser(userId);
      this.getUsersMap.set(userId, fallbackUser);
      
      return fallbackUser;
    }
  },
  
  // Создание заглушки пользователя, если не удалось получить реальные данные
  getFallbackUser(userId: number): UserResponse {
    const fallbackUser = {
      id: userId,
      username: `Пользователь ${userId}`,
      email: '',
      created_at: new Date().toISOString(),
      // Добавляем флаг, чтобы отметить, что это заглушка
      _isFallback: true
    };
    
    // Добавляем заглушку в кэш
    this.getUsersMap.set(userId, fallbackUser as UserResponse);
    
    return fallbackUser as UserResponse;
  },
  
  // Получение отображаемого имени пользователя
  getUserDisplayName(userId: number): string {
    if (!userId) return 'Неизвестный пользователь';
    
    const user = this.getUsersMap.get(userId);
    
    if (user) {
      // Если есть имя пользователя
      if ('username' in user && user.username) {
        return user.username;
      }
    }
    
    return `Пользователь ${userId}`;
  },
  
  // Получение URL аватара пользователя
  getUserAvatarUrl(userId: number): string | undefined {
    if (!userId) return undefined;
    
    const user = this.getUsersMap.get(userId);
    
    if (user) {
      // Проверяем, есть ли avatar_url в объекте пользователя или профиля
      if ('avatar_url' in user && user.avatar_url) {
        return user.avatar_url;
      }
      
      // Проверяем, есть ли profile с avatar_url в объекте пользователя
      if ('profile' in user && user.profile && user.profile.avatar_url) {
        return user.profile.avatar_url;
      }
    }
    
    return undefined;
  },
  
  // Предзагрузка информации о нескольких пользователях
  async preloadUsers(userIds: number[]): Promise<void> {
    if (!userIds || userIds.length === 0) {
      return;
    }
    
    try {
      // Фильтруем только валидные ID, которых нет в кэше и которые не были помечены как проблемные
      const idsToLoad = userIds.filter(id => 
        id && 
        id > 0 && 
        !this.getUsersMap.has(id) && 
        !this.failedUserRequests.has(id)
      );
      
      if (idsToLoad.length === 0) {
        return;
      }
      
      // Загружаем пользователей (до 10 за один запрос для уменьшения нагрузки)
      const chunkSize = 10;
      for (let i = 0; i < idsToLoad.length; i += chunkSize) {
        const chunk = idsToLoad.slice(i, i + chunkSize);
        await this.getUsers(chunk);
      }
    } catch (error) {
      console.error('Ошибка предзагрузки пользователей:', error);
    }
  }
};

export default userApi; 