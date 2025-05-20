'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useSales } from '../hooks/sale';
import { useWallets } from '../hooks/wallet';
import { SaleStatus } from '../types/sale';
import formatPrice from '../utils/formatPrice';

interface BuyButtonProps {
  listingId: number;
  price: number;
  currency: string;
  sellerId: number;
}

export default function BuyButton({ listingId, price, currency, sellerId }: BuyButtonProps) {
  const router = useRouter();
  const { initiateSale, loading, error } = useSales();
  const { wallets, loading: walletsLoading } = useWallets();
  const [showWalletSelector, setShowWalletSelector] = useState(false);

  // Находим кошелек с достаточным балансом
  const suitableWallet = wallets?.find(wallet => 
    wallet.balances[currency] >= price
  );

  const handleBuy = async () => {
    try {
      if (!suitableWallet) {
        // Если нет подходящего кошелька, показываем селектор
        setShowWalletSelector(true);
        return;
      }

      // Создаем продажу
      const sale = await initiateSale(listingId, suitableWallet.id);
      
      // Перенаправляем на страницу продажи
      router.push(`/sales/${sale.id}`);
    } catch (err) {
      if (err instanceof Error && err.message.includes('Недостаточно средств')) {
        setShowWalletSelector(true);
      } else {
        console.error('Ошибка при создании продажи:', err);
      }
    }
  };

  const handleWalletSelect = async (walletId: number) => {
    try {
      const sale = await initiateSale(listingId, walletId);
      router.push(`/sales/${sale.id}`);
    } catch (err) {
      console.error('Ошибка при создании продажи:', err);
    } finally {
      setShowWalletSelector(false);
    }
  };

  if (walletsLoading) {
    return (
      <button
        disabled
        className="w-full px-4 py-2 bg-gray-400 text-white rounded cursor-not-allowed"
      >
        Загрузка...
      </button>
    );
  }

  if (showWalletSelector) {
    return (
      <div className="space-y-4">
        <div className="text-sm text-gray-600">
          Выберите кошелек для оплаты:
        </div>
        <div className="space-y-2">
          {wallets?.map(wallet => (
            <button
              key={wallet.id}
              onClick={() => handleWalletSelect(wallet.id)}
              disabled={wallet.balances[currency] < price}
              className={`w-full px-4 py-2 rounded ${
                wallet.balances[currency] >= price
                  ? 'bg-blue-500 text-white hover:bg-blue-600'
                  : 'bg-gray-200 text-gray-500 cursor-not-allowed'
              }`}
            >
              Кошелек #{wallet.id} - {formatPrice(wallet.balances[currency], currency)}
              {wallet.balances[currency] < price && ' (Недостаточно средств)'}
            </button>
          ))}
        </div>
        <button
          onClick={() => router.push('/wallet/deposit')}
          className="w-full px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
        >
          Пополнить кошелек
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <button
        onClick={handleBuy}
        disabled={loading}
        className={`w-full px-4 py-2 rounded ${
          loading
            ? 'bg-gray-400 cursor-not-allowed'
            : suitableWallet
            ? 'bg-green-500 hover:bg-green-600'
            : 'bg-blue-500 hover:bg-blue-600'
        } text-white`}
      >
        {loading ? 'Загрузка...' : suitableWallet ? 'Купить' : 'Выбрать кошелек'}
      </button>
      {error && (
        <div className="text-sm text-red-500">
          {error}
        </div>
      )}
      {!suitableWallet && (
        <div className="text-sm text-gray-600">
          Недостаточно средств на кошельке. Выберите другой кошелек или пополните баланс.
        </div>
      )}
    </div>
  );
} 