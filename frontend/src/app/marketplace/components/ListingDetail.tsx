'use client';

import { useState, useEffect, useRef } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useMarketplace } from '../../hooks/marketplace';
import { useAuth } from '../../hooks/auth';
import { formatDistanceToNow } from 'date-fns';
import { ru } from 'date-fns/locale';
import formatPrice from '../../utils/formatPrice';
import ListingCard from './ListingCard';
import { Card, Button, Typography, Modal, Input, Avatar, List, Divider, message, Spin, Tabs, Tooltip } from 'antd';
import { SendOutlined, UserOutlined, ShoppingCartOutlined, CloseCircleOutlined, CheckCircleOutlined, InfoCircleOutlined, QuestionCircleOutlined, MessageOutlined } from '@ant-design/icons';
import BuyButton from '../../components/BuyButton';
import ChatModal from '../../components/ChatModal';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;
const { TabPane } = Tabs;

interface ListingDetailProps {
  listingId: number;
}

// Обновляем интерфейс для листинга с поддержкой иерархической структуры категорий
interface Category {
  id: number;
  name: string;
  description?: string;
  icon_url?: string;
  game_id: number;
  parent_id?: number | null;
  parent?: Category;
  category_type?: string;
  order_index?: number;
  created_at: string;
  updated_at: string;
}

interface ItemTemplate {
  id: number;
  name: string;
  description?: string;
  icon_url?: string;
  is_tradable: boolean;
  base_price: number;
  category_id: number;
  category?: Category;
  attributes?: any[];
  template_attributes?: Array<{
    id: number;
    name: string;
    description?: string;
    attribute_type: string;
    is_required: boolean;
    is_filterable: boolean;
    default_value?: string;
    options?: any;
    template_id: number;
    created_at: string;
    updated_at: string;
  }>;
  created_at: string;
  updated_at: string;
}

interface Listing {
  id: number;
  title: string;
  description?: string;
  price: number;
  currency: string;
  status: string;
  is_negotiable: boolean;
  seller_id: number;
  item_id: number;
  item_template_id: number;
  views_count: number;
  expires_at?: string | null;
  created_at: string;
  updated_at: string;
  seller: {
    id: number;
    username: string;
    email: string;
    created_at: string;
    updated_at?: string | null;
  };
  item_template?: ItemTemplate;
  images: Array<{
    id: number;
    url: string;
    is_main: boolean;
    order_index: number;
  }>;
  item_attributes?: Array<{
    id: number;
    attribute_id: number;
    attribute_name: string;
    attribute_type: string;
    value_string?: string;
    value_number?: number;
    value_boolean?: boolean;
  }>;
  template_attributes?: Array<{
    id: number;
    template_attribute_id: number;
    attribute_name: string;
    attribute_type: string;
    value_string?: string;
    value_number?: number;
    value_boolean?: boolean;
  }>;
  all_attributes?: Array<{
    attribute_id: number;
    attribute_name: string;
    attribute_type: string;
    attribute_source: string;
    value_string?: string;
    value_number?: number;
    value_boolean?: boolean;
    is_template_attr?: boolean;
  }>;
  similar_listings?: Array<{
    id: number;
    title: string;
    description?: string;
    price: number;
    currency: string;
    status: string;
    seller_id: number;
    item_template_id: number;
    item_id: number;
    views_count: number;
    created_at: string;
    updated_at: string;
    images?: Array<{
      id: number;
      url: string;
      is_main: boolean;
      order_index: number;
    }>;
  }>;
  seller_rating?: number | null;
}

// Интерфейс для сообщения чата
interface ChatMessage {
  id: number;
  senderId: number;
  senderName: string;
  receiverId: number;
  message: string;
  timestamp: string;
  isRead: boolean;
}

export default function ListingDetail({ listingId }: ListingDetailProps) {
  const router = useRouter();
  const { isAuthenticated, user } = useAuth();
  const { getListingById, deleteListing } = useMarketplace();
  
  const [listing, setListing] = useState<Listing | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeImageIndex, setActiveImageIndex] = useState(0);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [isChatModalOpen, setIsChatModalOpen] = useState(false);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [messageText, setMessageText] = useState('');
  const [isSendingMessage, setIsSendingMessage] = useState(false);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [currentTransaction, setCurrentTransaction] = useState<any>(null);
  const [transactionStatus, setTransactionStatus] = useState<string | null>(null);
  const [isLoadingTransaction, setIsLoadingTransaction] = useState(false);
  
  // Используем ref для предотвращения циклических запросов данных
  const dataLoadedRef = useRef<boolean>(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  // Загрузка данных объявления
  useEffect(() => {
    if (dataLoadedRef.current) {
      // Если данные уже были загружены, не загружаем их повторно
      return;
    }
    
    const fetchListing = async () => {
      setIsLoading(true);
      setError(null);
      
      // Предотвращаем повторную загрузку
      const isMounted = true;
      
      try {
        console.log(`Загрузка информации об объявлении ${listingId}`);
        const data = await getListingById(listingId);
        
        // Предотвращаем обновление размонтированного компонента
        if (!isMounted) return;
        
        // Проверка на существование данных
        if (!data) {
          setError('Объявление не найдено');
          setIsLoading(false);
          return;
        }
        
        // Проверяем наличие различных типов данных без доступа к несуществующим свойствам
        const hasImages = data.images && data.images.length > 0;
        const hasCompleteData = 
          (data as any).all_attributes?.length > 0 || 
          (data as any).item_attributes?.length > 0 || 
          (data as any).template_attributes?.length > 0;
        
        // Обновляем данные объявления
        setListing(data as unknown as Listing);
        
        // Помечаем, что данные были загружены
        dataLoadedRef.current = true;
        
        if (!hasImages || !hasCompleteData) {
          console.log('Получение дополнительной информации об объявлении', listingId);
          
          try {
            const detailResponse = await fetch(`${process.env.NEXT_PUBLIC_MARKETPLACE_URL || 'http://localhost:8001/api/marketplace'}/listings/${listingId}/detail`);
            if (detailResponse.ok) {
              const detailData = await detailResponse.json();
              
              // Предотвращаем обновление размонтированного компонента
              if (!isMounted) return;
              
              if (detailData && detailData.data) {
                // Принудительное обновление типов
                const detailListing = detailData.data as unknown as Listing;
                // Объединяем базовую информацию с детальными данными
                setListing({
                  ...data,
                  ...detailListing,
                } as unknown as Listing);
              }
            }
          } catch (detailErr) {
            console.error('Ошибка при получении детальной информации:', detailErr);
          }
        }
      } catch (err) {
        if (isMounted) {
          setError('Ошибка при загрузке объявления');
          console.error(err);
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };
    
    fetchListing();
    
    // Функция очистки для предотвращения обновления состояния при размонтировании
    return () => {
      dataLoadedRef.current = false;
    };
  }, [listingId, getListingById]);
  
  // Скролл чата вниз при добавлении новых сообщений
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [chatMessages]);
  
  // Загрузка истории сообщений
  const loadChatHistory = async (sellerId: number) => {
    if (!user || !isAuthenticated) {
      message.error('Для использования чата необходимо авторизоваться');
      return;
    }
    
    setLoadingMessages(true);
    
    try {
      // В реальном приложении здесь будет вызов API для получения истории сообщений
      // const response = await fetch(`/api/chat/history?sellerId=${sellerId}`);
      // const data = await response.json();
      
      // Временная заглушка для демонстрации
      const mockMessages: ChatMessage[] = [
        {
          id: 1,
          senderId: user?.id || 0,
          senderName: user?.username || 'Вы',
          receiverId: sellerId,
          message: 'Здравствуйте! Меня интересует ваш товар. Он ещё доступен?',
          timestamp: new Date(Date.now() - 86400000).toISOString(), // 24 часа назад
          isRead: true
        },
        {
          id: 2,
          senderId: sellerId,
          senderName: listing?.seller?.username || 'Продавец',
          receiverId: user?.id || 0,
          message: 'Добрый день! Да, товар в наличии и готов к продаже.',
          timestamp: new Date(Date.now() - 82800000).toISOString(), // 23 часа назад
          isRead: true
        },
        {
          id: 3,
          senderId: user?.id || 0,
          senderName: user?.username || 'Вы',
          receiverId: sellerId,
          message: 'Отлично! У меня есть несколько вопросов о товаре...',
          timestamp: new Date(Date.now() - 43200000).toISOString(), // 12 часов назад
          isRead: true
        },
        {
          id: 4,
          senderId: sellerId,
          senderName: listing?.seller?.username || 'Продавец',
          receiverId: user?.id || 0,
          message: 'Конечно, спрашивайте! Я готов ответить на любые вопросы по товару.',
          timestamp: new Date(Date.now() - 39600000).toISOString(), // 11 часов назад
          isRead: true
        }
      ];
      
      setChatMessages(mockMessages);
    } catch (error) {
      console.error('Ошибка при загрузке истории сообщений:', error);
      message.error('Не удалось загрузить историю сообщений');
    } finally {
      setLoadingMessages(false);
    }
  };
  
  // Загрузка информации о транзакции, если она есть
  const loadTransactionInfo = async () => {
    if (!user || !isAuthenticated || !listing) return;
    
    setIsLoadingTransaction(true);
    
    try {
      // В реальном приложении здесь будет вызов API для получения информации о транзакции
      // const response = await fetch(`/api/transactions/listing/${listingId}`);
      // const data = await response.json();
      
      // Временная заглушка для демонстрации
      const mockTransaction = {
        id: 12345,
        status: 'escrow_held', // pending, escrow_held, completed, refunded, disputed, canceled
        amount: listing.price,
        currency: listing.currency,
        createdAt: new Date(Date.now() - 172800000).toISOString(), // 48 часов назад
        updatedAt: new Date(Date.now() - 86400000).toISOString() // 24 часа назад
      };
      
      setCurrentTransaction(mockTransaction);
      setTransactionStatus(mockTransaction.status);
    } catch (error) {
      console.error('Ошибка при загрузке информации о транзакции:', error);
    } finally {
      setIsLoadingTransaction(false);
    }
  };
  
  // Отправка сообщения
  const sendMessage = async () => {
    if (!messageText.trim() || !user || !isAuthenticated || !listing) {
      return;
    }
    
    setIsSendingMessage(true);
    
    try {
      // В реальном приложении здесь будет вызов API для отправки сообщения
      // const response = await fetch('/api/chat/send', {
      //   method: 'POST',
      //   headers: {
      //     'Content-Type': 'application/json',
      //   },
      //   body: JSON.stringify({
      //     receiverId: listing.seller.id,
      //     message: messageText,
      //     listingId
      //   }),
      // });
      // const data = await response.json();
      
      // Временная заглушка для демонстрации
      const newMessage: ChatMessage = {
        id: chatMessages.length + 1,
        senderId: user.id,
        senderName: user.username,
        receiverId: listing.seller.id,
        message: messageText,
        timestamp: new Date().toISOString(),
        isRead: false
      };
      
      setChatMessages(prev => [...prev, newMessage]);
      setMessageText('');
      
      // Симулируем ответ продавца через 2 секунды
      setTimeout(() => {
        const sellerReply: ChatMessage = {
          id: chatMessages.length + 2,
          senderId: listing.seller.id,
          senderName: listing.seller.username,
          receiverId: user.id,
          message: 'Спасибо за сообщение! Я отвечу вам в ближайшее время.',
          timestamp: new Date().toISOString(),
          isRead: false
        };
        
        setChatMessages(prev => [...prev, sellerReply]);
      }, 2000);
      
    } catch (error) {
      console.error('Ошибка при отправке сообщения:', error);
      message.error('Не удалось отправить сообщение');
    } finally {
      setIsSendingMessage(false);
    }
  };
  
  // Подтверждение получения товара
  const confirmDelivery = async () => {
    if (!currentTransaction) return;
    
    try {
      // В реальном приложении здесь будет вызов API для подтверждения получения товара
      // const response = await fetch(`/api/transactions/${currentTransaction.id}/complete`, {
      //   method: 'POST'
      // });
      // const data = await response.json();
      
      // Временная заглушка для демонстрации
      setTransactionStatus('completed');
      message.success('Получение товара подтверждено. Средства перечислены продавцу.');
      
    } catch (error) {
      console.error('Ошибка при подтверждении получения:', error);
      message.error('Не удалось подтвердить получение товара');
    }
  };
  
  // Запрос помощи поддержки
  const requestSupport = async () => {
    if (!currentTransaction) return;
    
    try {
      // В реальном приложении здесь будет вызов API для запроса помощи поддержки
      // const response = await fetch(`/api/transactions/${currentTransaction.id}/dispute`, {
      //   method: 'POST',
      //   headers: {
      //     'Content-Type': 'application/json',
      //   },
      //   body: JSON.stringify({
      //     reason: 'Необходима помощь службы поддержки',
      //   }),
      // });
      // const data = await response.json();
      
      // Временная заглушка для демонстрации
      setTransactionStatus('disputed');
      message.success('Запрос отправлен в службу поддержки. Мы свяжемся с вами в ближайшее время.');
      
    } catch (error) {
      console.error('Ошибка при запросе поддержки:', error);
      message.error('Не удалось отправить запрос в службу поддержки');
    }
  };
  
  // Обработчики
  const handleEdit = () => {
    router.push(`/marketplace/listings/edit/${listingId}`);
  };
  
  const handleDelete = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      await deleteListing(listingId);
      router.push('/marketplace/listings');
    } catch (err) {
      setError('Ошибка при удалении объявления');
      console.error(err);
      setIsLoading(false);
    }
  };
  
  // Обработчик контакта с продавцом
  const handleContactSeller = () => {
    if (!isAuthenticated) {
      message.error('Для контакта с продавцом необходимо авторизоваться');
      router.push('/login');
      return;
    }
    
    if (listing && listing.seller) {
      setIsChatModalOpen(true);
    }
  };
  
  // Рендер статуса транзакции
  const renderTransactionStatus = () => {
    if (isLoadingTransaction) {
      return <Spin size="small" />;
    }
    
    if (!currentTransaction) {
      return <Text type="secondary">Транзакция не найдена</Text>;
    }
    
    let statusColor = 'default';
    let statusText = 'Неизвестно';
    
    switch (transactionStatus) {
      case 'pending':
        statusColor = 'warning';
        statusText = 'Ожидание оплаты';
        break;
      case 'escrow_held':
        statusColor = 'processing';
        statusText = 'Ожидание доставки';
        break;
      case 'completed':
        statusColor = 'success';
        statusText = 'Завершено';
        break;
      case 'refunded':
        statusColor = 'default';
        statusText = 'Возврат средств';
        break;
      case 'disputed':
        statusColor = 'error';
        statusText = 'В процессе разрешения спора';
        break;
      case 'canceled':
        statusColor = 'default';
        statusText = 'Отменено';
        break;
    }
    
    return (
      <div>
        <Text strong>Статус сделки: </Text>
        <Text type={statusColor as any}>{statusText}</Text>
      </div>
    );
  };
  
  // Рендер действий в зависимости от статуса транзакции
  const renderTransactionActions = () => {
    if (!currentTransaction || isLoadingTransaction) {
      return null;
    }
    
    switch (transactionStatus) {
      case 'escrow_held':
        return (
          <div className="mt-4 space-y-2">
            <Button 
              type="primary" 
              icon={<CheckCircleOutlined />}
              onClick={confirmDelivery}
              block
            >
              Подтвердить получение товара
            </Button>
            <Button 
              danger
              icon={<QuestionCircleOutlined />}
              onClick={requestSupport}
              block
            >
              Запросить помощь поддержки
            </Button>
          </div>
        );
      case 'disputed':
        return (
          <div className="mt-4">
            <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-md">
              <Text type="warning">
                <InfoCircleOutlined className="mr-1" />
                Запрос в службу поддержки отправлен. Ожидайте ответа.
              </Text>
            </div>
          </div>
        );
      case 'completed':
        return (
          <div className="mt-4">
            <div className="p-3 bg-green-50 border border-green-200 rounded-md">
              <Text type="success">
                <CheckCircleOutlined className="mr-1" />
                Транзакция успешно завершена!
              </Text>
            </div>
          </div>
        );
      default:
        return null;
    }
  };
  
  // Отображение хлебных крошек с иерархией категорий
  const renderBreadcrumbs = () => {
    if (!listing) return null;
    
    const breadcrumbs = [];
    
    // Добавляем главную и маркетплейс
    breadcrumbs.push(
      <li key="home" className="inline-flex items-center">
        <Link href="/" className="text-gray-700 hover:text-blue-600">
          Главная
        </Link>
      </li>,
      <li key="marketplace">
        <div className="flex items-center">
          <span className="mx-2 text-gray-400">/</span>
          <Link href="/marketplace/listings" className="text-gray-700 hover:text-blue-600">
            Маркетплейс
          </Link>
        </div>
      </li>
    );
    
    // Добавляем игру, если она указана (убираем game_name, так как его нет в новой структуре)
    // const gameName = listing.item_template?.category?.game_name || '';
    // if (gameName) {
    //   breadcrumbs.push(
    //     <li key="game">
    //       <div className="flex items-center">
    //         <span className="mx-2 text-gray-400">/</span>
    //         <span className="text-gray-500">{gameName}</span>
    //       </div>
    //     </li>
    //   );
    // }
    
    // Функция для построения пути категорий
    const buildCategoryPath = (category?: Category): Category[] => {
      if (!category) return [];
      
      const path: Category[] = [category];
      let current = category;
      
      // Пока есть родительская категория, добавляем её в начало пути
      while (current.parent) {
        path.unshift(current.parent);
        current = current.parent;
      }
      
      return path;
    };
    
    // Получаем путь категорий (убираем ссылку на listing.category)
    const categoryPath = buildCategoryPath(listing.item_template?.category);
    
    // Добавляем категории в хлебные крошки
    categoryPath.forEach((category, index) => {
      breadcrumbs.push(
        <li key={`category-${category.id}`}>
          <div className="flex items-center">
            <span className="mx-2 text-gray-400">/</span>
            <span className="text-gray-500">{category.name}</span>
          </div>
        </li>
      );
    });
    
    return (
      <div className="mb-6">
        <nav className="flex" aria-label="Breadcrumb">
          <ol className="inline-flex items-center space-x-1 md:space-x-3">
            {breadcrumbs}
          </ol>
        </nav>
      </div>
    );
  };
  
  // Группировка атрибутов по категориям для лучшего отображения
  const renderAttributes = () => {
    if (!listing) return null;
    
    // Проверяем наличие атрибутов в различных местах
    const hasAllAttributes = listing.all_attributes && listing.all_attributes.length > 0;
    const hasItemAttributes = listing.item_attributes && listing.item_attributes.length > 0;
    const hasTemplateAttributes = listing.template_attributes && listing.template_attributes.length > 0;
    
    // Если нет атрибутов вообще, возвращаем null
    if (!hasAllAttributes && !hasItemAttributes && !hasTemplateAttributes) {
      return null;
    }
    
    let groupedAttributes = {
      category: [] as any[],
      template: [] as any[]
    };
    
    if (hasAllAttributes && listing.all_attributes) {
      // Используем all_attributes, если он есть и не пустой
      groupedAttributes = {
        category: listing.all_attributes.filter(attr => attr.attribute_source === 'category'),
        template: listing.all_attributes.filter(attr => attr.attribute_source === 'template')
      };
    } else {
      // Если all_attributes пуст или отсутствует, используем item_attributes и template_attributes
      if (hasItemAttributes && listing.item_attributes) {
        groupedAttributes.category = listing.item_attributes.map(attr => ({
          ...attr,
          attribute_source: 'category',
          attribute_id: attr.attribute_id,
          attribute_name: attr.attribute_name,
          attribute_type: attr.attribute_type
        }));
      }
      
      if (hasTemplateAttributes && listing.template_attributes) {
        groupedAttributes.template = listing.template_attributes.map(attr => ({
          ...attr,
          attribute_source: 'template',
          attribute_id: attr.template_attribute_id,
          attribute_name: attr.attribute_name,
          attribute_type: attr.attribute_type
        }));
      }
    }
    
    return (
      <div className="mt-6">
        <h2 className="text-xl font-semibold mb-4">Характеристики</h2>
        
        {/* Атрибуты категории */}
        {groupedAttributes.category.length > 0 && (
          <div className="mb-4">
            <h3 className="text-lg font-medium mb-2">Основные характеристики</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {groupedAttributes.category.map((attr, index) => {
                // Определяем значение атрибута в зависимости от его типа
                let displayValue;
                if (attr.attribute_type === 'number') {
                  displayValue = attr.value_number?.toString();
                } else if (attr.attribute_type === 'boolean') {
                  displayValue = attr.value_boolean ? 'Да' : 'Нет';
                } else {
                  displayValue = attr.value_string;
                }
                
                return (
                  <div 
                    key={`category-${attr.attribute_id || attr.id}-${index}`} 
                    className="flex justify-between py-2 border-b"
                  >
                    <span className="text-gray-600">
                      {attr.attribute_name}:
                    </span>
                    <span className="font-medium">{displayValue}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
        
        {/* Атрибуты шаблона */}
        {groupedAttributes.template.length > 0 && (
          <div>
            <h3 className="text-lg font-medium mb-2">Специальные характеристики</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {groupedAttributes.template.map((attr, index) => {
                // Определяем значение атрибута в зависимости от его типа
                let displayValue;
                if (attr.attribute_type === 'number') {
                  displayValue = attr.value_number?.toString();
                } else if (attr.attribute_type === 'boolean') {
                  displayValue = attr.value_boolean ? 'Да' : 'Нет';
                } else {
                  displayValue = attr.value_string;
                }
                
                return (
                  <div 
                    key={`template-${attr.attribute_id || attr.template_attribute_id || attr.id}-${index}`} 
                    className="flex justify-between py-2 border-b text-blue-700"
                  >
                    <span className="text-blue-600">
                      {attr.attribute_name}:
                    </span>
                    <span className="font-medium">{displayValue}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    );
  };
  
  // Рендер дополнительной информации для продавца
  const renderSellerInfo = () => {
    if (!isOwner || !listing) return null;
    
    return (
      <Card className="mb-6" title="Информация для продавца">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">{listing.views_count}</div>
            <div className="text-sm text-gray-500">Просмотров</div>
          </div>
          
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">
              {listing.status === 'active' ? 'Активно' : 
               listing.status === 'pending' ? 'На модерации' :
               listing.status === 'sold' ? 'Продано' : 
               listing.status === 'expired' ? 'Истекло' : 'Неизвестно'}
            </div>
            <div className="text-sm text-gray-500">Статус</div>
          </div>
          
          <div className="text-center">
            <div className="text-2xl font-bold text-purple-600">
              {formatDistanceToNow(new Date(listing.created_at), { addSuffix: false, locale: ru })}
            </div>
            <div className="text-sm text-gray-500">На сайте</div>
          </div>
        </div>
        
        {listing.expires_at && (
          <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
            <Text type="warning">
              <InfoCircleOutlined className="mr-1" />
              Объявление истекает: {new Date(listing.expires_at).toLocaleDateString('ru-RU')}
            </Text>
          </div>
        )}
        
        {listing.status === 'pending' && (
          <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-md">
            <Text type="secondary">
              <InfoCircleOutlined className="mr-1" />
              Ваше объявление находится на модерации. Оно станет видимым после проверки.
            </Text>
          </div>
        )}
      </Card>
    );
  };
  
  // Рендер информации о товаре (item template)
  const renderItemTemplateInfo = () => {
    if (!listing?.item_template) return null;
    
    const template = listing.item_template;
    
    return (
      <Card className="mb-6" title="О товаре">
        <div className="space-y-4">
          <div>
            <Text strong>Название: </Text>
            <Text>{template.name}</Text>
          </div>
          
          {template.description && (
            <div>
              <Text strong>Описание: </Text>
              <Paragraph>{template.description}</Paragraph>
            </div>
          )}
          
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Text strong>Торгуемый: </Text>
              <Text type={template.is_tradable ? 'success' : 'danger'}>
                {template.is_tradable ? 'Да' : 'Нет'}
              </Text>
            </div>
            
            {template.base_price > 0 && (
              <div>
                <Text strong>Базовая цена: </Text>
                <Text>{formatPrice(template.base_price, listing.currency)}</Text>
              </div>
            )}
          </div>
          
          {template.category && (
            <div>
              <Text strong>Категория: </Text>
              <Text>{template.category.name}</Text>
              {template.category.description && (
                <div className="text-sm text-gray-500 mt-1">
                  {template.category.description}
                </div>
              )}
            </div>
          )}
        </div>
      </Card>
    );
  };
  
  // Рендер информации о продавце с расширенными данными
  const renderSellerCard = () => {
    if (!listing?.seller) return null;
    
    const seller = listing.seller;
    const memberSince = formatDistanceToNow(new Date(seller.created_at), { addSuffix: true, locale: ru });
    
    return (
      <Card className="mb-6" title="Продавец">
        <div className="flex items-start space-x-4">
          <Avatar size={64} icon={<UserOutlined />} />
          
          <div className="flex-1">
            <div className="flex items-center space-x-2 mb-2">
              <Text strong className="text-lg">{seller.username}</Text>
              {listing.seller_rating && (
                <div className="flex items-center">
                  <span className="text-yellow-500">★</span>
                  <span className="ml-1">{listing.seller_rating.toFixed(1)}</span>
                </div>
              )}
            </div>
            
            <div className="text-sm text-gray-500 mb-3">
              На сайте {memberSince}
            </div>
            
            {!isOwner && isAuthenticated && (
              <Button 
                type="primary" 
                icon={<MessageOutlined />}
                onClick={handleContactSeller}
                className="w-full"
              >
                Связаться с продавцом
              </Button>
            )}
          </div>
        </div>
      </Card>
    );
  };
  
  // Рендер ценовой информации с дополнительными данными
  const renderPriceInfo = () => {
    if (!listing) return null;
    
    return (
      <Card className="mb-6">
        <div className="space-y-4">
          <div className="text-center">
            <div className="text-3xl font-bold text-gray-900 mb-2">
              {formatPrice(listing.price, listing.currency)}
            </div>
            
            {listing.is_negotiable && (
              <div className="inline-flex items-center px-3 py-1 rounded-full text-sm bg-green-100 text-green-800">
                Цена договорная
              </div>
            )}
          </div>
       
          
          <div className="text-sm text-gray-500 text-center">
            Размещено {formatDistanceToNow(new Date(listing.created_at), { addSuffix: true, locale: ru })}
          </div>
          
          <div className="text-sm text-gray-500 text-center">
            Обновлено {formatDistanceToNow(new Date(listing.updated_at), { addSuffix: true, locale: ru })}
          </div>
        </div>
      </Card>
    );
  };
  
  // Рендер рекомендаций для покупателей
  const renderBuyerTips = () => {
    if (isOwner || !listing) return null;
    
    return (
      <Card className="mt-6" title="💡 Советы покупателю">
        <div className="space-y-3 text-sm">
          <div className="flex items-start space-x-2">
            <CheckCircleOutlined className="text-green-500 mt-0.5" />
            <span>Обязательно свяжитесь с продавцом перед покупкой, чтобы уточнить детали</span>
          </div>
          
          <div className="flex items-start space-x-2">
            <CheckCircleOutlined className="text-green-500 mt-0.5" />
            <span>Проверьте рейтинг продавца и отзывы других покупателей</span>
          </div>
          
          {listing.is_negotiable && (
            <div className="flex items-start space-x-2">
              <CheckCircleOutlined className="text-green-500 mt-0.5" />
              <span>Цена договорная - можете предложить свою цену продавцу</span>
            </div>
          )}
          
          {listing.item_template?.is_tradable && (
            <div className="flex items-start space-x-2">
              <CheckCircleOutlined className="text-green-500 mt-0.5" />
              <span>Товар торгуемый - можете обменять на другие предметы</span>
            </div>
          )}
          
          <div className="flex items-start space-x-2">
            <InfoCircleOutlined className="text-blue-500 mt-0.5" />
            <span>Все платежи проходят через безопасную систему эскроу</span>
          </div>
        </div>
      </Card>
    );
  };
  
  // Рендер статистики объявления для всех пользователей
  const renderListingStats = () => {
    if (!listing) return null;
    
    return (
      <Card className="mt-6" title="📊 Статистика объявления">
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div className="text-center">
            <div className="text-lg font-semibold text-blue-600">{listing.views_count}</div>
            <div className="text-gray-500">Просмотров</div>
          </div>
          
          <div className="text-center">
            <div className="text-lg font-semibold text-green-600">
              {formatDistanceToNow(new Date(listing.created_at), { locale: ru })}
            </div>
            <div className="text-gray-500">Назад создано</div>
          </div>
          
          {listing.updated_at !== listing.created_at && (
            <>
              <div className="text-center">
                <div className="text-lg font-semibold text-orange-600">
                  {formatDistanceToNow(new Date(listing.updated_at), { locale: ru })}
                </div>
                <div className="text-gray-500">Назад обновлено</div>
              </div>
              
              <div className="text-center">
                <div className="text-lg font-semibold text-purple-600">
                  {Math.round((new Date().getTime() - new Date(listing.updated_at).getTime()) / (1000 * 60 * 60 * 24))}
                </div>
                <div className="text-gray-500">Дней с обновления</div>
              </div>
            </>
          )}
        </div>
      </Card>
    );
  };
  
  // Отображение загрузки
  if (isLoading) {
    return (
      <div className="flex justify-center py-20">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    );
  }
  
  // Отображение ошибки
  if (error || !listing) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
          {error || 'Объявление не найдено'}
        </div>
        <div className="flex justify-center">
          <button
            onClick={() => router.push('/marketplace/listings')}
            className="bg-gray-200 hover:bg-gray-300 text-gray-800 font-medium py-2 px-4 rounded"
          >
            Вернуться к списку объявлений
          </button>
        </div>
      </div>
    );
  }
  
  // Получаем главное изображение или первое из списка
  const mainImage = listing.images?.find((img) => img.is_main) || listing.images?.[0];
  
  // Проверяем, является ли текущий пользователь продавцом
  const isOwner = isAuthenticated && user?.id === listing.seller?.id;
  
  return (
    <div className="container mx-auto px-4 py-8">
      {/* Хлебные крошки */}
      {renderBreadcrumbs()}
      
      {/* Информация для продавца (только если это его объявление) */}
      {renderSellerInfo()}
      
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Галерея изображений */}
        <div className="lg:col-span-2">
          {listing.images && listing.images.length > 0 ? (
            <div className="space-y-4">
              <div className="aspect-w-16 aspect-h-9 bg-gray-100 rounded-lg overflow-hidden">
                <div className="relative w-full h-96">
                  <Image
                    src={listing.images[activeImageIndex].url}
                    alt={listing.title}
                    fill
                    className="object-contain"
                    quality={90}
                    priority
                  />
                </div>
              </div>
              
              {listing.images.length > 1 && (
                <div className="grid grid-cols-6 gap-2">
                  {listing.images.map((image, index) => (
                    <div
                      key={image.id}
                      className={`cursor-pointer border-2 rounded ${
                        index === activeImageIndex
                          ? 'border-blue-500'
                          : 'border-transparent hover:border-gray-300'
                      }`}
                      onClick={() => setActiveImageIndex(index)}
                    >
                      <div className="relative w-full h-16">
                        <Image
                          src={image.url}
                          alt={`Изображение ${index + 1}`}
                          fill
                          className="object-cover rounded"
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="bg-gray-100 h-96 rounded-lg flex items-center justify-center">
              <span className="text-gray-400">Нет изображений</span>
            </div>
          )}
          
          {/* Информация о товаре (item template) */}
          {renderItemTemplateInfo()}
          
          {/* Описание и атрибуты */}
          <div className="mt-8 bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-xl font-semibold mb-4">Описание объявления</h2>
            <p className="whitespace-pre-line text-gray-700">{listing.description || 'Описание отсутствует'}</p>
            
            {/* Атрибуты предмета - используем новую функцию renderAttributes */}
            {renderAttributes()}
          </div>
        </div>
        
        {/* Боковая панель с информацией */}
        <div className="lg:col-span-1 space-y-6">
          
          {/* Ценовая информация */}
          {renderPriceInfo()}
          
          {/* Информация о продавце */}
          {renderSellerCard()}
          
          {/* Кнопки действий */}
          <div className="space-y-4">
            {!isOwner && listing.status === 'active' && (
              <BuyButton
                listingId={listing.id}
                price={listing.price}
                currency={listing.currency}
                sellerId={listing.seller.id}
              />
            )}
            
            {isOwner && (
              <div className="space-y-3">
                <Button
                  type="primary"
                  onClick={() => router.push(`/marketplace/listings/${listing.id}/edit`)}
                  className="w-full"
                  size="large"
                >
                  Редактировать
                </Button>
                <Button
                  danger
                  onClick={() => setIsDeleteModalOpen(true)}
                  className="w-full"
                  size="large"
                >
                  Удалить
                </Button>
              </div>
            )}
          </div>
          
          {/* Рекомендации для покупателей */}
          {renderBuyerTips()}
          
          {/* Статистика объявления */}
          {renderListingStats()}
        </div>
      </div>
      
      {/* Модальное окно подтверждения удаления */}
      {isDeleteModalOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full">
            <h3 className="text-xl font-bold mb-4">Подтверждение удаления</h3>
            <p className="mb-6">Вы уверены, что хотите удалить это объявление? Это действие нельзя отменить.</p>
            
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => setIsDeleteModalOpen(false)}
                className="px-4 py-2 border border-gray-300 rounded text-gray-700 hover:bg-gray-50 transition"
              >
                Отмена
              </button>
              <button
                onClick={handleDelete}
                className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition"
              >
                Удалить
              </button>
            </div>
          </div>
        </div>
      )}
      
      {/* Похожие объявления */}
      {listing.similar_listings && listing.similar_listings.length > 0 && (
        <div className="mt-12">
          <h2 className="text-2xl font-bold mb-6">Похожие объявления</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
            {listing.similar_listings.map(item => (
              <Card
                key={item.id}
                hoverable
                className="overflow-hidden"
                onClick={() => router.push(`/marketplace/listings/${item.id}`)}
                cover={
                  <div className="h-48 bg-gray-100 relative">
                    {item.images && item.images.length > 0 ? (
                      <Image
                        src={item.images[0].url}
                        alt={item.title}
                        fill
                        className="object-cover"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <span className="text-gray-400">Нет изображения</span>
                      </div>
                    )}
                    
                    {/* Статус объявления */}
                    <div className="absolute top-2 right-2">
                      <span className={`px-2 py-1 text-xs rounded-full ${
                        item.status === 'active' ? 'bg-green-100 text-green-800' :
                        item.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                        item.status === 'sold' ? 'bg-red-100 text-red-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {item.status === 'active' ? 'Активно' : 
                         item.status === 'pending' ? 'Модерация' :
                         item.status === 'sold' ? 'Продано' : 
                         item.status}
                      </span>
                    </div>
                  </div>
                }
              >
                <Card.Meta
                  title={
                    <div className="line-clamp-2 text-sm font-medium">
                      {item.title}
                    </div>
                  }
                  description={
                    <div className="space-y-2">
                      <div className="text-lg font-bold text-blue-600">
                        {formatPrice(item.price, item.currency)}
                      </div>
                      
                      <div className="flex justify-between text-xs text-gray-500">
                        <span>{item.views_count} просм.</span>
                        <span>{formatDistanceToNow(new Date(item.created_at), { addSuffix: true, locale: ru })}</span>
                      </div>
                      
                      {item.description && (
                        <div className="text-xs text-gray-600 line-clamp-2">
                          {item.description}
                        </div>
                      )}
                    </div>
                  }
                />
              </Card>
            ))}
          </div>
        </div>
      )}
      
      {/* Заменяем старое модальное окно чата на новый ChatModal */}
      <ChatModal
        visible={isChatModalOpen}
        onClose={() => setIsChatModalOpen(false)}
        listingId={listing?.id}
        sellerId={listing?.seller?.id}
        title={`Чат с продавцом: ${listing?.seller?.username || 'Продавец'}`}
      />
    </div>
  );
} 