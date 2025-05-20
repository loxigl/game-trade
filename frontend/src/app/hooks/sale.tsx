import { useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { salesApi } from '../utils/api';
import { SaleStatus, Sale } from '../types/sale';
import { processEscrowPayment, disputeTransaction } from '../api/transaction';
import { Transaction } from '../types/transaction';
import { paymentApi } from '../utils/api';

export function useSales() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const initiateSale = useCallback(async (listingId: number) => {
    setLoading(true);
    setError(null);
    try {
      const response = await salesApi.initiateSale(listingId);
      return response;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Произошла ошибка при создании продажи';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const getSale = useCallback(async (saleId: number) => {
    setLoading(true);
    setError(null);
    try {
      const response = await salesApi.getSale(saleId);
      return response;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Произошла ошибка при получении информации о продаже';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const getUserSales = useCallback(async (
    role: string = "buyer", 
    status?: string, 
    page: number = 1, 
    pageSize: number = 20
  ) => {
    setLoading(true);
    setError(null);
    try {
      const response = await salesApi.getUserSales(role, status, page, pageSize);
      return response;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Произошла ошибка при получении списка продаж';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const updateSaleStatus = useCallback(async (saleId: number, status: SaleStatus) => {
    setLoading(true);
    setError(null);
    try {
      const response = await salesApi.updateSaleStatus(saleId, status);
      return response;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Произошла ошибка при обновлении статуса продажи';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const processPayment = useCallback(async (saleId: number, walletId: number): Promise<Transaction> => {
    setLoading(true);
    setError(null);
    try {
      // Шаг 1: Сначала инициируем платеж, создавая транзакцию
      const idempotencyKey = `payment-${saleId}-${Date.now()}`;
      const paymentResult = await paymentApi.initiatePayment(saleId, walletId, idempotencyKey);
      
      // Получаем ID транзакции из ответа
      const transactionId = paymentResult?.data?.transaction?.id;
      
      if (!transactionId) {
        throw new Error('Не удалось получить ID транзакции после инициализации платежа');
      }
      
      // Шаг 2: Обновляем статус заказа на PAYMENT_PROCESSING перед переводом денег
      try {
        console.log('Обновление статуса заказа на PAYMENT_PROCESSING перед переводом в эскроу');
        await salesApi.updateSaleStatus(saleId, SaleStatus.PAYMENT_PROCESSING);
      } catch (statusErr) {
        console.error('Ошибка при обновлении статуса на PAYMENT_PROCESSING:', statusErr);
        // Продолжаем процесс даже если обновление статуса не удалось
      }
      
      // Шаг 3: Теперь выполняем перевод средств в escrow, используя ID транзакции
      const response = await processEscrowPayment(transactionId, { wallet_id: walletId });
      
      // Шаг 4: После успешного перевода средств в эскроу, обновляем статус продажи на DELIVERY_PENDING
      if (response && response.id) {
        try {
          console.log('Обновление статуса заказа на DELIVERY_PENDING после перевода в эскроу');
          await salesApi.updateSaleStatus(saleId, SaleStatus.DELIVERY_PENDING);
        } catch (statusErr) {
          console.error('Ошибка при обновлении статуса на DELIVERY_PENDING:', statusErr);
        }
      }
      
      return response;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Произошла ошибка при обработке оплаты';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const openDispute = useCallback(async (saleId: number, reason: string): Promise<Transaction> => {
    setLoading(true);
    setError(null);
    try {
      const response = await disputeTransaction(saleId, reason);
      return response;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Произошла ошибка при открытии спора';
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    loading,
    error,
    initiateSale,
    getSale,
    getUserSales,
    updateSaleStatus,
    processPayment,
    openDispute
  };
} 