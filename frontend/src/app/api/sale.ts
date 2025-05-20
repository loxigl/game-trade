import apiClient, { PAYMENTS_API_URL } from './client';

// Интерфейс для запроса на вывод средств
export interface FundsReleaseRequest {
  wallet_id: number;
  withdrawal_details?: Record<string, any>;
}

// Интерфейс для ответа на запрос вывода средств
export interface FundsReleaseResponse {
  status: string;
  message: string;
  sale_id: number;
  transaction_id: number;
  amount: number;
  currency: string;
  wallet_id: number;
  wallet_transaction_id: number;
  timestamp: string;
}

// Интерфейс для запроса на подтверждение доставки
export interface CompletionRequest {
  comment?: string;
}

// Запрос продавца на вывод средств после завершения эскроу
export const releaseFunds = async (
  saleId: number,
  transactionId: number,
  walletId: number,
  withdrawalDetails?: Record<string, any>
): Promise<FundsReleaseResponse> => {
  const response = await apiClient.post<{ data: FundsReleaseResponse }>(
    `${PAYMENTS_API_URL}/sales/${saleId}/release-funds?transaction_id=${transactionId}`,
    {
      wallet_id: walletId,
      withdrawal_details: withdrawalDetails || {}
    },
    {
      headers: {
        'X-Idempotency-Key': `release-funds-${saleId}-${transactionId}-${Date.now()}`
      }
    }
  );
  
  return response.data.data;
};

// Подтверждение завершения доставки покупателем
export const completeDelivery = async (
  saleId: number,
  transactionId: number,
  comment?: string
): Promise<any> => {
  const response = await apiClient.post<{ data: any }>(
    `${PAYMENTS_API_URL}/sales/${saleId}/complete-delivery?transaction_id=${transactionId}`,
    {
      comment
    },
    {
      headers: {
        'X-Idempotency-Key': `complete-delivery-${saleId}-${transactionId}-${Date.now()}`
      }
    }
  );
  
  return response.data.data;
};

// Получение ожидающих подтверждения продаж
export const getPendingSales = async (
  sellerId: number,
  page: number = 1,
  pageSize: number = 10
): Promise<any> => {
  const queryParams = new URLSearchParams();
  
  queryParams.append('seller_id', sellerId.toString());
  queryParams.append('page', page.toString());
  queryParams.append('size', pageSize.toString());
  
  const response = await apiClient.get<{ data: any }>(
    `${PAYMENTS_API_URL}/sales/pending?${queryParams.toString()}`
  );
  
  return response.data.data;
};

// Получение завершенных продаж
export const getCompletedSales = async (
  sellerId: number,
  page: number = 1,
  pageSize: number = 10
): Promise<any> => {
  const queryParams = new URLSearchParams();
  
  queryParams.append('seller_id', sellerId.toString());
  queryParams.append('page', page.toString());
  queryParams.append('size', pageSize.toString());
  
  const response = await apiClient.get<{ data: any }>(
    `${PAYMENTS_API_URL}/sales/completed?${queryParams.toString()}`
  );
  
  return response.data.data;
}; 