'use client';

import React, { useState, useEffect } from 'react';
import { Badge, Dropdown, List, Avatar, Typography, Button, Empty, Spin, Card } from 'antd';
import { BellOutlined, MessageOutlined, UserOutlined, CheckOutlined, DeleteOutlined } from '@ant-design/icons';
import { formatDistanceToNow } from 'date-fns';
import { ru } from 'date-fns/locale';
import { useAuth } from '../hooks/auth';

const { Text } = Typography;

export interface Notification {
  id: string;
  type: 'message' | 'chat_created' | 'mention';
  title: string;
  message: string;
  chatId?: number;
  messageId?: number;
  senderId?: number;
  senderName?: string;
  timestamp: string;
  read: boolean;
  metadata?: {
    chatTitle?: string;
    avatar?: string;
  };
}

interface NotificationCenterProps {
  notifications: Notification[];
  loading?: boolean;
  onMarkAsRead: (notificationId: string) => void;
  onMarkAllAsRead: () => void;
  onDeleteNotification: (notificationId: string) => void;
  onNotificationClick: (notification: Notification) => void;
}

export default function NotificationCenter({
  notifications,
  loading = false,
  onMarkAsRead,
  onMarkAllAsRead,
  onDeleteNotification,
  onNotificationClick
}: NotificationCenterProps) {
  const { user } = useAuth();
  const [visible, setVisible] = useState(false);

  const unreadCount = notifications.filter(n => !n.read).length;

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case 'message':
        return <MessageOutlined style={{ color: '#1890ff' }} />;
      case 'chat_created':
        return <UserOutlined style={{ color: '#52c41a' }} />;
      case 'mention':
        return <MessageOutlined style={{ color: '#f5222d' }} />;
      default:
        return <BellOutlined style={{ color: '#faad14' }} />;
    }
  };

  const handleNotificationClick = (notification: Notification) => {
    if (!notification.read) {
      onMarkAsRead(notification.id);
    }
    onNotificationClick(notification);
    setVisible(false);
  };

  const dropdownContent = (
    <Card
      style={{ width: 380, maxHeight: 500 }}
      bodyStyle={{ padding: 0 }}
      title={
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span>Уведомления ({unreadCount})</span>
          {unreadCount > 0 && (
            <Button
              type="link"
              size="small"
              icon={<CheckOutlined />}
              onClick={(e) => {
                e.stopPropagation();
                onMarkAllAsRead();
              }}
            >
              Отметить все как прочитанные
            </Button>
          )}
        </div>
      }
    >
      {loading ? (
        <div style={{ padding: '20px', textAlign: 'center' }}>
          <Spin tip="Загрузка уведомлений..." />
        </div>
      ) : notifications.length === 0 ? (
        <div style={{ padding: '20px' }}>
          <Empty 
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="Нет уведомлений"
          />
        </div>
      ) : (
        <List
          style={{ maxHeight: 400, overflow: 'auto' }}
          dataSource={notifications}
          renderItem={(notification) => (
            <List.Item
              key={notification.id}
              style={{
                padding: '12px 16px',
                cursor: 'pointer',
                backgroundColor: notification.read ? 'transparent' : '#f6ffed',
                borderLeft: notification.read ? 'none' : '3px solid #52c41a'
              }}
              onClick={() => handleNotificationClick(notification)}
              actions={[
                <Button
                  key="delete"
                  type="text"
                  size="small"
                  icon={<DeleteOutlined />}
                  onClick={(e) => {
                    e.stopPropagation();
                    onDeleteNotification(notification.id);
                  }}
                  style={{ color: '#ff4d4f' }}
                />
              ]}
            >
              <List.Item.Meta
                avatar={
                  <Badge dot={!notification.read}>
                    <Avatar 
                      icon={getNotificationIcon(notification.type)}
                      style={{ backgroundColor: '#f0f0f0' }}
                    />
                  </Badge>
                }
                title={
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <Text strong={!notification.read} style={{ fontSize: '14px' }}>
                      {notification.title}
                    </Text>
                    <Text type="secondary" style={{ fontSize: '12px', whiteSpace: 'nowrap' }}>
                      {formatDistanceToNow(new Date(notification.timestamp), { addSuffix: true, locale: ru })}
                    </Text>
                  </div>
                }
                description={
                  <div>
                    <Text type="secondary" style={{ fontSize: '13px' }}>
                      {notification.message}
                    </Text>
                    {notification.metadata?.chatTitle && (
                      <div style={{ marginTop: '4px' }}>
                        <Text type="secondary" style={{ fontSize: '12px', fontStyle: 'italic' }}>
                          в чате: {notification.metadata.chatTitle}
                        </Text>
                      </div>
                    )}
                  </div>
                }
              />
            </List.Item>
          )}
        />
      )}
    </Card>
  );

  return (
    <Dropdown
      overlay={dropdownContent}
      trigger={['click']}
      placement="bottomRight"
      visible={visible}
      onVisibleChange={setVisible}
    >
      <div style={{ cursor: 'pointer', padding: '8px' }}>
        <Badge count={unreadCount} size="small" offset={[2, 2]}>
          <BellOutlined style={{ fontSize: '18px', color: '#666' }} />
        </Badge>
      </div>
    </Dropdown>
  );
} 