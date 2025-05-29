'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { notification as antNotification } from 'antd';
import { useAuth } from './auth';
import { useChat } from './useChat';
import type { Notification } from '../components/NotificationCenter';

interface UseNotificationsReturn {
  notifications: Notification[];
  loading: boolean;
  unreadCount: number;
  markAsRead: (notificationId: string) => void;
  markAllAsRead: () => void;
  deleteNotification: (notificationId: string) => void;
  addNotification: (notification: Omit<Notification, 'id'>) => void;
}

const STORAGE_KEY = 'chat_notifications';
const MAX_NOTIFICATIONS = 50;

export function useNotifications(): UseNotificationsReturn {
  const { user, isAuthenticated } = useAuth();
  const { connected } = useChat();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(false);
  const notificationSound = useRef<HTMLAudioElement | null>(null);

  // Загружаем уведомления из localStorage при инициализации
  useEffect(() => {
    if (isAuthenticated && user) {
      setLoading(true);
      try {
        const stored = localStorage.getItem(`${STORAGE_KEY}_${user.id}`);
        console.log('Loading notifications from localStorage:', stored);
        if (stored) {
          const parsed = JSON.parse(stored) as Notification[];
          console.log('Parsed notifications:', parsed);
          setNotifications(parsed);
        } else {
          console.log('No stored notifications found');
          setNotifications([]); // Явно устанавливаем пустой массив
        }
      } catch (error) {
        console.error('Ошибка загрузки уведомлений:', error);
        setNotifications([]); // При ошибке устанавливаем пустой массив
      } finally {
        setLoading(false);
      }
    } else {
      setNotifications([]); // Очищаем уведомления если пользователь не авторизован
    }
  }, [isAuthenticated, user?.id]); // Используем user?.id для более точного отслеживания

  // Сохраняем уведомления в localStorage при изменении
  useEffect(() => {
    if (isAuthenticated && user && notifications.length >= 0) { // Сохраняем даже пустой массив
      try {
        console.log('Saving notifications to localStorage:', notifications);
        localStorage.setItem(`${STORAGE_KEY}_${user.id}`, JSON.stringify(notifications));
      } catch (error) {
        console.error('Ошибка сохранения уведомлений:', error);
      }
    }
  }, [notifications, isAuthenticated, user?.id]);

  // Инициализируем звук уведомлений
  useEffect(() => {
    // Создаем аудио элемент для звука уведомлений
    notificationSound.current = new Audio('/sounds/notification.mp3');
    notificationSound.current.volume = 0.5;
    
    return () => {
      if (notificationSound.current) {
        notificationSound.current = null;
      }
    };
  }, []);

  // Добавляем новое уведомление
  const addNotification = useCallback((notificationData: Omit<Notification, 'id'>) => {
    console.log('Adding new notification:', notificationData);
    
    const newNotification: Notification = {
      ...notificationData,
      id: `notification_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    };

    console.log('Created notification with ID:', newNotification.id);

    setNotifications(prev => {
      console.log('Previous notifications:', prev);
      // Добавляем новое уведомление в начало списка
      const updated = [newNotification, ...prev];
      console.log('Updated notifications:', updated);
      
      // Ограничиваем количество уведомлений
      const final = updated.slice(0, MAX_NOTIFICATIONS);
      console.log('Final notifications array:', final);
      return final;
    });

    // Показываем браузерное уведомление, если разрешено
    if (typeof window !== 'undefined' && 'Notification' in window && window.Notification.permission === 'granted') {
      try {
        const browserNotification = new window.Notification(notificationData.title, {
          body: notificationData.message,
          icon: '/favicon.ico',
          badge: '/favicon.ico',
          tag: newNotification.id
        });

        // Автоматически закрываем уведомление через 5 секунд
        setTimeout(() => {
          browserNotification.close();
        }, 5000);
      } catch (error) {
        console.error('Ошибка показа браузерного уведомления:', error);
      }
    }

    // Воспроизводим звук
    if (notificationSound.current) {
      try {
        notificationSound.current.play().catch(error => {
          console.debug('Не удалось воспроизвести звук уведомления:', error);
        });
      } catch (error) {
        console.debug('Ошибка воспроизведения звука:', error);
      }
    }

    // Показываем антд уведомление
    antNotification.info({
      message: notificationData.title,
      description: notificationData.message,
      placement: 'topRight',
      duration: 4
    });
  }, []);

  // Отмечаем уведомление как прочитанное
  const markAsRead = useCallback((notificationId: string) => {
    setNotifications(prev => 
      prev.map(notification => 
        notification.id === notificationId 
          ? { ...notification, read: true }
          : notification
      )
    );
  }, []);

  // Отмечаем все уведомления как прочитанные
  const markAllAsRead = useCallback(() => {
    setNotifications(prev => 
      prev.map(notification => ({ ...notification, read: true }))
    );
  }, []);

  // Удаляем уведомление
  const deleteNotification = useCallback((notificationId: string) => {
    setNotifications(prev => 
      prev.filter(notification => notification.id !== notificationId)
    );
  }, []);

  // Запрашиваем разрешение на показ браузерных уведомлений
  useEffect(() => {
    if (isAuthenticated && typeof window !== 'undefined' && 'Notification' in window && window.Notification.permission === 'default') {
      window.Notification.requestPermission().then(permission => {
        console.log('Notification permission:', permission);
      }).catch(error => {
        console.debug('Пользователь отклонил разрешение на уведомления:', error);
      });
    }
  }, [isAuthenticated]);

  const unreadCount = notifications.filter(n => !n.read).length;

  return {
    notifications,
    loading,
    unreadCount,
    markAsRead,
    markAllAsRead,
    deleteNotification,
    addNotification
  };
} 