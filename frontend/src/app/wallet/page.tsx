'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { useWallets, useWallet, useCurrencyExchange, useWalletTransactions } from '../hooks/wallet';
import { Currency, WalletType, WalletStatus, TransactionStatus, WalletTransactionType } from '../types/wallet';
import formatPrice from '../utils/formatPrice';
import { formatDate } from '../utils/formatDate';
import { useAuth } from '../hooks/auth';

export default function WalletPage() {
  const router = useRouter();
  const { isAuthenticated } = useAuth();
  const { 
    wallets, 
    loading: walletsLoading, 
    error: walletsError,
    authError,
    refetch,
    pagination 
  } = useWallets();
  const [selectedWallet, setSelectedWallet] = useState<number | null>(null);
  const { wallet, loading: walletLoading, error: walletError } = useWallet(selectedWallet);
  const { rates, loading: ratesLoading } = useCurrencyExchange();
  const { getTransactions } = useWalletTransactions();
  const [transactions, setTransactions] = useState<WalletTransactionType[]>([]);
  const [transactionsLoading, setTransactionsLoading] = useState(false);
  const [transactionsError, setTransactionsError] = useState<string | null>(null);

  // Перенаправляем на страницу логина, если пользователь не авторизован
  useEffect(() => {
    if (authError && !isAuthenticated) {
      console.log('Redirecting to login due to auth error on wallet page');
      router.push('/login?redirected=true&from=/wallet');
    }
  }, [authError, isAuthenticated, router]);

  // Устанавливаем первый кошелек как выбранный только при первой загрузке
  useEffect(() => {
    if (wallets?.length > 0 && selectedWallet === null) {
      setSelectedWallet(wallets[0].id);
    }
  }, [wallets?.length, selectedWallet]);

  // Загружаем транзакции для выбранного кошелька
  const loadTransactions = async () => {
    if (!selectedWallet) return;
    
    setTransactionsLoading(true);
    setTransactionsError(null);
    
    try {
      const data = await getTransactions(selectedWallet);
      setTransactions(data?.items || []);
    } catch (error) {
      console.error('Error fetching wallet transactions:', error);
      setTransactionsError('Не удалось загрузить транзакции');
    } finally {
      setTransactionsLoading(false);
    }
  };
  
  useEffect(() => {
    if (selectedWallet) {
      loadTransactions();
    }
  }, [selectedWallet, getTransactions]);

  // Обработчик смены кошелька
  const handleWalletChange = (walletId: number) => {
    setSelectedWallet(walletId);
  };

  // Обработчик для перехода на страницу депозита
  const handleDeposit = () => {
    if (selectedWallet) {
      router.push(`/wallet/deposit?wallet_id=${selectedWallet}`);
    }
  };

  // Обработчик для перехода на страницу вывода средств
  const handleWithdraw = () => {
    if (selectedWallet) {
      router.push(`/wallet/withdraw?wallet_id=${selectedWallet}`);
    }
  };

  // Обработчик для перехода на страницу конвертации валюты
  const handleExchange = () => {
    if (selectedWallet) {
      router.push(`/wallet/exchange?wallet_id=${selectedWallet}`);
    }
  };

  // Функция получения цвета статуса транзакции
  const getStatusColor = (status: TransactionStatus) => {
    switch (status) {
      case TransactionStatus.COMPLETED:
        return 'text-green-600';
      case TransactionStatus.PENDING:
        return 'text-yellow-600';
      case TransactionStatus.FAILED:
        return 'text-red-600';
      case TransactionStatus.REFUNDED:
        return 'text-blue-600';
      case TransactionStatus.CANCELED:
        return 'text-gray-600';
      case TransactionStatus.ESCROW_HELD:
        return 'text-purple-600';
      default:
        return 'text-gray-600';
    }
  };

  if (walletsLoading || (selectedWallet && walletLoading)) {
    return (
      <div className="flex justify-center items-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (walletsError || walletError) {
    return (
      <div className="text-center p-8">
        <h1 className="text-2xl text-red-600 mb-4">Произошла ошибка</h1>
        <p className="mb-4">{walletsError || walletError}</p>
        <button 
          onClick={() => refetch()} 
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          Попробовать снова
        </button>
      </div>
    );
  }

  if (!wallets || wallets.length === 0) {
    return (
      <div className="text-center p-8">
        <h1 className="text-2xl mb-4">У вас пока нет кошельков</h1>
        <p className="text-gray-600 mb-4">Всего кошельков: {pagination.total}</p>
        <button 
          onClick={() => router.push('/wallet/create')} 
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          Создать кошелек
        </button>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-3xl font-bold mb-6">Мой кошелек</h1>
      
      {/* Кнопка создания нового кошелька */}
      <div className="mb-4 flex justify-between items-center">
        <div className="text-sm text-gray-600">
        Показано {wallets.length} из {pagination.total} кошельков
        {pagination.pages > 1 && ` (страница ${pagination.page} из ${pagination.pages})`}
        </div>
        <button 
          onClick={() => router.push('/wallet/create')}
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          + Создать новый кошелек
        </button>
      </div>

      {/* Выбор кошелька */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">Выберите кошелек</label>
        <select 
          value={selectedWallet || ''} 
          onChange={(e) => handleWalletChange(Number(e.target.value))}
          className="w-full p-2 border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500"
        >
          {wallets.map(wallet => (
            <option key={wallet.id} value={wallet.id}>
              Кошелек #{wallet.id} {wallet.is_default ? '(Основной)' : ''}
            </option>
          ))}
        </select>
      </div>

      {/* Информация о кошельке */}
      {wallet && (
        <div className="bg-white shadow-md rounded-lg p-6 mb-6">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold">Информация о кошельке #{wallet.id}</h2>
            <span className={`px-3 py-1 rounded-full text-sm ${
              wallet.status === WalletStatus.ACTIVE ? 'bg-green-100 text-green-800' :
              wallet.status === WalletStatus.BLOCKED ? 'bg-red-100 text-red-800' :
              wallet.status === WalletStatus.PENDING ? 'bg-yellow-100 text-yellow-800' :
              'bg-gray-100 text-gray-800'
            }`}>
              {wallet.status}
            </span>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            <div>
              <p className="text-gray-600 mb-1">Статус:</p>
              <p className="font-medium">{wallet.status}</p>
            </div>
            <div>
              <p className="text-gray-600 mb-1">Создан:</p>
              <p className="font-medium">{wallet.created_at ? formatDate(wallet.created_at) : 'Дата не указана'}</p>
            </div>
            <div>
              <p className="text-gray-600 mb-1">Обновлен:</p>
              <p className="font-medium">{wallet.updated_at ? formatDate(wallet.updated_at) : 'Дата не указана'}</p>
            </div>
            <div>
              <p className="text-gray-600 mb-1">Примечание:</p>
              <p className="font-medium">{wallet.notes || 'Не указано'}</p>
            </div>
          </div>
          
          <h3 className="text-lg font-semibold mb-3">Балансы:</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 mb-6">
            {Object.entries(wallet.balances).map(([currency, amount]) => (
              <div key={currency} className="bg-gray-50 p-3 rounded">
                <p className="text-gray-600 text-sm">{currency}</p>
                <p className="text-xl font-bold">{formatPrice(amount, currency as Currency)}</p>
                {rates[currency as Currency] && (
                  <p className="text-xs text-gray-500">
                    ≈ {formatPrice(amount * rates[Currency.USD] / rates[currency as Currency], Currency.USD)}
                  </p>
                )}
              </div>
            ))}
          </div>
          
          <div className="flex flex-wrap gap-3">
            <button 
              onClick={handleDeposit}
              className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
            >
              Пополнить
            </button>
            <button 
              onClick={handleWithdraw}
              className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600"
            >
              Вывести
            </button>
            <button 
              onClick={handleExchange}
              className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
            >
              Обменять валюту
            </button>
          </div>
        </div>
      )}

      {/* История транзакций */}
      <div className="bg-white shadow-md rounded-lg p-6">
        <h2 className="text-xl font-semibold mb-4">История транзакций</h2>
        
        {transactionsLoading ? (
          <div className="flex justify-center items-center h-32">
            <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-500"></div>
          </div>
        ) : transactionsError ? (
          <div className="text-center py-8">
            <p className="text-red-500 mb-4">{transactionsError}</p>
            <button 
              onClick={() => {
                setTransactionsError(null);
                if (selectedWallet) {
                  loadTransactions();
                }
              }}
              className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
            >
              Попробовать снова
            </button>
          </div>
        ) : transactions.length === 0 ? (
          <p className="text-center py-8 text-gray-500">История транзакций пуста</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Дата</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Тип</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Сумма</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Статус</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {transactions.map((transaction) => (
                  <tr key={transaction.id}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {transaction.created_at ? formatDate(transaction.created_at) : 'Дата не указана'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      {transaction.transaction_type || 'Не указано'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      {formatPrice(transaction.amount, transaction.currency)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <span className={getStatusColor(transaction.status)}>
                        {transaction.status || 'Не указано'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
} 