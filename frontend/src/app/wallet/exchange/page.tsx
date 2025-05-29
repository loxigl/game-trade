'use client';

import { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useWallet, useCurrencyExchange } from '../../hooks/wallet';
import { Currency } from '../../types/wallet';
import formatPrice from '../../utils/formatPrice';

// Компонент с использованием useSearchParams
function ExchangeContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const walletId = searchParams?.get('wallet_id') ? parseInt(searchParams.get('wallet_id')!) : null;
  
  const { wallet, loading: walletLoading, error: walletError } = useWallet(walletId);
  const { rates, loading: ratesLoading, error: ratesError, convertCurrency } = useCurrencyExchange();
  
  const [amount, setAmount] = useState<string>('');
  const [fromCurrency, setFromCurrency] = useState<Currency>(Currency.USD);
  const [toCurrency, setToCurrency] = useState<Currency>(Currency.EUR);
  const [convertedAmount, setConvertedAmount] = useState<number | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [success, setSuccess] = useState<boolean>(false);
  const [conversionResponse, setConversionResponse] = useState<any>(null);
  const [exchangeError, setExchangeError] = useState<string | null>(null);

  // При загрузке кошелька устанавливаем валюты по умолчанию
  useEffect(() => {
    if (wallet && wallet.balances) {
      const currencies = Object.keys(wallet.balances);
      if (currencies.length > 0) {
        setFromCurrency(currencies[0] as Currency);
        // Устанавливаем toCurrency на другую валюту, если есть
        if (currencies.length > 1) {
          setToCurrency(currencies[1] as Currency);
        }
      }
    }
  }, [wallet]);

  // Рассчитываем конвертацию при изменении суммы, валют или курсов
  useEffect(() => {
    if (!amount || isNaN(parseFloat(amount)) || !rates || !rates[toCurrency]) return;
    
    const amountValue = parseFloat(amount);
    const fromRate = rates[fromCurrency] || 1;
    const toRate = rates[toCurrency] || 1;
    
    // Корректная формула конвертации:
    // USD -> EUR: multiply USD by EUR/USD rate
    const convertedValue = amountValue * (toRate / fromRate);
    setConvertedAmount(convertedValue);
  }, [amount, fromCurrency, toCurrency, rates]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!walletId || !amount || isNaN(parseFloat(amount)) || parseFloat(amount) <= 0) {
      return;
    }
    
    // Проверка на достаточность средств
    if (wallet && wallet.balances && wallet.balances[fromCurrency] < parseFloat(amount)) {
      setExchangeError(`Недостаточно средств. Доступно: ${formatPrice(wallet.balances[fromCurrency], fromCurrency)}`);
      return;
    }
    
    const conversionData = {
      wallet_id: walletId,
      from_currency: fromCurrency,
      to_currency: toCurrency,
      amount: parseFloat(amount)
    };
    
    setIsSubmitting(true);
    setExchangeError(null);
    
    try {
      const response = await convertCurrency(conversionData);
      setConversionResponse(response);
      setSuccess(true);
    } catch (err) {
      console.error('Ошибка при конвертации валюты:', err);
      setExchangeError(err instanceof Error ? err.message : 'Произошла ошибка при конвертации валюты');
    } finally {
      setIsSubmitting(false);
    }
  };
  
  if (walletLoading || ratesLoading) {
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
  
  if (ratesError) {
    return (
      <div className="text-center p-8">
        <h1 className="text-2xl text-red-600 mb-4">Ошибка загрузки курсов валют</h1>
        <p className="mb-4">{ratesError}</p>
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
          <h2 className="text-2xl font-bold mb-4">Обмен валюты выполнен!</h2>
          <p className="mb-2">
            Вы успешно обменяли {formatPrice(conversionResponse?.debit_transaction?.amount || 0, conversionResponse?.debit_transaction?.currency || '')}
          </p>
          <p className="mb-6">
            на {formatPrice(conversionResponse?.credit_transaction?.amount || 0, conversionResponse?.credit_transaction?.currency || '')}
          </p>
          <p className="text-sm text-gray-500 mb-6">
            Курс: 1 {conversionResponse?.debit_transaction?.currency || ''} = {conversionResponse?.exchange_rate || 0} {conversionResponse?.credit_transaction?.currency || ''}
          </p>
          <div className="flex justify-center space-x-4">
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
                setConvertedAmount(null);
                setConversionResponse(null);
              }} 
              className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-100"
            >
              Новый обмен
            </button>
          </div>
        </div>
      </div>
    );
  }
  
  return (
    <div className="container mx-auto max-w-md p-6">
      <h1 className="text-2xl font-bold mb-6">Обмен валюты</h1>
      
      <div className="bg-white shadow-md rounded-lg p-6">
        <div className="mb-4">
          <h2 className="text-lg font-medium">Кошелек #{wallet.id}</h2>
          <p className="text-gray-600">
            {wallet.is_default ? 'Основной кошелек' : 'Дополнительный кошелек'}
          </p>
        </div>
        
        {exchangeError && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
            <p>{exchangeError}</p>
          </div>
        )}
        
        <form onSubmit={handleSubmit}>
          <div className="mb-6">
            <label htmlFor="amount" className="block text-sm font-medium text-gray-700 mb-1">
              Сумма обмена
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
                  id="fromCurrency"
                  name="fromCurrency"
                  value={fromCurrency}
                  onChange={(e) => {
                    const newCurrency = e.target.value as Currency;
                    // Если выбрана та же валюта что и целевая, меняем целевую
                    if (newCurrency === toCurrency) {
                      const currencies = Object.keys(wallet.balances || {});
                      const otherCurrencies = currencies.filter(c => c !== newCurrency);
                      if (otherCurrencies.length > 0) {
                        setToCurrency(otherCurrencies[0] as Currency);
                      }
                    }
                    setFromCurrency(newCurrency);
                  }}
                  className="focus:ring-blue-500 focus:border-blue-500 h-full py-0 pl-2 pr-7 border-transparent bg-transparent text-gray-500 sm:text-sm rounded-md"
                >
                  {wallet.balances && Object.keys(wallet.balances).map((curr) => (
                    <option key={curr} value={curr}>{curr}</option>
                  ))}
                </select>
              </div>
            </div>
            {wallet.balances && (
              <p className="mt-1 text-xs text-gray-500">
                Доступно: {formatPrice(wallet.balances[fromCurrency] || 0, fromCurrency)}
            </p>
            )}
          </div>
          
          <div className="mb-6">
            <div className="flex justify-center items-center mb-2">
              <svg 
                className="w-6 h-6 text-gray-400" 
                fill="none" 
                stroke="currentColor" 
                viewBox="0 0 24 24" 
                xmlns="http://www.w3.org/2000/svg"
              >
                <path 
                  strokeLinecap="round" 
                  strokeLinejoin="round" 
                  strokeWidth="2" 
                  d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"
                ></path>
              </svg>
            </div>
          
            <label htmlFor="toCurrency" className="block text-sm font-medium text-gray-700 mb-1">
              Конвертировать в
            </label>
            <div className="flex items-center">
                <select
                  id="toCurrency"
                  name="toCurrency"
                  value={toCurrency}
                  onChange={(e) => {
                  const newCurrency = e.target.value as Currency;
                  // Если выбрана та же валюта что и исходная, меняем исходную
                  if (newCurrency === fromCurrency) {
                    const currencies = Object.keys(wallet.balances || {});
                    const otherCurrencies = currencies.filter(c => c !== newCurrency);
                    if (otherCurrencies.length > 0) {
                      setFromCurrency(otherCurrencies[0] as Currency);
                    }
                    }
                  setToCurrency(newCurrency);
                  }}
                className="focus:ring-blue-500 focus:border-blue-500 block w-full py-2 px-3 sm:text-sm border border-gray-300 rounded-md"
                >
                  {wallet.balances && Object.keys(wallet.balances).map((curr) => (
                    <option key={curr} value={curr}>{curr}</option>
                  ))}
                </select>
          </div>
          
            {convertedAmount !== null && amount && rates && (
              <div className="mt-3 p-3 bg-gray-50 rounded">
                <p className="text-lg font-medium">
                  {parseFloat(amount).toFixed(2)} {fromCurrency} = {convertedAmount.toFixed(2)} {toCurrency}
                </p>
                <p className="text-xs text-gray-500">
                  Курс: 1 {fromCurrency} = {(rates[toCurrency] / rates[fromCurrency]).toFixed(4)} {toCurrency}
              </p>
            </div>
          )}
          </div>
          
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
              disabled={isSubmitting || !amount || parseFloat(amount) <= 0 || fromCurrency === toCurrency}
              className={`px-4 py-2 bg-blue-500 text-white rounded ${
                isSubmitting || !amount || parseFloat(amount) <= 0 || fromCurrency === toCurrency
                  ? 'opacity-50 cursor-not-allowed'
                  : 'hover:bg-blue-600'
              }`}
            >
              {isSubmitting ? 'Обработка...' : 'Обменять валюту'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// Загрузочное состояние для Suspense
function ExchangeLoading() {
  return (
    <div className="flex justify-center items-center h-screen">
      <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
    </div>
  );
}

// Основной экспортируемый компонент
export default function ExchangePage() {
  return (
    <Suspense fallback={<ExchangeLoading />}>
      <ExchangeContent />
    </Suspense>
  );
} 