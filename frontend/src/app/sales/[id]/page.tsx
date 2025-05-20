'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useSales } from '../../hooks/sale';
import { useWallets } from '../../hooks/wallet';
import { Sale, SaleStatus } from '../../types/sale';
import formatPrice from '../../utils/formatPrice';
import { 
  Button, 
  notification, 
  Spin, 
  Descriptions, 
  Badge, 
  Space, 
  Modal, 
  Select, 
  Input, 
  Divider, 
  Card, 
  Avatar, 
  Tabs 
} from 'antd';
import {
  DollarOutlined,
  ShoppingCartOutlined,
  WarningOutlined,
  CheckCircleOutlined,
  MessageOutlined,
  CloseCircleOutlined
} from '@ant-design/icons';
import { useAuth } from '../../hooks/auth';
import { Currency, WalletType } from '../../types/wallet';
import ChatWidget from '../../../components/chat/ChatWidget';

// Метки и цвета для статусов
const statusLabels: Record<SaleStatus, string> = {
  [SaleStatus.PENDING]: 'Ожидает оплаты',
  [SaleStatus.PAYMENT_PROCESSING]: 'Обработка оплаты',
  [SaleStatus.DELIVERY_PENDING]: 'Ожидает доставки',
  [SaleStatus.COMPLETED]: 'Завершена',
  [SaleStatus.CANCELED]: 'Отменена',
  [SaleStatus.REFUNDED]: 'Возвращена',
  [SaleStatus.DISPUTED]: 'Спор',
};

const statusColors: Record<SaleStatus, string> = {
  [SaleStatus.PENDING]: 'bg-yellow-100 text-yellow-800',
  [SaleStatus.PAYMENT_PROCESSING]: 'bg-blue-100 text-blue-800',
  [SaleStatus.DELIVERY_PENDING]: 'bg-purple-100 text-purple-800',
  [SaleStatus.COMPLETED]: 'bg-green-100 text-green-800',
  [SaleStatus.CANCELED]: 'bg-red-100 text-red-800',
  [SaleStatus.REFUNDED]: 'bg-gray-100 text-gray-800',
  [SaleStatus.DISPUTED]: 'bg-orange-100 text-orange-800',
};

export default function SalePage() {
  const params = useParams();
  const router = useRouter();
  const { user } = useAuth();
  const { getSale, processPayment, openDispute } = useSales();
  const { wallets } = useWallets();
  
  const [sale, setSale] = useState<Sale | null>(null);
  const [loading, setLoading] = useState(true);
  const [showChat, setShowChat] = useState(false);
  const [showDisputeModal, setShowDisputeModal] = useState(false);
  const [disputeReason, setDisputeReason] = useState('');
  const [selectedWalletId, setSelectedWalletId] = useState<number | null>(null);
  const [processingPayment, setProcessingPayment] = useState(false);
  const [processingDispute, setProcessingDispute] = useState(false);

  useEffect(() => {
    if (params?.id) {
      fetchSaleDetails();
    }
  }, [params?.id]);

  const fetchSaleDetails = async () => {
    if (!params?.id) return;
    
    setLoading(true);
      try {
      const data = await getSale(Number(params.id));
      setSale(data);
      
      // Если у пользователя есть кошельки, выбираем первый по умолчанию
      if (wallets.length > 0) {
        setSelectedWalletId(wallets[0].id);
      }
    } catch (error) {
      notification.error({
        message: 'Ошибка при загрузке',
        description: 'Не удалось загрузить информацию о продаже'
      });
    } finally {
      setLoading(false);
      }
    };

  const handlePayment = async () => {
    if (!params?.id) return;
    if (!selectedWalletId) {
      notification.warning({
        message: 'Выберите кошелек',
        description: 'Пожалуйста, выберите кошелек для оплаты'
      });
      return;
    }

    setProcessingPayment(true);
    try {
      const transaction = await processPayment(sale!.id, selectedWalletId);
      notification.success({
        message: 'Оплата обработана',
        description: `Платеж успешно обработан. ID транзакции: ${transaction.id}`
      });
      
      // Обновляем информацию о продаже
      const refreshedSale = await getSale(Number(params.id));
      setSale(refreshedSale);
      
      // Автоматически открываем чат после успешной оплаты
      if (refreshedSale.chat_id) {
        setShowChat(true);
      }
      
    } catch (error) {
      notification.error({
        message: 'Ошибка при оплате',
        description: error instanceof Error ? error.message : 'Произошла ошибка при обработке платежа'
      });
    } finally {
      setProcessingPayment(false);
    }
  };

  const handleDispute = async () => {
    if (!params?.id) return;
    if (!disputeReason.trim()) {
      notification.warning({
        message: 'Укажите причину',
        description: 'Пожалуйста, укажите причину открытия спора'
      });
      return;
    }

    setProcessingDispute(true);
    try {
      await openDispute(sale!.id, disputeReason);
      notification.success({
        message: 'Спор открыт',
        description: 'Спор успешно открыт. Наши модераторы рассмотрят ваше обращение.'
      });
      
      // Закрываем модальное окно и очищаем ввод
      setShowDisputeModal(false);
      setDisputeReason('');
      
      // Обновляем информацию о продаже
      const refreshedSale = await getSale(Number(params.id));
      setSale(refreshedSale);
    } catch (error) {
      notification.error({
        message: 'Ошибка при открытии спора',
        description: error instanceof Error ? error.message : 'Произошла ошибка при открытии спора'
      });
    } finally {
      setProcessingDispute(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-96">
        <Spin size="large" tip="Загрузка деталей продажи..." />
      </div>
    );
  }

  if (!sale) {
    return (
      <div className="max-w-4xl mx-auto p-6 text-center">
        <h1 className="text-2xl font-bold text-red-600">Продажа не найдена</h1>
        <p className="mt-4 text-gray-600">
          Продажа с указанным ID не существует или у вас нет доступа к ней
        </p>
        <Button type="primary" onClick={() => router.push('/sales')} className="mt-4">
          Вернуться к списку продаж
        </Button>
      </div>
    );
  }

  const isBuyer = user?.id === sale.buyer_id;
  const isSeller = user?.id === sale.seller_id;
  const canPay = isBuyer && sale.status === SaleStatus.PENDING;
  const canDispute = 
    (isBuyer || isSeller) && 
    [SaleStatus.PAYMENT_PROCESSING, SaleStatus.DELIVERY_PENDING].includes(sale.status);

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="bg-white rounded-lg shadow-lg overflow-hidden">
        {/* Заголовок */}
        <div className="p-6 border-b">
          <div className="flex justify-between items-start">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">
                Продажа #{sale.id}
              </h1>
              <p className="text-sm text-gray-500">
                Создана {new Date(sale.created_at).toLocaleString()}
              </p>
            </div>
            <div className="flex items-center space-x-3">
              {sale.transaction_id && (
                <Button 
                  type="primary" 
                  onClick={() => router.push(`/sales/transactions/${sale.transaction_id}`)}
                  icon={<ShoppingCartOutlined />}
                  size="middle"
                  className="bg-blue-500 hover:bg-blue-600"
                >
                  Расширенный просмотр сделки
                </Button>
              )}
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${statusColors[sale.status]}`}>
              {statusLabels[sale.status]}
            </span>
            </div>
          </div>
        </div>

        {/* Детали продажи */}
        <div className="p-6 space-y-6">
          <div className="grid grid-cols-2 gap-6">
            <div>
              <h3 className="text-sm font-medium text-gray-500">Цена</h3>
              <p className="mt-1 text-lg font-semibold text-gray-900">
                {formatPrice(sale.price, sale.currency)}
              </p>
            </div>
            <div>
              <h3 className="text-sm font-medium text-gray-500">Статус</h3>
              <p className="mt-1 text-lg font-semibold text-gray-900">
                {statusLabels[sale.status]}
              </p>
            </div>
          </div>

          {sale.description && (
            <div>
              <h3 className="text-sm font-medium text-gray-500">Описание</h3>
              <p className="mt-1 text-gray-900">{sale.description}</p>
            </div>
          )}

          {/* Информация о продавце и покупателе */}
          <div className="grid grid-cols-2 gap-6">
            <Card size="small" title="Продавец">
              <p><strong>ID:</strong> {sale.seller_id}</p>
              <p><strong>Имя:</strong> {sale.seller_name || 'Не указано'}</p>
            </Card>
            <Card size="small" title="Покупатель">
              <p><strong>ID:</strong> {sale.buyer_id}</p>
              <p><strong>Имя:</strong> {sale.buyer_name || 'Не указано'}</p>
            </Card>
          </div>

          {/* Действия */}
          <div className="mt-6 flex flex-col md:flex-row gap-4">
            {/* Кнопка оплаты для покупателя в статусе PENDING */}
            {canPay && (
              <div className="flex-1">
                <h3 className="text-sm font-medium text-gray-500 mb-2">Оплата</h3>
                <div className="space-y-2">
                  <Select
                    placeholder="Выберите кошелек"
                    style={{ width: '100%' }}
                    value={selectedWalletId}
                    onChange={setSelectedWalletId}
                    disabled={processingPayment}
                  >
                    {wallets.map(wallet => (
                      <Select.Option key={wallet.id} value={wallet.id}>
                        Кошелек #{wallet.id} (Баланс: {wallet.balances[Currency.USD]} USD)
                      </Select.Option>
                    ))}
                  </Select>
                  <Button
                    type="primary"
                    icon={<DollarOutlined />}
                    onClick={handlePayment}
                    loading={processingPayment}
                    disabled={!selectedWalletId}
                    block
              >
                    Оплатить
                  </Button>
                </div>
              </div>
            )}

            {/* Кнопка для открытия спора */}
            {canDispute && (
              <div className="flex-1">
                <h3 className="text-sm font-medium text-gray-500 mb-2">Действия</h3>
                <Button
                  danger
                  icon={<WarningOutlined />}
                  onClick={() => setShowDisputeModal(true)}
                  block
                >
                  Открыть спор
                </Button>
              </div>
            )}

            {/* Кнопка для открытия чата */}
            {sale.chat_id && (
              <div className="flex-1">
                <h3 className="text-sm font-medium text-gray-500 mb-2">Общение</h3>
                <Button
                  type="default"
                  icon={<MessageOutlined />}
                  onClick={() => setShowChat(!showChat)}
                  block
                >
                  {showChat ? 'Скрыть чат' : 'Открыть чат'}
                </Button>
              </div>
            )}
          </div>

          {/* Чат */}
          {showChat && sale.chat_id && (
            <div className="mt-4 border rounded-lg overflow-hidden">
              <ChatWidget chatId={sale.chat_id} />
            </div>
          )}
        </div>
      </div>

      {/* Модальное окно для открытия спора */}
      <Modal
        title="Открыть спор"
        open={showDisputeModal}
        onOk={handleDispute}
        onCancel={() => setShowDisputeModal(false)}
        confirmLoading={processingDispute}
        okText="Открыть спор"
        cancelText="Отмена"
      >
        <p className="mb-4">
          Открытие спора приостановит транзакцию и уведомит администрацию сервиса. 
          Пожалуйста, опишите причину открытия спора как можно подробнее.
        </p>
        <Input.TextArea
          rows={4}
          placeholder="Опишите причину открытия спора..."
          value={disputeReason}
          onChange={e => setDisputeReason(e.target.value)}
        />
      </Modal>
    </div>
  );
} 