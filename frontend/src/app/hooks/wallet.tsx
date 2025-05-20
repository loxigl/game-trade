// Хуки для работы с кошельками
'use client';

import { useState, useEffect, useCallback } from 'react';
import { walletsApi, adminWalletsApi } from '../utils/api';
import { 
  WalletType, 
  WalletCreateRequest, 
  WalletUpdateRequest,
  CurrencyConversionRequest,
  DepositRequest,
  WithdrawalRequest,
  WithdrawalVerificationRequest,
  Currency,
  WalletListResponse
} from '../types/wallet';
import { useAuth } from '../hooks/auth';

// Хук для получения всех кошельков пользователя
export function useWallets() {
  const [wallets, setWallets] = useState<WalletType[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [authError, setAuthError] = useState<boolean>(false);
  const { isAuthenticated } = useAuth();
  const [pagination, setPagination] = useState<{
    total: number;
    page: number;
    size: number;
    pages: number;
  }>({
    total: 0,
    page: 1,
    size: 10,
    pages: 0
  });

  // Мемоизируем функцию fetchWallets
  const fetchWallets = useCallback(async () => {
    // Проверяем, есть ли доступный токен, прежде чем делать запрос
    const token = localStorage.getItem('accessToken') || localStorage.getItem('token');
    
    if (!token || !isAuthenticated) {
      console.log('Skipping wallet fetch - no authentication token available');
      setLoading(false);
      setAuthError(true);
      setWallets([]);
      return;
    }
    
    // Сбрасываем флаг ошибки аутентификации
    setAuthError(false);
    
    try {
      setLoading(true);
      setError(null);
      const response = await walletsApi.getWallets();
      console.log('API Response:', response);
      
      if (!response || !Array.isArray(response.items)) {
        console.error('Invalid response format:', response);
        throw new Error('Неверный формат ответа от сервера');
      }
      
      // Используем функциональное обновление состояния
      setWallets(() => response.items);
      setPagination(() => ({
        total: response.total,
        page: response.page,
        size: response.size,
        pages: response.pages
      }));
    } catch (err: any) {
      console.error('Error fetching wallets:', err);
      
      // Проверяем, является ли ошибка ошибкой аутентификации (401)
      if (err?.response?.status === 401 || 
          err?.message?.includes('401') || 
          err?.message?.includes('unauthorized') || 
          err?.message?.includes('Unauthorized')) {
        setAuthError(true);
        setWallets([]); // Очищаем данные при ошибке аутентификации
      }
      
      setError(() => err instanceof Error ? err.message : 'Произошла ошибка при загрузке кошельков');
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated]);

  // Используем useEffect только для начальной загрузки и при изменении статуса аутентификации
  useEffect(() => {
    // Загружаем кошельки только если пользователь аутентифицирован
    if (isAuthenticated) {
      fetchWallets();
    } else {
      // Очищаем данные, если пользователь не аутентифицирован
      setWallets([]);
      setLoading(false);
      setAuthError(true);
    }
  }, [fetchWallets, isAuthenticated]);

  return { 
    wallets, 
    loading, 
    error,
    authError, 
    refetch: fetchWallets,
    pagination 
  };
}

// Хук для работы с отдельным кошельком
export function useWallet(walletId: number | null) {
  const [wallet, setWallet] = useState<WalletType | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchWallet = useCallback(async () => {
    if (!walletId) return;
    
    setLoading(true);
    setError(null);
    try {
      const data = await walletsApi.getWallet(walletId);
      setWallet(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Произошла ошибка при загрузке кошелька');
    } finally {
      setLoading(false);
    }
  }, [walletId]);

  useEffect(() => {
    if (walletId) {
      fetchWallet();
    }
  }, [walletId, fetchWallet]);

  // Функция создания кошелька
  const createWallet = async (data: WalletCreateRequest) => {
    setLoading(true);
    setError(null);
    try {
      const newWallet = await walletsApi.createWallet(data);
      setWallet(newWallet);
      return newWallet;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Произошла ошибка при создании кошелька');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // Функция обновления кошелька
  const updateWallet = async (id: number, data: WalletUpdateRequest) => {
    setLoading(true);
    setError(null);
    try {
      const updatedWallet = await walletsApi.updateWallet(id, data);
      setWallet(updatedWallet);
      return updatedWallet;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Произошла ошибка при обновлении кошелька');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // Функция получения баланса
  const getBalance = async (id: number) => {
    setLoading(true);
    setError(null);
    try {
      return await walletsApi.getWalletBalance(id);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Произошла ошибка при получении баланса');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { 
    wallet, 
    loading, 
    error, 
    fetchWallet, 
    createWallet, 
    updateWallet,
    getBalance
  };
}

// Хук для работы с обменом валют
export function useCurrencyExchange() {
  const [rates, setRates] = useState<Record<Currency, number>>({} as Record<Currency, number>);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchRates = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await walletsApi.getExchangeRates();
      setRates(data.rates);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Произошла ошибка при загрузке курсов валют');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchRates();
  }, [fetchRates]);

  // Функция конвертации валюты
  const convertCurrency = async (data: CurrencyConversionRequest) => {
    setLoading(true);
    setError(null);
    try {
      return await walletsApi.convertCurrency(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Произошла ошибка при конвертации валюты');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { rates, loading, error, fetchRates, convertCurrency };
}

// Хук для депозитов и снятия средств
export function useWalletTransactions() {
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Мемоизируем функцию getTransactions
  const getTransactions = useCallback(async (walletId: number) => {
    setLoading(true);
    setError(null);
    try {
      return await walletsApi.getWalletTransactions(walletId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Произошла ошибка при загрузке транзакций');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []); // Пустой массив зависимостей, так как функция не зависит от внешних переменных

  // Мемоизируем остальные функции
  const deposit = useCallback(async (data: DepositRequest) => {
    setLoading(true);
    setError(null);
    try {
      return await walletsApi.depositToWallet(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Произошла ошибка при пополнении кошелька');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  // Эмуляция успешного платежа (для тестирования)
  const simulateSuccessfulDeposit = useCallback(async (walletId: number, transactionId: number) => {
    setLoading(true);
    setError(null);
    try {
      return await walletsApi.simulateSuccessfulDeposit(walletId, transactionId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Произошла ошибка при эмуляции платежа');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const withdraw = useCallback(async (data: WithdrawalRequest) => {
    setLoading(true);
    setError(null);
    try {
      return await walletsApi.withdrawFromWallet(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Произошла ошибка при выводе средств');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const verifyWithdrawal = useCallback(async (data: WithdrawalVerificationRequest) => {
    setLoading(true);
    setError(null);
    try {
      return await walletsApi.verifyWithdrawal(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Произошла ошибка при верификации вывода средств');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return { 
    loading, 
    error, 
    deposit, 
    withdraw, 
    verifyWithdrawal, 
    getTransactions,
    simulateSuccessfulDeposit
  };
}

// Хук для администраторов
export function useAdminWallets() {
  const [wallets, setWallets] = useState<WalletType[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAllWallets = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await adminWalletsApi.getAllWallets();
      setWallets(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Произошла ошибка при загрузке кошельков');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAllWallets();
  }, [fetchAllWallets]);

  // Функция обновления статуса кошелька
  const updateWalletStatus = async (walletId: number, status: string) => {
    setLoading(true);
    setError(null);
    try {
      const updatedWallet = await adminWalletsApi.updateWalletStatus(walletId, status);
      setWallets(prev => prev.map(wallet => 
        wallet.id === walletId ? updatedWallet : wallet
      ));
      return updatedWallet;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Произошла ошибка при обновлении статуса кошелька');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // Функция получения всех транзакций
  const getAllTransactions = async (page: number = 1, limit: number = 20) => {
    setLoading(true);
    setError(null);
    try {
      return await adminWalletsApi.getAllTransactions(page, limit);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Произошла ошибка при загрузке транзакций');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // Функция обновления статуса транзакции
  const updateTransactionStatus = async (transactionId: number, status: string) => {
    setLoading(true);
    setError(null);
    try {
      return await adminWalletsApi.updateTransactionStatus(transactionId, status);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Произошла ошибка при обновлении статуса транзакции');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  // Функция получения статистики
  const getStatistics = async () => {
    setLoading(true);
    setError(null);
    try {
      return await adminWalletsApi.getWalletStatistics();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Произошла ошибка при загрузке статистики');
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { 
    wallets, 
    loading, 
    error, 
    fetchAllWallets, 
    updateWalletStatus,
    getAllTransactions,
    updateTransactionStatus,
    getStatistics
  };
} 