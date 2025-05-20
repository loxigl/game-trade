'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Table, Tag, Button, Input, Space, Spin, Empty, message, Pagination, Tabs } from 'antd';
import { SearchOutlined, FilterOutlined, SortAscendingOutlined, SortDescendingOutlined, EyeOutlined } from '@ant-design/icons';
import Link from 'next/link';
import { useAuth } from '../../hooks/auth';
import { format } from 'date-fns';
import { getAllSales } from '../../api/market';

const { TabPane } = Tabs;

interface AllOrdersListProps {
  role?: 'seller' | 'buyer';
}

const AllOrdersList: React.FC<AllOrdersListProps> = ({ role = 'seller' }) => {
  const { user } = useAuth();
  const [orders, setOrders] = useState<any[]>([]);
  const [filteredOrders, setFilteredOrders] = useState<any[]>([]);
  const [status, setStatus] = useState<string | undefined>(undefined);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchText, setSearchText] = useState('');
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 10,
    total: 0
  });
  const [activeTab, setActiveTab] = useState(role === 'seller' ? 'seller' : 'buyer');
  
  // Получение списка заказов
  const fetchOrders = useCallback(async (page = 1, pageSize = 10) => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await getAllSales(
        status,
        page,
        pageSize,
        activeTab === 'seller'
      );
      
      setOrders(response.items);
      setFilteredOrders(response.items);
      setPagination({
        current: response.page,
        pageSize: response.size,
        total: response.total
      });
    } catch (err) {
      console.error('Ошибка при получении заказов:', err);
      setError('Не удалось загрузить список заказов.');
    } finally {
      setLoading(false);
    }
  }, [status, activeTab]);
  
  // Загружаем заказы при изменении параметров
  useEffect(() => {
    fetchOrders();
  }, [fetchOrders]);
  
  // Обработка изменения поискового запроса
  useEffect(() => {
    if (searchText) {
      const filtered = orders.filter(order => 
        order.listingTitle?.toLowerCase().includes(searchText.toLowerCase())
      );
      setFilteredOrders(filtered);
    } else {
      setFilteredOrders(orders);
    }
  }, [searchText, orders]);
  
  // Обработчик изменения статуса
  const handleStatusChange = (newStatus: string | undefined) => {
    setStatus(newStatus);
  };
  
  // Обработчик изменения пагинации
  const handlePaginationChange = (page: number, pageSize?: number) => {
    fetchOrders(page, pageSize || pagination.pageSize);
  };
  
  // Обработчик изменения вкладки (роли)
  const handleTabChange = (key: string) => {
    setActiveTab(key);
  };
  
  // Форматирование цены
  const formatPrice = (price: number, currency: string) => {
    switch (currency) {
      case 'USD':
        return `$${price}`;
      case 'EUR':
        return `€${price}`;
      case 'RUB':
        return `${price} ₽`;
      default:
        return `${price} ${currency}`;
    }
  };
  
  // Отображение статуса
  const renderStatus = (status: string) => {
    switch (status) {
      case 'pending':
        return <Tag color="orange">Ожидание оплаты</Tag>;
      case 'payment_processing':
        return <Tag color="blue">Обработка оплаты</Tag>;
      case 'delivery_pending':
        return <Tag color="purple">Ожидание доставки</Tag>;
      case 'completed':
        return <Tag color="green">Завершено</Tag>;
      case 'canceled':
        return <Tag color="red">Отменено</Tag>;
      case 'disputed':
        return <Tag color="volcano">Спор</Tag>;
      default:
        return <Tag>{status}</Tag>;
    }
  };
  
  // Определение колонок таблицы
  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 70,
    },
    {
      title: 'Название товара',
      dataIndex: 'listingTitle',
      key: 'listingTitle',
      render: (text: string, record: any) => (
        <Link href={`/marketplace/listings/${record.listingId}`} className="text-blue-600 hover:underline">
          {text}
        </Link>
      ),
    },
    {
      title: activeTab === 'seller' ? 'Покупатель' : 'Продавец',
      dataIndex: activeTab === 'seller' ? 'buyerName' : 'sellerName',
      key: 'counterparty',
    },
    {
      title: 'Цена',
      dataIndex: 'price',
      key: 'price',
      render: (price: number, record: any) => formatPrice(price, record.currency),
    },
    {
      title: 'Статус',
      dataIndex: 'status',
      key: 'status',
      render: renderStatus,
    },
    {
      title: 'Дата создания',
      dataIndex: 'createdAt',
      key: 'createdAt',
      render: (date: string) => format(new Date(date), 'dd.MM.yyyy HH:mm'),
    },
    {
      title: 'Действия',
      key: 'actions',
      render: (_: unknown, record: any) => (
        <Space>
          <Link href={`/sales/transactions/${record.id}`} passHref>
            <Button size="small" icon={<EyeOutlined />}>
              Детали
            </Button>
          </Link>
        </Space>
      ),
    },
  ];
  
  return (
    <div className="orders-list">
      <Tabs activeKey={activeTab} onChange={handleTabChange} className="mb-4">
        <TabPane tab="Мои продажи" key="seller" />
        <TabPane tab="Мои покупки" key="buyer" />
      </Tabs>
      
      <div className="mb-4 flex justify-between items-center">
        <div>
          <h2 className="text-xl font-semibold">
            {activeTab === 'seller' ? 'Мои продажи' : 'Мои покупки'}
          </h2>
        </div>
        <div className="flex gap-2">
          <Input
            placeholder="Поиск по названию"
            prefix={<SearchOutlined />}
            value={searchText}
            onChange={e => setSearchText(e.target.value)}
            style={{ width: 200 }}
          />
        </div>
      </div>
      
      <div className="mb-4">
        <Space>
          <Button 
            type={status === undefined ? 'primary' : 'default'} 
            onClick={() => handleStatusChange(undefined)}
          >
            Все
          </Button>
          <Button 
            type={status === 'pending' ? 'primary' : 'default'} 
            onClick={() => handleStatusChange('pending')}
          >
            Ожидание оплаты
          </Button>
          <Button 
            type={status === 'delivery_pending' ? 'primary' : 'default'} 
            onClick={() => handleStatusChange('delivery_pending')}
          >
            Ожидание доставки
          </Button>
          <Button 
            type={status === 'completed' ? 'primary' : 'default'} 
            onClick={() => handleStatusChange('completed')}
          >
            Завершенные
          </Button>
          <Button 
            type={status === 'disputed' ? 'primary' : 'default'} 
            onClick={() => handleStatusChange('disputed')}
          >
            Споры
          </Button>
        </Space>
      </div>
      
      {loading && (
        <div className="flex justify-center py-10">
          <Spin size="large" />
        </div>
      )}
      
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}
      
      {!loading && filteredOrders.length === 0 && (
        <Empty 
          description={`У вас пока нет ${activeTab === 'seller' ? 'продаж' : 'покупок'}`} 
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      )}
      
      {filteredOrders.length > 0 && (
        <>
          <Table 
            columns={columns} 
            dataSource={filteredOrders} 
            rowKey="id"
            pagination={false}
          />
          
          <div className="mt-4 flex justify-end">
            <Pagination
              current={pagination.current}
              pageSize={pagination.pageSize}
              total={pagination.total}
              onChange={handlePaginationChange}
              showSizeChanger
              showTotal={(total) => `Всего ${total} ${activeTab === 'seller' ? 'продаж' : 'покупок'}`}
            />
          </div>
        </>
      )}
    </div>
  );
};

export default AllOrdersList; 