'use client';

import { useState } from 'react';
import { useAdminWallets } from '../../hooks/wallet';
import { WalletStatus, Currency } from '../../types/wallet';
import formatPrice from '../../utils/formatPrice';
import { formatDate } from '../../utils/formatDate';

export default function AdminWalletsPage() {
  const { 
    wallets, 
    loading, 
    error, 
    fetchAllWallets, 
    updateWalletStatus 
  } = useAdminWallets();
  
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [walletIdToEdit, setWalletIdToEdit] = useState<number | null>(null);
  const [isUpdating, setIsUpdating] = useState(false);
  const [newStatus, setNewStatus] = useState<WalletStatus>(WalletStatus.ACTIVE);

  // Функция для фильтрации кошельков
  const filteredWallets = wallets.filter(wallet => {
    // Фильтрация по поиску (ID кошелька или ID пользователя)
    const searchMatch = searchTerm === '' || 
      wallet.id.toString().includes(searchTerm) || 
      wallet.user_id.toString().includes(searchTerm);
    
    // Фильтрация по статусу
    const statusMatch = statusFilter === 'all' || wallet.status === statusFilter;
    
    return searchMatch && statusMatch;
  });

  // Обработчик для обновления статуса кошелька
  const handleStatusUpdate = async (walletId: number, status: string) => {
    setIsUpdating(true);
    try {
      await updateWalletStatus(walletId, status);
      setWalletIdToEdit(null);
    } catch (error) {
      console.error('Ошибка при обновлении статуса кошелька:', error);
    } finally {
      setIsUpdating(false);
    }
  };

  // Получение общего баланса в определенной валюте для всех кошельков
  const getTotalBalance = (currency: Currency) => {
    return wallets.reduce((total, wallet) => {
      return total + (wallet.balances[currency] || 0);
    }, 0);
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center p-8">
        <h1 className="text-2xl text-red-600 mb-4">Произошла ошибка</h1>
        <p className="mb-4">{error}</p>
        <button 
          onClick={() => fetchAllWallets()} 
          className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          Попробовать снова
        </button>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-3xl font-bold mb-6">Управление кошельками</h1>
      
      {/* Статистика по кошелькам */}
      <div className="bg-white shadow-md rounded-lg p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4">Статистика кошельков</h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-blue-50 p-4 rounded-lg">
            <p className="text-sm text-gray-500">Всего кошельков</p>
            <p className="text-2xl font-bold">{wallets.length}</p>
          </div>
          <div className="bg-green-50 p-4 rounded-lg">
            <p className="text-sm text-gray-500">Активных кошельков</p>
            <p className="text-2xl font-bold">
              {wallets.filter(wallet => wallet.status === WalletStatus.ACTIVE).length}
            </p>
          </div>
          <div className="bg-red-50 p-4 rounded-lg">
            <p className="text-sm text-gray-500">Заблокированных кошельков</p>
            <p className="text-2xl font-bold">
              {wallets.filter(wallet => wallet.status === WalletStatus.BLOCKED).length}
            </p>
          </div>
          <div className="bg-yellow-50 p-4 rounded-lg">
            <p className="text-sm text-gray-500">Ожидающих верификации</p>
            <p className="text-2xl font-bold">
              {wallets.filter(wallet => wallet.status === WalletStatus.PENDING).length}
            </p>
          </div>
        </div>
      </div>
      
      {/* Общие балансы всех кошельков */}
      <div className="bg-white shadow-md rounded-lg p-6 mb-6">
        <h2 className="text-xl font-semibold mb-4">Общие балансы всех кошельков</h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
          {Object.values(Currency).map(currency => (
            <div key={currency} className="bg-gray-50 p-3 rounded">
              <p className="text-gray-600 text-sm">{currency}</p>
              <p className="text-xl font-bold">{formatPrice(getTotalBalance(currency), currency)}</p>
            </div>
          ))}
        </div>
      </div>
      
      {/* Фильтры и поиск */}
      <div className="bg-white shadow-md rounded-lg p-6 mb-6">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="w-full md:w-1/3">
            <label htmlFor="search" className="block text-sm font-medium text-gray-700 mb-1">
              Поиск по ID кошелька или пользователя
            </label>
            <input
              type="text"
              id="search"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full p-2 border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500"
              placeholder="Введите ID..."
            />
          </div>
          
          <div className="w-full md:w-1/3">
            <label htmlFor="status-filter" className="block text-sm font-medium text-gray-700 mb-1">
              Фильтр по статусу
            </label>
            <select
              id="status-filter"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="w-full p-2 border border-gray-300 rounded focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="all">Все статусы</option>
              {Object.values(WalletStatus).map(status => (
                <option key={status} value={status}>{status}</option>
              ))}
            </select>
          </div>
          
          <div className="w-full md:w-1/3 md:self-end">
            <button
              onClick={() => fetchAllWallets()}
              className="w-full p-2 bg-blue-500 text-white rounded hover:bg-blue-600"
            >
              Обновить список
            </button>
          </div>
        </div>
      </div>
      
      {/* Таблица кошельков */}
      <div className="bg-white shadow-md rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  ID кошелька
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  ID пользователя
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Статус
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Балансы
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Дата создания
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Действия
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {filteredWallets.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-4 text-center text-gray-500">
                    Кошельки не найдены
                  </td>
                </tr>
              ) : (
                filteredWallets.map(wallet => (
                  <tr key={wallet.id}>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900">{wallet.id}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900">{wallet.user_id}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      {walletIdToEdit === wallet.id ? (
                        <select
                          value={newStatus}
                          onChange={(e) => setNewStatus(e.target.value as WalletStatus)}
                          className="text-sm border border-gray-300 rounded p-1"
                        >
                          {Object.values(WalletStatus).map(status => (
                            <option key={status} value={status}>{status}</option>
                          ))}
                        </select>
                      ) : (
                        <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full 
                          ${wallet.status === WalletStatus.ACTIVE ? 'bg-green-100 text-green-800' :
                          wallet.status === WalletStatus.BLOCKED ? 'bg-red-100 text-red-800' :
                          wallet.status === WalletStatus.PENDING ? 'bg-yellow-100 text-yellow-800' :
                          'bg-gray-100 text-gray-800'}`}
                        >
                          {wallet.status}
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-gray-900 space-y-1">
                        {Object.entries(wallet.balances).map(([currency, amount]) => (
                          <div key={currency}>
                            <span className="font-medium">{currency}:</span> {formatPrice(amount, currency as Currency)}
                          </div>
                        ))}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm text-gray-900">{formatDate(wallet.created_at)}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      {walletIdToEdit === wallet.id ? (
                        <div className="flex justify-end space-x-2">
                          <button
                            onClick={() => handleStatusUpdate(wallet.id, newStatus)}
                            disabled={isUpdating}
                            className="text-blue-600 hover:text-blue-900"
                          >
                            {isUpdating ? 'Сохранение...' : 'Сохранить'}
                          </button>
                          <button
                            onClick={() => setWalletIdToEdit(null)}
                            className="text-gray-600 hover:text-gray-900"
                          >
                            Отмена
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => {
                            setWalletIdToEdit(wallet.id);
                            setNewStatus(wallet.status);
                          }}
                          className="text-blue-600 hover:text-blue-900"
                        >
                          Изменить
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
} 