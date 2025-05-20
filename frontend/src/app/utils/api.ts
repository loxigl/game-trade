// Утилиты для работы с API
import { 
  WalletType, 
  WalletCreateRequest, 
  WalletUpdateRequest, 
  WalletBalanceResponse,
  CurrencyConversionRequest,
  CurrencyConversionResponse,
  ExchangeRatesResponse,
  DepositRequest,
  DepositResponse,
  WithdrawalRequest,
  WithdrawalResponse,
  WithdrawalVerificationRequest,
  WalletListResponse,
  WalletTransactionType
} from '../types/wallet';
import { Sale, SaleListResponse, SaleStatus, SaleStatusUpdate } from '../types/sale';
import { MARKETPLACE_API_URL, PAYMENTS_API_URL } from '../api/client';
import apiClient from '../api/client';

const API_BASE_URL = process.env.NEXT_PUBLIC_PAYMENT_URL || 'http://localhost:8000';

// Определяем типы для HTTP методов
type HttpMethod = 'GET' | 'POST' | 'PUT' | 'DELETE';

// Обновляем сигнатуру fetchApi
async function fetchApi<T = any>(
    method: HttpMethod,
    endpoint: string,
    data?: any,
    requireAuth: boolean = false,
    additionalHeaders: Record<string, string> = {}
): Promise<T> {
    const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        ...additionalHeaders
    };

    if (requireAuth) {
        const token = localStorage.getItem('accessToken');
        if (!token) {
            throw new Error('Требуется авторизация');
        }
        headers['Authorization'] = `Bearer ${token}`;
    }

    // Проверяем, является ли endpoint полным URL
    const url = endpoint.startsWith('http') ? endpoint : API_BASE_URL + endpoint;

    const response = await fetch(url, {
        method,
        headers,
        body: data ? JSON.stringify(data) : undefined
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ message: 'Неизвестная ошибка' }));
        throw new Error(error.message || `HTTP error! status: ${response.status}`);
    }

    return response.json();
}

// API кошельков
export const walletsApi = {
  // Получить все кошельки пользователя
  getWallets: async () => {
    try {
      const response = await apiClient.get<WalletListResponse>(`${PAYMENTS_API_URL}/wallets`);
      return response.data;
    } catch (error) {
      console.error('Error fetching wallets:', error);
      throw error;
    }
  },
  
  // Получить конкретный кошелек
  getWallet: async (id: number) => {
    try {
      const response = await apiClient.get<WalletType>(`${PAYMENTS_API_URL}/wallets/${id}`);
      return response.data;
    } catch (error) {
      console.error(`Error fetching wallet ${id}:`, error);
      throw error;
    }
  },
  
  // Создать новый кошелек
  createWallet: async (data: WalletCreateRequest) => {
    try {
      const response = await apiClient.post<WalletType>(`${PAYMENTS_API_URL}/wallets`, data);
      return response.data;
    } catch (error) {
      console.error('Error creating wallet:', error);
      throw error;
    }
  },
  
  // Обновить кошелек
  updateWallet: async (id: number, data: WalletUpdateRequest) => {
    try {
      const response = await apiClient.patch<WalletType>(`${PAYMENTS_API_URL}/wallets/${id}`, data);
      return response.data;
    } catch (error) {
      console.error(`Error updating wallet ${id}:`, error);
      throw error;
    }
  },
  
  // Получить баланс кошелька
  getWalletBalance: async (id: number) => {
    try {
      const response = await apiClient.get<WalletBalanceResponse>(`${PAYMENTS_API_URL}/wallets/${id}/balance`);
      return response.data;
    } catch (error) {
      console.error(`Error fetching wallet ${id} balance:`, error);
      throw error;
    }
  },
  
  // Пополнить кошелек
  depositToWallet: async (data: DepositRequest) => {
    try {
      const response = await apiClient.post<DepositResponse>(
        `${PAYMENTS_API_URL}/wallets/${data.wallet_id}/deposit`, 
        {
          amount: data.amount,
          currency: data.currency,
          payment_method: data.payment_method
        }
      );
      return response.data;
    } catch (error) {
      console.error('Error depositing to wallet:', error);
      throw error;
    }
  },
  
  // Вывод средств
  withdrawFromWallet: async (data: WithdrawalRequest) => {
    try {
      const response = await apiClient.post<WithdrawalResponse>(
        `${PAYMENTS_API_URL}/wallets/${data.wallet_id}/withdraw`, 
        {
          amount: data.amount,
          currency: data.currency,
          withdrawal_method: data.withdrawal_method,
          account_details: data.account_details
        }
      );
      return response.data;
    } catch (error) {
      console.error('Error withdrawing from wallet:', error);
      throw error;
    }
  },
  
  // Верификация вывода средств
  verifyWithdrawal: async (data: WithdrawalVerificationRequest) => {
    try {
      const response = await apiClient.post<WithdrawalResponse>(
        `${PAYMENTS_API_URL}/withdrawals/${data.withdrawal_id}/verify`, 
        {
          verification_code: data.verification_code
        }
      );
      return response.data;
    } catch (error) {
      console.error('Error verifying withdrawal:', error);
      throw error;
    }
  },
  
  // Получить историю транзакций кошелька
  getWalletTransactions: async (id: number) => {
    try {
      const response = await apiClient.get<{ items: WalletTransactionType[], total: number, page: number, size: number, pages: number }>(
        `${PAYMENTS_API_URL}/wallets/${id}/transactions`
      );
      return response.data;
    } catch (error) {
      console.error(`Error fetching wallet ${id} transactions:`, error);
      throw error;
    }
  },
  
  // Конвертация валюты
  convertCurrency: async (data: CurrencyConversionRequest) => {
    try {
      const response = await apiClient.post<CurrencyConversionResponse>(
        `${PAYMENTS_API_URL}/wallets/${data.wallet_id}/convert`, 
        {
          from_currency: data.from_currency,
          to_currency: data.to_currency,
          amount: data.amount
        }
      );
      return response.data;
    } catch (error) {
      console.error('Error converting currency:', error);
      throw error;
    }
  },
  
  // Получить текущие курсы обмена валют
  getExchangeRates: async () => {
    try {
      const response = await apiClient.get<ExchangeRatesResponse>(`${PAYMENTS_API_URL}/currency/rates`);
      return response.data;
    } catch (error) {
      console.error('Error fetching exchange rates:', error);
      // В случае ошибки возвращаем мок для непрерывной работы интерфейса
      return {
        base_currency: 'USD' as any,
        rates: {
          USD: 1,
          EUR: 0.93,
          GBP: 0.79,
          RUB: 92.5,
          JPY: 110.2,
          CNY: 7.2
        },
        timestamp: new Date().toISOString()
      };
    }
  },

  // Эмуляция успешного платежа (для тестирования)
  simulateSuccessfulDeposit: async (walletId: number, transactionId: number) => {
    try {
      const response = await apiClient.post<any>(
        `${PAYMENTS_API_URL}/wallets/${walletId}/deposit/${transactionId}/simulate-success`
      );
      return response.data;
    } catch (error) {
      console.error('Error simulating successful deposit:', error);
      throw error;
    }
  },
};

// API управления транзакциями для администраторов
export const adminWalletsApi = {
  // Получить все кошельки в системе (доступно только администраторам)
  getAllWallets: () => 
    fetchApi<WalletType[]>('GET', `${PAYMENTS_API_URL}/admin/wallets`, undefined, true),
  
  // Изменить статус кошелька (блокировка/разблокировка)
  updateWalletStatus: (id: number, status: string) => 
    fetchApi<WalletType>('PUT', `${PAYMENTS_API_URL}/admin/wallets/${id}/status`, { status }, true),
  
  // Получить все транзакции в системе
  getAllTransactions: (page: number = 1, limit: number = 20) => 
    fetchApi<any>('GET', `${PAYMENTS_API_URL}/admin/transactions?page=${page}&limit=${limit}`, undefined, true),
  
  // Изменить статус транзакции (например, отменить или подтвердить)
  updateTransactionStatus: (id: number, status: string) => 
    fetchApi<any>('PUT', `${PAYMENTS_API_URL}/admin/transactions/${id}/status`, { status }, true),
  
  // Получить статистику по кошелькам и транзакциям
  getWalletStatistics: () => 
    fetchApi<any>('GET', `${PAYMENTS_API_URL}/admin/statistics/wallets`, undefined, true),
};

// Методы для работы с продажами через marketplace-svc
export const salesApi = {
    // Инициировать продажу (создание записи о продаже)
    initiateSale: async (listingId: number) => {
        return fetchApi<void>('POST', `${MARKETPLACE_API_URL}/sales/${listingId}/initiate`, undefined, true);
    },

    // Получить информацию о продаже
    getSale: async (saleId: number) => {
        return fetchApi<Sale>('GET', `${MARKETPLACE_API_URL}/sales/${saleId}`, undefined, true);
    },

    // Получить список продаж пользователя
    getUserSales: async (role: string = "buyer", status?: string, page: number = 1, pageSize: number = 20) => {
        const queryParams = new URLSearchParams();
        queryParams.append('role', role);
        if (status) queryParams.append('status', status);
        queryParams.append('page', page.toString());
        queryParams.append('page_size', pageSize.toString());
        
        console.log(`Выполняется запрос на URL: ${MARKETPLACE_API_URL}/sales/?${queryParams.toString()}`);
        
        return fetchApi<{
            items: Sale[],
            total: number,
            page: number,
            size: number,
            pages: number
        }>('GET', `${MARKETPLACE_API_URL}/sales/?${queryParams.toString()}`, undefined, true);
    },

    // Обновить статус продажи
    updateSaleStatus: async (saleId: number, status: string) => {
        return fetchApi<void>('PUT', `${MARKETPLACE_API_URL}/sales/${saleId}/status`, { status }, true);
    }
};

// Методы для работы с платежами через payment-svc
export const paymentApi = {
    // Инициировать платеж по продаже
    initiatePayment: async (saleId: number, walletId: number, idempotencyKey?: string) => {
        const headers: Record<string, string> = {};
        if (idempotencyKey) {
            headers['x-idempotency-key'] = idempotencyKey;
        }

        return fetchApi<{
            data: {
                sale: any;
                transaction: any;
            };
            meta: { message: string };
        }>('POST', `${PAYMENTS_API_URL}/sales/${saleId}/initiate-payment?wallet_id=${walletId}`, undefined, true, headers);
    },

    // Подтвердить платеж
    confirmPayment: async (saleId: number, transactionId: number, idempotencyKey?: string) => {
        const headers: Record<string, string> = {};
        if (idempotencyKey) {
            headers['x-idempotency-key'] = idempotencyKey;
        }

        return fetchApi<void>('POST', `${PAYMENTS_API_URL}/sales/${saleId}/confirm?transaction_id=${transactionId}`, undefined, true, headers);
    },

    // Отклонить платеж
    rejectPayment: async (saleId: number, transactionId: number, reason?: string, idempotencyKey?: string) => {
        const headers: Record<string, string> = {};
        if (idempotencyKey) {
            headers['x-idempotency-key'] = idempotencyKey;
        }

        return fetchApi<void>('POST', `${PAYMENTS_API_URL}/sales/${saleId}/reject?transaction_id=${transactionId}`, { reason }, true, headers);
    },

    // Получить информацию о платеже
    getPayment: async (paymentId: number) => {
        return fetchApi<any>('GET', `${PAYMENTS_API_URL}/transactions/${paymentId}`, undefined, true);
    }
};

export default {
  walletsApi,
  adminWalletsApi,
  salesApi,
  paymentApi
}; 