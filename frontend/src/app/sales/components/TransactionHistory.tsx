'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Table, Card, DatePicker, Button, Select, Space, Tag, Input, Spin, Empty, message, Tooltip } from 'antd';
import { DownloadOutlined, FileExcelOutlined, FilePdfOutlined, SearchOutlined, FilterOutlined } from '@ant-design/icons';
import { format } from 'date-fns';
import { useAuth } from '../../hooks/auth';
import { getTransactionsHistory, generateTransactionsReport } from '../../api/transaction';
import { TransactionHistoryItem, TransactionStatus, TransactionType } from '../../types/transaction';
import TransactionDetails from './TransactionDetails';

const { RangePicker } = DatePicker;
const { Option } = Select;

const TransactionHistory: React.FC = () => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [transactions, setTransactions] = useState<TransactionHistoryItem[]>([]);
  const [filteredTransactions, setFilteredTransactions] = useState<TransactionHistoryItem[]>([]);
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 10,
    total: 0
  });
  
  // Фильтры
  const [searchText, setSearchText] = useState('');
  const [dateRange, setDateRange] = useState<[Date, Date] | null>(null);
  const [typeFilter, setTypeFilter] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [selectedTransactionId, setSelectedTransactionId] = useState<number | null>(null);
  const [isDetailsModalOpen, setIsDetailsModalOpen] = useState(false);

  // Получение истории транзакций
  const fetchTransactions = useCallback(async (page = 1, pageSize = 10) => {
    if (!user?.id) return;
    
    setLoading(true);
    try {
      const type = typeFilter as TransactionType | undefined;
      const status = statusFilter as TransactionStatus | undefined;
      
      const response = await getTransactionsHistory(
        user.id,
        type,
        status,
        dateRange ? dateRange[0] : undefined,
        dateRange ? dateRange[1] : undefined,
        page,
        pageSize
      );
      
      setTransactions(response.items);
      setFilteredTransactions(response.items);
      setPagination({
        current: response.page,
        pageSize: response.size,
        total: response.total
      });
    } catch (error) {
      console.error('Ошибка при получении истории транзакций:', error);
      message.error('Не удалось загрузить историю транзакций');
    } finally {
      setLoading(false);
    }
  }, [user?.id, typeFilter, statusFilter, dateRange]);

  // Загрузка данных при первоначальном рендере
  useEffect(() => {
    fetchTransactions();
  }, [fetchTransactions]);

  // Обработчик изменения пагинации и сортировки
  const handleTableChange = (pagination: any, filters: any, sorter: any) => {
    fetchTransactions(pagination.current, pagination.pageSize);
  };

  // Применение поискового фильтра (локально, после загрузки данных)
  useEffect(() => {
    if (searchText && transactions.length > 0) {
      const filtered = transactions.filter(tx => 
        tx.reason?.toLowerCase().includes(searchText.toLowerCase()) ||
        tx.transactionId.toString().includes(searchText) ||
        tx.initiatorType?.toLowerCase().includes(searchText.toLowerCase())
      );
      setFilteredTransactions(filtered);
    } else {
      setFilteredTransactions(transactions);
    }
  }, [searchText, transactions]);

  // Фильтрация по типу и статусу через API
  useEffect(() => {
    fetchTransactions(1, pagination.pageSize);
  }, [typeFilter, statusFilter, dateRange, fetchTransactions]);

  // Экспорт транзакций в CSV
  const exportTransactionsCSV = async () => {
    if (filteredTransactions.length === 0) {
      message.warning('Нет данных для экспорта');
      return;
    }
    
    try {
      const blob = await generateTransactionsReport(
        user?.id,
        statusFilter as TransactionStatus | undefined,
        dateRange ? dateRange[0] : undefined,
        dateRange ? dateRange[1] : undefined,
        'csv'
      );
      
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `transactions-${new Date().toISOString().split('T')[0]}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      message.success('Отчёт успешно сгенерирован и скачан');
    } catch (error) {
      console.error('Ошибка при экспорте отчета:', error);
      message.error('Не удалось экспортировать отчет');
    }
  };

  // Экспорт транзакций в Excel
  const exportTransactionsExcel = async () => {
    if (filteredTransactions.length === 0) {
      message.warning('Нет данных для экспорта');
      return;
    }
    
    try {
      const blob = await generateTransactionsReport(
        user?.id,
        statusFilter as TransactionStatus | undefined,
        dateRange ? dateRange[0] : undefined,
        dateRange ? dateRange[1] : undefined,
        'excel'
      );
      
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `transactions-${new Date().toISOString().split('T')[0]}.xlsx`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      message.success('Excel-файл успешно сгенерирован и скачан');
    } catch (error) {
      console.error('Ошибка при экспорте отчета:', error);
      message.error('Не удалось экспортировать отчет');
    }
  };

  // Очистка всех фильтров
  const clearAllFilters = () => {
    setSearchText('');
    setDateRange(null);
    setTypeFilter(null);
    setStatusFilter(null);
  };

  // Получение названия для статуса
  const getStatusText = (status: string) => {
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

  // Получение названия для типа транзакции
  const getTypeText = (type: string) => {
    switch (type) {
      case TransactionType.PURCHASE:
        return 'Покупка';
      case TransactionType.WITHDRAWAL:
        return 'Вывод';
      case TransactionType.DEPOSIT:
        return 'Пополнение';
      case TransactionType.REFUND:
        return 'Возврат';
      case TransactionType.FEE:
        return 'Комиссия';
      default:
        return type;
    }
  };

  // Получение цвета тега для статуса
  const getStatusTagColor = (status: string) => {
    switch (status) {
      case TransactionStatus.COMPLETED:
        return 'green';
      case TransactionStatus.PENDING:
        return 'blue';
      case TransactionStatus.ESCROW_HELD:
        return 'cyan';
      case TransactionStatus.REFUNDED:
        return 'purple';
      case TransactionStatus.DISPUTED:
        return 'orange';
      case TransactionStatus.RESOLVED:
        return 'geekblue';
      case TransactionStatus.CANCELED:
        return 'red';
      default:
        return 'default';
    }
  };

  // Открытие модального окна с деталями транзакции
  const showTransactionDetails = (transactionId: number) => {
    setSelectedTransactionId(transactionId);
    setIsDetailsModalOpen(true);
  };

  // Определение колонок таблицы
  const columns = [
    {
      title: 'ID',
      dataIndex: 'transactionId',
      key: 'transactionId',
      render: (text: number) => (
        <Tooltip title="Нажмите для просмотра деталей">
          <Button 
            type="link" 
            onClick={() => showTransactionDetails(text)}
            style={{ padding: 0 }}
          >
            TRX-{text}
          </Button>
        </Tooltip>
      ),
    },
    {
      title: 'Дата',
      dataIndex: 'timestamp',
      key: 'timestamp',
      sorter: true,
      render: (date: string) => format(new Date(date), 'dd.MM.yyyy HH:mm'),
    },
    {
      title: 'Статус изменен на',
      dataIndex: 'newStatus',
      key: 'newStatus',
      render: (status: string) => (
        <Tag color={getStatusTagColor(status)}>
          {getStatusText(status)}
        </Tag>
      ),
    },
    {
      title: 'Инициатор',
      dataIndex: 'initiatorType',
      key: 'initiatorType',
      render: (text: string, record: TransactionHistoryItem) => 
        record.initiatorType ? `${record.initiatorType} (ID: ${record.initiatorId})` : '-',
    },
    {
      title: 'Причина',
      dataIndex: 'reason',
      key: 'reason',
      ellipsis: true,
      render: (text: string) => text || '-',
    },
  ];

  if (loading && !transactions.length) {
    return (
      <div className="flex justify-center items-center py-10">
        <Spin size="large" tip="Загрузка истории транзакций..." />
      </div>
    );
  }

  return (
    <div className="transaction-history">
      <Card className="mb-6 shadow-sm">
        <div className="flex flex-col lg:flex-row lg:justify-between lg:items-center">
          <div className="mb-4 lg:mb-0">
            <Input 
              placeholder="Поиск по ID, причине или инициатору" 
              value={searchText}
              onChange={e => setSearchText(e.target.value)}
              prefix={<SearchOutlined />}
              allowClear
              className="w-full lg:w-80"
            />
          </div>
          
          <Space wrap>
            <Select
              placeholder="Тип транзакции"
              style={{ width: 150 }}
              allowClear
              value={typeFilter}
              onChange={value => setTypeFilter(value)}
            >
              <Option value={TransactionType.PURCHASE}>Покупка</Option>
              <Option value={TransactionType.WITHDRAWAL}>Вывод</Option>
              <Option value={TransactionType.DEPOSIT}>Пополнение</Option>
              <Option value={TransactionType.REFUND}>Возврат</Option>
              <Option value={TransactionType.FEE}>Комиссия</Option>
            </Select>
            
            <Select
              placeholder="Статус"
              style={{ width: 150 }}
              allowClear
              value={statusFilter}
              onChange={value => setStatusFilter(value)}
            >
              <Option value={TransactionStatus.COMPLETED}>Завершено</Option>
              <Option value={TransactionStatus.PENDING}>В обработке</Option>
              <Option value={TransactionStatus.ESCROW_HELD}>В Escrow</Option>
              <Option value={TransactionStatus.REFUNDED}>Возврат</Option>
              <Option value={TransactionStatus.DISPUTED}>Спор</Option>
              <Option value={TransactionStatus.RESOLVED}>Разрешено</Option>
              <Option value={TransactionStatus.CANCELED}>Отменено</Option>
            </Select>
            
            <RangePicker 
              onChange={(dates) => {
                if (dates) {
                  setDateRange([dates[0]!.toDate(), dates[1]!.toDate()]);
                } else {
                  setDateRange(null);
                }
              }}
            />
            
            <Button 
              icon={<FilterOutlined />} 
              onClick={clearAllFilters}
            >
              Сбросить
            </Button>
          </Space>
        </div>
      </Card>
      
      <Card className="shadow-sm">
        <div className="flex justify-between items-center mb-4">
          <div className="text-base font-medium">{filteredTransactions.length} транзакций</div>
          <Space>
            <Button icon={<DownloadOutlined />} onClick={exportTransactionsCSV}>
              Экспорт CSV
            </Button>
            <Button icon={<FileExcelOutlined />} onClick={exportTransactionsExcel}>
              Экспорт Excel
            </Button>
          </Space>
        </div>
        
        <Table 
          dataSource={filteredTransactions}
          columns={columns}
          rowKey="id"
          pagination={pagination}
          onChange={handleTableChange}
          loading={loading}
          scroll={{ x: true }}
        />
      </Card>

      {/* Модальное окно с деталями транзакции */}
      {selectedTransactionId && (
        <TransactionDetails
          transactionId={selectedTransactionId}
          isOpen={isDetailsModalOpen}
          onClose={() => setIsDetailsModalOpen(false)}
        />
      )}
    </div>
  );
};

export default TransactionHistory; 