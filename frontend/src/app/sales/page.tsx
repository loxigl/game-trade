'use client';

import React, { useState, useEffect } from 'react';
import { Tabs, Card, Breadcrumb, Spin, Result, Button, Flex } from 'antd';
import { 
  ShoppingOutlined, 
  ClockCircleOutlined, 
  HistoryOutlined, 
  BarChartOutlined,
  HomeOutlined
} from '@ant-design/icons';
import SalesStatistics from './components/SalesStatistics';
import SalesList from './components/SalesList';
import ActiveUserListings from './components/ActiveUserListings';
import PendingSales from './components/PendingSales';
import TransactionHistory from './components/TransactionHistory';
import CreateListingButton from './components/CreateListingButton';
import Link from 'next/link';
import { useAuth } from '../hooks/auth';
import { useRouter } from 'next/navigation';
import { useSales } from '../hooks/sale';
import { Sale, SaleStatus } from '../types/sale';
import formatPrice from '../utils/formatPrice';

const { TabPane } = Tabs;

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
  [SaleStatus.PENDING]: 'bg-yellow-100 text-yellow-800',
  [SaleStatus.PAYMENT_PROCESSING]: 'bg-blue-100 text-blue-800',
  [SaleStatus.DELIVERY_PENDING]: 'bg-purple-100 text-purple-800',
  [SaleStatus.COMPLETED]: 'bg-green-100 text-green-800',
  [SaleStatus.CANCELED]: 'bg-red-100 text-red-800',
  [SaleStatus.REFUNDED]: 'bg-gray-100 text-gray-800',
  [SaleStatus.DISPUTED]: 'bg-orange-100 text-orange-800',
};

type Role = 'buyer' | 'seller';

const SalesPage: React.FC = () => {
  const [activeKey, setActiveKey] = useState('statistics');
  const { user, isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  const { getUserSales, loading, error } = useSales();
  const [sales, setSales] = useState<Sale[]>([]);
  const [role, setRole] = useState<Role>('buyer');
  const [status, setStatus] = useState<SaleStatus | 'all'>('all');
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  
  // Проверяем, имеет ли пользователь роль продавца
  const hasSellerRole = user?.roles?.includes('seller') || user?.roles?.includes('admin');
  
  // Загрузка продаж
  useEffect(() => {
    const loadSales = async () => {
      if (!isAuthenticated || !hasSellerRole) return;
      
      try {
        const response = await getUserSales(role, status === 'all' ? undefined : status, page);
        setSales(response.items);
        setTotalPages(response.pages);
      } catch (err) {
        console.error('Ошибка при загрузке продаж:', err);
      }
    };

    loadSales();
  }, [role, status, page, getUserSales, isAuthenticated, hasSellerRole]);
  
  // Редирект, если пользователь не авторизован или не имеет доступа
  useEffect(() => {
    if (!isLoading && (!isAuthenticated || !hasSellerRole)) {
      router.push('/access-denied');
    }
  }, [isLoading, isAuthenticated, hasSellerRole, router]);

  const handleRoleChange = (newRole: Role) => {
    setRole(newRole);
    setPage(1);
  };

  const handleStatusChange = (newStatus: SaleStatus | 'all') => {
    setStatus(newStatus);
    setPage(1);
  };
  
  // Показываем спиннер во время загрузки
  if (isLoading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <Spin size="large" tip="Загрузка..." />
      </div>
    );
  }
  
  // Показываем сообщение об отказе в доступе, если пользователь не имеет роли продавца
  if (!isLoading && !hasSellerRole) {
    return (
      <Result
        status="403"
        title="Нет доступа"
        subTitle="У вас нет прав для доступа к этой странице. Необходимо иметь статус продавца."
        extra={
          <Button type="primary" onClick={() => router.push('/')}>
            Вернуться на главную
          </Button>
        }
      />
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <h2 className="text-lg font-semibold text-red-800">Ошибка</h2>
          <p className="text-red-600">{error}</p>
        </div>
      </div>
    );
  }
  
  return (
    <div className="container mx-auto py-6 px-4">
      <Breadcrumb className="mb-6">
        <Breadcrumb.Item>
          <Link href="/" passHref>
            <HomeOutlined /> Главная
          </Link>
        </Breadcrumb.Item>
        <Breadcrumb.Item>Мои продажи</Breadcrumb.Item>
      </Breadcrumb>
      
      <Flex justify="space-between" align="center" className="mb-6">
        <h1 className="text-2xl font-bold">Мои продажи</h1>
        <CreateListingButton />
      </Flex>
      
      <Card className="sales-container shadow-sm">
        <Tabs activeKey={activeKey} onChange={setActiveKey}>
          <TabPane 
            tab={
              <span>
                <BarChartOutlined /> Статистика
              </span>
            } 
            key="statistics"
          >
            <SalesStatistics />
          </TabPane>
          
          <TabPane 
            tab={
              <span>
                <ShoppingOutlined /> Активные объявления
              </span>
            } 
            key="active"
          >
            <ActiveUserListings status="active" />
          </TabPane>
          
          <TabPane 
            tab={
              <span>
                <ClockCircleOutlined /> Ожидающие подтверждения
              </span>
            } 
            key="pending"
          >
            <PendingSales />
          </TabPane>
          
          <TabPane 
            tab={
              <span>
                <HistoryOutlined /> История транзакций
              </span>
            } 
            key="history"
          >
            <TransactionHistory />
          </TabPane>
          
          <TabPane 
            tab={
              <span>
                <ShoppingOutlined /> Завершенные продажи
              </span>
            } 
            key="sold"
          >
            <ActiveUserListings status="sold" />
          </TabPane>
        </Tabs>
      </Card>
    </div>
  );
};

export default SalesPage; 