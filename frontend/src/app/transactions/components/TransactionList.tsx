import React, { useState, useEffect, useCallback } from 'react';
import { 
  List, 
  Select, 
  Space, 
  Input, 
  Typography, 
  Pagination, 
  Spin, 
  Empty, 
  message
} from 'antd';
import { SearchOutlined, FilterOutlined } from '@ant-design/icons';
import { Transaction, TransactionStatus, TransactionListResponse } from '../../types/transaction';
import TransactionCard from './TransactionCard';
import * as transactionApi from '../../api/transaction';

const { Title } = Typography;
const { Option } = Select;

interface TransactionListProps {
  userId?: number; // ID пользователя для фильтрации (если не указан, показываются все)
  pageSize?: number; // Размер страницы
  isSellerView?: boolean; // Показывать ли транзакции, где пользователь - продавец (иначе как покупатель)
}

const TransactionList: React.FC<TransactionListProps> = ({ 
  userId, 
  pageSize = 10, 
  isSellerView = false
}) => {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [page, setPage] = useState<number>(1);
  const [loading, setLoading] = useState<boolean>(true);
  const [statusFilter, setStatusFilter] = useState<TransactionStatus | undefined>(undefined);
  const [searchQuery, setSearchQuery] = useState<string>('');

  // Создаем стабильную функцию fetchTransactions с помощью useCallback
  const fetchTransactions = useCallback(async () => {
    setLoading(true);
    
    try {
      // В реальном приложении добавить поддержку поиска по строке query на бэкенде
      // Здесь мы просто загружаем данные с фильтрами status и userId
      const response = await transactionApi.getUserTransactions(
        userId,
        statusFilter,
        page,
        pageSize,
        isSellerView
      );
      
      setTransactions(response.items);
      setTotal(response.total);
    } catch (error) {
      console.error('Ошибка загрузки транзакций:', error);
      message.error('Не удалось загрузить список транзакций');
    } finally {
      setLoading(false);
    }
  }, [userId, page, pageSize, statusFilter, isSellerView]);

  // Загрузка транзакций
  useEffect(() => {
    fetchTransactions();
  }, [fetchTransactions]);

  // Обработчик изменения фильтра статуса
  const handleStatusChange = (value: TransactionStatus | undefined) => {
    setStatusFilter(value);
    setPage(1); // Сбрасываем на первую страницу при изменении фильтра
  };

  // Обработчик изменения страницы
  const handlePageChange = (newPage: number) => {
    setPage(newPage);
  };

  // Обработчик изменения поискового запроса
  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value);
  };

  // Обработчик нажатия кнопки поиска
  const handleSearch = () => {
    setPage(1); // Сбрасываем на первую страницу при поиске
    fetchTransactions();
  };

  return (
    <div className="transaction-list">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6">
        <Title level={4} className="mb-4 md:mb-0">
          {isSellerView ? 'Мои продажи' : 'Мои покупки'}
        </Title>
        
        <Space direction="horizontal" wrap>
          <Input
            placeholder="Поиск по ID или описанию"
            prefix={<SearchOutlined />}
            allowClear
            value={searchQuery}
            onChange={handleSearchChange}
            onPressEnter={handleSearch}
            style={{ width: 250 }}
          />
          
          <Select
            placeholder="Статус транзакции"
            allowClear
            style={{ width: 200 }}
            value={statusFilter}
            onChange={handleStatusChange}
            suffixIcon={<FilterOutlined />}
          >
            <Option value={TransactionStatus.PENDING}>В ожидании</Option>
            <Option value={TransactionStatus.ESCROW_HELD}>В Escrow</Option>
            <Option value={TransactionStatus.COMPLETED}>Завершена</Option>
            <Option value={TransactionStatus.REFUNDED}>Возврат</Option>
            <Option value={TransactionStatus.DISPUTED}>Спор</Option>
            <Option value={TransactionStatus.RESOLVED}>Разрешена</Option>
            <Option value={TransactionStatus.CANCELED}>Отменена</Option>
          </Select>
        </Space>
      </div>
      
      {loading ? (
        <div className="flex justify-center items-center min-h-[200px]">
          <Spin tip="Загрузка транзакций..." />
        </div>
      ) : transactions.length === 0 ? (
        <Empty description="Транзакции не найдены" />
      ) : (
        <>
          <List
            dataSource={transactions}
            renderItem={(transaction) => (
              <List.Item key={transaction.id}>
                <TransactionCard transaction={transaction} />
              </List.Item>
            )}
          />
          
          <div className="flex justify-center mt-6">
            <Pagination
              current={page}
              total={total}
              pageSize={pageSize}
              onChange={handlePageChange}
              showSizeChanger={false}
              showTotal={(total) => `Всего ${total} транзакций`}
            />
          </div>
        </>
      )}
    </div>
  );
};

export default TransactionList; 