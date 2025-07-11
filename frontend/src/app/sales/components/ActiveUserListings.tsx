'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Table, Tag, Button, Input, Space, Spin, Empty, message, Pagination } from 'antd';
import { SearchOutlined, SortAscendingOutlined, SortDescendingOutlined, EditOutlined, EyeOutlined, PauseCircleOutlined, PlayCircleOutlined, DeleteOutlined } from '@ant-design/icons';
import Link from 'next/link';
import { useAuth } from '../../hooks/auth';
import { useMarketplace } from '../../hooks/marketplace';
import { format } from 'date-fns';
import { pauseListing, activateListing, deleteListing } from '../../api/market';

interface ActiveUserListingsProps {
  status?: string; // Можно передать 'active', 'paused' или undefined для всех
}

const ActiveUserListings: React.FC<ActiveUserListingsProps> = ({ status = 'active' }) => {
  const { user } = useAuth();
  const { getUserListings, isLoading, error } = useMarketplace();
  
  const [listings, setListings] = useState<any[]>([]);
  const [filteredListings, setFilteredListings] = useState<any[]>([]);
  const [searchText, setSearchText] = useState('');
  const [listingStatus, setListingStatus] = useState<string | undefined>(status);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 10,
    total: 0
  });
  const [actionLoading, setActionLoading] = useState<number | null>(null);

  // Получение списка объявлений пользователя
  const fetchUserListings = useCallback(async (page = 1, pageSize = 10) => {
    try {
      const response = await getUserListings(
        listingStatus,
        page,
        pageSize,
        'created_at',
        sortDirection
      );
      
      const items = response.items.map(item => ({
        ...item,
        createdAt: item.created_at || item.createdAt,
        updatedAt: item.updated_at || item.updatedAt,
        viewsCount: item.views_count || item.viewsCount
      }));
      
      setListings(items);
      setFilteredListings(items);
      setPagination({
        current: response.meta.current_page,
        pageSize: response.meta.items_per_page,
        total: response.meta.total_items
      });
    } catch (error) {
      console.error('Ошибка при получении объявлений пользователя:', error);
      message.error('Не удалось загрузить объявления пользователя');
    }
  }, [getUserListings, listingStatus, sortDirection]);

  useEffect(() => {
    fetchUserListings();
  }, [fetchUserListings]);

  // Обработка изменения поискового запроса
  useEffect(() => {
    if (searchText) {
      const filtered = listings.filter(listing => 
        listing.title.toLowerCase().includes(searchText.toLowerCase())
      );
      setFilteredListings(filtered);
    } else {
      setFilteredListings(listings);
    }
  }, [searchText, listings]);

  // Сортировка по дате
  const handleSortToggle = () => {
    const newDirection = sortDirection === 'asc' ? 'desc' : 'asc';
    setSortDirection(newDirection);
  };

  // Обработчик изменения статуса
  const handleStatusChange = (newStatus: string | undefined) => {
    setListingStatus(newStatus);
  };

  // Обработчик изменения пагинации
  const handlePaginationChange = (page: number, pageSize?: number) => {
    fetchUserListings(page, pageSize || pagination.pageSize);
  };

  // Приостановка объявления
  const handlePauseListing = async (listingId: number) => {
    setActionLoading(listingId);
    try {
      await pauseListing(listingId);
      message.success('Объявление приостановлено');
      fetchUserListings(pagination.current, pagination.pageSize);
    } catch (error) {
      console.error('Ошибка при приостановке объявления:', error);
      message.error('Не удалось приостановить объявление');
    } finally {
      setActionLoading(null);
    }
  };

  // Активация объявления
  const handleActivateListing = async (listingId: number) => {
    setActionLoading(listingId);
    try {
      await activateListing(listingId);
      message.success('Объявление активировано');
      fetchUserListings(pagination.current, pagination.pageSize);
    } catch (error) {
      console.error('Ошибка при активации объявления:', error);
      message.error('Не удалось активировать объявление');
    } finally {
      setActionLoading(null);
    }
  };

  // Удаление объявления
  const handleDeleteListing = async (listingId: number) => {
    setActionLoading(listingId);
    try {
      await deleteListing(listingId);
      message.success('Объявление удалено');
      fetchUserListings(pagination.current, pagination.pageSize);
    } catch (error) {
      console.error('Ошибка при удалении объявления:', error);
      message.error('Не удалось удалить объявление');
    } finally {
      setActionLoading(null);
    }
  };

  // Отображение статуса
  const renderStatus = (status: string) => {
    switch (status) {
      case 'active':
        return <Tag color="green">Активно</Tag>;
      case 'sold':
        return <Tag color="blue">Продано</Tag>;
      case 'completed':
        return <Tag color="blue">Завершено</Tag>;
      case 'pending':
        return <Tag color="orange">Ожидает</Tag>;
      case 'rejected':
        return <Tag color="red">Отклонено</Tag>;
      case 'paused':
        return <Tag color="gray">Приостановлено</Tag>;
      default:
        return <Tag>{status}</Tag>;
    }
  };

  // Форматирование цены
  const formatPrice = (price: number, currency: string) => {
    switch (currency) {
      case 'USD':
        return `$${price}`;
      case 'EUR':
        return `€${price}`;
      case 'RUB':
        return `${price} ₽`;
      default:
        return `${price} ${currency}`;
    }
  };

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 70,
    },
    {
      title: 'Название',
      dataIndex: 'title',
      key: 'title',
      render: (text: string, record: any) => (
        <Link href={`/marketplace/listings/${record.id}`} className="text-blue-600 hover:underline">
          {text}
        </Link>
      ),
    },
    {
      title: 'Цена',
      dataIndex: 'price',
      key: 'price',
      render: (price: number, record: any) => formatPrice(price, record.currency),
    },
    {
      title: 'Статус',
      dataIndex: 'status',
      key: 'status',
      render: renderStatus,
    },
    {
      title: 'Дата создания',
      dataIndex: 'createdAt',
      key: 'createdAt',
      render: (date: string) => format(new Date(date), 'dd.MM.yyyy HH:mm'),
    },
    {
      title: 'Просмотры',
      dataIndex: 'viewsCount',
      key: 'viewsCount',
    },
    {
      title: 'Действия',
      key: 'actions',
      render: (_: unknown, record: any) => (
        <Space>
          <Link href={`/marketplace/listings/${record.id}`} passHref>
            <Button size="small" icon={<EyeOutlined />}>
              Просмотр
            </Button>
          </Link>

          {record.status === 'active' && (
            <>
              <Link href={`/marketplace/listings/edit/${record.id}`} passHref>
                <Button size="small" type="primary" icon={<EditOutlined />}>
                  Редактировать
                </Button>
              </Link>
              <Button 
                size="small" 
                icon={<PauseCircleOutlined />} 
                onClick={() => handlePauseListing(record.id)}
                loading={actionLoading === record.id}
              >
                Приостановить
              </Button>
            </>
          )}

          {record.status === 'paused' && (
            <Button 
              size="small" 
              type="primary" 
              icon={<PlayCircleOutlined />} 
              onClick={() => handleActivateListing(record.id)}
              loading={actionLoading === record.id}
            >
              Активировать
            </Button>
          )}

          <Button 
            size="small" 
            danger 
            icon={<DeleteOutlined />} 
            onClick={() => handleDeleteListing(record.id)}
            loading={actionLoading === record.id}
          >
            Удалить
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div className="user-listings">
      <div className="mb-4 flex justify-between items-center">
        <h2 className="text-xl font-semibold">Мои объявления</h2>
        <div className="flex gap-2">
          <Input
            placeholder="Поиск по названию"
            prefix={<SearchOutlined />}
            value={searchText}
            onChange={e => setSearchText(e.target.value)}
            style={{ width: 200 }}
          />
          <Button 
            icon={sortDirection === 'asc' ? <SortAscendingOutlined /> : <SortDescendingOutlined />} 
            onClick={handleSortToggle}
          >
            {sortDirection === 'asc' ? 'По возрастанию' : 'По убыванию'}
          </Button>
        </div>
      </div>

      <div className="mb-4">
        <Space>
          <Button 
            type={listingStatus === undefined ? 'primary' : 'default'} 
            onClick={() => handleStatusChange(undefined)}
          >
            Все
          </Button>
          <Button 
            type={listingStatus === 'active' ? 'primary' : 'default'} 
            onClick={() => handleStatusChange('active')}
          >
            Активные
          </Button>
          <Button 
            type={listingStatus === 'sold' ? 'primary' : 'default'} 
            onClick={() => handleStatusChange('sold')}
          >
            Проданные
          </Button>
          <Button 
            type={listingStatus === 'paused' ? 'primary' : 'default'} 
            onClick={() => handleStatusChange('paused')}
          >
            Приостановленные
          </Button>
        </Space>
      </div>

      {isLoading && (
        <div className="flex justify-center py-10">
          <Spin size="large" />
        </div>
      )}

      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      {!isLoading && filteredListings.length === 0 && (
        <Empty 
          description="У вас пока нет объявлений" 
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      )}

      {!isLoading && filteredListings.length > 0 && (
        <>
          <Table 
            columns={columns}
            dataSource={filteredListings}
            rowKey="id"
            pagination={false}
            className="mb-4"
          />
          <Pagination
            current={pagination.current}
            pageSize={pagination.pageSize}
            total={pagination.total}
            onChange={handlePaginationChange}
            showSizeChanger
            showQuickJumper
            showTotal={(total) => `Всего ${total} объявлений`}
          />
        </>
      )}
    </div>
  );
};

export default ActiveUserListings; 