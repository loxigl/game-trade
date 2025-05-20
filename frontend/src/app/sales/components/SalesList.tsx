'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Table, Tag, Button, Input, Space, Spin, Empty, message, Modal } from 'antd';
import { SearchOutlined, FilterOutlined, SortAscendingOutlined, SortDescendingOutlined, EditOutlined, EyeOutlined, PauseCircleOutlined, PlayCircleOutlined, DeleteOutlined } from '@ant-design/icons';
import Link from 'next/link';
import { useAuth } from '../../hooks/auth';
import { useMarketplace } from '../../hooks/marketplace';
import { format } from 'date-fns';
import { getCompletedSales, pauseListing, activateListing, deleteListing } from '../../api/market';
import { Listing } from '../../api/market';
import EditListingModal from './EditListingModal';

interface SalesListProps {
  status: 'active' | 'sold' | 'all';
}

const SalesList: React.FC<SalesListProps> = ({ status }) => {
  const { user } = useAuth();
  const { getUserListings } = useMarketplace();
  const [sales, setSales] = useState<Listing[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchText, setSearchText] = useState('');
  const [filteredSales, setFilteredSales] = useState<Listing[]>([]);
  const [sortDirection, setSortDirection] = useState<'asc' | 'desc'>('desc');
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 10,
    total: 0
  });
  const [selectedListing, setSelectedListing] = useState<Listing | null>(null);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [actionLoading, setActionLoading] = useState<number | null>(null);
  const adaptResponse = (res: any) => {
    const items = res?.items ?? res?.data ?? [];   // items или data
    const meta  = res?.meta ?? {};
  
    return {
      items,
      total: meta.total ?? items.length,
      page:  meta.page  ?? 1,
      size:  meta.limit ?? items.length,
      pages: meta.pages ?? 1,
    };
  };
  // Получение списка продаж
  const fetchSales = useCallback(async (page = 1, pageSize = 10) => {
    setLoading(true);
    try {
      // Получаем данные через API
      const apiStatus = status === 'all' ? undefined : status;
      
      // Используем другой API для завершенных продаж
      let rawResponse;
      if (status === 'sold') {
        rawResponse = await getCompletedSales(undefined, page, pageSize);
      } else {
        rawResponse = await getUserListings(apiStatus, page, pageSize, 'created_at', 'desc');
      }
      const response = adaptResponse(rawResponse);
      const mapListing = (l: any): Listing => ({
        ...l,
        createdAt: l.createdAt || l.created_at,
      });
      const mappedItems = response.items.map(mapListing);
      setSales(mappedItems);
      setFilteredSales(mappedItems);
      setPagination({
        current: response.page,
        pageSize: response.size,
        total: response.total
      });
    } catch (error) {
      console.error('Ошибка при получении списка продаж:', error);
      message.error('Не удалось загрузить список продаж');
    } finally {
      setLoading(false);
    }
  }, [status, getUserListings]);

  useEffect(() => {
    fetchSales();
  }, [fetchSales]);

  // Обработчик изменения пагинации и сортировки
  const handleTableChange = (pagination: any) => {
    fetchSales(pagination.current, pagination.pageSize);
  };

  // Поиск по названию - локальный поиск после загрузки данных
  useEffect(() => {
    if (searchText) {
      const filtered = sales.filter(sale => 
        sale.title.toLowerCase().includes(searchText.toLowerCase()) ||
        (sale.game?.name && sale.game.name.toLowerCase().includes(searchText.toLowerCase()))
      );
      setFilteredSales(filtered);
    } else {
      setFilteredSales(sales);
    }
  }, [searchText, sales]);

  // Сортировка по дате
  const handleSortToggle = () => {
    const newDirection = sortDirection === 'asc' ? 'desc' : 'asc';
    setSortDirection(newDirection);
    
    setFilteredSales(prev => {
      const sorted = [...prev].sort((a, b) => {
        const dateA = new Date(a.createdAt).getTime();
        const dateB = new Date(b.createdAt).getTime();
        return newDirection === 'asc' ? dateA - dateB : dateB - dateA;
      });
      return sorted;
    });
  };

  // Открытие модального окна редактирования
  const handleEdit = (listing: Listing) => {
    setSelectedListing(listing);
    setIsEditModalOpen(true);
  };

  // Успешное редактирование объявления
  const handleEditSuccess = () => {
    fetchSales(pagination.current, pagination.pageSize);
  };

  // Приостановка объявления
  const handlePauseListing = async (listingId: number) => {
    setActionLoading(listingId);
    try {
      await pauseListing(listingId);
      message.success('Объявление приостановлено');
      fetchSales(pagination.current, pagination.pageSize);
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
      fetchSales(pagination.current, pagination.pageSize);
    } catch (error) {
      console.error('Ошибка при активации объявления:', error);
      message.error('Не удалось активировать объявление');
    } finally {
      setActionLoading(null);
    }
  };

  // Удаление объявления
  const handleDeleteListing = (listing: Listing) => {
    Modal.confirm({
      title: 'Удаление объявления',
      content: `Вы действительно хотите удалить объявление "${listing.title}"?`,
      okText: 'Удалить',
      okType: 'danger',
      cancelText: 'Отмена',
      onOk: async () => {
        setActionLoading(listing.id);
        try {
          await deleteListing(listing.id);
          message.success('Объявление удалено');
          fetchSales(pagination.current, pagination.pageSize);
        } catch (error) {
          console.error('Ошибка при удалении объявления:', error);
          message.error('Не удалось удалить объявление');
        } finally {
          setActionLoading(null);
        }
      }
    });
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
      render: (text: string, record: Listing) => (
        <Link href={`/marketplace/listings/${record.id}`} className="text-blue-600 hover:underline">
          {text}
        </Link>
      ),
    },
    {
      title: 'Игра',
      dataIndex: ['game', 'name'],
      key: 'game',
      render: (_: string, record: Listing) => record.game?.name || '-',
    },
    {
      title: 'Цена',
      dataIndex: 'price',
      key: 'price',
      render: (price: number, record: Listing) => formatPrice(price, record.currency),
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
      render: (_: unknown, record: Listing) => (
        <Space>
          {record.status === 'active' && (
            <Button 
              size="small" 
              type="primary"
              icon={<EditOutlined />}
              onClick={() => handleEdit(record)}
            >
              Редактировать
            </Button>
          )}
          
          <Link href={`/marketplace/listings/${record.id}`} passHref>
            <Button size="small" icon={<EyeOutlined />}>
              Просмотр
            </Button>
          </Link>

          {record.status === 'active' && (
            <Button 
              size="small" 
              icon={<PauseCircleOutlined />}
              onClick={() => handlePauseListing(record.id)}
              loading={actionLoading === record.id}
            >
              Приостановить
            </Button>
          )}

          {record.status === 'paused' && (
            <Button 
              size="small" 
              type="primary"
              ghost
              icon={<PlayCircleOutlined />}
              onClick={() => handleActivateListing(record.id)}
              loading={actionLoading === record.id}
            >
              Активировать
            </Button>
          )}

          {(record.status === 'active' || record.status === 'paused') && (
            <Button 
              size="small" 
              danger
              icon={<DeleteOutlined />}
              onClick={() => handleDeleteListing(record)}
              loading={actionLoading === record.id}
            >
              Удалить
            </Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div className="sales-list">
      <div className="mb-4 flex flex-wrap justify-between items-center">
        <Space className="mb-2 sm:mb-0">
          <Input
            placeholder="Поиск по названию или игре"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            prefix={<SearchOutlined />}
            allowClear
            style={{ width: 250 }}
          />
          <Button 
            icon={sortDirection === 'asc' ? <SortAscendingOutlined /> : <SortDescendingOutlined />}
            onClick={handleSortToggle}
          >
            {sortDirection === 'asc' ? 'По возрастанию' : 'По убыванию'}
          </Button>
        </Space>
      </div>
      
      {loading && sales.length === 0 ? (
        <div className="flex justify-center items-center py-10">
          <Spin size="large" tip="Загрузка продаж..." />
        </div>
      ) : filteredSales.length === 0 ? (
        <Empty 
          description={
            <span className="text-gray-600 ">
              {searchText 
                ? 'По вашему запросу ничего не найдено' 
                : status === 'active' 
                  ? 'У вас нет активных объявлений'
                  : 'У вас нет завершенных продаж'
              }
            </span>
          }
        />
      ) : (
        <div className="overflow-x-auto">
          <Table 
            dataSource={filteredSales} 
            columns={columns} 
            rowKey="id"
            pagination={pagination}
            onChange={handleTableChange}
            loading={loading}
            scroll={{ x: 'max-content' }}
            className="sales-table"
          />
        </div>
      )}
      
      {/* Модальное окно редактирования объявления */}
      {selectedListing && (
        <EditListingModal
          listing={selectedListing}
          isOpen={isEditModalOpen}
          onClose={() => setIsEditModalOpen(false)}
          onSuccess={handleEditSuccess}
        />
      )}
    </div>
  );
};

export default SalesList; 