'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Input, Button, Spin, List, Avatar, message } from 'antd';
import { SendOutlined, UserOutlined } from '@ant-design/icons';
import { useAuth } from '../hooks/auth';
import { format } from 'date-fns';

// Заглушка для API чата (в дальнейшем заменить на реальные API)
const chatApi = {
  getMessages: async (transactionId: number) => {
    // Имитация задержки запроса
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    // Заглушка с тестовыми данными
    return [
      {
        id: 1,
        senderId: 1,
        recipientId: 2,
        senderName: 'Продавец',
        content: 'Здравствуйте! Спасибо за покупку. Готов ответить на любые вопросы по товару.',
        timestamp: new Date(Date.now() - 86400000).toISOString() // Вчерашняя дата
      },
      {
        id: 2,
        senderId: 2,
        recipientId: 1,
        senderName: 'Покупатель',
        content: 'Добрый день! Когда примерно будет доставка?',
        timestamp: new Date(Date.now() - 43200000).toISOString() // 12 часов назад
      },
      {
        id: 3,
        senderId: 1,
        recipientId: 2,
        senderName: 'Продавец',
        content: 'Отправил сегодня. Трек-номер пришлю вечером.',
        timestamp: new Date(Date.now() - 21600000).toISOString() // 6 часов назад
      }
    ];
  },
  
  sendMessage: async (transactionId: number, senderId: number, recipientId: number, content: string) => {
    // Имитация задержки запроса
    await new Promise(resolve => setTimeout(resolve, 800));
    
    // Заглушка успешного ответа
    return {
      id: Date.now(),
      senderId,
      recipientId,
      senderName: 'Вы',
      content,
      timestamp: new Date().toISOString()
    };
  }
};

interface ChatComponentProps {
  transactionId: number;
  recipientId?: number;
  recipientName?: string;
}

interface Message {
  id: number;
  senderId: number;
  recipientId: number;
  senderName: string;
  content: string;
  timestamp: string;
}

const ChatComponent: React.FC<ChatComponentProps> = ({ 
  transactionId, 
  recipientId,
  recipientName = 'Собеседник'
}) => {
  const { user } = useAuth();
  const [messages, setMessages] = useState<Message[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  // Загрузка истории сообщений
  useEffect(() => {
    const fetchMessages = async () => {
      try {
        setLoading(true);
        const fetchedMessages = await chatApi.getMessages(transactionId);
        setMessages(fetchedMessages);
      } catch (error) {
        console.error('Ошибка при загрузке сообщений:', error);
        message.error('Не удалось загрузить историю сообщений');
      } finally {
        setLoading(false);
      }
    };
    
    fetchMessages();
    
    // В реальном приложении здесь можно настроить веб-сокеты для получения новых сообщений
  }, [transactionId]);
  
  // Прокрутка вниз при новых сообщениях
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);
  
  // Отправка нового сообщения
  const handleSendMessage = async () => {
    if (!newMessage.trim() || !user || !recipientId) return;
    
    try {
      setSending(true);
      const sentMessage = await chatApi.sendMessage(
        transactionId,
        user.id,
        recipientId,
        newMessage.trim()
      );
      
      setMessages([...messages, sentMessage]);
      setNewMessage('');
    } catch (error) {
      console.error('Ошибка при отправке сообщения:', error);
      message.error('Не удалось отправить сообщение');
    } finally {
      setSending(false);
    }
  };
  
  // Обработка нажатия Enter
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };
  
  // Определение, является ли сообщение отправленным текущим пользователем
  const isOwnMessage = (senderId: number) => {
    return user?.id === senderId;
  };
  
  if (loading) {
    return (
      <div className="flex justify-center py-10">
        <Spin size="large" />
      </div>
    );
  }
  
  return (
    <div className="chat-component">
      <div className="chat-header mb-4 pb-2 border-b">
        <h3 className="font-medium">Чат с {recipientName}</h3>
        <p className="text-sm text-gray-500">ID транзакции: {transactionId}</p>
      </div>
      
      <div className="chat-messages mb-4 overflow-y-auto" style={{ maxHeight: '350px' }}>
        {messages.length === 0 ? (
          <div className="text-center py-8 text-gray-500">
            Сообщений пока нет. Начните общение!
          </div>
        ) : (
          <List
            itemLayout="horizontal"
            dataSource={messages}
            renderItem={(item) => (
              <List.Item 
                className={`${isOwnMessage(item.senderId) ? 'justify-end' : 'justify-start'}`}
              >
                <div 
                  className={`
                    max-w-xs sm:max-w-md rounded-lg px-4 py-2 mb-1
                    ${isOwnMessage(item.senderId) 
                      ? 'bg-blue-500 text-white ml-auto' 
                      : 'bg-gray-100 text-gray-800 mr-auto'}
                  `}
                >
                  <div className="font-medium text-sm mb-1">
                    {isOwnMessage(item.senderId) ? 'Вы' : item.senderName}
                  </div>
                  <div>{item.content}</div>
                  <div className={`text-xs mt-1 text-right ${isOwnMessage(item.senderId) ? 'text-blue-100' : 'text-gray-500'}`}>
                    {format(new Date(item.timestamp), 'dd.MM.yyyy HH:mm')}
                  </div>
                </div>
              </List.Item>
            )}
          />
        )}
        <div ref={messagesEndRef} />
      </div>
      
      <div className="chat-input">
        <div className="flex">
          <Input.TextArea
            value={newMessage}
            onChange={(e) => setNewMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Введите сообщение..."
            autoSize={{ minRows: 1, maxRows: 4 }}
            disabled={sending}
            className="flex-grow"
          />
          <Button 
            type="primary" 
            icon={<SendOutlined />} 
            onClick={handleSendMessage} 
            loading={sending}
            disabled={!newMessage.trim()}
            className="ml-2 flex items-center"
          >
            Отправить
          </Button>
        </div>
        <div className="text-xs text-gray-500 mt-1">
          Нажмите Enter для отправки, Shift+Enter для переноса строки
        </div>
      </div>
    </div>
  );
};

export default ChatComponent; 