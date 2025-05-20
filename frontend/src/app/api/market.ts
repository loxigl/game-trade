import apiClient from './client';
import { MARKETPLACE_API_URL, PAYMENTS_API_URL } from './client';
import { AxiosResponse } from 'axios';
import axios from 'axios';

export interface Listing {
  id: number;
  title: string;
  description: string;
  price: number;
  currency: string;
  status: 'active' | 'sold' | 'pending' | 'rejected' | 'paused' | 'completed';
  viewsCount: number;
  createdAt: string;
  updatedAt: string;
  images: Array<{
    id: number;
    url: string;
    isMain: boolean;
  }>;
  game?: {
    id: number;
    name: string;
    image?: string;
  };
  category?: {
    id: number;
    name: string;
  };
}
export interface Game {
  id: number;
  name: string;
  image?: string;
}

interface ApiResponse<T> {
  success: boolean;
  data: T;
  meta?: {
    total: number;
    page: number;
    limit: number;
    pages: number;
  };
}
export interface ListingsResponse {
  items: Listing[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface PendingSale {
  id: number;
  listingId: number;
  listingTitle: string;
  buyerId: number;
  buyerName: string;
  price: number;
  currency: string;
  status: 'pending' | 'payment_processing' | 'delivery_pending' | 'completed' | 'canceled' | 'disputed';
  createdAt: string;
  expiresAt?: string;
  gameInfo?: {
    id: number;
    name: string;
    image?: string;
  };
}

export interface PendingSalesResponse {
  items: PendingSale[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

// Получение активных объявлений продавца
export const getSellerListings = async (
  sellerId?: number,
  status: string = 'active',
  page: number = 1,
  pageSize: number = 10
): Promise<ListingsResponse> => {
  const queryParams = new URLSearchParams();
  
  if (sellerId) {
    queryParams.append('seller_id', sellerId.toString());
  }
  queryParams.append('status', status);
  queryParams.append('page', page.toString());
  queryParams.append('page_size', pageSize.toString());
  
  // Для завершенных продаж используем платежный сервис
  if (status === 'completed') {
    const response = await apiClient.get<{ data: PendingSalesResponse }>(
      `${PAYMENTS_API_URL}/sales/completed?${queryParams.toString()}`
    );
    
    // Преобразуем формат ответа от платежного сервиса к формату ListingsResponse
    const data = response.data.data;
    return {
      items: data.items.map(sale => ({
        id: sale.id,
        title: sale.listingTitle,
        description: '',
        price: sale.price,
        currency: sale.currency,
        status: 'completed',
        viewsCount: 0,
        createdAt: sale.createdAt,
        updatedAt: sale.createdAt,
        images: [],
        game: sale.gameInfo
      })),
      total: data.total,
      page: data.page,
      size: data.size,
      pages: data.pages
    };
  }
  
  // Для остальных статусов используем маркетплейс
  const response = await apiClient.get<ListingsResponse>(
    `${MARKETPLACE_API_URL}/listings?${queryParams.toString()}`
  );
  
  return response.data;
};

// Получение объявлений текущего пользователя
export const getUserListings = async (
  status?: string,
  page: number = 1,
  pageSize: number = 10,
  sortBy: string = 'created_at',
  sortOrder: string = 'desc'
): Promise<ListingsResponse> => {
  const queryParams = new URLSearchParams();
  
  if (status) {
    queryParams.append('status', status);
  }
  queryParams.append('page', page.toString());
  queryParams.append('page_size', pageSize.toString());
  queryParams.append('sort_by', sortBy);
  queryParams.append('sort_order', sortOrder);
  
  // Используем специальный эндпоинт для получения объявлений текущего пользователя
  const response = await apiClient.get<{ data: any, meta: any }>(
    `${MARKETPLACE_API_URL}/listings/my-listings?${queryParams.toString()}`
  );
  
  // Если API не возвращает стандартный формат ListingsResponse, преобразуем его
  if (response.data.data && response.data.meta) {
    return {
      items: response.data.data,
      total: response.data.meta.total,
      page: response.data.meta.page,
      size: response.data.meta.limit,
      pages: response.data.meta.pages
    };
  }
  
  return response.data;
};

// Получение ожидающих подтверждения продаж
export const getPendingSales = async (
  status: string = 'pending',
  page: number = 1, 
  pageSize: number = 10
): Promise<PendingSalesResponse> => {
  const queryParams = new URLSearchParams();
  
  if (status) {
    queryParams.append('status', status);
  }
  queryParams.append('page', page.toString());
  queryParams.append('page_size', pageSize.toString());
  
  const response = await apiClient.get<{ data: PendingSalesResponse }>(
    `${PAYMENTS_API_URL}/sales/?${queryParams.toString()}`
  );
  
  return response.data.data;
};

// Получение завершенных продаж
export const getCompletedSales = async (
  sellerId?: number,
  page: number = 1, 
  pageSize: number = 10
): Promise<PendingSalesResponse> => {
  const queryParams = new URLSearchParams();
  
  queryParams.append('status', 'completed');
  if (sellerId) {
    queryParams.append('seller_id', sellerId.toString());
  }
  queryParams.append('page', page.toString());
  queryParams.append('page_size', pageSize.toString());
  
  const response = await apiClient.get<{ data: PendingSalesResponse }>(
    `${PAYMENTS_API_URL}/sales/?${queryParams.toString()}`
  );
  
  return response.data.data;
};

// Получение всех продаж пользователя с разными статусами
export const getAllSales = async (
  status?: string,
  page: number = 1,
  pageSize: number = 10,
  asSeller: boolean = true
): Promise<PendingSalesResponse> => {
  const queryParams = new URLSearchParams();
  
  if (status) {
    queryParams.append('status', status);
  }
  queryParams.append('page', page.toString());
  queryParams.append('page_size', pageSize.toString());
  queryParams.append('as_seller', asSeller.toString());
  
  const response = await apiClient.get<{ data: PendingSalesResponse }>(
    `${PAYMENTS_API_URL}/sales/?${queryParams.toString()}`
  );
  
  return response.data.data;
};

// Подтверждение продажи
export const confirmSale = async (
  saleId: number,
  data?: Record<string, any>
): Promise<PendingSale> => {
  const response = await apiClient.post<PendingSale>(
    `${MARKETPLACE_API_URL}/sales/${saleId}/confirm`,
    data,
    {
      headers: {
        'X-Idempotency-Key': `confirm-${saleId}-${Date.now()}`
      }
    }
  );
  
  return response.data;
};

// Отклонение продажи
export const rejectSale = async (
  saleId: number,
  reason?: string
): Promise<PendingSale> => {
  const response = await apiClient.post<PendingSale>(
    `${MARKETPLACE_API_URL}/sales/${saleId}/reject`,
    { reason },
    {
      headers: {
        'X-Idempotency-Key': `reject-${saleId}-${Date.now()}`
      }
    }
  );
  
  return response.data;
};

// Создание нового объявления
export const createListing = async (formData: FormData): Promise<Listing> => {
  console.log('Создание объявления, отправляемые данные:', 
    Array.from(formData.entries()).reduce((obj: any, [key, value]) => {
      obj[key] = typeof value === 'string' ? value : `<File: ${(value as File).name}>`;
      return obj;
    }, {})
  );
  
  try {
    // НЕ устанавливаем Content-Type для FormData, браузер сделает это сам
    console.log('Отправка запроса без явного установления Content-Type для FormData');
    
    const response = await apiClient.post<Listing>(
      `${MARKETPLACE_API_URL}/listings`,
      formData
      // Не указываем headers для FormData
    );
    
    console.log('Успешный ответ на создание объявления:', response.data);
    return response.data;
  } catch (error) {
    console.error('Ошибка при создании объявления:', error);
    
    // Более подробный лог ошибки
    if (axios.isAxiosError(error)) {
      console.error('Детали ошибки Axios:', {
        status: error.response?.status,
        statusText: error.response?.statusText,
        headers: error.response?.headers,
        data: error.response?.data
      });
    }
    
    throw error;
  }
};

// Обновление объявления
export const updateListing = async (
  listingId: number,
  formData: FormData
): Promise<Listing> => {
  const response = await apiClient.put<Listing>(
    `${MARKETPLACE_API_URL}/listings/${listingId}`,
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    }
  );
  
  return response.data;
};

// Удаление объявления
export const deleteListing = async (listingId: number): Promise<void> => {
  await apiClient.delete(`${MARKETPLACE_API_URL}/listings/${listingId}`);
};

// Приостановка объявления
export const pauseListing = async (listingId: number): Promise<Listing> => {
  const response = await apiClient.post<Listing>(
    `${MARKETPLACE_API_URL}/listings/${listingId}/pause`
  );
  
  return response.data;
};

// Активация объявления
export const activateListing = async (listingId: number): Promise<Listing> => {
  const response = await apiClient.post<Listing>(
    `${MARKETPLACE_API_URL}/listings/${listingId}/activate`
  );
  
  return response.data;
};

// Получение категорий для игры
export const getCategoriesByGame = async (gameId: number): Promise<Array<{ id: number; name: string; }>> => {
  const response = await apiClient.get<Array<{ id: number; name: string; }>>(
    `${MARKETPLACE_API_URL}/games/${gameId}/categories`
  );
  
  return response.data;
};

// Получение списка игр
export const getGames = async (): Promise<Game[]> => {
  const { data }: AxiosResponse<ApiResponse<Game[]>> =
    await apiClient.get(`${MARKETPLACE_API_URL}/games`);

  return data.data;             
};