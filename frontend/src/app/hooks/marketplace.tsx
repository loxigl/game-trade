  import { useState, useEffect, useCallback, useRef } from 'react';
  import { useAuth } from './auth';

  // Определение типов данных
  interface Game {
    id: number;
    name: string;
    logo_url: string;
    description: string;
  }

  interface Category {
    id: number;
    name: string;
    icon_url: string;
    game_id: number;
    game_name: string;
  }

  interface Attribute {
    id: number;
    name: string;
    type: string;
    options: string | null;
    is_required: boolean;
    is_filterable: boolean;
  }

  interface ItemTemplate {
    id: number;
    name: string;
    description: string;
    category_id: number;
    category?: Category;
  }

  interface SellerProfile {
    id: number;
    username: string;
    rating?: number;
    avatar_url?: string;
  }

  interface ListingImage {
    id: number;
    url: string;
    is_main: boolean;
    order_index: number;
  }

  interface Listing {
    id: number;
    title: string;
    description: string;
    price: number;
    currency: string;
    seller_id: number;
    item_template_id: number;
    status: string;
    views_count: number;
    created_at: string;
    updated_at: string;
    seller?: SellerProfile;
    item_template?: ItemTemplate;
    images: ListingImage[];
    attribute_values?: Array<{
      attribute_id: number;
      attribute_type: string;
      value_string?: string;
      value_number?: number;
      value_boolean?: boolean;
    }>;
  }

  interface ListingFormData {
    title: string;
    description: string;
    price: number;
    currency: string;
    item_template_id: number;
    game_id?: number;
    category_id?: number;
  }

  interface SearchParams {
    query?: string;
    game_ids?: number[];
    category_ids?: number[];
  }

  interface FilterParams {
    min_price?: number;
    max_price?: number;
    currency?: string;
    attributes?: { [key: string]: string | number | boolean };
  }

  interface PaginationParams {
    page: number;
    limit: number;
  }

  interface PaginationMeta {
    current_page: number;
    total_pages: number;
    total_items: number;
    items_per_page: number;
    // Дополнительные поля, которые может возвращать API
    page?: number;
    pages?: number;
    total?: number;
    limit?: number;
    query?: string | null;
  }

  // Хук для работы с API маркетплейса
  export const useMarketplace = () => {
    const { isAuthenticated } = useAuth();
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // API URL для маркетплейса
    const API_URL = process.env.NEXT_PUBLIC_MARKETPLACE_URL || 'http://localhost:8001/api/marketplace';

    // Кэш для хранения результатов запросов
    const cacheRef = useRef<Map<string, { data: any, timestamp: number }>>(new Map());
    // Время жизни кэша (5 минут)
    const CACHE_TTL = 5 * 60 * 1000;
    // Отслеживание текущих запросов
    const pendingRequestsRef = useRef<Map<string, AbortController>>(new Map());

    // Функция для создания ключа кэша
    const createCacheKey = (endpoint: string, params?: any) => {
      return `${endpoint}:${params ? JSON.stringify(params) : ''}`;
    };

    // Функция для проверки и получения данных из кэша
    const getFromCache = (cacheKey: string) => {
      if (cacheRef.current.has(cacheKey)) {
        const cachedData = cacheRef.current.get(cacheKey);
        if (cachedData && Date.now() - cachedData.timestamp < CACHE_TTL) {
          return cachedData.data;
        } else {
          // Удаляем устаревший кэш
          cacheRef.current.delete(cacheKey);
        }
      }
      return null;
    };

    // Функция для сохранения данных в кэш
    const saveToCache = (cacheKey: string, data: any) => {
      cacheRef.current.set(cacheKey, {
        data,
        timestamp: Date.now()
      });
    };

    // Функция для выполнения запроса с кэшированием
    const fetchWithCache = async (endpoint: string, options: RequestInit = {}, params?: any, useCache = true) => {
      const cacheKey = createCacheKey(endpoint, params);

      // Проверяем, есть ли данные в кэше
      if (useCache) {
        const cachedData = getFromCache(cacheKey);
        if (cachedData) {
          return cachedData;
        }
      }

      // Отменяем предыдущий запрос с такими же параметрами, если он еще выполняется
      if (pendingRequestsRef.current.has(cacheKey)) {
        pendingRequestsRef.current.get(cacheKey)?.abort();
        pendingRequestsRef.current.delete(cacheKey);
      }

      // Создаем новый AbortController для текущего запроса
      const abortController = new AbortController();
      pendingRequestsRef.current.set(cacheKey, abortController);

      try {
        const response = await fetch(endpoint, {
          ...options,
          signal: abortController.signal
        });

        if (!response.ok) {
          // Получаем подробную информацию об ошибке
          let errorMessage = `API error: ${response.status}`;
          let errorDetails: any = null;
          
          try {
            // Пытаемся прочитать JSON с деталями ошибки
            const errorData = await response.clone().json();
            errorDetails = errorData;
            
            if (errorData.detail) {
              if (typeof errorData.detail === 'string') {
                errorMessage = errorData.detail;
              } else if (Array.isArray(errorData.detail)) {
                errorMessage = errorData.detail.map((e: any) => 
                  e.loc && e.msg ? `${e.loc.join('.')}: ${e.msg}` : JSON.stringify(e)
                ).join('; ');
              } else {
                errorMessage = JSON.stringify(errorData.detail);
              }
            }
          } catch (jsonErr) {
            // Если не удалось прочитать JSON, пробуем прочитать текст
            try {
              errorMessage = await response.clone().text();
            } catch (textErr) {
              console.error('Не удалось прочитать ответ ошибки:', textErr);
            }
          }
          
          // Создаем расширенный объект ошибки с дополнительными данными
          const error = new Error(errorMessage);
          (error as any).status = response.status;
          (error as any).details = errorDetails;
          (error as any).response = response;
          
          // Бросаем расширенную ошибку
          throw error;
        }

        const data = await response.json();

        // Сохраняем результаты в кэш
        if (useCache) {
          saveToCache(cacheKey, data);
        }

        return data;
      } finally {
        // Удаляем запрос из списка выполняемых
        pendingRequestsRef.current.delete(cacheKey);
      }
    };

    // Получение токена авторизации
    const getAuthHeader = useCallback(() => {
      const token = localStorage.getItem('accessToken');
      return token ? { Authorization: `Bearer ${token}` } : undefined;
    }, []);

    // Получение списка игр
    const getGames = useCallback(async (): Promise<Game[]> => {
      setIsLoading(true);
      setError(null);

      try {
        const data = await fetchWithCache(`${API_URL}/games`);
        return data.data || [];
      } catch (err) {
        if (err instanceof Error && err.name !== 'AbortError') {
          setError(err.message || 'Произошла ошибка при загрузке игр');
        }
        return [];
      } finally {
        setIsLoading(false);
      }
    }, [API_URL]);

    // Получение категорий для выбранной игры
    const getCategoriesByGame = useCallback(async (gameId: number): Promise<Category[]> => {
      setIsLoading(true);
      setError(null);

      try {
        const data = await fetchWithCache(`${API_URL}/categories?game_id=${gameId}`);
        return data.data || [];
      } catch (err) {
        if (err instanceof Error && err.name !== 'AbortError') {
          setError(err.message || 'Произошла ошибка при загрузке категорий');
        }
        return [];
      } finally {
        setIsLoading(false);
      }
    }, [API_URL]);

    // Получение атрибутов для выбранной категории
    const getAttributesByCategory = useCallback(async (categoryId: number): Promise<Attribute[]> => {
      setIsLoading(true);
      setError(null);

      try {
        const data = await fetchWithCache(`${API_URL}/categories/${categoryId}/attributes`);
        return data.data || [];
      } catch (err) {
        if (err instanceof Error && err.name !== 'AbortError') {
          setError(err.message || 'Произошла ошибка при загрузке атрибутов');
        }
        return [];
      } finally {
        setIsLoading(false);
      }
    }, [API_URL]);

    // Получение атрибутов для выбранного шаблона
    const getTemplateAttributes = useCallback(async (templateId: number): Promise<any[]> => {
      setIsLoading(true);
      setError(null);

      try {
        const data = await fetchWithCache(`${API_URL}/templates/${templateId}/attributes`);
        return data.data || [];
      } catch (err) {
        if (err instanceof Error && err.name !== 'AbortError') {
          setError(err.message || 'Произошла ошибка при загрузке атрибутов шаблона');
        }
        return [];
      } finally {
        setIsLoading(false);
      }
    }, [API_URL]);

    // Получение шаблонов предметов по категории
    const getTemplatesByCategory = useCallback(async (categoryId: number): Promise<ItemTemplate[]> => {
      setIsLoading(true);
      setError(null);

      try {
        const data = await fetchWithCache(`${API_URL}/categories/${categoryId}/templates`);
        return data.data || [];
      } catch (err) {
        if (err instanceof Error && err.name !== 'AbortError') {
          setError(err.message || 'Произошла ошибка при загрузке шаблонов');
        }
        return [];
      } finally {
        setIsLoading(false);
      }
    }, [API_URL]);

    // Поиск объявлений с фильтрацией
    const searchListings = useCallback(async (
      searchParams: SearchParams,
      filterParams?: FilterParams,
      pagination: PaginationParams = { page: 1, limit: 20 },
      sortBy: string = 'created_at',
      sortOrder: string = 'desc'
    ): Promise<{ items: Listing[], meta: PaginationMeta }> => {
      setIsLoading(true);
      setError(null);

      try {
        const url = new URL(`${API_URL}/search/listings`);
        url.searchParams.append('page', pagination.page.toString());
        url.searchParams.append('limit', pagination.limit.toString());
        url.searchParams.append('sort_by', sortBy);
        url.searchParams.append('sort_order', sortOrder);

        const requestParams = {
          search_params: searchParams,
          filter_params: filterParams
        };

        const data = await fetchWithCache(
          url.toString(),
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestParams)
          },
          requestParams,
          false // Не используем кэш для поиска
        );

        const totalPages = data.meta.total_pages || data.meta.pages || 1;

        return {
          items: data.data || [],
          meta: {
            current_page: data.meta.current_page,
            total_pages: totalPages,
            total_items: data.meta.total_items,
            items_per_page: pagination.limit
          }
        };
      } catch (err) {
        if (err instanceof Error && err.name !== 'AbortError') {
          setError(err.message || 'Произошла ошибка при поиске объявлений');
        }
        return {
          items: [],
          meta: {
            current_page: 1,
            total_pages: 1,
            total_items: 0,
            items_per_page: pagination.limit
          }
        };
      } finally {
        setIsLoading(false);
      }
    }, [API_URL]);

    // Получение объявления по ID
    const getListingById = useCallback(async (listingId: number): Promise<Listing | null> => {
      setIsLoading(true);
      setError(null);

      try {
        // Используем детальный эндпоинт вместо базового для получения полной информации
        const data = await fetchWithCache(`${API_URL}/listings/${listingId}/detail`);
        return data.data;
      } catch (err) {
        if (err instanceof Error && err.name !== 'AbortError') {
          setError(err.message || 'Произошла ошибка при загрузке объявления');
        }
        return null;
      } finally {
        setIsLoading(false);
      }
    }, [API_URL]);

    // Создание нового объявления
    const createListing = useCallback(async (formData: ListingFormData): Promise<Listing | null> => {
      if (!isAuthenticated) {
        setError('Необходимо авторизоваться для создания объявления');
        return null;
      }

      setIsLoading(true);
      setError(null);

      try {
        const headers: HeadersInit = {
          'Content-Type': 'application/json'
        };

        const authHeader = getAuthHeader();
        if (authHeader) {
          Object.assign(headers, authHeader);
        }

        const data = await fetchWithCache(
          `${API_URL}/listings`,
          {
            method: 'POST',
            headers,
            body: JSON.stringify(formData)
          },
          formData,
          false // Не используем кэш для создания
        );

        return data.data;
      } catch (err) {
        // Просто пробрасываем ошибку дальше для обработки в компоненте
        console.error('Ошибка при создании объявления:', err);
        
        // Сохраняем сообщение в состоянии ошибки
        if (err instanceof Error) {
          setError(err.message || 'Произошла ошибка при создании объявления');
        } else {
          setError('Неизвестная ошибка при создании объявления');
        }
        
        // Пробрасываем исходную ошибку для обработки в компоненте
        throw err;
      } finally {
        setIsLoading(false);
      }
    }, [API_URL, isAuthenticated, getAuthHeader]);

    // Обновление объявления
    const updateListing = useCallback(async (listingId: number, formData: Partial<ListingFormData>): Promise<Listing | null> => {
      if (!isAuthenticated) {
        setError('Необходимо авторизоваться для обновления объявления');
        return null;
      }

      setIsLoading(true);
      setError(null);

      try {
        const headers: HeadersInit = {
          'Content-Type': 'application/json'
        };

        const authHeader = getAuthHeader();
        if (authHeader) {
          Object.assign(headers, authHeader);
        }

        // Используем fetchWithCache для унификации обработки ошибок
        const data = await fetchWithCache(
          `${API_URL}/listings/${listingId}`,
          {
            method: 'PUT',
            headers,
            body: JSON.stringify(formData)
          },
          formData,
          false // Не используем кэш для обновления
        );

        return data.data;
      } catch (err) {
        // Просто пробрасываем ошибку дальше для обработки в компоненте
        console.error('Ошибка при обновлении объявления:', err);
        
        // Сохраняем сообщение в состоянии ошибки
        if (err instanceof Error) {
          setError(err.message || 'Произошла ошибка при обновлении объявления');
        } else {
          setError('Неизвестная ошибка при обновлении объявления');
        }
        
        // Пробрасываем исходную ошибку для обработки в компоненте
        throw err;
      } finally {
        setIsLoading(false);
      }
    }, [API_URL, isAuthenticated, getAuthHeader]);

    // Удаление объявления
    const deleteListing = useCallback(async (listingId: number): Promise<boolean> => {
      if (!isAuthenticated) {
        setError('Необходимо авторизоваться для удаления объявления');
        return false;
      }

      setIsLoading(true);
      setError(null);

      try {
        const headers: HeadersInit = {};

        const authHeader = getAuthHeader();
        if (authHeader) {
          Object.assign(headers, authHeader);
        }

        const response = await fetch(`${API_URL}/listings/${listingId}`, {
          method: 'DELETE',
          headers
        });

        if (!response.ok) {
          throw new Error('Failed to delete listing');
        }

        return true;
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Произошла ошибка при удалении объявления');
        return false;
      } finally {
        setIsLoading(false);
      }
    }, [API_URL, isAuthenticated, getAuthHeader]);

    // Очистка кэша
    const clearCache = useCallback(() => {
      cacheRef.current.clear();
    }, []);

    // Отмена всех текущих запросов
    useEffect(() => {
      return () => {
        pendingRequestsRef.current.forEach(controller => {
          controller.abort();
        });
        pendingRequestsRef.current.clear();
      };
    }, []);

    // Возвращаем методы и состояние
    return {
      isLoading,
      error,
      getGames,
      getCategoriesByGame,
      getAttributesByCategory,
      getTemplateAttributes,
      getTemplatesByCategory,
      searchListings,
      getListingById,
      createListing,
      updateListing,
      deleteListing,
      clearCache
    };
  };
