'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useWallet } from '../../hooks/wallet';
import { Currency } from '../../types/wallet';
import { useAuth } from '../../hooks/auth';

export default function CreateWalletPage() {
  const router = useRouter();
  const { createWallet, loading, error } = useWallet(null);
  const { user } = useAuth();
  const [isDefaultWallet, setIsDefaultWallet] = useState<boolean>(true);
  const [notes, setNotes] = useState<string>('');
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!user?.id) {
      setErrorMessage('Необходимо авторизоваться для создания кошелька');
      return;
    }
    
    try {
      setErrorMessage(null);
      const wallet = await createWallet({
        user_id: user.id,
        is_default: isDefaultWallet,
        notes: notes || undefined,
        initial_balances: {
          [Currency.USD]: 0,
          [Currency.EUR]: 0,
          [Currency.RUB]: 0,
          [Currency.GBP]: 0,
          [Currency.JPY]: 0,
          [Currency.CNY]: 0
        }
      });
      
      setSuccessMessage(`Кошелек успешно создан! ID: ${wallet.id}`);
      
      // Задержка перед перенаправлением на страницу кошелька
      setTimeout(() => {
        router.push('/wallet');
      }, 2000);
    } catch (err) {
      console.error('Ошибка при создании кошелька:', err);
      setErrorMessage(err instanceof Error ? err.message : 'Произошла ошибка при создании кошелька');
    }
  };
  
  if (loading) {
    return (
      <div className="flex justify-center items-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }
  
  if (successMessage) {
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
          <h2 className="text-2xl font-bold mb-4">Кошелек создан!</h2>
          <p className="mb-6">{successMessage}</p>
          <p className="text-gray-600 mb-6">Вы будете перенаправлены на страницу кошелька...</p>
        </div>
      </div>
    );
  }
  
  return (
    <div className="container mx-auto max-w-md p-6">
      <h1 className="text-2xl font-bold mb-6">Создание нового кошелька</h1>
      
      {errorMessage && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          <strong className="font-bold">Ошибка!</strong>
          <span className="block sm:inline"> {errorMessage}</span>
        </div>
      )}
      
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          <strong className="font-bold">Ошибка!</strong>
          <span className="block sm:inline"> {error}</span>
        </div>
      )}
      
      <div className="bg-white shadow-md rounded-lg p-6">
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-gray-700 text-sm font-bold mb-2">
              ID пользователя
            </label>
            <input
              type="text"
              className="bg-gray-200 border border-gray-300 text-gray-700 py-2 px-4 rounded w-full"
              value={user?.id || 'Не авторизован'}
              disabled
            />
            <p className="text-gray-600 text-xs mt-1">Кошелек будет создан для вашего аккаунта</p>
          </div>
          
          <div className="mb-4">
            <label className="flex items-center cursor-pointer">
              <input
                type="checkbox"
                className="form-checkbox h-5 w-5 text-blue-500"
                checked={isDefaultWallet}
                onChange={() => setIsDefaultWallet(!isDefaultWallet)}
              />
              <span className="ml-2 text-gray-700">Сделать основным кошельком</span>
            </label>
            <p className="text-gray-600 text-xs mt-1">Основной кошелек используется для транзакций по умолчанию</p>
          </div>
          
          <div className="mb-6">
            <label className="block text-gray-700 text-sm font-bold mb-2">
              Примечания (необязательно)
            </label>
            <textarea
              className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              placeholder="Добавьте примечания к кошельку..."
            ></textarea>
          </div>
          
          <div className="flex items-center justify-between">
            <button
              type="submit"
              className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline"
              disabled={loading || !user?.id}
            >
              {loading ? 'Создание...' : 'Создать кошелек'}
            </button>
            <button
              type="button"
              className="text-gray-600 font-semibold hover:text-gray-800"
              onClick={() => router.back()}
            >
              Отмена
            </button>
          </div>
        </form>
      </div>
    </div>
  );
} 