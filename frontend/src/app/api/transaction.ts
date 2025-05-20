import apiClient from './client';
import {
  Transaction,
  TransactionCreate,
  TransactionAction,
  TransactionListResponse,
  TransactionActionResponse,
  TransactionStatus,
  TransactionHistoryItem,
  TransactionHistoryListResponse,
  TransactionType,
  SellerStatistics,
  TransactionSummary
} from '../types/transaction';
import { PAYMENTS_API_URL, API_BASE_URL } from './client';
import { AxiosRequestConfig } from 'axios';

// Добавляем функцию getAuthHeader, которая получает токен из localStorage
const getAuthHeader = () => {
  if (typeof window === 'undefined') return null;
  const token = localStorage.getItem('token') || localStorage.getItem('accessToken');
  return token ? `Bearer ${token}` : null;
};

const TRANSACTION_API_URL = `${PAYMENTS_API_URL}/transactions`;
const TRANSACTION_HISTORY_API_URL = `${PAYMENTS_API_URL}/transactions/history`;
const PAYMENT_API_URL = PAYMENTS_API_URL;

// Создание транзакции
export const createTransaction = async (data: TransactionCreate): Promise<Transaction> => {
  const response = await apiClient.post<Transaction>(TRANSACTION_API_URL, data);
  return response.data;
};

// Получение транзакции по ID
export const getTransaction = async (id: number): Promise<Transaction> => {
  const response = await apiClient.get<Transaction>(`${TRANSACTION_API_URL}/${id}`);
  return response.data;
};

// Получение списка транзакций пользователя
export const getUserTransactions = async (
  userId?: number,
  status?: TransactionStatus,
  page: number = 1,
  pageSize: number = 10,
  isSellerView: boolean = false
): Promise<TransactionListResponse> => {
  const queryParams = new URLSearchParams();
  
  if (userId) queryParams.append('user_id', userId.toString());
  if (status) queryParams.append('status', status);
  queryParams.append('page', page.toString());
  queryParams.append('page_size', pageSize.toString());
  queryParams.append('is_seller_view', isSellerView.toString());
  
  const response = await apiClient.get<TransactionListResponse>(
    `${TRANSACTION_API_URL}?${queryParams.toString()}`
  );
  
  return response.data;
};

// Получение доступных действий для транзакции
export const getTransactionActions = async (id: number): Promise<TransactionActionResponse> => {
  const response = await apiClient.get<{ data: TransactionActionResponse }>(
    `${TRANSACTION_API_URL}/${id}/actions`
  );
  return response.data.data;
};

// Выполнение перевода средств в Escrow
export const processEscrowPayment = async (
  id: number,
  data?: Record<string, any>
): Promise<Transaction> => {
  const response = await apiClient.post<Transaction>(
    `${TRANSACTION_API_URL}/${id}/escrow`,
    data,
    {
      headers: {
        'X-Idempotency-Key': `escrow-${id}-${Date.now()}`
      }
    }
  );
  return response.data;
};

// Завершение транзакции (перевод средств продавцу)
export const completeTransaction = async (
  id: number,
  data?: Record<string, any>
): Promise<Transaction> => {
  const response = await apiClient.post<Transaction>(
    `${TRANSACTION_API_URL}/${id}/complete`,
    data,
    {
      headers: {
        'X-Idempotency-Key': `complete-${id}-${Date.now()}`
      }
    }
  );
  return response.data;
};

// Возврат средств покупателю
export const refundTransaction = async (
  id: number,
  reason?: string
): Promise<Transaction> => {
  const response = await apiClient.post<Transaction>(
    `${TRANSACTION_API_URL}/${id}/refund`,
    { reason },
    {
      headers: {
        'X-Idempotency-Key': `refund-${id}-${Date.now()}`
      }
    }
  );
  return response.data;
};

// Открытие спора по транзакции
export const disputeTransaction = async (
  id: number,
  reason: string
): Promise<Transaction> => {
  const response = await apiClient.post<Transaction>(
    `${TRANSACTION_API_URL}/${id}/dispute`,
    { reason },
    {
      headers: {
        'X-Idempotency-Key': `dispute-${id}-${Date.now()}`
      }
    }
  );
  return response.data;
};

// Разрешение спора по транзакции
export const resolveDispute = async (
  id: number,
  inFavorOfSeller: boolean,
  reason?: string
): Promise<Transaction> => {
  const response = await apiClient.post<Transaction>(
    `${TRANSACTION_API_URL}/${id}/resolve`,
    { reason },
    {
      params: { in_favor_of_seller: inFavorOfSeller },
      headers: {
        'X-Idempotency-Key': `resolve-${id}-${Date.now()}`
      }
    }
  );
  return response.data;
};

// Отмена транзакции
export const cancelTransaction = async (
  id: number,
  reason?: string
): Promise<Transaction> => {
  const response = await apiClient.post<Transaction>(
    `${TRANSACTION_API_URL}/${id}/cancel`,
    { reason },
    {
      headers: {
        'X-Idempotency-Key': `cancel-${id}-${Date.now()}`
      }
    }
  );
  return response.data;
};

// Получение истории транзакций с фильтрами и пагинацией
export const getTransactionsHistory = async (
  userId?: number,
  type?: TransactionType,
  status?: TransactionStatus,
  startDate?: Date,
  endDate?: Date,
  page: number = 1,
  pageSize: number = 20
): Promise<TransactionHistoryListResponse> => {
  const queryParams = new URLSearchParams();
  
  if (userId) queryParams.append('user_id', userId.toString());
  if (type) queryParams.append('type', type);
  if (status) queryParams.append('status', status);
  if (startDate) queryParams.append('start_date', startDate.toISOString());
  if (endDate) queryParams.append('end_date', endDate.toISOString());
  queryParams.append('page', page.toString());
  queryParams.append('page_size', pageSize.toString());
  
  const response = await apiClient.get<TransactionHistoryListResponse>(
    `${TRANSACTION_HISTORY_API_URL}?${queryParams.toString()}`
  );
  
  if (!response.data || !response.data.items) {
    return { items: [], total: 0, page: 1, size: pageSize, pages: 0 };
  }
  
  return response.data;
};

// Получение истории конкретной транзакции
export const getTransactionHistory = async (transactionId: number): Promise<TransactionHistoryItem[]> => {
  const response = await apiClient.get<TransactionHistoryItem[]>(
    `${TRANSACTION_HISTORY_API_URL}/${transactionId}`
  );
  return response.data;
};

// Получение хронологического таймлайна транзакции
export const getTransactionTimeline = async (transactionId: number): Promise<TransactionHistoryItem[]> => {
  const response = await apiClient.get<TransactionHistoryItem[]>(
    `${TRANSACTION_HISTORY_API_URL}/${transactionId}/timeline`
  );
  return response.data;
};

// Экспорт истории транзакции в CSV или JSON
export const exportTransactionHistory = async (
  transactionId: number,
  format: 'csv' | 'json' = 'csv'
): Promise<Blob> => {
  const response = await apiClient.get(
    `${TRANSACTION_HISTORY_API_URL}/${transactionId}/export?format=${format}`,
    { responseType: 'blob' }
  );
  return response.data;
};

// Генерация отчета по транзакциям
export const generateTransactionsReport = async (
  userId?: number,
  status?: TransactionStatus,
  startDate?: Date,
  endDate?: Date,
  format: 'csv' | 'json' | 'excel' = 'csv'
): Promise<Blob> => {
  const queryParams = new URLSearchParams();
  
  if (userId) queryParams.append('user_id', userId.toString());
  if (status) queryParams.append('status', status);
  if (startDate) queryParams.append('start_date', startDate.toISOString());
  if (endDate) queryParams.append('end_date', endDate.toISOString());
  queryParams.append('format', format);
  
  const response = await apiClient.get(
    `${TRANSACTION_HISTORY_API_URL}/report?${queryParams.toString()}`,
    { responseType: 'blob' }
  );
  
  return response.data;
};

// Получение статистики продаж для продавца
export const getSellerStatistics = async (
  sellerId?: number,
  period: 'week' | 'month' | 'quarter' | 'year' | 'all' = 'month',
  startDate?: Date,
  endDate?: Date
): Promise<SellerStatistics> => {
  const queryParams = new URLSearchParams();
  
  if (sellerId) queryParams.append('seller_id', sellerId.toString());
  queryParams.append('period', period);
  if (startDate) queryParams.append('start_date', startDate.toISOString());
  if (endDate) queryParams.append('end_date', endDate.toISOString());
  
  const response = await apiClient.get<{ data: SellerStatistics }>(
    `/payments/statistics/seller?${queryParams.toString()}`
  );
  
  return response.data.data;
};

// Получение сводки по транзакциям
export const getTransactionsSummary = async (
  sellerId?: number,
  groupBy: 'game' | 'month' | 'status' | 'type' = 'month',
  period: 'week' | 'month' | 'quarter' | 'year' | 'all' = 'month',
  startDate?: Date,
  endDate?: Date
): Promise<TransactionSummary[]> => {
  const queryParams = new URLSearchParams();
  
  if (sellerId) queryParams.append('seller_id', sellerId.toString());
  queryParams.append('group_by', groupBy);
  queryParams.append('period', period);
  if (startDate) queryParams.append('start_date', startDate.toISOString());
  if (endDate) queryParams.append('end_date', endDate.toISOString());
  
  const response = await apiClient.get<{ data: TransactionSummary[] }>(
    `/payments/statistics/transactions/summary?${queryParams.toString()}`
  );
  
  return response.data.data;
};

// Получение деталей транзакции по ID
export const getTransactionById = async (transactionId: number): Promise<Transaction> => {
  try {
    const response = await apiClient.get(`${TRANSACTION_API_URL}/${transactionId}`);
    return response.data;
  } catch (error) {
    console.error('Ошибка при получении данных о транзакции:', error);
    throw error;
  }
};

// Подтверждение получения товара покупателем
export const confirmDelivery = async (transactionId: number): Promise<void> => {
  try {
    const response = await apiClient.post(`${API_BASE_URL}/transactions/${transactionId}/confirm`);
    return response.data;
  } catch (error) {
    console.error('Ошибка при подтверждении получения:', error);
    throw error;
  }
};

// Подтверждение доставки продавцом
export const confirmSellerDelivery = async (transactionId: number): Promise<void> => {
  try {
    const response = await apiClient.post(`${API_BASE_URL}/transactions/${transactionId}/seller-confirm`);
    return response.data;
  } catch (error) {
    console.error('Ошибка при подтверждении доставки продавцом:', error);
    throw error;
  }
};

// Инициирование спора
export const initiateDispute = async (transactionId: number, reason: string): Promise<void> => {
  try {
    const response = await apiClient.post(`${API_BASE_URL}/transactions/${transactionId}/dispute`, { reason });
    return response.data;
  } catch (error) {
    console.error('Ошибка при инициировании спора:', error);
    throw error;
  }
};

// Оплата транзакции (для первоначального эскроу)
export const payTransaction = async (id: number, paymentMethod: string): Promise<void> => {
  await apiClient.post(`${PAYMENTS_API_URL}/sales/${id}/pay`, { paymentMethod });
};

// Получение детальной информации о транзакции
export const getTransactionDetails = async (transactionId: number): Promise<any> => {
  try {
    const response = await apiClient.get(`${TRANSACTION_API_URL}/${transactionId}/details`);
    console.log('Transaction details response:', response.data);
    return response.data;
  } catch (error) {
    console.error('Ошибка при получении детальной информации о транзакции:', error);
    throw error;
  }
}; 