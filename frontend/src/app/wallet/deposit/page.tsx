'use client';

import { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useWallet, useWalletTransactions } from '../../hooks/wallet';
import { Currency, DepositRequest } from '../../types/wallet';
import formatPrice from '../../utils/formatPrice';

// Компонент с использованием useSearchParams
function DepositContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const walletId = searchParams?.get('wallet_id') ? parseInt(searchParams.get('wallet_id')!) : null;
  
  const { wallet, loading: walletLoading, error: walletError } = useWallet(walletId);
  const { deposit, simulateSuccessfulDeposit, loading, error } = useWalletTransactions();
  
  const [amount, setAmount] = useState<string>('');
  const [currency, setCurrency] = useState<Currency>(Currency.USD);
  const [paymentMethod, setPaymentMethod] = useState<string>('card');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [success, setSuccess] = useState<boolean>(false);
  const [depositResponse, setDepositResponse] = useState<any>(null);

  // При загрузке кошелька устанавливаем валюту по умолчанию
  useEffect(() => {
    if (wallet && wallet.balances) {
      // Выбираем первую валюту из доступных в кошельке
      const currencies = Object.keys(wallet.balances);
      if (currencies.length > 0) {
        setCurrency(currencies[0] as Currency);
      }
    }
  }, [wallet]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!walletId || !amount || isNaN(parseFloat(amount)) || parseFloat(amount) <= 0) {
      return;
    }
    
    const depositData: DepositRequest = {
      wallet_id: walletId,
      amount: parseFloat(amount),
      currency,
      payment_method: paymentMethod
    };
    
    setIsSubmitting(true);
    
    try {
      const response = await deposit(depositData);
      setDepositResponse(response);
      setSuccess(true);
      
      // Если есть redirect_url, то перенаправляем пользователя
      if (response.redirect_url) {
        window.location.href = response.redirect_url;
        return;
      }
      
      // Если есть client_secret, то отображаем форму для Stripe Elements
      if (response.client_secret) {
        // В нашем случае используется мок, поэтому симулируем успешное завершение
        setTimeout(() => {
          setSuccess(true);
        }, 2000);
      }
    } catch (err) {
      console.error('Ошибка при пополнении:', err);
    } finally {
      setIsSubmitting(false);
    }
  };
  
  if (walletLoading) {
    return (
      <div className="flex justify-center items-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }
  
  if (walletError || !wallet) {
    return (
      <div className="text-center p-8">
        <h1 className="text-2xl text-red-600 mb-4">Ошибка загрузки кошелька</h1>
        <p className="mb-4">{walletError || 'Кошелек не найден'}</p>
        <button 
          onClick={() => router.back()} 
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          Вернуться назад
        </button>
      </div>
    );
  }
  
  if (success) {
    return (
      <div className="container mx-auto max-w-md p-6">
        <div className="bg-white shadow-md rounded-lg p-6 text-center">
          <svg 
            className="w-16 h-16 text-green-500 mx-auto mb-4" 
            fill="none" 
            stroke="currentColor" 
            viewBox="0 0 24 24" 
            xmlns="http://www.w3.org/2000/svg"
          >
            <path 
              strokeLinecap="round" 
              strokeLinejoin="round" 
              strokeWidth="2" 
              d="M5 13l4 4L19 7"
            ></path>
          </svg>
          <h2 className="text-2xl font-bold mb-4">Пополнение успешно инициировано!</h2>
          <p className="mb-6">
            {depositResponse?.status === 'succeeded' 
              ? `Ваш кошелек успешно пополнен на ${formatPrice(depositResponse?.amount, depositResponse?.currency)}`
              : 'Запрос на пополнение был создан и находится в обработке. Статус транзакции будет обновлен автоматически.'}
          </p>
          <div className="flex justify-center space-x-4 mb-4">
            <button 
              onClick={() => router.push('/wallet')} 
              className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
            >
              Вернуться к кошельку
            </button>
            <button 
              onClick={() => {
                setSuccess(false);
                setAmount('');
                setDepositResponse(null);
              }} 
              className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-100"
            >
              Новое пополнение
            </button>
          </div>
          
          {/* Кнопка для эмуляции успешного пополнения (только для разработки) */}
          {depositResponse?.status !== 'succeeded' && (
            <div className="mt-4 p-3 bg-yellow-50 rounded">
              <p className="text-sm text-yellow-700 mb-2">Для разработки: эмулировать успешное пополнение</p>
              <button 
                onClick={async () => {
                  if (!walletId || !depositResponse?.transaction_id) return;
                  
                  try {
                    await simulateSuccessfulDeposit(walletId, depositResponse.transaction_id);
                    alert('Пополнение успешно эмулировано. Обновите страницу кошелька для проверки баланса.');
                  } catch (err) {
                    console.error('Ошибка при эмуляции пополнения:', err);
                    alert('Ошибка при эмуляции пополнения');
                  }
                }} 
                className="px-4 py-2 bg-yellow-500 text-white rounded hover:bg-yellow-600"
              >
                Эмулировать платеж
              </button>
            </div>
          )}
        </div>
      </div>
    );
  }
  
  return (
    <div className="container mx-auto max-w-md p-6">
      <h1 className="text-2xl font-bold mb-6">Пополнение кошелька</h1>
      
      <div className="bg-white shadow-md rounded-lg p-6">
        <div className="mb-4">
          <h2 className="text-lg font-medium">Кошелек #{wallet.id}</h2>
          <p className="text-gray-600">
            {wallet.is_default ? 'Основной кошелек' : 'Дополнительный кошелек'}
          </p>
        </div>
        
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label htmlFor="amount" className="block text-sm font-medium text-gray-700 mb-1">
              Сумма пополнения
            </label>
            <div className="relative rounded-md shadow-sm">
              <input
                type="number"
                id="amount"
                name="amount"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                className="focus:ring-blue-500 focus:border-blue-500 block w-full pl-3 pr-12 py-2 sm:text-sm border border-gray-300 rounded-md"
                placeholder="0.00"
                step="0.01"
                min="0.01"
                required
              />
              <div className="absolute inset-y-0 right-0 flex items-center">
                <select
                  id="currency"
                  name="currency"
                  value={currency}
                  onChange={(e) => setCurrency(e.target.value as Currency)}
                  className="focus:ring-blue-500 focus:border-blue-500 h-full py-0 pl-2 pr-7 border-transparent bg-transparent text-gray-500 sm:text-sm rounded-md"
                >
                  {wallet.balances && Object.keys(wallet.balances).map((curr) => (
                    <option key={curr} value={curr}>{curr}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>
          
          <div className="mb-6">
            <label htmlFor="payment_method" className="block text-sm font-medium text-gray-700 mb-1">
              Способ оплаты
            </label>
            <select
              id="payment_method"
              name="payment_method"
              value={paymentMethod}
              onChange={(e) => setPaymentMethod(e.target.value)}
              className="focus:ring-blue-500 focus:border-blue-500 block w-full py-2 px-3 sm:text-sm border border-gray-300 rounded-md"
              required
            >
              <option value="card">Банковская карта</option>
              <option value="bank_transfer">Банковский перевод</option>
              <option value="crypto">Криптовалюта</option>
              <option value="electronic_wallet">Электронный кошелек</option>
            </select>
          </div>
          
          {error && (
            <div className="mb-4 p-3 bg-red-50 text-red-700 rounded">
              {error}
            </div>
          )}
          
          <div className="flex items-center justify-between">
            <button
              type="button"
              onClick={() => router.back()}
              className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-100"
            >
              Отмена
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !amount || parseFloat(amount) <= 0}
              className={`px-4 py-2 bg-blue-500 text-white rounded ${
                isSubmitting || !amount || parseFloat(amount) <= 0
                  ? 'opacity-50 cursor-not-allowed'
                  : 'hover:bg-blue-600'
              }`}
            >
              {isSubmitting ? 'Обработка...' : 'Пополнить'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// Загрузочное состояние для Suspense
function DepositLoading() {
  return (
    <div className="flex justify-center items-center h-screen">
      <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
    </div>
  );
}

// Основной экспортируемый компонент
export default function DepositPage() {
  return (
    <Suspense fallback={<DepositLoading />}>
      <DepositContent />
    </Suspense>
  );
} 