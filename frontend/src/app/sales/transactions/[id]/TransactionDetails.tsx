'use client';

import React, { useState, useEffect, useRef } from 'react';
import { Card, Descriptions, Badge, Timeline, Skeleton, Alert, Tabs, Divider, Tag, Row, Col, Statistic, Button, Space, Modal, Typography, Steps, Avatar, Table, Tooltip, Empty } from 'antd';
import { ClockCircleOutlined, CheckCircleOutlined, DollarOutlined, UserOutlined, ShoppingOutlined, 
         WarningOutlined, ExclamationCircleOutlined, LockOutlined, UnlockOutlined, HistoryOutlined,
         CloseCircleOutlined, SafetyOutlined, MessageOutlined, CommentOutlined, SendOutlined, 
         FileDoneOutlined, InfoCircleOutlined } from '@ant-design/icons';
import { format } from 'date-fns';
import { getTransactionDetails, completeTransaction, disputeTransaction, refundTransaction, cancelTransaction } from '../../../api/transaction';
import formatPrice from '../../../utils/formatPrice';
import { PAYMENTS_API_URL } from '../../../api/client';
import { formatDate, formatTransactionTime, formatRegistrationDate } from '../../../utils/date';
import { useUsers } from '../../../hooks/useUsers';
import ChatModal from '../../../components/ChatModal';

const { TabPane } = Tabs;
const { Text, Title } = Typography;
const { Step } = Steps;

interface TransactionDetailsProps {
  transactionId: number;
}

const TransactionDetails: React.FC<TransactionDetailsProps> = ({ transactionId }) => {
  const [details, setDetails] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [disputeReason, setDisputeReason] = useState<string>('');
  const [activeTab, setActiveTab] = useState<string>('details');
  
  // Состояние для модальных окон
  const [isCompleteModalVisible, setIsCompleteModalVisible] = useState<boolean>(false);
  const [isDisputeModalVisible, setIsDisputeModalVisible] = useState<boolean>(false);
  const [isRefundModalVisible, setIsRefundModalVisible] = useState<boolean>(false);
  const [isCancelModalVisible, setIsCancelModalVisible] = useState<boolean>(false);
  
  // Добавляем состояние для модалки чата
  const [isChatModalVisible, setIsChatModalVisible] = useState<boolean>(false);
  
  // Получаем функции для работы с пользователями
  const { preloadUsers, getUserName, getUserAvatar } = useUsers();
  
  // Добавляем ref для предотвращения повторной загрузки пользователей
  const loadedUsersRef = useRef<boolean>(false);

  useEffect(() => {
    const fetchTransactionDetails = async () => {
      try {
        setLoading(true);
        const data = await getTransactionDetails(transactionId);
        setDetails(data);
        console.log("Transaction details:", data);
        
        // Добавляем более детальное логирование для отладки
        console.log("Transaction status:", data?.transaction?.status);
        console.log("Available actions:", data?.available_actions);
        console.log("Action status:", data?.action_status);
        console.log("User role:", data?.user_role);
        console.log("API URL:", `${PAYMENTS_API_URL}/transactions/${transactionId}/details`);
        
        // Предзагрузка информации о пользователях
        if (data && !loadedUsersRef.current) {
          const userIds = [];
          
          // Добавляем ID покупателя и продавца, если они есть
          if (data.buyer?.id) userIds.push(data.buyer.id);
          if (data.seller?.id) userIds.push(data.seller.id);
          
          // Добавляем ID из транзакции, если они отличаются
          if (data.transaction?.buyer_id && !userIds.includes(data.transaction.buyer_id)) {
            userIds.push(data.transaction.buyer_id);
          }
          if (data.transaction?.seller_id && !userIds.includes(data.transaction.seller_id)) {
            userIds.push(data.transaction.seller_id);
          }
          
          // Если есть ID пользователей, загружаем их данные
          if (userIds.length > 0) {
            preloadUsers(userIds)
              .then(() => { loadedUsersRef.current = true; })
              .catch(err => console.error("Ошибка загрузки данных пользователей:", err));
          }
        }
      } catch (err) {
        console.error("Error fetching transaction details:", err);
        setError(err instanceof Error ? err.message : 'Ошибка загрузки данных');
      } finally {
        setLoading(false);
      }
    };

    if (transactionId) {
      fetchTransactionDetails();
    }
    
    // Сбрасываем флаг загрузки пользователей при размонтировании
    return () => {
      loadedUsersRef.current = false;
    };
  }, [transactionId, preloadUsers]);

  // Сопоставление статусов с удобочитаемыми названиями и цветами
  const getStatusBadge = (status: string) => {
    const statusMap: Record<string, { color: string, text: string, icon: React.ReactNode }> = {
      'pending': { 
        color: 'processing', 
        text: 'Ожидание оплаты',
        icon: <ClockCircleOutlined />
      },
      'escrow_held': { 
        color: 'warning', 
        text: 'Средства в Escrow',
        icon: <LockOutlined />
      },
      'completed': { 
        color: 'success', 
        text: 'Завершена',
        icon: <CheckCircleOutlined />
      },
      'refunded': { 
        color: 'default', 
        text: 'Возврат средств',
        icon: <SendOutlined />
      },
      'disputed': { 
        color: 'error', 
        text: 'В споре',
        icon: <WarningOutlined />
      },
      'canceled': { 
        color: 'default', 
        text: 'Отменена',
        icon: <CloseCircleOutlined />
      },
      'failed': { 
        color: 'error', 
        text: 'Ошибка',
        icon: <ExclamationCircleOutlined />
      }
    };

    const statusInfo = statusMap[status] || { color: 'default', text: status, icon: <InfoCircleOutlined /> };
    return (
      <Badge 
        status={statusInfo.color as any} 
        text={
          <Space>
            {statusInfo.icon}
            <span>{statusInfo.text}</span>
          </Space>
        } 
      />
    );
  };

  // Функция для получения шагов транзакции
  const getTransactionSteps = () => {
    const statusOrder = ['pending', 'escrow_held', 'completed'];
    const currentStatus = details?.transaction?.status || 'pending';
    
    // Определяем текущий шаг
    let current = statusOrder.indexOf(currentStatus);
    if (current === -1) current = 0;
    
    // Если транзакция отменена или возвращена, показываем соответствующий статус
    const isCancelledOrRefunded = ['canceled', 'refunded', 'disputed', 'failed'].includes(currentStatus);
    const statusMap: Record<string, { title: string, description: string, icon: React.ReactNode }> = {
      'pending': { 
        title: 'Ожидание оплаты', 
        description: 'Ожидание перевода средств',
        icon: <ClockCircleOutlined />
      },
      'escrow_held': { 
        title: 'Средства в Escrow', 
        description: 'Деньги удерживаются в безопасном хранилище',
        icon: <LockOutlined />
      },
      'completed': { 
        title: 'Завершена', 
        description: 'Транзакция успешно завершена',
        icon: <CheckCircleOutlined />
      }
    };
    
    return (
      <Steps 
        current={current} 
        status={isCancelledOrRefunded ? 'error' : 'process'}
        style={{ marginBottom: 24 }}
      >
        {statusOrder.map((status, index) => (
          <Step 
            key={status} 
            title={statusMap[status].title} 
            description={statusMap[status].description}
            icon={statusMap[status].icon}
          />
        ))}
      </Steps>
    );
  };

  // Обработчик для завершения транзакции
  const handleComplete = async () => {
    console.log('handleComplete вызван');
    setIsCompleteModalVisible(true);
  };
  
  const confirmComplete = async () => {
    console.log('confirmComplete вызван');
    try {
      setActionLoading(true);
      console.log('confirmComplete: вызов API completeTransaction', transactionId);
      await completeTransaction(transactionId);
      // Обновляем данные транзакции
      const updatedData = await getTransactionDetails(transactionId);
      console.log('confirmComplete: получены обновленные данные', updatedData);
      setDetails(updatedData);
      setIsCompleteModalVisible(false);
      Modal.success({
        title: 'Транзакция завершена',
        content: 'Транзакция успешно завершена, средства переведены продавцу.'
      });
    } catch (err) {
      console.error('Ошибка при завершении транзакции:', err);
      Modal.error({
        title: 'Ошибка',
        content: 'Не удалось завершить транзакцию. Пожалуйста, попробуйте позже.'
      });
    } finally {
      setActionLoading(false);
    }
  };

  // Обработчик для открытия спора
  const handleDispute = () => {
    console.log('handleDispute вызван');
    setIsDisputeModalVisible(true);
  };
  
  const confirmDispute = async () => {
    console.log('confirmDispute: вызван', {disputeReason});
    if (!disputeReason.trim()) {
      Modal.warning({
        title: 'Требуется причина',
        content: 'Пожалуйста, укажите причину спора'
      });
      return;
    }
    
    try {
      setActionLoading(true);
      console.log('confirmDispute: вызов API disputeTransaction', transactionId, disputeReason);
      await disputeTransaction(transactionId, disputeReason);
      // Обновляем данные транзакции
      const updatedData = await getTransactionDetails(transactionId);
      console.log('confirmDispute: получены обновленные данные', updatedData);
      setDetails(updatedData);
      setDisputeReason('');
      setIsDisputeModalVisible(false);
      Modal.success({
        title: 'Спор открыт',
        content: 'Спор успешно открыт. Администрация рассмотрит ваше обращение.'
      });
    } catch (err) {
      console.error('Ошибка при открытии спора:', err);
      Modal.error({
        title: 'Ошибка',
        content: 'Не удалось открыть спор. Пожалуйста, попробуйте позже.'
      });
    } finally {
      setActionLoading(false);
    }
  };

  // Обработчик для возврата средств
  const handleRefund = () => {
    console.log('handleRefund вызван');
    setIsRefundModalVisible(true);
  };
  
  const confirmRefund = async () => {
    console.log('confirmRefund вызван');
    try {
      setActionLoading(true);
      console.log('confirmRefund: вызов API refundTransaction', transactionId);
      await refundTransaction(transactionId);
      // Обновляем данные транзакции
      const updatedData = await getTransactionDetails(transactionId);
      console.log('confirmRefund: получены обновленные данные', updatedData);
      setDetails(updatedData);
      setIsRefundModalVisible(false);
      Modal.success({
        title: 'Возврат выполнен',
        content: 'Средства успешно возвращены покупателю.'
      });
    } catch (err) {
      console.error('Ошибка при возврате средств:', err);
      Modal.error({
        title: 'Ошибка',
        content: 'Не удалось выполнить возврат. Пожалуйста, попробуйте позже.'
      });
    } finally {
      setActionLoading(false);
    }
  };

  // Обработчик для отмены транзакции
  const handleCancel = () => {
    console.log('handleCancel вызван');
    setIsCancelModalVisible(true);
  };
  
  const confirmCancel = async () => {
    console.log('confirmCancel вызван');
    try {
      setActionLoading(true);
      console.log('confirmCancel: вызов API cancelTransaction', transactionId);
      await cancelTransaction(transactionId);
      // Обновляем данные транзакции
      const updatedData = await getTransactionDetails(transactionId);
      console.log('confirmCancel: получены обновленные данные', updatedData);
      setDetails(updatedData);
      setIsCancelModalVisible(false);
      Modal.success({
        title: 'Транзакция отменена',
        content: 'Транзакция успешно отменена.'
      });
    } catch (err) {
      console.error('Ошибка при отмене транзакции:', err);
      Modal.error({
        title: 'Ошибка',
        content: 'Не удалось отменить транзакцию. Пожалуйста, попробуйте позже.'
      });
    } finally {
      setActionLoading(false);
    }
  };

  // Обработчик для открытия чата
  const handleOpenChat = () => {
    setIsChatModalVisible(true);
  };
  
  // Обработчик для закрытия чата
  const handleCloseChat = () => {
    setIsChatModalVisible(false);
  };

  if (loading) {
    return (
      <Card>
        <Skeleton active paragraph={{ rows: 10 }} />
      </Card>
    );
  }

  if (error) {
    return (
      <Alert
        message="Ошибка при загрузке данных"
        description={error}
        type="error"
        showIcon
      />
    );
  }

  if (!details) {
    return (
      <Alert
        message="Нет данных"
        description="Информация о транзакции не найдена"
        type="warning"
        showIcon
      />
    );
  }

  const { transaction, history, sale, buyer, seller, escrow_info, time_info, available_actions, action_status, item, user_role, payment_info } = details;

  // Отображаем кнопки доступных действий
  const renderActionButtons = () => {
    // Добавляем отладочный вывод состояния кнопок
    console.log('Rendering action buttons with state:', {
      action_status,
      available_actions,
      transaction_status: transaction?.status,
      user_role
    });

    return (
      <Card 
        title={<div><FileDoneOutlined /> Действия</div>} 
        className="mb-4 shadow-sm"
        bodyStyle={{ padding: '16px' }}
      >
        <Space wrap style={{ width: '100%', justifyContent: 'center' }}>
          {action_status?.can_complete && (
            <Button 
              type="primary" 
              icon={<CheckCircleOutlined />} 
              onClick={handleComplete}
              loading={actionLoading}
              style={{ backgroundColor: '#52c41a', borderColor: '#52c41a' }}
            >
              Подтвердить получение
            </Button>
          )}
          
          {action_status?.can_dispute && (
            <Button 
              danger
              icon={<WarningOutlined />} 
              onClick={handleDispute}
              loading={actionLoading}
            >
              Открыть спор
            </Button>
          )}
          
          {action_status?.can_refund && (
            <Button 
              icon={<SendOutlined />} 
              onClick={handleRefund}
              loading={actionLoading}
            >
              Вернуть средства
            </Button>
          )}
          
          {action_status?.can_cancel && (
            <Button 
              icon={<CloseCircleOutlined />} 
              onClick={handleCancel}
              loading={actionLoading}
            >
              Отменить
            </Button>
          )}
          
          
          {(!action_status?.can_complete && !action_status?.can_dispute && 
           !action_status?.can_refund && !action_status?.can_cancel && 
           (transaction?.status === 'canceled' || transaction?.status === 'failed')) && (
            <Alert
              message="Нет доступных действий"
              description="В текущем статусе транзакции нет доступных действий"
              type="info"
              showIcon
              style={{ width: '100%' }}
            />
          )}
        </Space>
      </Card>
    );
  };

  return (
    <div className="transaction-details">
      
      {/* Заголовок и основная информация */}
      <Card 
        title={
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>Транзакция #{transaction.id}</span>
            <div>{getStatusBadge(transaction.status)}</div>
          </div>
        }
        bordered={true}
        className="mb-4 shadow-sm"
      >
        {/* Шаги транзакции */}
        {getTransactionSteps()}
        
        <Row gutter={[24, 24]}>
          <Col xs={24} md={8}>
            <Statistic 
              title="Сумма" 
              value={formatPrice(transaction.amount, transaction.currency)} 
              prefix={<DollarOutlined />} 
              valueStyle={{ color: '#3f8600' }}
            />
          </Col>
          <Col xs={24} md={8}>
            <Statistic 
              title="Дата создания" 
              value={formatTransactionTime(transaction.created_at)} 
              prefix={<ClockCircleOutlined />}
            />
          </Col>
          <Col xs={24} md={8}>
            <Statistic 
              title="Тип транзакции" 
              value={transaction.type || "Покупка"} 
              prefix={<ShoppingOutlined />}
            />
          </Col>
        </Row>

        {escrow_info?.is_in_escrow && (
          <Alert
            message="Средства в Escrow"
            description={`Средства находятся в Escrow уже ${escrow_info.days_in_escrow || 0} дней. Они будут удерживаться до подтверждения получения товара.`}
            type="warning"
            showIcon
            icon={<LockOutlined />}
            className="mt-4"
          />
        )}

        {time_info?.is_expired && (
          <Alert
            message="Срок транзакции истек"
            description="Срок выполнения этой транзакции истек. Обратитесь в службу поддержки."
            type="error"
            showIcon
            icon={<ExclamationCircleOutlined />}
            className="mt-4"
          />
        )}
      </Card>

      {/* Блок с кнопками действий */}
      {renderActionButtons()}

      {/* Вкладки с детальной информацией */}
      <Card className="shadow-sm">
        <Tabs 
          activeKey={activeTab} 
          onChange={setActiveTab}
          type="card"
          tabBarStyle={{ marginBottom: 16 }}
        >
          <TabPane 
            tab={<span><InfoCircleOutlined /> Детали</span>} 
            key="details"
          >
            <Descriptions 
              bordered 
              column={{ xxl: 3, xl: 3, lg: 2, md: 2, sm: 1, xs: 1 }}
              labelStyle={{ fontWeight: 'bold', backgroundColor: '#fafafa' }}
            >
              <Descriptions.Item label="ID транзакции" span={1}>
                {transaction.id}
              </Descriptions.Item>
              <Descriptions.Item label="Статус" span={1}>
                {getStatusBadge(transaction.status)}
              </Descriptions.Item>
              <Descriptions.Item label="Тип" span={1}>
                {transaction.type || "Покупка"}
              </Descriptions.Item>
              
              <Descriptions.Item label="Сумма" span={1}>
                {formatPrice(transaction.amount, transaction.currency)}
              </Descriptions.Item>
              <Descriptions.Item label="Комиссия" span={1}>
                {formatPrice(transaction.fee_amount, transaction.currency)} ({transaction.fee_percentage}%)
              </Descriptions.Item>
              <Descriptions.Item label="Итого" span={1}>
                {formatPrice(transaction.amount - transaction.fee_amount, transaction.currency)}
              </Descriptions.Item>
              
              <Descriptions.Item label="Дата создания" span={1}>
                {formatTransactionTime(transaction.created_at)}
              </Descriptions.Item>
              {transaction.completed_at && (
                <Descriptions.Item label="Дата завершения" span={1}>
                  {formatTransactionTime(transaction.completed_at)}
                </Descriptions.Item>
              )}
              {transaction.escrow_held_at && (
                <Descriptions.Item label="В Escrow с" span={1}>
                  {formatTransactionTime(transaction.escrow_held_at)}
                </Descriptions.Item>
              )}
              
              {transaction.description && (
                <Descriptions.Item label="Описание" span={3}>
                  {transaction.description}
                </Descriptions.Item>
              )}
              
              {transaction.notes && (
                <Descriptions.Item label="Примечания" span={3}>
                  {transaction.notes}
                </Descriptions.Item>
              )}
            </Descriptions>
          </TabPane>
          
          <TabPane 
            tab={<span><UserOutlined /> Участники</span>} 
            key="participants"
          >
            <Row gutter={[24, 24]}>
              <Col xs={24} md={12}>
                <Card 
                  title={<span><UserOutlined /> Покупатель</span>}
                  extra={<Tag color="blue">Покупатель</Tag>}
                  bordered={true}
                  style={{ height: '100%' }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', marginBottom: 16 }}>
                    <Avatar 
                      size={64} 
                      icon={<UserOutlined />} 
                      src={buyer?.avatar || getUserAvatar(buyer?.id || transaction.buyer_id)}
                      style={{ backgroundColor: '#1890ff' }}
                    />
                    <div style={{ marginLeft: 16 }}>
                      <Text strong style={{ fontSize: 16 }}>
                        {buyer?.username || getUserName(buyer?.id || transaction.buyer_id)}
                      </Text>
                      <div>
                        <Text type="secondary">{buyer?.email}</Text>
                      </div>
                      {buyer?.verified && <Tag color="green">Проверенный</Tag>}
                    </div>
                  </div>
                  
                  <Descriptions column={1} size="small" style={{ marginTop: 16 }}>
                   
                    {buyer?.registration_date && (
                      <Descriptions.Item label="Дата регистрации">
                        {formatRegistrationDate(buyer.registration_date)}
                      </Descriptions.Item>
                    )}
                    {buyer?.total_purchases && (
                      <Descriptions.Item label="Всего покупок">{buyer.total_purchases}</Descriptions.Item>
                    )}
                    {buyer?.rating && (
                      <Descriptions.Item label="Рейтинг">{buyer.rating}/5</Descriptions.Item>
                    )}
                  </Descriptions>
                </Card>
              </Col>
              
              <Col xs={24} md={12}>
                <Card 
                  title={<span><UserOutlined /> Продавец</span>}
                  extra={<Tag color="orange">Продавец</Tag>}
                  bordered={true}
                  style={{ height: '100%' }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', marginBottom: 16 }}>
                    <Avatar 
                      size={64} 
                      icon={<UserOutlined />} 
                      src={seller?.avatar || getUserAvatar(seller?.id || transaction.seller_id)}
                      style={{ backgroundColor: '#52c41a' }}
                    />
                    <div style={{ marginLeft: 16 }}>
                      <Text strong style={{ fontSize: 16 }}>
                        {seller?.username || getUserName(seller?.id || transaction.seller_id)}
                      </Text>
                      <div>
                        <Text type="secondary">{seller?.email}</Text>
                      </div>
                      {seller?.verified && <Tag color="green">Проверенный</Tag>}
                    </div>
                  </div>
                  
                  <Descriptions column={1} size="small" style={{ marginTop: 16 }}>
                    {seller?.registration_date && (
                      <Descriptions.Item label="Дата регистрации">
                        {formatRegistrationDate(seller.registration_date)}
                      </Descriptions.Item>
                    )}
                    {seller?.total_sales && (
                      <Descriptions.Item label="Всего продаж">{seller.total_sales}</Descriptions.Item>
                    )}
                    {seller?.rating && (
                      <Descriptions.Item label="Рейтинг">{seller.rating}/5</Descriptions.Item>
                    )}
                  </Descriptions>
                </Card>
              </Col>
            </Row>
            
            {/* Информация о товаре */}
            {item && (
              <Card 
                title={<span><ShoppingOutlined /> Информация о товаре</span>}
                style={{ marginTop: 24 }}
                bordered={true}
              >
                <Row gutter={[24, 16]}>
                  <Col xs={24} md={16}>
                    <div style={{ marginBottom: 16 }}>
                      <Title level={4}>{item.title}</Title>
                      <Text type="secondary">{item.description}</Text>
                    </div>
                    
                    <Descriptions column={{ xxl: 3, xl: 3, lg: 2, md: 2, sm: 1, xs: 1 }} bordered>
                      <Descriptions.Item label="ID товара">{item.id}</Descriptions.Item>
                      <Descriptions.Item label="Категория">{item.category}</Descriptions.Item>
                      <Descriptions.Item label="Состояние">{item.condition}</Descriptions.Item>
                      <Descriptions.Item label="Цена">{formatPrice(item.price, item.currency)}</Descriptions.Item>
                      {item.location && (
                        <Descriptions.Item label="Местоположение">{item.location}</Descriptions.Item>
                      )}
                      <Descriptions.Item label="Дата создания">
                        <div className="text-xs text-gray-500">
                          {formatDate(item.created_at)}
                        </div>
                      </Descriptions.Item>
                    </Descriptions>
                    
                    {item.tags && item.tags.length > 0 && (
                      <div style={{ marginTop: 16 }}>
                        <Text strong>Метки:</Text>
                        <div style={{ marginTop: 8 }}>
                          {item.tags.map((tag: string, index: number) => (
                            <Tag key={index}>{tag}</Tag>
                          ))}
                        </div>
                      </div>
                    )}
                  </Col>
                  
                  <Col xs={24} md={8}>
                    {item.images && item.images.length > 0 ? (
                      <div style={{ textAlign: 'center' }}>
                        <img 
                          src={item.images[0]} 
                          alt={item.title} 
                          style={{ maxWidth: '100%', maxHeight: 200, objectFit: 'contain', borderRadius: 8 }}
                        />
                        
                        {item.images.length > 1 && (
                          <div style={{ display: 'flex', justifyContent: 'center', marginTop: 8 }}>
                            {item.images.slice(1, 3).map((image: string, index: number) => (
                              <img 
                                key={index}
                                src={image} 
                                alt={`${item.title} - изображение ${index + 2}`} 
                                style={{ width: 60, height: 60, objectFit: 'cover', margin: '0 4px', borderRadius: 4 }}
                              />
                            ))}
                          </div>
                        )}
                      </div>
                    ) : (
                      <div style={{ textAlign: 'center' }}>
                        <div 
                          style={{ 
                            width: '100%', 
                            height: 200, 
                            backgroundColor: '#f0f2f5', 
                            display: 'flex', 
                            alignItems: 'center', 
                            justifyContent: 'center',
                            borderRadius: 8 
                          }}
                        >
                          <ShoppingOutlined style={{ fontSize: 48, color: '#bfbfbf' }} />
                        </div>
                        <Text type="secondary">Изображения отсутствуют</Text>
                      </div>
                    )}
                  </Col>
                </Row>
              </Card>
            )}
          </TabPane>
          
          <TabPane 
            tab={<span><HistoryOutlined /> История</span>} 
            key="history"
          >
            {history && history.length > 0 ? (
              <Timeline mode="left">
                {history.map((event: any) => {
                  let color = 'blue';
                  let icon = <InfoCircleOutlined />;
                  
                  // Определяем цвет и иконку в зависимости от действия
                  if (event.action === 'create') {
                    color = 'blue';
                    icon = <InfoCircleOutlined />;
                  } else if (event.action === 'status_change') {
                    if (event.to_status === 'COMPLETED') {
                      color = 'green';
                      icon = <CheckCircleOutlined />;
                    } else if (event.to_status === 'ESCROW_HELD') {
                      color = 'orange';
                      icon = <LockOutlined />;
                    } else if (event.to_status === 'DISPUTED') {
                      color = 'red';
                      icon = <WarningOutlined />;
                    } else if (event.to_status === 'REFUNDED') {
                      color = 'gray';
                      icon = <SendOutlined />;
                    } else if (event.to_status === 'CANCELED') {
                      color = 'gray';
                      icon = <CloseCircleOutlined />;
                    }
                  }
                  
                  return (
                    <Timeline.Item 
                      key={event.id} 
                      color={color}
                      dot={icon}
                      label={formatTransactionTime(event.timestamp)}
                    >
                      <div>
                        <strong>
                          {event.action === 'create' 
                            ? 'Создание транзакции' 
                            : `Изменение статуса: ${event.from_status || 'Новый'} → ${event.to_status}`}
                        </strong>
                        {event.notes && <div>{event.notes}</div>}
                      </div>
                    </Timeline.Item>
                  );
                })}
              </Timeline>
            ) : (
              <Empty description="История транзакции отсутствует" />
            )}
          </TabPane>
        </Tabs>
      </Card>

      {/* Модальные окна для действий */}
      <Modal
        title="Подтверждение завершения"
        open={isCompleteModalVisible}
        onOk={confirmComplete}
        onCancel={() => setIsCompleteModalVisible(false)}
        okText="Подтвердить"
        cancelText="Отмена"
        confirmLoading={actionLoading}
      >
        <p>Вы уверены, что хотите завершить транзакцию? Средства будут переведены продавцу.</p>
      </Modal>

      <Modal
        title="Открытие спора"
        open={isDisputeModalVisible}
        onOk={confirmDispute}
        onCancel={() => setIsDisputeModalVisible(false)}
        okText="Открыть спор"
        cancelText="Отмена"
        confirmLoading={actionLoading}
      >
        <div>
          <p>Укажите причину спора:</p>
          <textarea 
            rows={4} 
            style={{ width: '100%', marginTop: '8px', padding: '8px', borderRadius: '4px', border: '1px solid #d9d9d9' }}
            value={disputeReason}
            onChange={(e) => setDisputeReason(e.target.value)}
            placeholder="Подробно опишите причину спора..."
          />
        </div>
      </Modal>

      <Modal
        title="Возврат средств"
        open={isRefundModalVisible}
        onOk={confirmRefund}
        onCancel={() => setIsRefundModalVisible(false)}
        okText="Подтвердить возврат"
        cancelText="Отмена"
        confirmLoading={actionLoading}
      >
        <p>Вы уверены, что хотите вернуть средства покупателю?</p>
      </Modal>

      <Modal
        title="Отмена транзакции"
        open={isCancelModalVisible}
        onOk={confirmCancel}
        onCancel={() => setIsCancelModalVisible(false)}
        okText="Да, отменить"
        cancelText="Нет"
        confirmLoading={actionLoading}
      >
        <p>Вы уверены, что хотите отменить транзакцию?</p>
      </Modal>
    </div>
  );
};

export default TransactionDetails; 