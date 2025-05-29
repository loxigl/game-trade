'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Table, Tag, Button, Space, Spin, Empty, Tabs, message, Tooltip } from 'antd';
import { SearchOutlined, MessageOutlined, EyeOutlined } from '@ant-design/icons';
import Link from 'next/link';
import { useAuth } from '../hooks/auth';
import { format } from 'date-fns';
import { Sale, SaleStatus } from '../types/sale';
import { salesApi } from '../utils/api';
import formatPrice from '../utils/formatPrice';

const { TabPane } = Tabs;

interface AllOrdersListProps {
  onOpenChat?: (chatId: number) => void;
}

// Метки и цвета для статусов
const statusLabels: Record<SaleStatus, string> = {
  [SaleStatus.PENDING]: 'Ожидает оплаты',
  [SaleStatus.PAYMENT_PROCESSING]: 'Обработка оплаты',
  [SaleStatus.DELIVERY_PENDING]: 'Ожидает доставки',
  [SaleStatus.COMPLETED]: 'Завершена',
  [SaleStatus.CANCELED]: 'Отменена',
  [SaleStatus.REFUNDED]: 'Возвращена',
  [SaleStatus.DISPUTED]: 'Спор',
};

const statusColors: Record<SaleStatus, string> = {
  [SaleStatus.PENDING]: 'warning',
  [SaleStatus.PAYMENT_PROCESSING]: 'processing',
  [SaleStatus.DELIVERY_PENDING]: 'purple',
  [SaleStatus.COMPLETED]: 'success',
  [SaleStatus.CANCELED]: 'error',
  [SaleStatus.REFUNDED]: 'default',
  [SaleStatus.DISPUTED]: 'volcano',
};

const AllOrdersList: React.FC<AllOrdersListProps> = ({ onOpenChat }) => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState<'all' | 'buyer' | 'seller'>('all');
  const [buyerOrders, setBuyerOrders] = useState<Sale[]>([]);
  const [sellerOrders, setSellerOrders] = useState<Sale[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchText, setSearchText] = useState('');
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 10,
    total: 0
  });

  // Получение заказов пользователя
  const fetchOrders = useCallback(async (role: 'buyer' | 'seller', page = 1, pageSize = 10) => {
    try {
      setLoading(true);
      console.log(`Загрузка заказов пользователя (роль: ${role}, страница: ${page})`);
      const response = await salesApi.getUserSales(role, undefined, page, pageSize);
      
      if (role === 'buyer') {
        setBuyerOrders(response.items);
      } else {
        setSellerOrders(response.items);
      }
      
      setPagination({
        current: response.page,
        pageSize: response.size,
        total: response.total
      });
      
      setError(null);
    } catch (err) {
      console.error(`Ошибка при загрузке заказов для роли ${role}:`, err);
      setError(err instanceof Error ? err.message : 'Не удалось загрузить список заказов');
    } finally {
      setLoading(false);
    }
  }, []);

  // Загрузка заказов при монтировании компонента
  useEffect(() => {
    // Загружаем заказы покупателя
    fetchOrders('buyer');
    // Загружаем заказы продавца
    fetchOrders('seller');
  }, [fetchOrders]);

  // Фильтрация заказов по поисковому запросу
  const getFilteredOrders = () => {
    const orders = activeTab === 'buyer' 
      ? buyerOrders 
      : activeTab === 'seller' 
        ? sellerOrders 
        : [...buyerOrders, ...sellerOrders];
    
    if (!searchText) return orders;
    
    return orders.filter(order => 
      order.listing_title?.toLowerCase().includes(searchText.toLowerCase()) ||
      order.id.toString().includes(searchText)
    );
  };

  // Обработчик изменения пагинации и сортировки
  const handleTableChange = (newPagination: any) => {
    if (activeTab === 'buyer') {
      fetchOrders('buyer', newPagination.current, newPagination.pageSize);
    } else if (activeTab === 'seller') {
      fetchOrders('seller', newPagination.current, newPagination.pageSize);
    } else {
      // Для вкладки "все" загружаем обе роли
      fetchOrders('buyer', newPagination.current, newPagination.pageSize);
      fetchOrders('seller', newPagination.current, newPagination.pageSize);
    }
  };

  // Обработчик нажатия на кнопку чата
  const handleChatClick = (chatId: number | null) => {
    if (!chatId) {
      message.warning('Чат недоступен для этого заказа');
      return;
    }
    
    if (onOpenChat) {
      onOpenChat(chatId);
    } else {
      // Если нет функции открытия чата, перенаправляем на страницу заказа
      // Это запасной вариант
      window.location.href = `/sales/${chatId}`;
    }
  };

  // Определение доступности чата
  const isChatAvailable = (sale: Sale) => {
    return sale.chat_id && 
      [SaleStatus.PAYMENT_PROCESSING, SaleStatus.DELIVERY_PENDING, SaleStatus.COMPLETED].includes(sale.status);
  };

  // Колонки для таблицы
  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 70,
    },
    {
      title: 'Товар',
      dataIndex: 'listing_title',
      key: 'listing_title',
      render: (text: string, record: Sale) => (
        <Link href={`/marketplace/listings/${record.listing_id}`} className="text-blue-600 hover:underline">
          {text || `Объявление #${record.listing_id}`}
        </Link>
      ),
    },
    {
      title: 'Роль',
      key: 'role',
      render: (_: unknown, record: Sale) => (
        user?.id === record.buyer_id ? (
          <Tag color="green">Покупатель</Tag>
        ) : user?.id === record.seller_id ? (
          <Tag color="blue">Продавец</Tag>
        ) : (
          <Tag>Неизвестно</Tag>
        )
      ),
    },
    {
      title: 'Цена',
      dataIndex: 'price',
      key: 'price',
      render: (price: number, record: Sale) => formatPrice(price, record.currency),
    },
    {
      title: 'Статус',
      dataIndex: 'status',
      key: 'status',
      render: (status: SaleStatus) => (
        <Tag color={statusColors[status]}>
          {statusLabels[status]}
        </Tag>
      ),
    },
    {
      title: 'Дата создания',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => format(new Date(date), 'dd.MM.yyyy HH:mm'),
    },
    {
      title: 'Действия',
      key: 'actions',
      render: (_: unknown, record: Sale) => (
        <Space>
          <Link href={`/sales/${record.id}`} passHref>
            <Button size="small" icon={<EyeOutlined />}>
              Просмотр
            </Button>
          </Link>
          
          {/* {isChatAvailable(record) && (
            <Tooltip title="Открыть чат с продавцом/покупателем">
              <Button 
                size="small" 
                type="primary"
                icon={<MessageOutlined />}
                onClick={() => handleChatClick(record.chat_id)}
              >
                Чат
              </Button>
            </Tooltip>
          )} */}
        </Space>
      ),
    },
  ];

  return (
    <div className="all-orders-list">
      <Tabs activeKey={activeTab} onChange={(key) => setActiveTab(key as 'all' | 'buyer' | 'seller')}>
        <TabPane tab="Все заказы" key="all">
          {/* Содержимое для всех заказов */}
        </TabPane>
        <TabPane tab="Я покупатель" key="buyer">
          {/* Содержимое для заказов, где пользователь - покупатель */}
        </TabPane>
        <TabPane tab="Я продавец" key="seller">
          {/* Содержимое для заказов, где пользователь - продавец */}
        </TabPane>
      </Tabs>
      
      <div className="mb-4 flex justify-between items-center">
        <div className="w-64">
          <div className="relative">
            <input
              type="text"
              placeholder="Поиск заказов..."
              className="w-full p-2 pr-10 border rounded-md"
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
            />
            <SearchOutlined className="absolute right-3 top-3 text-gray-400" />
          </div>
        </div>
      </div>
      
      {loading && getFilteredOrders().length === 0 ? (
        <div className="flex justify-center items-center py-10">
          <Spin size="large" tip="Загрузка заказов..." />
        </div>
      ) : error ? (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
          <p className="text-red-600">{error}</p>
        </div>
      ) : getFilteredOrders().length === 0 ? (
        <Empty 
          description={
            <span className="text-gray-600">
              {searchText 
                ? 'По вашему запросу ничего не найдено' 
                : 'У вас нет заказов'
              }
            </span>
          }
        />
      ) : (
        <div className="overflow-x-auto">
          <Table 
            dataSource={getFilteredOrders()} 
            columns={columns} 
            rowKey="id"
            pagination={pagination}
            onChange={handleTableChange}
            loading={loading}
            scroll={{ x: 'max-content' }}
          />
        </div>
      )}
    </div>
  );
};

export default AllOrdersList; 