'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Card, List, Avatar, Typography, Badge, Empty, Spin, Alert, Tabs, Space, Button, Tag, Divider } from 'antd';
import { UserOutlined, MessageOutlined, ShoppingOutlined, ClockCircleOutlined, CommentOutlined } from '@ant-design/icons';
import { useAuth } from '../hooks/auth';
import { useChat } from '../hooks/useChat';
import { useUsers } from '../hooks/useUsers';
import { formatRelativeDate } from '../utils/date';
import ChatModal from '../components/ChatModal';
import { Chat } from '../types/chat';
import { useSearchParams } from 'next/navigation';

const { Title, Text } = Typography;
const { TabPane } = Tabs;

interface GroupedChats {
  [listingId: string]: {
    listingTitle: string;
    listingId: number;
    chats: {
      [userId: string]: Chat[];
    };
  };
}

export default function ChatsPage() {
  const { user, isAuthenticated } = useAuth();
  const { chats, loading, loadChats, connected } = useChat();
  const { getUserName, getUserAvatar, preloadUsers } = useUsers();
  const [selectedChat, setSelectedChat] = useState<Chat | null>(null);
  const [chatModalVisible, setChatModalVisible] = useState(false);
  const [activeTab, setActiveTab] = useState('listing');
  const searchParams = useSearchParams();
  
  // Для предотвращения повторных запросов и отслеживания загруженных пользователей
  const loadedUsersRef = useRef<Set<number>>(new Set());
  const usersLoadAttemptedRef = useRef<boolean>(false);

  useEffect(() => {
    if (isAuthenticated && user) {
      loadChats();
    }
  }, [isAuthenticated, user, loadChats]);

  // Предзагрузка пользователей при получении списка чатов
  useEffect(() => {
    if (chats.length > 0 && !usersLoadAttemptedRef.current) {
      // Собираем уникальные ID пользователей из чатов
      const userIds = new Set<number>();
      
      chats.forEach(chat => {
        // Добавляем участников чата
        chat.participants.forEach(participant => {
          if (participant.user_id && participant.user_id !== user?.id) {
            userIds.add(participant.user_id);
          }
        });
      });
      
      if (userIds.size > 0) {
        const uniqueUserIds = Array.from(userIds);
        
        // Фильтруем только те ID, которые еще не загружали
        const idsToLoad = uniqueUserIds.filter(id => !loadedUsersRef.current.has(id));
        
        if (idsToLoad.length > 0) {
          // Загружаем информацию о пользователях
          preloadUsers(idsToLoad)
            .then(() => {
              // Отмечаем пользователей как загруженных
              idsToLoad.forEach(id => loadedUsersRef.current.add(id));
            })
            .catch(error => {
              console.error("Ошибка загрузки пользователей:", error);
            });
        }
      }
      
      usersLoadAttemptedRef.current = true;
    }
  }, [chats, user?.id, preloadUsers]);

  const openChat = (chat: Chat) => {
    setSelectedChat(chat);
    setChatModalVisible(true);
  };

  const closeChat = () => {
    setChatModalVisible(false);
    setSelectedChat(null);
  };

  // Обработка URL параметра для автоматического открытия чата
  useEffect(() => {
    const openChatId = searchParams?.get('openChat');
    if (openChatId && chats.length > 0) {
      const chatToOpen = chats.find(chat => chat.id === parseInt(openChatId));
      if (chatToOpen) {
        openChat(chatToOpen);
      }
    }
  }, [searchParams, chats]);

  // Группируем чаты по объявлениям
  const groupChatsByListing = (): GroupedChats => {
    const grouped: GroupedChats = {};

    chats.forEach(chat => {
      if (chat.type === 'listing' && chat.listing_id) {
        const listingKey = chat.listing_id.toString();
        
        if (!grouped[listingKey]) {
          grouped[listingKey] = {
            listingTitle: chat.title || `Объявление #${chat.listing_id}`,
            listingId: chat.listing_id,
            chats: {}
          };
        }

        // Определяем собеседника
        const interlocutorId = chat.participants.find(p => p.user_id !== user?.id)?.user_id;
        if (interlocutorId) {
          const userKey = interlocutorId.toString();
          
          if (!grouped[listingKey].chats[userKey]) {
            grouped[listingKey].chats[userKey] = [];
          }
          
          grouped[listingKey].chats[userKey].push(chat);
        }
      }
    });

    return grouped;
  };

  // Группируем чаты по транзакциям
  const groupChatsByTransaction = () => {
    return chats.filter(chat => chat.type === 'completion' && chat.transaction_id);
  };

  // Другие чаты (поддержка, споры)
  const getOtherChats = () => {
    return chats.filter(chat => !['listing', 'completion'].includes(chat.type));
  };

  // Получаем имя пользователя
  const getUserDisplayName = (userId: number) => {
    if (!userId) return 'Неизвестный пользователь';
    return getUserName(userId);
  };

  // Получаем аватар пользователя
  const getUserAvatarImage = (userId: number) => {
    return getUserAvatar(userId);
  };

  // Генерируем цвет аватара на основе ID пользователя
  const getAvatarColor = (userId: number) => {
    if (!userId) return '#cccccc';
    const colors = ['#f56a00', '#7265e6', '#ffbf00', '#00a2ae', '#87d068', '#108ee9', '#722ed1', '#eb2f96'];
    return colors[userId % colors.length];
  };

  // Получаем последнее сообщение для отображения
  const getLastMessagePreview = (chat: Chat) => {
    if (chat.last_message) {
      return chat.last_message.length > 50 
        ? `${chat.last_message.substring(0, 50)}...` 
        : chat.last_message;
    }
    return 'Нет сообщений';
  };

  // Рендер чата в группе
  const renderChatItem = (chat: Chat, interlocutorId?: number) => (
    <List.Item
      key={chat.id}
      className="chat-item"
      style={{ 
        cursor: 'pointer', 
        padding: '12px 16px',
        borderRadius: '8px',
        marginBottom: '8px',
        border: '1px solid #f0f0f0',
        transition: 'all 0.3s ease'
      }}
      onClick={() => openChat(chat)}
      onMouseEnter={(e) => {
        e.currentTarget.style.backgroundColor = '#f5f5f5';
        e.currentTarget.style.borderColor = '#d9d9d9';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.backgroundColor = 'transparent';
        e.currentTarget.style.borderColor = '#f0f0f0';
      }}
    >
      <List.Item.Meta
        avatar={
          <Badge count={chat.unread_count || 0} size="small">
            <Avatar 
              icon={<UserOutlined />} 
              src={interlocutorId ? getUserAvatarImage(interlocutorId) : undefined}
              style={{ 
                backgroundColor: interlocutorId ? 
                  (getUserAvatarImage(interlocutorId) ? 'transparent' : getAvatarColor(interlocutorId)) 
                  : '#87d068' 
              }}
            />
          </Badge>
        }
        title={
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Text strong>
              {interlocutorId ? getUserDisplayName(interlocutorId) : chat.title}
            </Text>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Tag color={chat.status === 'active' ? 'green' : 'orange'}>
                {chat.status === 'active' ? 'Активный' : 'Архивный'}
              </Tag>
              {chat.created_at && (
                <Text type="secondary" style={{ fontSize: '12px' }}>
                  {formatRelativeDate(chat.created_at)}
                </Text>
              )}
            </div>
          </div>
        }
        description={
          <div>
            <Text type="secondary" style={{ fontSize: '13px' }}>
              {getLastMessagePreview(chat)}
            </Text>
            {chat.type === 'completion' && chat.transaction_id && (
              <div style={{ marginTop: '4px' }}>
                <Tag color="blue">
                  Транзакция #{chat.transaction_id}
                </Tag>
              </div>
            )}
          </div>
        }
      />
    </List.Item>
  );

  if (!isAuthenticated) {
    return (
      <div style={{ maxWidth: '800px', margin: '0 auto', padding: '24px' }}>
        <Alert
          message="Требуется авторизация"
          description="Пожалуйста, войдите в систему для просмотра чатов"
          type="error"
          showIcon
        />
      </div>
    );
  }

  if (loading) {
    return (
      <div style={{ maxWidth: '800px', margin: '0 auto', padding: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '400px' }}>
          <Spin size="large" tip="Загрузка чатов..." />
        </div>
      </div>
    );
  }

  const groupedListingChats = groupChatsByListing();
  const transactionChats = groupChatsByTransaction();
  const otherChats = getOtherChats();

  return (
    <div style={{ maxWidth: '1000px', margin: '0 auto', padding: '24px' }}>
      <div style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={2} style={{ margin: 0 }}>
          <MessageOutlined /> Мои чаты
        </Title>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Badge 
            status={connected ? 'success' : 'error'} 
            text={connected ? 'Подключен' : 'Не подключен'} 
          />
        </div>
      </div>

      <Tabs activeKey={activeTab} onChange={setActiveTab} type="card">
        <TabPane 
          tab={
            <span>
              <ShoppingOutlined />
              Чаты по объявлениям ({Object.keys(groupedListingChats).length})
            </span>
          } 
          key="listing"
        >
          {Object.keys(groupedListingChats).length === 0 ? (
            <Empty 
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description="Нет чатов по объявлениям"
            />
          ) : (
            <div>
              {Object.entries(groupedListingChats).map(([listingId, listingGroup]) => (
                <Card
                  key={listingId}
                  title={
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <ShoppingOutlined />
                      <span>{listingGroup.listingTitle}</span>
                      <Tag color="blue">ID: {listingGroup.listingId}</Tag>
                    </div>
                  }
                  style={{ marginBottom: '16px' }}
                  bodyStyle={{ padding: '12px' }}
                >
                  {Object.entries(listingGroup.chats).map(([userId, userChats]) => (
                    <div key={userId} style={{ marginBottom: '16px' }}>
                      <div style={{ marginBottom: '8px' }}>
                        <Text strong style={{ color: '#1890ff' }}>
                          {getUserDisplayName(parseInt(userId))} ({userChats.length} чат{userChats.length > 1 ? 'ов' : ''})
                        </Text>
                      </div>
                      <List
                        dataSource={userChats}
                        renderItem={(chat) => renderChatItem(chat, parseInt(userId))}
                        style={{ backgroundColor: '#fafafa', borderRadius: '6px', padding: '8px' }}
                      />
                    </div>
                  ))}
                </Card>
              ))}
            </div>
          )}
        </TabPane>

        <TabPane 
          tab={
            <span>
              <CommentOutlined />
              Чаты по транзакциям ({transactionChats.length})
            </span>
          } 
          key="transaction"
        >
          {transactionChats.length === 0 ? (
            <Empty 
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description="Нет чатов по транзакциям"
            />
          ) : (
            <List
              dataSource={transactionChats}
              renderItem={(chat) => renderChatItem(chat)}
            />
          )}
        </TabPane>

        <TabPane 
          tab={
            <span>
              <UserOutlined />
              Другие чаты ({otherChats.length})
            </span>
          } 
          key="other"
        >
          {otherChats.length === 0 ? (
            <Empty 
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description="Нет других чатов"
            />
          ) : (
            <List
              dataSource={otherChats}
              renderItem={(chat) => renderChatItem(chat)}
            />
          )}
        </TabPane>
      </Tabs>

      {/* Модальное окно чата */}
      <ChatModal
        visible={chatModalVisible}
        onClose={closeChat}
        chat={selectedChat}
        title={selectedChat?.title}
      />
    </div>
  );
}