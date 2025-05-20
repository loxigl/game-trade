import React from 'react';
import { Card, Typography, Space, Button, Tooltip, Divider, Tag } from 'antd';
import { ClockCircleOutlined, DollarOutlined, UserOutlined, ShoppingOutlined, ShopOutlined } from '@ant-design/icons';
import { Transaction } from '../../types/transaction';
import TransactionStatusBadge from './TransactionStatusBadge';
import { useRouter } from 'next/navigation';
import formatDate from '../../utils/formatDate';

const { Text, Title } = Typography;

interface TransactionCardProps {
  transaction: Transaction;
}

const TransactionCard: React.FC<TransactionCardProps> = ({ transaction }) => {
  const router = useRouter();
  
  const handleViewDetails = () => {
    router.push(`/transactions/${transaction.id}`);
  };

  return (
    <Card 
      hoverable
      className="mb-4 transaction-card"
      onClick={handleViewDetails}
    >
      <div className="flex flex-col md:flex-row justify-between">
        <div className="mb-2 md:mb-0">
          <Title level={5}>
            Транзакция #{transaction.id}
          </Title>
          <Space size={8} direction="vertical">
            <Space>
              <DollarOutlined /> 
              <Text strong>{transaction.amount.toFixed(2)}</Text>
            </Space>
            <Space>
              {transaction.type === 'sale' || transaction.type === 'seller_payout' ? (
                <>
                  <ShopOutlined style={{ color: '#52c41a' }} />
                  <Text>Моя продажа</Text>
                </>
              ) : (
                <>
                  <ShoppingOutlined style={{ color: '#1890ff' }} />
                  <Text>Моя покупка</Text>
                </>
              )}
            </Space>
            <Space>
              <UserOutlined /> 
              <Text>{transaction.type === 'sale' || transaction.type === 'seller_payout' ? 'Покупатель' : 'Продавец'}: ID {transaction.type === 'sale' || transaction.type === 'seller_payout' ? transaction.buyerId : transaction.sellerId}</Text>
            </Space>
            <Space>
              <ClockCircleOutlined /> 
              <Text>{formatDate(transaction.createdAt, 'dd.MM.yyyy HH:mm')}</Text>
            </Space>
          </Space>
        </div>
        
        <div className="flex flex-col items-start md:items-end">
          <TransactionStatusBadge status={transaction.status} />
          
          {transaction.expirationDate && (
            <Tooltip title="Дата истечения срока">
              <Text type="secondary" className="mt-2">
                Истекает: {formatDate(transaction.expirationDate, 'dd.MM.yyyy HH:mm')}
              </Text>
            </Tooltip>
          )}
          
          <Divider className="my-2" />
          
          <Button type="primary" size="small" onClick={(e) => {
            e.stopPropagation();
            handleViewDetails();
          }}>
            Подробнее
          </Button>
        </div>
      </div>
    </Card>
  );
};

export default TransactionCard; 