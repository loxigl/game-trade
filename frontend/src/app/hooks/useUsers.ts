import { useState, useEffect, useCallback, useRef } from 'react';
import userApi from '../api/user';
import { UserResponse, ProfileResponse } from '../types/user';

interface UseUsersReturn {
  users: Map<number, UserResponse | ProfileResponse>;
  loading: boolean;
  error: string | null;
  getUser: (userId: number) => Promise<UserResponse | ProfileResponse | null>;
  getUserName: (userId: number) => string;
  getUserAvatar: (userId: number) => string | undefined;
  preloadUsers: (userIds: number[]) => Promise<void>;
  clearCache: () => void;
}

export function useUsers(): UseUsersReturn {
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  
  // Используем useRef для отслеживания загружаемых пользователей
  const loadingUserIds = useRef<Set<number>>(new Set());
  
  // Для управления кэшем используем API напрямую
  const usersMap = userApi.getUsersMap;
  
  // Для предотвращения повторных загрузок после перерендера
  const mountedRef = useRef<boolean>(true);
  
  // Эффект для очистки флага при размонтировании
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  // Загрузка информации о пользователе без циклических вызовов
  const getUser = useCallback(async (userId: number): Promise<UserResponse | ProfileResponse | null> => {
    // Если ID некорректный, возвращаем null
    if (!userId || userId <= 0) {
      return null;
    }

    // Если пользователь уже в кэше, просто возвращаем его
    if (usersMap.has(userId)) {
      return usersMap.get(userId) || null;
    }

    // Если пользователь уже загружается, не делаем повторный запрос
    if (loadingUserIds.current.has(userId)) {
      return null;
    }
    
    // Если пользователь находится в списке неудачных запросов, возвращаем заглушку
    if (userApi.failedUserRequests.has(userId)) {
      return userApi.getFallbackUser(userId);
    }

    try {
      // Помечаем пользователя как загружаемого
      loadingUserIds.current.add(userId);
      setLoading(true);
      
      // Загружаем пользователя через API
      const user = await userApi.getCachedUser(userId);
      
      // Если компонент все еще смонтирован, обновляем состояние
      if (mountedRef.current) {
        setError(null);
      }
      
      // Возвращаем результат или заглушку
      return user || userApi.getFallbackUser(userId);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Ошибка получения пользователя';
      
      // Если компонент все еще смонтирован, обновляем состояние ошибки
      if (mountedRef.current) {
        setError(errorMessage);
      }
      
      console.error(`Ошибка загрузки пользователя ${userId}:`, err);
      return userApi.getFallbackUser(userId);
    } finally {
      // Снимаем пометку о загрузке
      loadingUserIds.current.delete(userId);
      
      // Если компонент все еще смонтирован, обновляем состояние загрузки
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, []);

  // Синхронная функция получения имени пользователя (без автоматической загрузки)
  const getUserName = useCallback((userId: number): string => {
    if (!userId || userId <= 0) {
      return 'Неизвестный пользователь';
    }
    
    // Сначала пробуем получить из кэша
    const cachedName = userApi.getUserDisplayName(userId);
    
    // Если пользователя нет в кэше, он не загружается, и он не в черном списке,
    // запускаем загрузку, но не ждем результат
    if (!usersMap.has(userId) && 
        !loadingUserIds.current.has(userId) && 
        !userApi.failedUserRequests.has(userId)) {
      getUser(userId).catch(() => {});
    }
    
    return cachedName;
  }, [getUser]);

  // Синхронная функция получения аватара пользователя (без автоматической загрузки)
  const getUserAvatar = useCallback((userId: number): string | undefined => {
    if (!userId || userId <= 0) {
      return undefined;
    }
    
    // Сначала пробуем получить из кэша
    const cachedAvatar = userApi.getUserAvatarUrl(userId);
    
    // Если пользователя нет в кэше, он не загружается, и он не в черном списке,
    // запускаем загрузку, но не ждем результат
    if (!usersMap.has(userId) && 
        !loadingUserIds.current.has(userId) && 
        !userApi.failedUserRequests.has(userId)) {
      getUser(userId).catch(() => {});
    }
    
    return cachedAvatar;
  }, [getUser]);

  // Предзагрузка нескольких пользователей
  const preloadUsers = useCallback(async (userIds: number[]): Promise<void> => {
    if (!userIds || userIds.length === 0) {
      return;
    }
    
    // Фильтруем только валидные ID, которых нет в кэше, не загружаются в данный момент и не в черном списке
    const idsToLoad = userIds.filter(id => 
      id && id > 0 && 
      !usersMap.has(id) && 
      !loadingUserIds.current.has(id) &&
      !userApi.failedUserRequests.has(id)
    );
    
    if (idsToLoad.length === 0) {
      return;
    }
    
    try {
      if (mountedRef.current) {
        setLoading(true);
      }
      
      // Помечаем всех пользователей как загружаемых
      idsToLoad.forEach(id => loadingUserIds.current.add(id));
      
      // Загружаем пользователей
      await userApi.preloadUsers(idsToLoad);
      
      if (mountedRef.current) {
        setError(null);
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Ошибка предзагрузки пользователей';
      
      if (mountedRef.current) {
        setError(errorMessage);
      }
      
      console.error('Ошибка предзагрузки пользователей:', err);
    } finally {
      // Снимаем пометки о загрузке
      idsToLoad.forEach(id => loadingUserIds.current.delete(id));
      
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, []);
  
  // Очистка кэша (экспортируем метод API)
  const clearCache = useCallback(() => {
    userApi.clearCache();
  }, []);

  return {
    users: usersMap,
    loading,
    error,
    getUser,
    getUserName,
    getUserAvatar,
    preloadUsers,
    clearCache
  };
} 