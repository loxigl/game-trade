import React, { useState, useEffect } from 'react';
import { Timeline, Typography, Spin, Empty, Tag, Tooltip, Card } from 'antd';
import { ClockCircleOutlined, InfoCircleOutlined, UserOutlined, RobotOutlined, ToolOutlined } from '@ant-design/icons';
import { TransactionHistoryItem, TransactionStatus } from '../../types/transaction';
import * as transactionApi from '../../api/transaction';
import formatDate from '../../utils/formatDate';

const { Title, Text } = Typography;

interface TransactionHistoryTimelineProps {
  transactionId: number;
}

// Получение иконки для типа инициатора
const getInitiatorIcon = (initiatorType?: string) => {
  switch (initiatorType) {
    case 'user':
      return <UserOutlined />;
    case 'admin':
      return <ToolOutlined />;
    case 'system':
    default:
      return <RobotOutlined />;
  }
};

// Форматирование даты/времени для отображения
const formatTimestamp = (timestamp: string): string => {
  try {
    return formatDate(timestamp);
  } catch (error) {
    return timestamp;
  }
};

// Получение цвета для строки временной линии в зависимости от статуса
const getStatusColor = (status: TransactionStatus): string => {
  switch (status) {
    case TransactionStatus.PENDING:
      return 'orange';
    case TransactionStatus.ESCROW_HELD:
      return 'blue';
    case TransactionStatus.COMPLETED:
      return 'green';
    case TransactionStatus.REFUNDED:
      return 'purple';
    case TransactionStatus.DISPUTED:
      return 'red';
    case TransactionStatus.RESOLVED:
      return 'cyan';
    case TransactionStatus.CANCELED:
      return 'gray';
    default:
      return 'blue';
  }
};

const TransactionHistoryTimeline: React.FC<TransactionHistoryTimelineProps> = ({ transactionId }) => {
  const [timeline, setTimeline] = useState<TransactionHistoryItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchTimeline = async () => {
      try {
        setLoading(true);
        const historyData = await transactionApi.getTransactionTimeline(transactionId);
        setTimeline(historyData);
      } catch (err) {
        console.error('Ошибка при получении таймлайна:', err);
        setError('Не удалось загрузить историю транзакции');
      } finally {
        setLoading(false);
      }
    };

    fetchTimeline();
  }, [transactionId]);

  if (loading) {
    return (
      <div className="flex justify-center items-center h-40">
        <Spin tip="Загрузка истории транзакции..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center text-red-500">
        <InfoCircleOutlined className="mr-2" />
        {error}
      </div>
    );
  }

  if (!timeline.length) {
    return <Empty description="История транзакции не найдена" />;
  }

  return (
    <Card className="transaction-history-timeline">
      <Title level={5} className="mb-4">История изменений статуса</Title>
      
      <Timeline mode="left">
        {timeline.map((item) => (
          <Timeline.Item 
            key={item.id}
            color={getStatusColor(item.newStatus)}
            label={formatTimestamp(item.timestamp)}
          >
            <div className="flex flex-col">
              <div className="flex items-center mb-1">
                <Text strong>
                  {item.previousStatus ? (
                    <>
                      {item.previousStatus} <span className="mx-1">&rarr;</span> {item.newStatus}
                    </>
                  ) : (
                    <>Создание: {item.newStatus}</>
                  )}
                </Text>
              </div>
              
              {item.reason && (
                <Text type="secondary" className="ml-1">
                  {item.reason}
                </Text>
              )}
              
              <div className="flex items-center mt-1">
                <Tooltip title={`Инициатор: ${item.initiatorType || 'система'}`}>
                  <Tag icon={getInitiatorIcon(item.initiatorType)}>
                    {item.initiatorType === 'user' ? 'Пользователь' : 
                      item.initiatorType === 'admin' ? 'Администратор' : 'Система'}
                    {item.initiatorId ? ` #${item.initiatorId}` : ''}
                  </Tag>
                </Tooltip>
              </div>
            </div>
          </Timeline.Item>
        ))}
      </Timeline>
    </Card>
  );
};

export default TransactionHistoryTimeline; 