'use client';

import React, { useState, useEffect, useRef } from 'react';
import {
  Modal,
  Input,
  Button,
  List,
  Avatar,
  Typography,
  Spin,
  Space,
  Divider,
  message as messageNotification,
  Badge,
  Empty
} from 'antd';
import {
  SendOutlined,
  UserOutlined,
  MessageOutlined,
  EllipsisOutlined
} from '@ant-design/icons';
import { formatChatTime } from '../utils/date';
import { useChat } from '../hooks/useChat';
import { useAuth } from '../hooks/auth';
import { Chat, Message } from '../types/chat';
import { useUsers } from '../hooks/useUsers';

const { TextArea } = Input;
const { Text, Title } = Typography;

interface ChatModalProps {
  visible: boolean;
  onClose: () => void;
  chat?: Chat | null;
  listingId?: number;
  sellerId?: number;
  transactionId?: number;
  buyerId?: number;
  title?: string;
}

export default function ChatModal({
  visible,
  onClose,
  chat: initialChat,
  listingId,
  sellerId,
  transactionId,
  buyerId,
  title
}: ChatModalProps) {
  const { user } = useAuth();
  const {
    activeChat,
    messages,
    messagesLoading,
    sendingMessage,
    typingUsers,
    connected,
    openChat,
    closeChat,
    sendMessage,
    sendTyping,
    openListingChat,
    openTransactionChat
  } = useChat();
  const { getUserName, getUserAvatar, preloadUsers } = useUsers();

  const [newMessage, setNewMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const lastTypingTime = useRef<number>(0);
  const loadedParticipantsRef = useRef<boolean>(false);
  const loadedMessagesRef = useRef<boolean>(false);
  
  // Используем ref для отслеживания предыдущих значений и предотвращения циклических вызовов
  const prevPropsRef = useRef({
    visible: false,
    initialChat: null as Chat | null,
    listingId: undefined as number | undefined,
    sellerId: undefined as number | undefined,
    transactionId: undefined as number | undefined,
    buyerId: undefined as number | undefined
  });

  // Автопрокрутка к концу сообщений
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Прокрутка при загрузке новых сообщений или открытии чата
  useEffect(() => {
    if (visible && messages.length > 0) {
      // Небольшая задержка для рендеринга сообщений
      setTimeout(scrollToBottom, 100);
    }
  }, [visible, messages.length]);

  // Прокрутка при добавлении нового сообщения
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Обработка URL параметра для автоматического открытия чата
  useEffect(() => {
    const prevProps = prevPropsRef.current;
    
    // Проверяем, действительно ли изменились нужные нам пропсы
    const propsChanged = 
      prevProps.visible !== visible ||
      prevProps.initialChat?.id !== (initialChat?.id || null) ||
      prevProps.listingId !== listingId ||
      prevProps.sellerId !== sellerId ||
      prevProps.transactionId !== transactionId ||
      prevProps.buyerId !== buyerId;

    if (!propsChanged) {
      return;
    }

    // Обновляем предыдущие значения
    prevPropsRef.current = {
      visible,
      initialChat: initialChat || null,
      listingId,
      sellerId,
      transactionId,
      buyerId
    };

    if (visible) {
      console.log('Открытие модального окна чата с параметрами:', {
        initialChat: initialChat?.id,
        listingId,
        sellerId, 
        transactionId,
        buyerId
      });
      
      if (initialChat) {
        openChat(initialChat);
      } else if (listingId && sellerId) {
        openListingChat(listingId, sellerId);
      } else if (transactionId && sellerId && buyerId) {
        openTransactionChat(transactionId, sellerId, buyerId);
      }
    } else {
      closeChat();
    }
  }, [
    visible, 
    initialChat?.id, 
    listingId, 
    sellerId, 
    transactionId, 
    buyerId,
    openChat,
    closeChat,
    openListingChat,
    openTransactionChat
  ]);

  // Предзагрузка информации о пользователях чата (только при первой загрузке)
  useEffect(() => {
    if (activeChat?.participants && 
        activeChat.participants.length > 0 && 
        !loadedParticipantsRef.current) {
      // Получаем ID участников
      const participantIds = activeChat.participants
        .filter(p => p.user_id && p.user_id > 0)
        .map(p => p.user_id);
      
      if (participantIds.length > 0) {
        console.log('Предзагрузка участников чата:', participantIds);
        preloadUsers(participantIds).catch(err => {
          console.error('Ошибка предзагрузки участников чата:', err);
        });
        loadedParticipantsRef.current = true;
      }
    }
  }, [activeChat?.participants, preloadUsers]);

  // Предзагрузка информации о пользователях, которые пишут сообщения (только если загрузились новые сообщения)
  useEffect(() => {
    if (messages.length > 0 && !loadedMessagesRef.current) {
      // Собираем уникальные ID пользователей из сообщений
      const senderIds = Array.from(
        new Set(
          messages
            .map(msg => msg.sender_id)
            .filter(id => id && id > 0) as number[]
        )
      );
      
      if (senderIds.length > 0) {
        console.log('Предзагрузка отправителей сообщений:', senderIds);
        preloadUsers(senderIds).catch(err => {
          console.error('Ошибка предзагрузки отправителей сообщений:', err);
        });
        loadedMessagesRef.current = true;
      }
    }
  }, [messages, preloadUsers]);
  
  // Предзагрузка участников в чате при видимом диалоге и при каждом изменении списка пользователей, печатающих сообщения
  useEffect(() => {
    if (visible && typingUsers.size > 0) {
      const typingUserIds = Array.from(typingUsers);
      if (typingUserIds.length > 0) {
        console.log('Предзагрузка печатающих пользователей:', typingUserIds);
        preloadUsers(typingUserIds).catch(err => {
          console.error('Ошибка предзагрузки печатающих пользователей:', err);
        });
      }
    }
  }, [visible, typingUsers, preloadUsers]);

  // Сброс флагов загрузки при закрытии чата
  useEffect(() => {
    if (!visible) {
      loadedParticipantsRef.current = false;
      loadedMessagesRef.current = false;
    }
  }, [visible]);

  const handleSendMessage = async () => {
    if (!newMessage.trim()) return;

    try {
      await sendMessage(newMessage);
      setNewMessage('');
      setIsTyping(false);
      sendTyping(false);
    } catch (error) {
      console.error('Ошибка отправки сообщения:', error);
    }
  };

  const handleTyping = (value: string) => {
    setNewMessage(value);
    
    const now = Date.now();
    lastTypingTime.current = now;
    
    if (!isTyping) {
      setIsTyping(true);
      sendTyping(true);
    }
    
    // Прекращаем отправку typing через 3 секунды
    setTimeout(() => {
      if (Date.now() - lastTypingTime.current >= 3000 && isTyping) {
        setIsTyping(false);
        sendTyping(false);
      }
    }, 3000);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // Заменяем функцию на импортированную из утилит
  const formatMessageTime = (timestamp: string) => {
    return formatChatTime(timestamp);
  };

  // Получаем имя пользователя из участников чата
  const getUserNameFromChat = (userId: number) => {
    if (!userId || userId <= 0) {
      return 'Система';
    }
    
    // Используем хук useUsers для получения имени пользователя
    return getUserName(userId);
  };

  // Определяем, является ли сообщение от текущего пользователя
  const isMyMessage = (message: Message) => {
    return message.sender_id === user?.id;
  };

  // Генерируем цвет аватара на основе ID пользователя
  const getAvatarColor = (userId: number) => {
    if (!userId || userId <= 0) {
      return '#cccccc'; // Серый цвет для неизвестных пользователей
    }
    
    const colors = ['#f56a00', '#7265e6', '#ffbf00', '#00a2ae', '#87d068', '#108ee9', '#722ed1', '#eb2f96'];
    return colors[userId % colors.length];
  };

  // Показываем кто печатает
  const renderTypingIndicator = () => {
    if (typingUsers.size === 0) return null;
    
    // Получаем имена пользователей с более дружественными названиями
    const typingUserNames = Array.from(typingUsers).map(userId => {
      const name = getUserNameFromChat(userId);
      
      // Если имя включает ID пользователя (формат "Пользователь #123"),
      // заменяем на более дружественное название
      if (name.includes(`#${userId}`)) {
        if (userId === user?.id) {
          return 'Вы';
        } else if (activeChat?.type === 'completion' && userId === buyerId) {
          return 'Покупатель';
        } else if (activeChat?.type === 'completion' && userId === sellerId) {
          return 'Продавец';
        }
      }
      
      return name;
    });
    
    return (
      <div style={{ 
        padding: '12px 20px', 
        display: 'flex',
        alignItems: 'center',
        gap: '8px',
        animation: 'fadeIn 0.3s ease-in-out'
      }}>
        <div style={{
          display: 'flex',
          gap: '2px'
        }}>
          <div style={{
            width: '6px',
            height: '6px',
            backgroundColor: '#1890ff',
            borderRadius: '50%',
            animation: 'typing-dot 1.4s infinite ease-in-out'
          }} />
          <div style={{
            width: '6px',
            height: '6px',
            backgroundColor: '#1890ff',
            borderRadius: '50%',
            animation: 'typing-dot 1.4s infinite ease-in-out 0.2s'
          }} />
          <div style={{
            width: '6px',
            height: '6px',
            backgroundColor: '#1890ff',
            borderRadius: '50%',
            animation: 'typing-dot 1.4s infinite ease-in-out 0.4s'
          }} />
        </div>
        <Text type="secondary" style={{ fontSize: '13px', fontStyle: 'italic' }}>
          {typingUserNames.join(', ')} печатает...
        </Text>
      </div>
    );
  };

  // Получение заголовка модального окна
  const getModalTitle = () => {
    if (title) return title;
    
    if (activeChat) {
      if (activeChat.title) {
        return activeChat.title;
      } else if (activeChat.type === 'listing') {
        return `Чат по объявлению #${activeChat.listing_id}`;
      } else if (activeChat.type === 'completion') {
        return `Чат по транзакции #${activeChat.transaction_id}`;
      }
    }
    
    return 'Чат';
  };

  // Функция для отладки времени (временная функция)
  const getDebugTimeInfo = (timestamp: string) => {
    if (!timestamp) return '';
    
    const utcDate = new Date(timestamp + 'Z'); // Принудительно UTC
    const localDate = new Date(timestamp);     // Локальная интерпретация
    
    return `
      Исходная строка: ${timestamp}
      UTC: ${utcDate.toLocaleString()}
      Локальное: ${localDate.toLocaleString()}
      Ваша зона: UTC${-new Date().getTimezoneOffset() / 60}
    `;
  };

  // Cleanup effect при размонтировании
  useEffect(() => {
    return () => {
      if (lastTypingTime.current) {
        clearTimeout(lastTypingTime.current);
      }
    };
  }, []);

  return (
    <>
      <style jsx>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        
        @keyframes typing-dot {
          0%, 80%, 100% { transform: scale(0.8); opacity: 0.5; }
          40% { transform: scale(1); opacity: 1; }
        }
        
        @keyframes slideInMessage {
          from { opacity: 0; transform: translateY(10px) scale(0.95); }
          to { opacity: 1; transform: translateY(0) scale(1); }
        }
        
        .message-item {
          animation: slideInMessage 0.3s ease-out;
        }
        
        .message-bubble {
          transition: all 0.2s ease;
        }
        
        .message-bubble:hover {
          transform: translateY(-1px);
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }
        
        .messages-container {
          background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        }
        
        .chat-header {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          padding: 16px 24px;
          border-radius: 8px 8px 0 0;
          margin: -24px -24px 0 -24px;
        }
        
        .input-container {
          background: white;
          border-radius: 12px;
          padding: 4px;
          border: 2px solid #f0f0f0;
          transition: border-color 0.3s ease;
        }
        
        .input-container:focus-within {
          border-color: #1890ff;
          box-shadow: 0 0 0 2px rgba(24, 144, 255, 0.1);
        }
        
        .send-button {
          border-radius: 8px !important;
          height: 40px !important;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
          border: none !important;
        }
        
        .send-button:hover {
          background: linear-gradient(135deg, #5a67d8 0%, #6b46c1 100%) !important;
          transform: translateY(-1px);
          box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3) !important;
        }
      `}</style>
      
      <Modal
        title={null}
        open={visible}
        onCancel={onClose}
        footer={null}
        width={750}
        style={{ top: 20 }}
        styles={{
          body: { padding: 0 },
          header: { display: 'none' }
        }}
      >
        {/* Кастомный заголовок */}
        <div className="chat-header">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <Title level={4} style={{ color: 'white', margin: 0, fontSize: '18px' }}>
                <MessageOutlined style={{ marginRight: '8px' }} />
                {getModalTitle()}
              </Title>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <Badge 
                status={connected ? 'success' : 'error'} 
                text={<span style={{ color: 'white', fontSize: '12px' }}>
                  {connected ? 'В сети' : 'Не в сети'}
                </span>}
              />
            </div>
          </div>
        </div>

        <div style={{ height: '520px', display: 'flex', flexDirection: 'column', padding: '20px' }}>
          {/* Область сообщений */}
          <div className="messages-container" style={{ 
            flex: 1, 
            overflowY: 'auto', 
            padding: '20px', 
            borderRadius: '16px',
            marginBottom: '20px',
            border: '1px solid #e8e8e8'
          }}>
            {messagesLoading ? (
              <div style={{ 
                textAlign: 'center', 
                padding: '80px 20px',
                background: 'rgba(255, 255, 255, 0.8)',
                borderRadius: '12px'
              }}>
                <Spin size="large" tip="Загрузка сообщений..." />
              </div>
            ) : messages.length === 0 ? (
              <div style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                height: '100%',
                background: 'rgba(255, 255, 255, 0.8)',
                borderRadius: '12px',
                padding: '40px'
              }}>
                <Empty 
                  description={
                    <Text style={{ color: '#666', fontSize: '16px' }}>
                      Начните общение - отправьте первое сообщение
                    </Text>
                  }
                  image={<MessageOutlined style={{ fontSize: '48px', color: '#d9d9d9' }} />}
                />
              </div>
            ) : (
              <>
                <List
                  dataSource={messages}
                  renderItem={(message) => {
                    const isMy = isMyMessage(message);
                    const senderId = message.sender_id || 0;
                    const avatarUrl = senderId > 0 ? getUserAvatar(senderId) : undefined;
                    
                    // Улучшаем получение имени пользователя
                    let userName = 'Система';
                    if (senderId > 0) {
                      // Пытаемся получить имя пользователя
                      userName = getUserNameFromChat(senderId);
                      
                      // Если имя включает ID пользователя (формат "Пользователь #123"),
                      // значит реальное имя не найдено, заменяем на более дружественное
                      if (userName.includes(`#${senderId}`)) {
                        if (isMy) {
                          userName = 'Вы';
                        } else if (activeChat?.type === 'completion' && senderId === buyerId) {
                          userName = 'Покупатель';
                        } else if (activeChat?.type === 'completion' && senderId === sellerId) {
                          userName = 'Продавец';
                        }
                      }
                    }
                    
                    return (
                      <List.Item 
                        className="message-item"
                        style={{ 
                          padding: '8px 0', 
                          borderBottom: 'none',
                          display: 'flex',
                          justifyContent: isMy ? 'flex-end' : 'flex-start'
                        }}
                      >
                        <div style={{ 
                          maxWidth: '70%',
                          display: 'flex',
                          flexDirection: 'column',
                          alignItems: isMy ? 'flex-end' : 'flex-start'
                        }}>
                          {!isMy && (
                            <div style={{ 
                              display: 'flex', 
                              alignItems: 'center', 
                              gap: '8px',
                              marginBottom: '6px'
                            }}>
                              <Avatar 
                                icon={<UserOutlined />} 
                                src={avatarUrl}
                                size="small"
                                style={{ 
                                  backgroundColor: avatarUrl ? 'transparent' : getAvatarColor(senderId),
                                  border: '2px solid white',
                                  boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
                                }}
                              />
                              <Text strong style={{ fontSize: '13px', color: '#666' }}>
                                {userName}
                              </Text>
                            </div>
                          )}
                          
                          <div className="message-bubble" style={{ 
                            background: isMy 
                              ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
                              : 'white',
                            color: isMy ? 'white' : '#333',
                            padding: '12px 16px',
                            borderRadius: isMy ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
                            fontSize: '14px',
                            lineHeight: '1.4',
                            border: isMy ? 'none' : '1px solid #e8e8e8',
                            boxShadow: isMy 
                              ? '0 2px 8px rgba(102, 126, 234, 0.3)'
                              : '0 2px 8px rgba(0, 0, 0, 0.1)',
                            wordBreak: 'break-word'
                          }}>
                            {message.content || ''}
                          </div>
                          
                          <Text 
                            type="secondary" 
                            style={{ 
                              fontSize: '11px',
                              marginTop: '4px',
                              color: '#999'
                            }}
                            title={getDebugTimeInfo(message.created_at)}
                          >
                            {formatMessageTime(message.created_at)}
                          </Text>
                        </div>
                      </List.Item>
                    );
                  }}
                />
                {renderTypingIndicator()}
                <div ref={messagesEndRef} />
              </>
            )}
          </div>

          {/* Поле ввода */}
          <div className="input-container" style={{ display: 'flex', gap: '8px', alignItems: 'flex-end' }}>
            <TextArea
              value={newMessage}
              onChange={(e) => handleTyping(e.target.value)}
              onPressEnter={handleKeyPress}
              placeholder="Напишите сообщение..."
              autoSize={{ minRows: 1, maxRows: 4 }}
              disabled={sendingMessage || !connected}
              style={{ 
                flex: 1,
                border: 'none',
                boxShadow: 'none',
                resize: 'none',
                fontSize: '14px',
                padding: '12px'
              }}
              variant="borderless"
            />
            <Button
              className="send-button"
              type="primary"
              icon={<SendOutlined />}
              loading={sendingMessage}
              disabled={!newMessage.trim() || !connected}
              onClick={handleSendMessage}
              style={{ margin: '4px' }}
            >
              Отправить
            </Button>
          </div>

          <div style={{ 
            marginTop: '12px', 
            fontSize: '12px', 
            color: '#999',
            textAlign: 'center',
            padding: '8px',
            background: 'rgba(0, 0, 0, 0.02)',
            borderRadius: '8px'
          }}>
            💡 Enter для отправки, Shift+Enter для новой строки
          </div>
        </div>
      </Modal>
    </>
  );
}