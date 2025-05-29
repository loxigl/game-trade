import { useState, useEffect, useCallback, useRef } from 'react';
import { message } from 'antd';
import { useAuth } from './auth';
import { 
  chatApi, 
  ChatWebSocket, 
  getOrCreateListingChat, 
  getOrCreateTransactionChat 
} from '../api/chat';
import { 
  Chat, 
  Message, 
  MessageCreateRequest, 
  ChatType 
} from '../types/chat';

interface UseChatReturn {
  chats: Chat[];
  activeChat: Chat | null;
  messages: Message[];
  loading: boolean;
  messagesLoading: boolean;
  sendingMessage: boolean;
  typingUsers: Set<number>;
  connected: boolean;
  totalUnreadCount: number;
  loadChats: () => Promise<void>;
  openChat: (chat: Chat) => Promise<void>;
  closeChat: () => void;
  sendMessage: (content: string) => Promise<void>;
  sendTyping: (isTyping: boolean) => void;
  openListingChat: (listingId: number, sellerId: number) => Promise<Chat | null>;
  openTransactionChat: (transactionId: number, sellerId: number, buyerId: number) => Promise<Chat | null>;
  subscribeToNotifications: (callback: (message: Message) => void) => () => void;
  connect: () => Promise<void>;
  fetchAndJoinAllChats: () => Promise<void>;
}

interface UseChatOptions {
  onNewMessage?: (message: Message) => void;
}

export function useChat(options: UseChatOptions = {}): UseChatReturn {
  const { user, getAuthHeader } = useAuth();
  const [chats, setChats] = useState<Chat[]>([]);
  const [activeChat, setActiveChat] = useState<Chat | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [messagesLoading, setMessagesLoading] = useState(false);
  const [sendingMessage, setSendingMessage] = useState(false);
  const [typingUsers, setTypingUsers] = useState<Set<number>>(new Set());
  
  const wsRef = useRef<ChatWebSocket | null>(null);
  const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Инициализация WebSocket подключения
  useEffect(() => {
    const authHeader = getAuthHeader();
    if (!authHeader || !user?.id) {
      console.log('No auth header or user, skipping WebSocket initialization');
      return;
    }

    // Предотвращаем создание нескольких подключений
    if (wsRef.current) {
      console.log('WebSocket already initialized, skipping');
      return;
    }

    // Извлекаем токен из Bearer токена
    const token = authHeader.replace('Bearer ', '');
    console.log('Инициализация WebSocket с токеном:', token ? 'токен получен' : 'токен отсутствует');
    
    const ws = new ChatWebSocket(token);
    wsRef.current = ws;

    // Подписываемся на события WebSocket
    ws.on('new_message', handleNewMessage);
    ws.on('message_updated', handleMessageUpdated);
    ws.on('message_deleted', handleMessageDeleted);
    ws.on('typing', handleTyping);
    ws.on('user_joined', handleUserJoined);
    ws.on('user_left', handleUserLeft);
    ws.on('error', handleWSError);

    // Подключаемся к WebSocket
    ws.connect().then(() => {
      console.log('WebSocket подключение установлено');
    }).catch(error => {
      console.error('Ошибка подключения к WebSocket:', error);
      message.error('Не удалось подключиться к чату');
    });

    // Пинг для поддержания соединения
    const pingInterval = setInterval(() => {
      if (ws.connected) {
        ws.ping();
      }
    }, 30000);

    return () => {
      console.log('Cleanup WebSocket connection');
      clearInterval(pingInterval);
      if (wsRef.current) {
        wsRef.current.disconnect();
        wsRef.current = null;
      }
    };
  }, [user?.id]); // Только user.id в зависимостях

  // Обработчики WebSocket событий
  const handleNewMessage = useCallback((messageData: Message) => {
    console.log('useChat: Received new message:', messageData);
    
    setMessages(prev => {
      // Проверяем, не дублируется ли сообщение
      const exists = prev.find(msg => msg.id === messageData.id);
      if (exists) return prev;
      
      return [...prev, messageData];
    });

    // Обновляем информацию о чате
    setChats(prev => prev.map(chat => {
      if (chat.id === messageData.chat_id) {
        const isActiveChat = activeChat?.id === messageData.chat_id;
        console.log(`Updating chat ${chat.id}, isActiveChat: ${isActiveChat}`);
        
        return { 
          ...chat, 
          last_message: messageData.content.substring(0, 100),
          // Увеличиваем unread_count только если это не активный чат
          unread_count: isActiveChat ? 0 : (chat.unread_count || 0) + 1
        };
      }
      return chat;
    }));

    // Вызываем callback для уведомлений через глобальный обработчик
    if (messageData.sender_id !== user?.id) {
      // Эмитим событие для уведомлений
      window.dispatchEvent(new CustomEvent('newChatMessage', { 
        detail: messageData 
      }));
    }
  }, [user?.id, activeChat?.id]);

  const handleMessageUpdated = useCallback((messageData: Message) => {
    setMessages(prev => prev.map(msg => 
      msg.id === messageData.id ? messageData : msg
    ));
  }, []);

  const handleMessageDeleted = useCallback((data: { message_id: number; chat_id: number }) => {
    setMessages(prev => prev.filter(msg => msg.id !== data.message_id));
  }, []);

  const handleTyping = useCallback((data: { user_id: number; chat_id: number; is_typing: boolean }) => {
    if (activeChat?.id === data.chat_id && data.user_id !== user?.id) {
      setTypingUsers(prev => {
        const newSet = new Set(prev);
        if (data.is_typing) {
          newSet.add(data.user_id);
        } else {
          newSet.delete(data.user_id);
        }
        return newSet;
      });

      // Автоматически убираем статус печатания через 3 секунды
      if (data.is_typing) {
        if (typingTimeoutRef.current) {
          clearTimeout(typingTimeoutRef.current);
        }
        typingTimeoutRef.current = setTimeout(() => {
          setTypingUsers(prev => {
            const newSet = new Set(prev);
            newSet.delete(data.user_id);
            return newSet;
          });
        }, 3000);
      }
    }
  }, [activeChat?.id, user?.id]);

  const handleUserJoined = useCallback((data: { user_id: number; chat_id: number }) => {
    console.log(`Пользователь ${data.user_id} присоединился к чату ${data.chat_id}`);
  }, []);

  const handleUserLeft = useCallback((data: { user_id: number; chat_id: number }) => {
    console.log(`Пользователь ${data.user_id} покинул чат ${data.chat_id}`);
  }, []);

  const handleWSError = useCallback((data: { message: string }) => {
    console.error('WebSocket ошибка:', data.message);
    message.error(`Ошибка чата: ${data.message}`);
  }, []);

  // Загрузка списка чатов
  const loadChats = useCallback(async () => {
    if (!user) return;

    setLoading(true);
    try {
      const response = await chatApi.getChats({ page_size: 50 });
      setChats(response.chats);
    } catch (error) {
      console.error('Ошибка загрузки чатов:', error);
      message.error('Не удалось загрузить чаты');
    } finally {
      setLoading(false);
    }
  }, [user]);

  // Загрузка сообщений чата
  const loadMessages = useCallback(async (chatId: number) => {
    // Добавляем проверку, чтобы не загружать сообщения повторно, если они уже загружаются
    if (messagesLoading) return;
    
    setMessagesLoading(true);
    try {
      const response = await chatApi.getMessages(chatId, { page_size: 100 });
      setMessages(response.messages);
      
      // Отмечаем сообщения как прочитанные только если чат активен
      if (activeChat?.id === chatId) {
        await chatApi.markAsRead(chatId);
        
        // Обновляем счетчик непрочитанных в локальном состоянии
        setChats(prev => prev.map(chat => 
          chat.id === chatId ? { ...chat, unread_count: 0 } : chat
        ));
      }
    } catch (error) {
      console.error('Ошибка загрузки сообщений:', error);
      message.error('Не удалось загрузить сообщения');
    } finally {
      setMessagesLoading(false);
    }
  }, [messagesLoading, activeChat?.id]);

  // Открытие чата
  const openChat = useCallback(async (chat: Chat) => {
    // Если уже открыт этот же чат, не делаем ничего
    if (activeChat?.id === chat.id) return;
    
    setActiveChat(chat);
    await loadMessages(chat.id);
    
    // Подписываемся на чат через WebSocket
    if (wsRef.current?.connected) {
      wsRef.current.joinChat(chat.id);
    }
  }, [loadMessages, activeChat?.id]);

  // Закрытие чата
  const closeChat = useCallback(() => {
    if (activeChat && wsRef.current?.connected) {
      wsRef.current.leaveChat(activeChat.id);
    }
    
    setActiveChat(null);
    setMessages([]);
    setTypingUsers(new Set());
  }, [activeChat]);

  // Отправка сообщения
  const sendMessage = useCallback(async (content: string) => {
    if (!activeChat || !content.trim()) return;

    setSendingMessage(true);
    try {
      const messageData: MessageCreateRequest = {
        content: content.trim(),
        type: 'text' as any
      };

      await chatApi.sendMessage(activeChat.id, messageData);
      
      // Обновляем preview сообщения в списке чатов
      setChats(prev => prev.map(chat => 
        chat.id === activeChat.id 
          ? { 
              ...chat, 
              last_message: content.substring(0, 100)
            }
          : chat
      ));
      
      // Сообщение придет через WebSocket и будет добавлено автоматически
    } catch (error) {
      console.error('Ошибка отправки сообщения:', error);
      message.error('Не удалось отправить сообщение');
    } finally {
      setSendingMessage(false);
    }
  }, [activeChat]);

  // Отправка уведомления о печатании
  const sendTyping = useCallback((isTyping: boolean) => {
    if (activeChat && wsRef.current?.connected) {
      wsRef.current.sendTyping(activeChat.id, isTyping);
    }
  }, [activeChat]);

  // Создание или открытие чата для объявления
  const openListingChat = useCallback(async (listingId: number, sellerId: number) => {
    if (!user) {
      message.error('Необходимо авторизоваться');
      return null;
    }

    setLoading(true);
    try {
      const chat = await getOrCreateListingChat(listingId, sellerId);
      
      // Добавляем чат в список, если его там нет
      setChats(prev => {
        const exists = prev.find(c => c.id === chat.id);
        if (exists) return prev;
        return [chat, ...prev];
      });
      
      await openChat(chat);
      return chat;
    } catch (error) {
      console.error('Ошибка открытия чата объявления:', error);
      message.error('Не удалось открыть чат');
      return null;
    } finally {
      setLoading(false);
    }
  }, [user, openChat]);

  // Создание или открытие чата для транзакции
  const openTransactionChat = useCallback(async (transactionId: number, sellerId: number, buyerId: number) => {
    if (!user) {
      message.error('Необходимо авторизоваться');
      return null;
    }
    
    // Проверяем, существует ли уже чат с таким transactionId
    const existingChat = chats.find(chat => 
      chat.type === 'completion' && chat.transaction_id === transactionId
    );
    
    if (existingChat) {
      await openChat(existingChat);
      return existingChat;
    }

    setLoading(true);
    try {
      const chat = await getOrCreateTransactionChat(transactionId, sellerId, buyerId);
      
      // Добавляем чат в список, если его там нет
      setChats(prev => {
        const exists = prev.find(c => c.id === chat.id);
        if (exists) return prev;
        return [chat, ...prev];
      });
      
      await openChat(chat);
      return chat;
    } catch (error) {
      console.error('Ошибка открытия чата транзакции:', error);
      message.error('Не удалось открыть чат');
      return null;
    } finally {
      setLoading(false);
    }
  }, [user, openChat, chats]);

  // Загрузка чатов при инициализации (только один раз при монтировании)
  useEffect(() => {
    if (user) {
      loadChats();
    }
  }, [user?.id]); // Используем только user.id вместо всего объекта user

  const subscribeToNotifications = useCallback((callback: (message: Message) => void) => {
    const unsubscribe = () => {
      // Implementation of unsubscribe
    };
    return unsubscribe;
  }, []);

  // Метод для ручного установления соединения
  const connect = useCallback(async () => {
    const authHeader = getAuthHeader();
    if (!authHeader || !user?.id) {
      console.log('No auth header or user, cannot connect');
      return;
    }

    // Если уже подключено, не делаем ничего
    if (wsRef.current?.connected) {
      console.log('WebSocket already connected');
      return;
    }

    // Если соединение уже создано, но не подключено
    if (wsRef.current) {
      try {
        await wsRef.current.connect();
        console.log('WebSocket reconnected');
      } catch (error) {
        console.error('Error reconnecting WebSocket:', error);
        message.error('Не удалось переподключиться к чату');
      }
      return;
    }

    // Если соединение не создано, создаем новое
    const token = authHeader.replace('Bearer ', '');
    console.log('Manual WebSocket initialization with token:', token ? 'token received' : 'token missing');
    
    const ws = new ChatWebSocket(token);
    wsRef.current = ws;

    // Подписываемся на события WebSocket
    ws.on('new_message', handleNewMessage);
    ws.on('message_updated', handleMessageUpdated);
    ws.on('message_deleted', handleMessageDeleted);
    ws.on('typing', handleTyping);
    ws.on('user_joined', handleUserJoined);
    ws.on('user_left', handleUserLeft);
    ws.on('error', handleWSError);

    try {
      await ws.connect();
      console.log('WebSocket connected manually');
    } catch (error) {
      console.error('Error manually connecting WebSocket:', error);
      message.error('Не удалось подключиться к чату');
    }
  }, [getAuthHeader, user?.id, handleNewMessage, handleMessageUpdated, handleMessageDeleted, handleTyping, handleUserJoined, handleUserLeft, handleWSError]);

  // Метод для загрузки и подключения ко всем чатам пользователя
  const fetchAndJoinAllChats = useCallback(async () => {
    if (!user) return;
    
    // Загружаем чаты, если еще не загружены
    if (chats.length === 0) {
      await loadChats();
    }
    
    // Если WebSocket не подключен, подключаем
    if (!wsRef.current?.connected) {
      await connect();
    }
    
    // Подписываемся на все чаты
    if (wsRef.current?.connected && chats.length > 0) {
      console.log(`Subscribing to ${chats.length} chats`);
      for (const chat of chats) {
        wsRef.current.joinChat(chat.id);
        console.log(`Joined chat ${chat.id}`);
      }
    }
  }, [user, chats, loadChats, connect]);

  return {
    // Состояние
    chats,
    activeChat,
    messages,
    loading,
    messagesLoading,
    sendingMessage,
    typingUsers,
    connected: wsRef.current?.connected || false,

    // Методы
    loadChats,
    openChat,
    closeChat,
    sendMessage,
    sendTyping,
    openListingChat,
    openTransactionChat,
    subscribeToNotifications,
    connect,
    fetchAndJoinAllChats,

    // Вычисляемые свойства
    totalUnreadCount: chats.reduce((sum, chat) => sum + (chat.unread_count || 0), 0)
  };
} 