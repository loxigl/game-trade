'use client';

import { useState, useEffect, useRef } from 'react';
import { useAuth } from '../hooks/auth';
import { Button, Input, Typography, Spin, message } from 'antd';
import { SendOutlined } from '@ant-design/icons';

const { TextArea } = Input;
const { Text } = Typography;

interface ChatMessage {
  id: number;
  senderId: number;
  senderName: string;
  receiverId: number;
  message: string;
  timestamp: string;
  isRead: boolean;
}

interface ChatProps {
  chatId: number;
}

export default function Chat({ chatId }: ChatProps) {
  const { user, isAuthenticated } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [messageText, setMessageText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Загрузка сообщений
  useEffect(() => {
    const loadMessages = async () => {
      if (!isAuthenticated || !user) return;

      setIsLoading(true);
      try {
        // TODO: Заменить на реальный API запрос
        // Временная заглушка для демонстрации
        const mockMessages: ChatMessage[] = [
          {
            id: 1,
            senderId: user.id,
            senderName: user.username,
            receiverId: 2,
            message: 'Здравствуйте! Меня интересует ваш товар.',
            timestamp: new Date(Date.now() - 3600000).toISOString(),
            isRead: true
          },
          {
            id: 2,
            senderId: 2,
            senderName: 'Продавец',
            receiverId: user.id,
            message: 'Добрый день! Чем могу помочь?',
            timestamp: new Date(Date.now() - 1800000).toISOString(),
            isRead: true
          }
        ];

        setMessages(mockMessages);
      } catch (error) {
        console.error('Ошибка при загрузке сообщений:', error);
        message.error('Не удалось загрузить сообщения');
      } finally {
        setIsLoading(false);
      }
    };

    loadMessages();
  }, [chatId, isAuthenticated, user]);

  // Автоматическая прокрутка к последнему сообщению
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Отправка сообщения
  const sendMessage = async () => {
    if (!messageText.trim() || !isAuthenticated || !user) return;

    setIsSending(true);
    try {
      // TODO: Заменить на реальный API запрос
      // Временная заглушка для демонстрации
      const newMessage: ChatMessage = {
        id: messages.length + 1,
        senderId: user.id,
        senderName: user.username,
        receiverId: 2, // ID продавца
        message: messageText,
        timestamp: new Date().toISOString(),
        isRead: false
      };

      setMessages(prev => [...prev, newMessage]);
      setMessageText('');

      // Симулируем ответ продавца через 2 секунды
      setTimeout(() => {
        const replyMessage: ChatMessage = {
          id: messages.length + 2,
          senderId: 2,
          senderName: 'Продавец',
          receiverId: user.id,
          message: 'Спасибо за сообщение! Я отвечу вам в ближайшее время.',
          timestamp: new Date().toISOString(),
          isRead: false
        };
        setMessages(prev => [...prev, replyMessage]);
      }, 2000);

    } catch (error) {
      console.error('Ошибка при отправке сообщения:', error);
      message.error('Не удалось отправить сообщение');
    } finally {
      setIsSending(false);
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="p-4 text-center">
        <Text type="secondary">Для использования чата необходимо авторизоваться</Text>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Spin size="large" tip="Загрузка сообщений..." />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-[500px] border rounded-lg">
      {/* Сообщения */}
      <div className="flex-grow p-4 overflow-y-auto">
        {messages.length === 0 ? (
          <div className="flex justify-center items-center h-full text-gray-400">
            <Text type="secondary">Нет сообщений</Text>
          </div>
        ) : (
          <div className="space-y-4">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex ${msg.senderId === user?.id ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[70%] p-3 rounded-lg ${
                    msg.senderId === user?.id
                      ? 'bg-blue-500 text-white rounded-br-none'
                      : 'bg-gray-100 rounded-bl-none'
                  }`}
                >
                  <div className="flex items-center mb-1">
                    <Text
                      strong
                      style={{
                        color: msg.senderId === user?.id ? 'white' : 'inherit',
                        marginRight: '8px'
                      }}
                    >
                      {msg.senderId === user?.id ? 'Вы' : msg.senderName}
                    </Text>
                    <Text
                      type="secondary"
                      style={{
                        fontSize: '0.75rem',
                        color: msg.senderId === user?.id ? 'rgba(255,255,255,0.7)' : undefined
                      }}
                    >
                      {new Date(msg.timestamp).toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit'
                      })}
                    </Text>
                  </div>
                  <div>{msg.message}</div>
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Ввод сообщения */}
      <div className="p-3 border-t">
        <div className="flex">
          <TextArea
            placeholder="Введите сообщение..."
            value={messageText}
            onChange={(e) => setMessageText(e.target.value)}
            onPressEnter={(e) => {
              if (!e.shiftKey) {
                e.preventDefault();
                sendMessage();
              }
            }}
            autoSize={{ minRows: 1, maxRows: 4 }}
            disabled={isSending}
            className="flex-grow mr-2"
          />
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={sendMessage}
            loading={isSending}
          />
        </div>
        <Text type="secondary" className="text-xs mt-1">
          Нажмите Shift+Enter для переноса строки
        </Text>
      </div>
    </div>
  );
} 