'use client';

import React from 'react';
import { Tabs, Card, Button, message } from 'antd';
import { FileTextOutlined } from '@ant-design/icons';
import TransactionList from './components/TransactionList';
import Link from 'next/link';
import { useAuth } from '../hooks/auth';
import { useRouter } from 'next/navigation';

export default function TransactionsPage() {
  const { isAuthenticated, user, isLoading } = useAuth();
  const router = useRouter();
  
  // Редирект неавторизованных пользователей
  React.useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      message.error('Для просмотра транзакций необходимо авторизоваться');
      router.push('/login');
    }
  }, [isAuthenticated, isLoading, router]);

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8 flex justify-center items-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-700 mx-auto mb-4"></div>
          <p>Загрузка...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated || !user) {
    return null; // Редирект обработан в useEffect
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Мои транзакции</h1>
        <Link href="/transactions/reports">
          <Button icon={<FileTextOutlined />} type="primary">
            Отчеты
          </Button>
        </Link>
      </div>
      
      <Card>
        <Tabs
          defaultActiveKey="purchases"
          items={[
            {
              key: 'purchases',
              label: 'Мои покупки',
              children: <TransactionList userId={user.id} isSellerView={false} />
            },
            {
              key: 'sales',
              label: 'Мои продажи',
              children: <TransactionList userId={user.id} isSellerView={true} />
            }
          ]}
        />
      </Card>
    </div>
  );
} 