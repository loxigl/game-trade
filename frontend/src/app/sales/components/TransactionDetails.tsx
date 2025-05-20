'use client';

import React, { useState, useEffect } from 'react';
import { Modal, Descriptions, Spin, Button, Timeline, Tag, Divider, Empty, Typography } from 'antd';
import { ClockCircleOutlined, CheckCircleOutlined, CloseCircleOutlined, InfoCircleOutlined, WarningOutlined } from '@ant-design/icons';
import { useAuth } from '../../hooks/auth';
import { getTransactionTimeline, getTransaction } from '../../api/transaction';
import { Transaction, TransactionHistoryItem, TransactionStatus } from '../../types/transaction';
import formatDate from '../../utils/formatDate';

const { Text, Title } = Typography;

interface TransactionDetailsProps {
  transactionId: number;
  isOpen: boolean;
  onClose: () => void;
}

const TransactionDetails: React.FC<TransactionDetailsProps> = ({ transactionId, isOpen, onClose }) => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [transaction, setTransaction] = useState<Transaction | null>(null);
  const [timeline, setTimeline] = useState<TransactionHistoryItem[]>([]);
  
  // Загрузка данных о транзакции
  useEffect(() => {
    if (isOpen && transactionId) {
      const fetchData = async () => {
        setLoading(true);
        try {
          // Параллельно запрашиваем транзакцию и таймлайн
          const [transactionData, timelineData] = await Promise.all([
            getTransaction(transactionId),
            getTransactionTimeline(transactionId)
          ]);
          
          setTransaction(transactionData);
          setTimeline(timelineData);
        } catch (error) {
          console.error('Ошибка при получении данных транзакции:', error);
        } finally {
          setLoading(false);
        }
      };
      
      fetchData();
    }
  }, [isOpen, transactionId]);
  
  // Форматирование цены
  const formatAmount = (amount: number) => {
    return new Intl.NumberFormat('ru-RU', {
      style: 'currency',
      currency: 'RUB'
    }).format(amount);
  };
  
  // Получение иконки для статуса в таймлайне
  const getStatusIcon = (status: TransactionStatus) => {
    switch (status) {
      case TransactionStatus.COMPLETED:
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case TransactionStatus.PENDING:
        return <ClockCircleOutlined style={{ color: '#1890ff' }} />;
      case TransactionStatus.ESCROW_HELD:
        return <InfoCircleOutlined style={{ color: '#1890ff' }} />;
      case TransactionStatus.REFUNDED:
        return <CloseCircleOutlined style={{ color: '#722ed1' }} />;
      case TransactionStatus.DISPUTED:
        return <WarningOutlined style={{ color: '#fa8c16' }} />;
      case TransactionStatus.RESOLVED:
        return <CheckCircleOutlined style={{ color: '#2f54eb' }} />;
      case TransactionStatus.CANCELED:
        return <CloseCircleOutlined style={{ color: '#f5222d' }} />;
      default:
        return <InfoCircleOutlined />;
    }
  };
  
  // Получение названия для статуса
  const getStatusText = (status: TransactionStatus) => {
    switch (status) {
      case TransactionStatus.COMPLETED:
        return 'Завершено';
      case TransactionStatus.PENDING:
        return 'В обработке';
      case TransactionStatus.ESCROW_HELD:
        return 'В Escrow';
      case TransactionStatus.REFUNDED:
        return 'Возврат';
      case TransactionStatus.DISPUTED:
        return 'Спор';
      case TransactionStatus.RESOLVED:
        return 'Разрешено';
      case TransactionStatus.CANCELED:
        return 'Отменено';
      default:
        return status;
    }
  };
  
  // Получение цвета тега для статуса
  const getStatusTagColor = (status: TransactionStatus) => {
    switch (status) {
      case TransactionStatus.COMPLETED:
        return 'success';
      case TransactionStatus.PENDING:
        return 'processing';
      case TransactionStatus.ESCROW_HELD:
        return 'cyan';
      case TransactionStatus.REFUNDED:
        return 'purple';
      case TransactionStatus.DISPUTED:
        return 'warning';
      case TransactionStatus.RESOLVED:
        return 'geekblue';
      case TransactionStatus.CANCELED:
        return 'error';
      default:
        return 'default';
    }
  };
  
  return (
    <Modal
      title="Детали транзакции"
      open={isOpen}
      onCancel={onClose}
      width={800}
      footer={[
        <Button key="close" onClick={onClose}>
          Закрыть
        </Button>
      ]}
    >
      {loading ? (
        <div className="flex justify-center items-center py-10">
          <Spin size="large" tip="Загрузка транзакции..." />
        </div>
      ) : transaction ? (
        <div>
          <Descriptions 
            title={<Title level={5}>Основная информация</Title>} 
            bordered 
            column={{ xxl: 4, xl: 3, lg: 3, md: 3, sm: 2, xs: 1 }}
          >
            <Descriptions.Item label="ID транзакции" span={2}>
              {transaction.id}
            </Descriptions.Item>
            <Descriptions.Item label="Статус" span={1}>
              <Tag color={getStatusTagColor(transaction.status)}>
                {getStatusText(transaction.status)}
              </Tag>
            </Descriptions.Item>
            <Descriptions.Item label="Продавец" span={2}>
              ID: {transaction.sellerId}
            </Descriptions.Item>
            <Descriptions.Item label="Покупатель" span={1}>
              ID: {transaction.buyerId}
            </Descriptions.Item>
            <Descriptions.Item label="Сумма" span={1}>
              {formatAmount(transaction.amount)}
            </Descriptions.Item>
            <Descriptions.Item label="Комиссия" span={1}>
              {transaction.fee ? formatAmount(transaction.fee) : '-'}
            </Descriptions.Item>
            <Descriptions.Item label="Тип" span={1}>
              {transaction.type}
            </Descriptions.Item>
            <Descriptions.Item label="Объявление" span={2}>
              ID: {transaction.listingId}
            </Descriptions.Item>
            
            <Descriptions.Item label="Создана" span={1}>
              {formatDate(transaction.createdAt)}
            </Descriptions.Item>
            <Descriptions.Item label="Обновлена" span={1}>
              {formatDate(transaction.updatedAt)}
            </Descriptions.Item>
            {transaction.expirationDate && (
              <Descriptions.Item label="Истекает" span={1}>
                {formatDate(transaction.expirationDate)}
              </Descriptions.Item>
            )}
          </Descriptions>
          
          {transaction.description && (
            <div className="mt-4">
              <Title level={5}>Описание</Title>
              <Text>{transaction.description}</Text>
            </div>
          )}
          
          {transaction.disputeReason && (
            <div className="mt-4">
              <Title level={5}>Причина спора</Title>
              <Text type="warning">{transaction.disputeReason}</Text>
            </div>
          )}
          
          {transaction.disputeResolution && (
            <div className="mt-4">
              <Title level={5}>Резолюция спора</Title>
              <Text>{transaction.disputeResolution}</Text>
            </div>
          )}
          
          <Divider orientation="left">История транзакции</Divider>
          
          {timeline.length > 0 ? (
            <Timeline mode="left">
              {timeline.map((item, index) => (
                <Timeline.Item 
                  key={item.id} 
                  dot={getStatusIcon(item.newStatus)}
                >
                  <div>
                    <Text strong>{getStatusText(item.newStatus)}</Text>
                    <div>{formatDate(item.timestamp)}</div>
                    {item.reason && <div className="mt-1 text-gray-500">{item.reason}</div>}
                    {item.initiatorId && (
                      <div className="mt-1 text-gray-500">
                        Инициатор: {item.initiatorType} (ID: {item.initiatorId})
                      </div>
                    )}
                  </div>
                </Timeline.Item>
              ))}
            </Timeline>
          ) : (
            <Empty description="История транзакции недоступна" />
          )}
        </div>
      ) : (
        <Empty description="Транзакция не найдена" />
      )}
    </Modal>
  );
};

export default TransactionDetails; 