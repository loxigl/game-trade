'use client';

import { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useWallet, useWalletTransactions } from '../../hooks/wallet';
import { Currency, WithdrawalVerificationRequest } from '../../types/wallet';
import formatPrice from '../../utils/formatPrice';

// Компонент с использованием useSearchParams
function WithdrawContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const walletId = searchParams.get('wallet_id') ? parseInt(searchParams.get('wallet_id')!) : null;
  
  const { wallet, loading: walletLoading, error: walletError } = useWallet(walletId);
  const { withdraw, verifyWithdrawal, loading, error } = useWalletTransactions();
  
  const [amount, setAmount] = useState<string>('');
  const [currency, setCurrency] = useState<Currency>(Currency.USD);
  const [withdrawalMethod, setWithdrawalMethod] = useState<string>('bank_transfer');
  const [accountName, setAccountName] = useState<string>('');
  const [accountNumber, setAccountNumber] = useState<string>('');
  const [bankName, setBankName] = useState<string>('');
  const [swiftCode, setSwiftCode] = useState<string>('');
  const [description, setDescription] = useState<string>('');
  
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [success, setSuccess] = useState<boolean>(false);
  const [withdrawalResponse, setWithdrawalResponse] = useState<any>(null);
  const [verification, setVerification] = useState<boolean>(false);
  const [verificationCode, setVerificationCode] = useState<string>('');

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
    
    const withdrawalData = {
      wallet_id: walletId,
      amount: parseFloat(amount),
      currency,
      withdrawal_method: withdrawalMethod,
      account_details: {
        account_name: accountName,
        account_number: accountNumber,
        bank_name: bankName,
        swift_code: swiftCode,
        description
      }
    };
    
    setIsSubmitting(true);
    
    try {
      const response = await withdraw(withdrawalData);
      setWithdrawalResponse(response);
      
      if (response.verification_required) {
        setVerification(true);
      } else {
        setSuccess(true);
      }
    } catch (err) {
      console.error('Ошибка при выводе средств:', err);
    } finally {
      setIsSubmitting(false);
    }
  };
  
  const handleVerificationSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!withdrawalResponse?.id || !verificationCode) {
      return;
    }
    
    setIsSubmitting(true);
    
    try {
      const verificationData: WithdrawalVerificationRequest = {
        withdrawal_id: withdrawalResponse.id,
        verification_code: verificationCode
      };
      
      const response = await verifyWithdrawal(verificationData);
      setWithdrawalResponse(response);
      setVerification(false);
      setSuccess(true);
    } catch (err) {
      console.error('Ошибка при верификации вывода средств:', err);
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
          <h2 className="text-2xl font-bold mb-4">Запрос на вывод средств создан!</h2>
          <p className="mb-6">
            {withdrawalResponse?.status === 'completed' 
              ? `Ваши средства успешно выведены в размере ${formatPrice(withdrawalResponse?.amount, withdrawalResponse?.currency)}`
              : 'Ваш запрос на вывод средств был создан и находится в обработке. Статус транзакции будет обновлен автоматически.'}
          </p>
          <div className="flex justify-center space-x-4">
            <button 
              onClick={() => router.push('/wallet')} 
              className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
            >
              Вернуться к кошельку
            </button>
          </div>
        </div>
      </div>
    );
  }
  
  if (verification) {
    return (
      <div className="container mx-auto max-w-md p-6">
        <div className="bg-white shadow-md rounded-lg p-6">
          <h2 className="text-2xl font-bold mb-4">Подтверждение вывода средств</h2>
          <p className="mb-6">
            Для завершения операции вывода средств, введите код подтверждения, который был отправлен на ваш email.
          </p>
          
          {error && (
            <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
              <p>{error}</p>
            </div>
          )}
          
          <form onSubmit={handleVerificationSubmit}>
            <div className="mb-4">
              <label htmlFor="verificationCode" className="block text-sm font-medium text-gray-700 mb-1">
                Код подтверждения
              </label>
              <input
                type="text"
                id="verificationCode"
                value={verificationCode}
                onChange={(e) => setVerificationCode(e.target.value)}
                className="focus:ring-blue-500 focus:border-blue-500 block w-full py-2 px-3 sm:text-sm border border-gray-300 rounded-md"
                required
              />
            </div>
            
            <div className="flex justify-between">
              <button
                type="button"
                onClick={() => router.back()}
                className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-100"
              >
                Отмена
              </button>
              <button
                type="submit"
                disabled={isSubmitting || !verificationCode}
                className={`px-4 py-2 bg-blue-500 text-white rounded ${
                  isSubmitting || !verificationCode
                    ? 'opacity-50 cursor-not-allowed'
                    : 'hover:bg-blue-600'
                }`}
              >
                {isSubmitting ? 'Проверка...' : 'Подтвердить'}
              </button>
            </div>
          </form>
        </div>
      </div>
    );
  }
  
  return (
    <div className="container mx-auto max-w-md p-6">
      <h1 className="text-2xl font-bold mb-6">Вывод средств</h1>
      
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
              Сумма вывода
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
            {wallet.balances && (
              <p className="mt-1 text-xs text-gray-500">
                Доступно: {formatPrice(wallet.balances[currency] || 0, currency)}
            </p>
            )}
          </div>
          
          <div className="mb-4">
            <label htmlFor="withdrawal_method" className="block text-sm font-medium text-gray-700 mb-1">
              Способ вывода
            </label>
            <select
              id="withdrawal_method"
              name="withdrawal_method"
              value={withdrawalMethod}
              onChange={(e) => setWithdrawalMethod(e.target.value)}
              className="focus:ring-blue-500 focus:border-blue-500 block w-full py-2 px-3 sm:text-sm border border-gray-300 rounded-md"
              required
            >
              <option value="bank_transfer">Банковский перевод</option>
              <option value="credit_card">На карту</option>
              <option value="electronic_wallet">Электронный кошелек</option>
              <option value="crypto">Криптовалюта</option>
            </select>
          </div>
          
          <div className="mb-4">
            <label htmlFor="accountName" className="block text-sm font-medium text-gray-700 mb-1">
              Имя получателя
            </label>
            <input
              type="text"
              id="accountName"
              name="accountName"
              value={accountName}
              onChange={(e) => setAccountName(e.target.value)}
              className="focus:ring-blue-500 focus:border-blue-500 block w-full py-2 px-3 sm:text-sm border border-gray-300 rounded-md"
              required
            />
          </div>
          
          <div className="mb-4">
            <label htmlFor="accountNumber" className="block text-sm font-medium text-gray-700 mb-1">
              Номер счета / карты
            </label>
            <input
              type="text"
              id="accountNumber"
              name="accountNumber"
              value={accountNumber}
              onChange={(e) => setAccountNumber(e.target.value)}
              className="focus:ring-blue-500 focus:border-blue-500 block w-full py-2 px-3 sm:text-sm border border-gray-300 rounded-md"
              required
            />
          </div>
          
          <div className="mb-4">
            <label htmlFor="bankName" className="block text-sm font-medium text-gray-700 mb-1">
              Название банка
            </label>
            <input
              type="text"
              id="bankName"
              name="bankName"
              value={bankName}
              onChange={(e) => setBankName(e.target.value)}
              className="focus:ring-blue-500 focus:border-blue-500 block w-full py-2 px-3 sm:text-sm border border-gray-300 rounded-md"
              required
            />
          </div>
          
          <div className="mb-4">
            <label htmlFor="swiftCode" className="block text-sm font-medium text-gray-700 mb-1">
              SWIFT / BIC код
            </label>
            <input
              type="text"
              id="swiftCode"
              name="swiftCode"
              value={swiftCode}
              onChange={(e) => setSwiftCode(e.target.value)}
              className="focus:ring-blue-500 focus:border-blue-500 block w-full py-2 px-3 sm:text-sm border border-gray-300 rounded-md"
            />
            <p className="mt-1 text-xs text-gray-500">
              Необходим для международных переводов
            </p>
          </div>
          
          <div className="mb-6">
            <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-1">
              Описание платежа (необязательно)
            </label>
            <textarea
              id="description"
              name="description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="focus:ring-blue-500 focus:border-blue-500 block w-full py-2 px-3 sm:text-sm border border-gray-300 rounded-md"
            ></textarea>
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
              {isSubmitting ? 'Обработка...' : 'Вывести средства'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// Загрузочное состояние для Suspense
function WithdrawLoading() {
  return (
    <div className="flex justify-center items-center h-screen">
      <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
    </div>
  );
}

// Основной экспортируемый компонент
export default function WithdrawPage() {
  return (
    <Suspense fallback={<WithdrawLoading />}>
      <WithdrawContent />
    </Suspense>
  );
} 