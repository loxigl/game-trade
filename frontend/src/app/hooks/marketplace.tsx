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
    parent_id?: number | null;
    subcategories?: Category[];
    description?: string;
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
    is_negotiable?: boolean;
    seller_id: number;
    item_template_id: number;
    status: string;
    views_count: number;
    expires_at?: string;
    created_at: string;
    updated_at: string;
    seller?: SellerProfile;
    item_template?: ItemTemplate;
    images: ListingImage[];
    // Атрибуты объявления
    item_attributes?: Array<{
      attribute_id: number;
      attribute_name?: string;
      attribute_type: string;
      value_string?: string;
      value_number?: number;
      value_boolean?: boolean;
      is_required?: boolean;
      options?: string | string[];
    }>;
    template_attributes?: Array<{
      template_attribute_id: number;
      attribute_name?: string;
      attribute_type: string;
      value_string?: string;
      value_number?: number;
      value_boolean?: boolean;
      is_required?: boolean;
      options?: string | string[];
    }>;
    all_attributes?: Array<{
      attribute_id?: number;
      template_attribute_id?: number;
      attribute_name?: string;
      name?: string;
      attribute_type: string;
      value_string?: string;
      value_number?: number;
      value_boolean?: boolean;
      is_required?: boolean;
      options?: string | string[];
      attribute_source?: string;
    }>;
    // Дополнительные поля для детального просмотра
    seller_rating?: number;
    similar_listings?: Array<{
      id: number;
      title: string;
      price: number;
      currency: string;
      images: ListingImage[];
    }>;
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
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
  const { isAuthenticated, getAuthHeader } = useAuth();
  const cacheRef = useRef<Map<string, { data: any; timestamp: number }>>(new Map());
  const pendingRequestsRef = useRef<Map<string, Promise<any>>>(new Map());
  const CACHE_TTL = 5 * 60 * 1000; // 5 минут

    const createCacheKey = (endpoint: string, params?: any) => {
    return params ? `${endpoint}:${JSON.stringify(params)}` : endpoint;
    };

    const getFromCache = (cacheKey: string) => {
    const cached = cacheRef.current.get(cacheKey);
    if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
      return cached.data;
    }
          cacheRef.current.delete(cacheKey);
      return null;
    };

    const saveToCache = (cacheKey: string, data: any) => {
      cacheRef.current.set(cacheKey, {
        data,
        timestamp: Date.now()
      });
    };

  const fetchWithCache = useCallback(async (
    endpoint: string,
    options: RequestInit = {},
    params?: any,
    useCache = true
  ) => {
      const cacheKey = createCacheKey(endpoint, params);

      if (useCache) {
        const cachedData = getFromCache(cacheKey);
      if (cachedData) return cachedData;
      }

    // Проверяем, есть ли уже запрос с таким ключом
    const existingRequest = pendingRequestsRef.current.get(cacheKey);
    if (existingRequest) {
      return existingRequest;
      }

    // Создаем новый запрос
    const request = fetch(endpoint, options)
      .then(async (response) => {
        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        if (useCache) {
          saveToCache(cacheKey, data);
        }
        return data;
      })
      .finally(() => {
        pendingRequestsRef.current.delete(cacheKey);
      });

    // Сохраняем запрос в Map
    pendingRequestsRef.current.set(cacheKey, request);
    return request;
  }, []);

  // Очистка кэша при размонтировании
  useEffect(() => {
    return () => {
      cacheRef.current.clear();
      pendingRequestsRef.current.clear();
    };
    }, []);

  // API URL для маркетплейса
  const API_URL = process.env.NEXT_PUBLIC_MARKETPLACE_URL || 'http://localhost:8001/api/marketplace';

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
  }, [fetchWithCache]);

    // Получение категорий для выбранной игры
    const getCategoriesByGame = useCallback(async (gameId: number): Promise<Category[]> => {
      setIsLoading(true);
      setError(null);

      try {
        // Добавляем параметр includeSubcategories=true, чтобы получить иерархическую структуру категорий
        const data = await fetchWithCache(`${API_URL}/categories?game_id=${gameId}&includeSubcategories=true`);
        
        let categories = data.data || [];
        
        // Проверяем, есть ли в категориях поле subcategories. Если нет, то преобразуем плоский список в иерархию
          if (categories.length > 0 && categories.every((cat: Category) => !cat.subcategories)) {
          console.log('Сервер вернул плоский список категорий, преобразуем в иерархию...');
          
          // Создаем словарь всех категорий по ID для быстрого доступа
          const categoriesMap = categories.reduce((map: Record<string, Category & { subcategories: Category[] }>, cat: Category) => {
            map[cat.id] = { ...cat, subcategories: [] };
            return map;
          }, {} as Record<string, Category & { subcategories: Category[] }>);
          
          // Создаем иерархическую структуру
          const rootCategories = [];
          
          for (const id in categoriesMap) {
            const category = categoriesMap[id];
            
            if (category.parent_id) {
              // Это подкатегория - добавляем ее к родительской категории
              if (categoriesMap[category.parent_id]) {
                if (!categoriesMap[category.parent_id].subcategories) {
                  categoriesMap[category.parent_id].subcategories = [];
                }
                categoriesMap[category.parent_id].subcategories.push(category);
              } else {
                console.warn(`Родительская категория с ID ${category.parent_id} не найдена для категории ${category.name}`);
                rootCategories.push(category);
              }
            } else {
              // Это корневая категория
              rootCategories.push(category);
            }
          }
          
          console.log(`Построена иерархия: ${rootCategories.length} корневых категорий`);
          categories = rootCategories;
        }
        
        return categories;
      } catch (err) {
        if (err instanceof Error && err.name !== 'AbortError') {
          setError(err.message || 'Произошла ошибка при загрузке категорий');
        }
        return [];
      } finally {
        setIsLoading(false);
      }
    }, [fetchWithCache]);

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
  }, [fetchWithCache]);

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
  }, [fetchWithCache]);

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
  }, [fetchWithCache]);

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
  }, [fetchWithCache]);

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
  }, [fetchWithCache]);

    // Создание нового объявления
    const createListing = useCallback(async (data: ListingFormData | FormData): Promise<Listing | null> => {
      if (!isAuthenticated) {
        setError('Необходимо авторизоваться для создания объявления');
        return null;
      }

      setIsLoading(true);
      setError(null);

      try {
        const headers: Record<string, string> = {};
        const authHeader = getAuthHeader();
        if (authHeader) {
          headers['Authorization'] = authHeader;
        }

        // Проверяем тип данных и при необходимости конвертируем
        let requestBody: any;

        if (data instanceof FormData) {
          requestBody = data;
          // НЕ устанавливаем Content-Type для FormData - браузер сам добавит с правильным boundary
          console.log('Отправка FormData с автоматически добавляемым браузером Content-Type');
          
          // Удаляем Content-Type из заголовков, если он там есть
          delete headers['Content-Type'];
        } else {
          requestBody = JSON.stringify(data);
          headers['Content-Type'] = 'application/json';
          console.log('Отправка JSON с Content-Type: application/json');
        }

        console.log('Заголовки запроса:', headers);
        console.log('Тип тела запроса:', data instanceof FormData ? 'FormData' : 'JSON');

        // Используем fetch напрямую для всех типов данных
        const response = await fetch(`${API_URL}/listings`, {
          method: 'POST',
          headers: headers,
          body: requestBody,
          credentials: 'include' // Добавляем куки (на случай, если авторизация идет через них)
        });

        if (!response.ok) {
          const errorText = await response.text();
          console.error('Ошибка создания объявления:', {
            status: response.status,
            statusText: response.statusText,
            body: errorText
          });
          throw new Error(errorText || `HTTP error! status: ${response.status}`);
        }

        const responseData = await response.json();
        return responseData.data;
      } catch (err) {
        // Подробный лог ошибки
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
    }, [isAuthenticated, getAuthHeader, API_URL]);

    // Обновление объявления
    const updateListing = useCallback(async (listingId: number, formData: Partial<ListingFormData> | FormData): Promise<Listing | null> => {
      if (!isAuthenticated) {
        setError('Необходимо авторизоваться для обновления объявления');
        return null;
      }

      setIsLoading(true);
      setError(null);

      try {
        const headers: Record<string, string> = {};
        
        const authHeader = getAuthHeader();
        if (authHeader) {
          headers['Authorization'] = authHeader;
        }

        let requestBody: any;
        
        // Проверяем, является ли formData экземпляром FormData
        if (formData instanceof FormData) { 
          requestBody = formData;
          // НЕ устанавливаем Content-Type для FormData, браузер сам добавит с правильным boundary
          console.log('Отправка FormData с автоматически добавляемым браузером Content-Type');
          
          // Удаляем Content-Type из заголовков, если он там есть
          delete headers['Content-Type'];
        } else {
          headers['Content-Type'] = 'application/json';
          requestBody = JSON.stringify(formData);
          console.log('Отправка JSON с Content-Type: application/json');
        }

        // Используем fetch напрямую для всех типов данных
        const response = await fetch(`${API_URL}/listings/${listingId}`, {
          method: 'PUT',
          headers: headers,
          body: requestBody,
          credentials: 'include' // Добавляем куки (если авторизация идет через них)
        });

        if (!response.ok) {
          const errorText = await response.text();
          console.error('Ошибка обновления объявления:', {
            status: response.status,
            statusText: response.statusText,
            body: errorText
          });
          throw new Error(errorText || `HTTP error! status: ${response.status}`);
        }

        const responseData = await response.json();
        return responseData;
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
    }, [fetchWithCache, isAuthenticated, getAuthHeader, API_URL]);

    // Удаление объявления
    const deleteListing = useCallback(async (listingId: number): Promise<boolean> => {
      if (!isAuthenticated) {
        setError('Необходимо авторизоваться для удаления объявления');
        return false;
      }

      setIsLoading(true);
      setError(null);

      try {
        const headers: Record<string, string> = {};

        const authHeader = getAuthHeader();
        if (authHeader) {
          headers['Authorization'] = authHeader;
        }

        const response = await fetch(`${API_URL}/listings/${listingId}`, {
          method: 'DELETE',
          headers,
          credentials: 'include' // Добавляем куки (если авторизация идет через них)
        });

        if (!response.ok) {
          console.error('Ошибка удаления объявления:', {
            status: response.status,
            statusText: response.statusText
          });
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        return true;
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Произошла ошибка при удалении объявления');
        return false;
      } finally {
        setIsLoading(false);
      }
    }, [isAuthenticated, getAuthHeader, API_URL]);

    // Получение объявлений текущего пользователя
    const getUserListings = useCallback(async (
      status?: string,
      page: number = 1,
      pageSize: number = 10,
      sortBy: string = 'created_at',
      sortOrder: string = 'desc'
    ): Promise<{ items: Listing[], meta: PaginationMeta }> => {
      setIsLoading(true);
      setError(null);

      try {
        const url = new URL(`${API_URL}/listings/my-listings`);
        if (status) url.searchParams.append('status', status);
        url.searchParams.append('page', page.toString());
        url.searchParams.append('limit', pageSize.toString());
        url.searchParams.append('sort_by', sortBy);
        url.searchParams.append('sort_order', sortOrder);

        const headers: Record<string, string> = {};
        
        const authHeader = getAuthHeader();
        if (authHeader) {
          headers['Authorization'] = authHeader;
        }

        console.log('Запрос на получение объявлений пользователя:', {
          url: url.toString(),
          headers
        });

        const response = await fetch(url.toString(), {
          headers,
          credentials: 'include' // Добавляем куки (если авторизация идет через них)
        });

        if (!response.ok) {
          console.error('Ошибка получения объявлений пользователя:', {
            status: response.status,
            statusText: response.statusText
          });
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        console.log('Получены объявления пользователя:', data);
        
        return {
          items: data.data || [],
          meta: {
            current_page: data.meta?.page || 1,
            total_pages: data.meta?.pages || 1,
            total_items: data.meta?.total || 0,
            items_per_page: data.meta?.limit || pageSize
          }
        };
      } catch (err) {
        if (err instanceof Error && err.name !== 'AbortError') {
          console.error('Ошибка при получении объявлений пользователя:', err);
          setError(err.message || 'Произошла ошибка при получении объявлений пользователя');
        }
        return {
          items: [],
          meta: {
            current_page: 1,
            total_pages: 1,
            total_items: 0,
            items_per_page: pageSize
          }
        };
      } finally {
        setIsLoading(false);
      }
    }, [API_URL, getAuthHeader]);

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
      getUserListings,
    };
  };

  const buildCategoryMap = (categories: Category[]): Map<number, string> => {
    const map = new Map();
    
    const processCategories = (cat: Category) => {
      map.set(cat.id, cat.name);
      if (cat.subcategories && cat.subcategories.length > 0) {
        cat.subcategories.forEach((child: Category) => processCategories(child));
      }
    };
    
    categories.forEach((cat: Category) => processCategories(cat));
    return map;
  };
