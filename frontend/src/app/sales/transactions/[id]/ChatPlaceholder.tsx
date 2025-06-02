'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Button, Space, Card, Typography, Spin, Alert } from 'antd';
import { CommentOutlined, UserOutlined } from '@ant-design/icons';
import { useAuth } from '../../../hooks/auth';
import { useChat } from '../../../hooks/useChat';
import { useUsers } from '../../../hooks/useUsers';
import ChatModal from '../../../components/ChatModal';
import { getTransactionDetails } from '../../../api/transaction';

const { Text } = Typography;

interface ChatPlaceholderProps {
  transactionId: number;
}

export default function ChatPlaceholder({ transactionId }: ChatPlaceholderProps) {
  const { user, isAuthenticated } = useAuth();
  const { connected } = useChat();
  const { getUserName, getUserAvatar, preloadUsers } = useUsers();
  const [chatModalVisible, setChatModalVisible] = useState(false);
  const [transactionDetails, setTransactionDetails] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const loadedUsersRef = useRef<boolean>(false);

  useEffect(() => {
    const fetchTransactionDetails = async () => {
      try {
        setLoading(true);
        const details = await getTransactionDetails(transactionId);
        setTransactionDetails(details);
        
        // Предзагрузка информации о пользователях
        if (details && !loadedUsersRef.current) {
          const userIds = [];
          
          if (details.transaction?.seller_id) userIds.push(details.transaction.seller_id);
          if (details.transaction?.buyer_id) userIds.push(details.transaction.buyer_id);
          if (details.seller?.id) userIds.push(details.seller.id);
          if (details.buyer?.id) userIds.push(details.buyer.id);
          
          // Если есть ID пользователей, загружаем их данные
          if (userIds.length > 0) {
            console.log('Предзагрузка пользователей в ChatPlaceholder:', userIds);
            preloadUsers(userIds)
              .then(() => { loadedUsersRef.current = true; })
              .catch(err => console.error('Ошибка загрузки данных пользователей:', err));
          }
        }
      } catch (err) {
        console.error('Ошибка получения деталей транзакции:', err);
        setError(err instanceof Error ? err.message : 'Ошибка загрузки данных');
      } finally {
        setLoading(false);
      }
    };

    if (transactionId) {
      fetchTransactionDetails();
    }
    
    // Сбрасываем флаг загрузки пользователей при размонтировании
    return () => {
      loadedUsersRef.current = false;
    };
  }, [transactionId, preloadUsers]);

  const openChat = () => {
    setChatModalVisible(true);
  };

  const closeChat = () => {
    setChatModalVisible(false);
  };

  if (!isAuthenticated) {
    return (
      <Alert
        message="Требуется авторизация"
        description="Войдите в систему для доступа к чату"
        type="warning"
        showIcon
      />
    );
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '200px' }}>
        <Spin size="large" tip="Загрузка информации о чате..." />
      </div>
    );
  }

  if (error) {
    return (
      <Alert
        message="Ошибка загрузки"
        description={error}
        type="error"
        showIcon
      />
    );
  }

  // Извлекаем данные для чата из транзакции
  const { transaction, sale, seller, buyer } = transactionDetails || {};
  const listingId = transaction?.listing_id || sale?.listing_id;
  const sellerId = transaction?.seller_id || sale?.seller_id;
  const buyerId = transaction?.buyer_id || sale?.buyer_id;

  // Получаем имена пользователей
  const sellerName = seller?.username || getUserName(sellerId);
  const buyerName = buyer?.username || getUserName(buyerId);

  if (!listingId || !sellerId || !buyerId) {
    return (
      <Alert
        message="Недостаточно данных"
        description="Не удалось определить участников чата для данной транзакции"
        type="warning"
        showIcon
      />
    );
  }

  return (
    <div style={{ padding: '16px' }}>
      <Card 
        title={
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <CommentOutlined />
            <span>Чат по транзакции</span>
          </div>
        }
        style={{ textAlign: 'center' }}
      >
        <div style={{ marginBottom: '16px' }}>
          <Text type="secondary">
            Общение между покупателем и продавцом по объявлению #{listingId}
          </Text>
        </div>
        
        <div style={{ marginBottom: '16px' }}>
          <Space direction="vertical" size="small">
            <div>
              <UserOutlined /> <Text strong>Продавец:</Text> {sellerName}
            </div>
            <div>
              <UserOutlined /> <Text strong>Покупатель:</Text> {buyerName}
            </div>
          </Space>
        </div>

        <div style={{ marginBottom: '16px' }}>
          <Text type="secondary" style={{ fontSize: '12px' }}>
            Статус подключения: {connected ? '🟢 Подключен' : '🔴 Не подключен'}
          </Text>
        </div>
        
        <Button 
          type="primary" 
          icon={<CommentOutlined />}
          onClick={openChat}
          size="large"
          disabled={!connected}
        >
          Открыть чат
        </Button>
        
        {!connected && (
          <div style={{ marginTop: '8px' }}>
            <Text type="secondary" style={{ fontSize: '12px' }}>
              Ожидание подключения к серверу чатов...
            </Text>
          </div>
        )}
      </Card>

      {/* Модальное окно чата */}
      <ChatModal
        visible={chatModalVisible}
        onClose={closeChat}
        transactionId={transactionId}
        sellerId={sellerId}
        buyerId={buyerId}
        title={`Чат по транзакции #${transactionId}`}
      />
    </div>
  );
} 