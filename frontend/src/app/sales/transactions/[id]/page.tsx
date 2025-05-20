'use client';

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Card, Button, Alert, Row, Col, Breadcrumb, Spin, Tabs, Divider } from 'antd';
import { HomeOutlined, ArrowLeftOutlined, ShoppingOutlined, CommentOutlined, InfoCircleOutlined, TeamOutlined } from '@ant-design/icons';
import { useAuth } from '../../../hooks/auth';
import Link from 'next/link';
import { getTransactionDetails } from '../../../api/transaction';
import { salesApi } from '../../../utils/api';

// Импортируем компоненты
import TransactionDetails from './TransactionDetails';
import ChatPlaceholder from './ChatPlaceholder';

const { TabPane } = Tabs;

export default function TransactionDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { user, isAuthenticated } = useAuth();
  
  // Безопасное извлечение id из параметров
  const id = params?.id as string;
  const transactionId = id ? parseInt(id) : 0;
  
  const [saleData, setSaleData] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [activeKey, setActiveKey] = useState<string>('details');

  useEffect(() => {
    const fetchRelatedData = async () => {
      try {
        setLoading(true);
        // Получаем детальную информацию о транзакции, включая связанные данные
        const details = await getTransactionDetails(transactionId);
        
        // Если в ответе есть информация о связанной продаже, храним её
        if (details?.sale) {
          setSaleData(details.sale);
        }
        // Если в ответе нет информации о продаже, но есть ID продажи в extra_data транзакции
        else if (details?.transaction?.extra_data?.sale_id) {
          try {
            const saleId = details.transaction.extra_data.sale_id;
            const saleDetails = await salesApi.getSale(saleId);
            setSaleData(saleDetails);
          } catch (saleErr) {
            console.error("Ошибка при получении информации о продаже:", saleErr);
          }
        }
      } catch (err) {
        console.error("Ошибка при получении связанных данных:", err);
        setError(err instanceof Error ? err.message : 'Ошибка загрузки данных');
      } finally {
        setLoading(false);
      }
    };

    if (transactionId) {
      fetchRelatedData();
    }
  }, [transactionId]);

  if (!isAuthenticated) {
    return (
      <Alert
        message="Требуется авторизация"
        description="Пожалуйста, войдите в систему для просмотра деталей транзакции"
        type="error"
        showIcon
        action={
          <Button type="primary" onClick={() => router.push('/login')}>
            Войти
          </Button>
        }
      />
    );
  }
  
  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '400px' }}>
        <Spin size="large" tip="Загрузка данных транзакции..." />
      </div>
    );
  }

  // Связанный ID продажи
  const saleId = saleData?.id;

  const handleTabChange = (key: string) => {
    setActiveKey(key);
  };

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '24px' }}>
      {/* Хлебные крошки */}
      <Breadcrumb style={{ marginBottom: '16px' }}>
        <Breadcrumb.Item>
          <Link href="/">
            <HomeOutlined /> Главная
          </Link>
        </Breadcrumb.Item>
        <Breadcrumb.Item>
          <Link href="/sales">
            <ShoppingOutlined /> Продажи
          </Link>
        </Breadcrumb.Item>
        {saleId && (
          <Breadcrumb.Item>
            <Link href={`/sales/${saleId}`}>
              Сделка #{saleId}
            </Link>
          </Breadcrumb.Item>
        )}
        <Breadcrumb.Item>Транзакция #{transactionId}</Breadcrumb.Item>
      </Breadcrumb>

      {/* Кнопка Назад и заголовок */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <h1 style={{ fontSize: '24px', fontWeight: 'bold', margin: 0 }}>Детали транзакции #{transactionId}</h1>
        {saleId && (
          <Button 
            onClick={() => router.push(`/sales/${saleId}`)} 
            icon={<ArrowLeftOutlined />}
          >
            Вернуться к сделке
          </Button>
        )}
      </div>
      
      {/* Десктоп версия: 2 колонки (Детали + Чат) */}
      <div className="desktop-view" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
        <Card
          className="transaction-tabs"
          bodyStyle={{ padding: 0 }}
        >
          <Tabs 
            activeKey={activeKey} 
            onChange={handleTabChange}
            tabPosition="top"
            type="card"
            style={{ padding: '16px' }}
            items={[
              {
                key: 'details',
                label: <span><InfoCircleOutlined /> Детали</span>,
                children: <TransactionDetails transactionId={transactionId} />
              },
              {
                key: 'chat',
                label: <span><CommentOutlined /> Чат</span>,
                children: <div style={{ padding: '16px' }}><ChatPlaceholder transactionId={transactionId} /></div>
              }
            ]}
          />
        </Card>
      </div>
    </div>
  );
} 