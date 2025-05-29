'use client';

import React, { createContext, useContext, useCallback, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useNotifications } from '../hooks/useNotifications';
import { useChat } from '../hooks/useChat';
import { useAuth } from '../hooks/auth';
import type { Notification } from '../components/NotificationCenter';
import { Message } from '../types/chat';

interface NotificationContextType {
  notifications: Notification[];
  loading: boolean;
  unreadCount: number;
  markAsRead: (notificationId: string) => void;
  markAllAsRead: () => void;
  deleteNotification: (notificationId: string) => void;
  handleNotificationClick: (notification: Notification) => void;
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

export function NotificationProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { user } = useAuth();
  const {
    notifications,
    loading,
    unreadCount,
    markAsRead,
    markAllAsRead,
    deleteNotification,
    addNotification
  } = useNotifications();

  // Инициализируем chat hook сразу
  const chat = useChat();

  // Обработчик новых сообщений для создания уведомлений
  const handleNewMessage = useCallback((message: Message) => {
    console.log('NotificationContext: Received new message:', message);
    console.log('NotificationContext: Current user ID:', user?.id);
    console.log('NotificationContext: Message sender ID:', message.sender_id);
    
    // Создаем уведомление только если сообщение не от текущего пользователя
    if (message.sender_id !== user?.id) {
      console.log('NotificationContext: Creating notification for message from another user');
      addNotification({
        type: 'message',
        title: 'Новое сообщение',
        message: message.content.length > 100 
          ? `${message.content.substring(0, 100)}...` 
          : message.content,
        chatId: message.chat_id,
        messageId: message.id,
        senderId: message.sender_id,
        timestamp: message.created_at,
        read: false,
        metadata: {
          chatTitle: `Чат #${message.chat_id}`
        }
      });
      console.log('NotificationContext: Notification created');
    } else {
      console.log('NotificationContext: Skipping notification for own message');
    }
  }, [addNotification, user?.id]);

  // Принудительно инициализируем соединение с WebSocket при загрузке компонента
  useEffect(() => {
    if (user?.id && !chat.connected) {
      console.log('NotificationContext: Initializing chat connection');
      chat.connect();
    }
  }, [user?.id, chat]);

  // Подписываемся на глобальное событие новых сообщений
  useEffect(() => {
    const handleCustomEvent = (event: CustomEvent<Message>) => {
      handleNewMessage(event.detail);
    };

    // Добавляем слушатель только когда есть пользователь
    if (user?.id) {
      console.log('NotificationContext: Subscribing to newChatMessage events');
      window.addEventListener('newChatMessage', handleCustomEvent as EventListener);
      
      return () => {
        console.log('NotificationContext: Unsubscribing from newChatMessage events');
        window.removeEventListener('newChatMessage', handleCustomEvent as EventListener);
      };
    }
  }, [user?.id, handleNewMessage]);

  // Логируем состояние подключения
  useEffect(() => {
    console.log('NotificationContext: Chat connected:', chat.connected);
    
    // Если соединение установлено, запрашиваем список чатов для автоматического присоединения
    if (chat.connected && user?.id) {
      console.log('NotificationContext: Fetching and joining all user chats');
      // Здесь можно добавить логику для загрузки и присоединения ко всем чатам пользователя
      chat.fetchAndJoinAllChats();
    }
  }, [chat.connected, user?.id]);

  // Обработчик клика по уведомлению
  const handleNotificationClick = useCallback((notification: Notification) => {
    console.log('NotificationContext: Notification clicked:', notification);
    if (notification.chatId) {
      // Переходим на страницу чатов и открываем нужный чат
      router.push(`/chats?openChat=${notification.chatId}`);
    }
  }, [router]);

  return (
    <NotificationContext.Provider
      value={{
        notifications,
        loading,
        unreadCount,
        markAsRead,
        markAllAsRead,
        deleteNotification,
        handleNotificationClick
      }}
    >
      {children}
    </NotificationContext.Provider>
  );
}

export function useNotificationContext() {
  const context = useContext(NotificationContext);
  if (context === undefined) {
    throw new Error('useNotificationContext must be used within a NotificationProvider');
  }
  return context;
} 