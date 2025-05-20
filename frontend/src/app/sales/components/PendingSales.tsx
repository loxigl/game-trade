'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Card, Steps, Button, Space, Spin, Empty, message, Modal, List, Typography, Tooltip } from 'antd';
import { 
  CheckCircleOutlined, 
  CloseCircleOutlined, 
  QuestionCircleOutlined,
  InfoCircleOutlined
} from '@ant-design/icons';
import { format } from 'date-fns';
import { useAuth } from '../../hooks/auth';
import { getPendingSales, confirmSale, rejectSale } from '../../api/market';
import { PendingSale as PendingSaleType } from '../../api/market';

const { Step } = Steps;
const { Text, Title } = Typography;

const PendingSales: React.FC = () => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [pendingSales, setPendingSales] = useState<PendingSaleType[]>([]);
  const [selectedSale, setSelectedSale] = useState<PendingSaleType | null>(null);
  const [isDetailsModalOpen, setIsDetailsModalOpen] = useState(false);
  const [isActionModalOpen, setIsActionModalOpen] = useState(false);
  const [actionType, setActionType] = useState<'approve' | 'reject' | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [pagination, setPagination] = useState({
    current: 1,
    pageSize: 10,
    total: 0
  });

  // Получение ожидающих продаж
  const fetchPendingSales = useCallback(async (page = 1, pageSize = 10) => {
    if (!user?.id) return;
    
    setLoading(true);
    try {
      const response = await getPendingSales(user.id, page, pageSize);
      
      setPendingSales(response.items);
      setPagination({
        current: response.page,
        pageSize: response.size,
        total: response.total
      });
    } catch (error) {
      console.error('Ошибка при получении ожидающих продаж:', error);
      message.error('Не удалось загрузить ожидающие продажи');
    } finally {
      setLoading(false);
    }
  }, [user?.id]);

  useEffect(() => {
    fetchPendingSales();
  }, [fetchPendingSales]);

  // Получение текущего статуса продажи в виде шага
  const getCurrentStep = (status: string) => {
    switch (status) {
      case 'pending':
        return 0;
      case 'payment_processing':
        return 1;
      case 'delivery_pending':
        return 2;
      default:
        return 0;
    }
  };

  // Открытие модального окна с деталями
  const showDetails = (sale: PendingSaleType) => {
    setSelectedSale(sale);
    setIsDetailsModalOpen(true);
  };

  // Открытие модального окна с подтверждением действия
  const showActionConfirmation = (sale: PendingSaleType, action: 'approve' | 'reject') => {
    setSelectedSale(sale);
    setActionType(action);
    setIsActionModalOpen(true);
  };

  // Обработка подтверждения/отклонения продажи
  const handleConfirmAction = async () => {
    if (!selectedSale || !actionType) return;
    
    setActionLoading(true);
    try {
      if (actionType === 'approve') {
        await confirmSale(selectedSale.id);
        message.success('Продажа успешно подтверждена');
      } else {
        await rejectSale(selectedSale.id, 'Отклонено продавцом');
        message.success('Продажа отклонена');
      }
      
      // Обновляем список после действия
      fetchPendingSales(pagination.current, pagination.pageSize);
      
      setIsActionModalOpen(false);
      setSelectedSale(null);
      setActionType(null);
    } catch (error) {
      console.error('Ошибка при обработке продажи:', error);
      message.error('Произошла ошибка. Попробуйте позже.');
    } finally {
      setActionLoading(false);
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

  // Получение текста для статуса
  const getStatusText = (status: string) => {
    switch (status) {
      case 'pending':
        return 'Ожидает вашего подтверждения';
      case 'payment_processing':
        return 'Ожидает оплаты покупателем';
      case 'delivery_pending':
        return 'Ожидает передачи товара';
      default:
        return 'В обработке';
    }
  };

  // Определение действий, доступных для текущего статуса
  const getActionsForStatus = (sale: PendingSaleType) => {
    switch (sale.status) {
      case 'pending':
        return (
          <Space>
            <Button 
              type="primary" 
              icon={<CheckCircleOutlined />}
              onClick={() => showActionConfirmation(sale, 'approve')}
            >
              Принять
            </Button>
            <Button 
              danger 
              icon={<CloseCircleOutlined />}
              onClick={() => showActionConfirmation(sale, 'reject')}
            >
              Отклонить
            </Button>
          </Space>
        );
      
      case 'payment_processing':
        return (
          <Space>
            <Button type="default" icon={<InfoCircleOutlined />}>
              Детали оплаты
            </Button>
            <Button 
              danger 
              icon={<CloseCircleOutlined />}
            >
              Отменить
            </Button>
          </Space>
        );
      
      case 'delivery_pending':
        return (
          <Space>
            <Button 
              type="primary" 
              icon={<CheckCircleOutlined />}
            >
              Подтвердить доставку
            </Button>
            <Button 
              type="default" 
              icon={<InfoCircleOutlined />}
            >
              Инструкции
            </Button>
          </Space>
        );
      
      default:
        return (
          <Button 
            type="default" 
            icon={<InfoCircleOutlined />}
            onClick={() => showDetails(sale)}
          >
            Подробнее
          </Button>
        );
    }
  };

  if (loading && pendingSales.length === 0) {
    return (
      <div className="flex justify-center items-center py-10">
        <Spin size="large" tip="Загрузка ожидающих продаж..." />
      </div>
    );
  }

  if (pendingSales.length === 0) {
    return (
      <Empty description="У вас нет ожидающих действий продаж" />
    );
  }

  return (
    <div className="pending-sales">
      <List
        dataSource={pendingSales}
        pagination={{
          ...pagination,
          onChange: (page) => fetchPendingSales(page, pagination.pageSize)
        }}
        loading={loading}
        renderItem={sale => (
          <Card 
            key={sale.id} 
            className="mb-4 shadow-sm hover:shadow-md transition-shadow"
          >
            <div className="flex flex-col md:flex-row md:justify-between md:items-start">
              {/* Информация о продаже */}
              <div className="mb-4 md:mb-0 md:mr-4 flex-grow">
                <Title level={5} className="mb-1">
                  {sale.listingTitle}
                  <Tooltip title="Посмотреть детали">
                    <Button 
                      type="text" 
                      size="small" 
                      icon={<InfoCircleOutlined />} 
                      onClick={() => showDetails(sale)}
                      className="ml-1"
                    />
                  </Tooltip>
                </Title>
                
                <div className="flex flex-wrap gap-x-6 gap-y-2 text-gray-600 mb-2">
                  <Text>
                    <span className="font-medium">Игра:</span> {sale.gameInfo?.name}
                  </Text>
                  <Text>
                    <span className="font-medium">Цена:</span> {formatPrice(sale.price, sale.currency)}
                  </Text>
                  <Text>
                    <span className="font-medium">Покупатель:</span> {sale.buyerName}
                  </Text>
                  <Text>
                    <span className="font-medium">Дата:</span> {format(new Date(sale.createdAt), 'dd.MM.yyyy HH:mm')}
                  </Text>
                </div>
                
                <Text type="secondary">
                  {getStatusText(sale.status)}
                </Text>
              </div>
              
              {/* Действия */}
              <div className="flex flex-col items-start">
                {getActionsForStatus(sale)}
              </div>
            </div>
            
            {/* Шаги процесса продажи */}
            <div className="mt-4">
              <Steps current={getCurrentStep(sale.status)} size="small">
                <Step title="Подтверждение" />
                <Step title="Оплата" />
                <Step title="Доставка" />
                <Step title="Завершено" />
              </Steps>
            </div>
          </Card>
        )}
      />
      
      {/* Модальное окно с деталями */}
      <Modal
        title="Детали сделки"
        open={isDetailsModalOpen}
        onCancel={() => setIsDetailsModalOpen(false)}
        footer={[
          <Button key="close" onClick={() => setIsDetailsModalOpen(false)}>
            Закрыть
          </Button>
        ]}
      >
        {selectedSale && (
          <div>
            <p><strong>ID сделки:</strong> {selectedSale.id}</p>
            <p><strong>Товар:</strong> {selectedSale.listingTitle}</p>
            <p><strong>Игра:</strong> {selectedSale.gameInfo?.name}</p>
            <p><strong>Покупатель:</strong> {selectedSale.buyerName}</p>
            <p><strong>Цена:</strong> {formatPrice(selectedSale.price, selectedSale.currency)}</p>
            <p><strong>Дата создания:</strong> {format(new Date(selectedSale.createdAt), 'dd.MM.yyyy HH:mm')}</p>
            <p><strong>Статус:</strong> {getStatusText(selectedSale.status)}</p>
            {selectedSale.expiresAt && (
              <p><strong>Истекает:</strong> {format(new Date(selectedSale.expiresAt), 'dd.MM.yyyy HH:mm')}</p>
            )}
          </div>
        )}
      </Modal>
      
      {/* Модальное окно с подтверждением действия */}
      <Modal
        title={actionType === 'approve' ? 'Подтверждение сделки' : 'Отклонение сделки'}
        open={isActionModalOpen}
        onCancel={() => {
          if (!actionLoading) {
            setIsActionModalOpen(false);
            setActionType(null);
          }
        }}
        confirmLoading={actionLoading}
        onOk={handleConfirmAction}
        okText={actionType === 'approve' ? 'Подтвердить' : 'Отклонить'}
        okButtonProps={{ 
          danger: actionType === 'reject',
          type: actionType === 'approve' ? 'primary' : 'default'
        }}
        cancelText="Отмена"
      >
        {selectedSale && (
          <div>
            <p>
              {actionType === 'approve' 
                ? 'Вы уверены, что хотите подтвердить эту сделку?' 
                : 'Вы уверены, что хотите отклонить эту сделку?'
              }
            </p>
            <p><strong>Товар:</strong> {selectedSale.listingTitle}</p>
            <p><strong>Цена:</strong> {formatPrice(selectedSale.price, selectedSale.currency)}</p>
            <p><strong>Покупатель:</strong> {selectedSale.buyerName}</p>
            
            {actionType === 'reject' && (
              <div className="mt-2">
                <Text type="warning">
                  Отклонение сделки отменит заявку покупателя. Это действие необратимо.
                </Text>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
};

export default PendingSales; 