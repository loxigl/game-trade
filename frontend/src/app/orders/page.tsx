'use client';

import React, { useState } from 'react';
import { Breadcrumb, Card, Drawer, Button } from 'antd';
import { HomeOutlined, ShoppingOutlined, CloseOutlined } from '@ant-design/icons';
import Link from 'next/link';
import AllOrdersList from '../components/AllOrdersList';
import ChatWidget from '../../components/chat/ChatWidget';
import { useAuth } from '../hooks/auth';

const OrdersPage: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth();
  const [chatDrawerVisible, setChatDrawerVisible] = useState(false);
  const [activeChatId, setActiveChatId] = useState<number | null>(null);

  // Обработчик для открытия чата
  const handleOpenChat = (chatId: number) => {
    setActiveChatId(chatId);
    setChatDrawerVisible(true);
  };

  // Закрытие чата
  const handleCloseChat = () => {
    setChatDrawerVisible(false);
  };

  // Показываем загрузку, пока проверяется аутентификация
  if (isLoading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  // Если пользователь не аутентифицирован, показываем сообщение
  if (!isAuthenticated) {
    return (
      <div className="container mx-auto py-8 px-4">
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center">
          <h2 className="text-lg font-semibold text-yellow-800 mb-2">Необходима авторизация</h2>
          <p className="text-yellow-600 mb-4">Для просмотра ваших заказов необходимо войти в систему.</p>
          <Link href="/login" passHref>
            <Button type="primary">Войти</Button>
          </Link>
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
        <Breadcrumb.Item>
          <ShoppingOutlined /> Мои заказы
        </Breadcrumb.Item>
      </Breadcrumb>
      
      <h1 className="text-2xl font-bold mb-6">Мои заказы</h1>
      
      <Card className="shadow-sm">
        <AllOrdersList onOpenChat={handleOpenChat} />
      </Card>
      
      {/* Боковая панель для чата */}
      <Drawer
        title={
          <div className="flex justify-between items-center">
            <span>Чат по заказу</span>
            <Button
              type="text"
              icon={<CloseOutlined />}
              onClick={handleCloseChat}
              className="p-0 flex items-center justify-center"
            />
          </div>
        }
        placement="right"
        closable={false}
        onClose={handleCloseChat}
        open={chatDrawerVisible}
        width={380}
        bodyStyle={{ padding: 0 }}
      >
        {activeChatId && <ChatWidget chatId={activeChatId} />}
      </Drawer>
    </div>
  );
};

export default OrdersPage; 