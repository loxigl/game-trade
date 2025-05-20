'use client';

import React, { useState } from 'react';
import { Card, Input, Button, Avatar, List, Typography, Empty, Divider, Badge } from 'antd';
import { SendOutlined, UserOutlined, CommentOutlined, PaperClipOutlined, SmileOutlined } from '@ant-design/icons';

const { TextArea } = Input;
const { Title, Text } = Typography;

interface ChatPlaceholderProps {
  transactionId: number;
  recipientName?: string;
}

const ChatPlaceholder: React.FC<ChatPlaceholderProps> = ({ transactionId, recipientName = "Продавец" }) => {
  const [message, setMessage] = useState('');
  
  // Заглушка - демонстрационные сообщения
  const mockMessages = [
    {
      id: 1,
      sender: 'seller',
      senderName: recipientName,
      content: 'Здравствуйте! Благодарю за покупку. Если у вас есть вопросы по товару, я с радостью отвечу.',
      timestamp: new Date(Date.now() - 3600000 * 24).toISOString()
    },
    {
      id: 2,
      sender: 'buyer',
      senderName: 'Вы',
      content: 'Добрый день! Подскажите, когда примерно будет доставка?',
      timestamp: new Date(Date.now() - 3600000 * 12).toISOString()
    },
    {
      id: 3,
      sender: 'seller',
      senderName: recipientName,
      content: 'Отправим завтра, доставка займет 2-3 дня. Я сообщу вам трек-номер, как только отправим.',
      timestamp: new Date(Date.now() - 3600000 * 10).toISOString()
    }
  ];

  const handleSendMessage = () => {
    if (message.trim()) {
      // Здесь будет логика отправки сообщения после реализации чата
      console.log(`Отправка сообщения: ${message}`);
      setMessage('');
    }
  };

  // Форматирование даты для сообщений
  const formatMessageDate = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleString('ru-RU', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <Card 
      title={
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <Badge dot status="success" className="mr-2" />
            <span>Чат по сделке</span>
          </div>
          <div>
            <Badge count={3} style={{ backgroundColor: '#52c41a' }} />
          </div>
        </div>
      }
      className="chat-card h-full"
      style={{ display: 'flex', flexDirection: 'column', height: '100%' }}
      bodyStyle={{ flex: 1, display: 'flex', flexDirection: 'column', padding: '12px', overflow: 'hidden' }}
      bordered={true}
    >
      <div 
        style={{ 
          flex: 1, 
          overflowY: 'auto', 
          marginBottom: '12px', 
          display: 'flex',
          flexDirection: 'column'
        }}
      >
        {mockMessages.length > 0 ? (
          <List
            itemLayout="horizontal"
            dataSource={mockMessages}
            style={{ width: '100%' }}
            renderItem={item => (
              <List.Item style={{ 
                padding: '4px 0',
                display: 'flex', 
                justifyContent: item.sender === 'buyer' ? 'flex-end' : 'flex-start',
                border: 'none'
              }}>
                <div 
                  style={{ 
                    display: 'flex',
                    flexDirection: item.sender === 'buyer' ? 'row-reverse' : 'row',
                    maxWidth: '80%',
                    alignItems: 'flex-start'
                  }}
                >
                  <Avatar 
                    icon={<UserOutlined />} 
                    style={{ 
                      backgroundColor: item.sender === 'buyer' ? '#1890ff' : '#52c41a',
                      margin: item.sender === 'buyer' ? '0 0 0 8px' : '0 8px 0 0',
                      flexShrink: 0
                    }} 
                  />
                  <div 
                    style={{ 
                      padding: '10px 14px',
                      borderRadius: '12px',
                      background: item.sender === 'buyer' ? '#e6f7ff' : '#f0f2f5',
                      position: 'relative',
                      boxShadow: '0 1px 2px rgba(0,0,0,0.1)'
                    }}
                  >
                    <Text strong style={{ display: 'block', marginBottom: '4px' }}>
                      {item.senderName}
                    </Text>
                    <div style={{ wordBreak: 'break-word' }}>{item.content}</div>
                    <Text type="secondary" style={{ fontSize: '11px', display: 'block', marginTop: '4px', textAlign: 'right' }}>
                      {formatMessageDate(item.timestamp)}
                    </Text>
                  </div>
                </div>
              </List.Item>
            )}
          />
        ) : (
          <Empty 
            description="Нет сообщений" 
            style={{ margin: 'auto' }}
            image={Empty.PRESENTED_IMAGE_SIMPLE} 
          />
        )}
      </div>
      
      <Divider style={{ margin: '8px 0' }} />
      
      <div style={{ marginTop: 'auto' }}>
        <div style={{ display: 'flex', alignItems: 'flex-end' }}>
          <TextArea
            value={message}
            onChange={e => setMessage(e.target.value)}
            placeholder="Введите сообщение..."
            autoSize={{ minRows: 1, maxRows: 4 }}
            style={{ flex: 1, marginRight: '8px', resize: 'none' }}
            onPressEnter={e => {
              if (!e.shiftKey) {
                e.preventDefault();
                handleSendMessage();
              }
            }}
          />
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <Button
              shape="circle"
              icon={<PaperClipOutlined />}
              style={{ marginBottom: '4px' }}
              title="Прикрепить файл"
            />
            <Button 
              type="primary" 
              shape="circle"
              icon={<SendOutlined />}
              onClick={handleSendMessage}
              disabled={!message.trim()}
              title="Отправить сообщение"
            />
          </div>
        </div>
        <div style={{ fontSize: '11px', color: '#8c8c8c', marginTop: '4px', textAlign: 'center' }}>
          Чат работает в режиме демонстрации. Ваши сообщения не сохраняются.
        </div>
      </div>
    </Card>
  );
};

export default ChatPlaceholder; 