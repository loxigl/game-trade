'use client';

import { useState, useEffect, useRef } from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useMarketplace } from '../../hooks/marketplace';
import { useAuth } from '../../hooks/auth';
import { formatDistanceToNow } from 'date-fns';
import { ru } from 'date-fns/locale';
import ListingCard from './ListingCard';

interface ListingDetailProps {
  listingId: number;
}

// Обновляем интерфейс для листинга с поддержкой иерархической структуры категорий
interface Category {
  id: number;
  name: string;
  icon_url?: string;
  game_id: number;
  parent_id?: number | null;
  parent?: Category;
  description?: string;
  game_name?: string;
}

interface ItemTemplate {
  id: number;
  name: string;
  description?: string;
  category_id: number;
  category?: Category;
  attributes?: any[];
  template_attributes?: any[];
}

interface Listing {
  id: number;
  title: string;
  description?: string;
  price: number;
  currency: string;
  status: string;
  created_at: string;
  updated_at: string;
  views_count: number;
  seller: {
    id: number;
    username: string;
    avatar_url?: string;
    rating?: number;
  };
  item_template?: ItemTemplate;
  category?: Category;
  images: Array<{
    id: number;
    url: string;
    is_main: boolean;
    order_index: number;
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
  similar_listings?: Listing[];
  seller_rating?: number;
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
  
  // Используем ref для предотвращения циклических запросов данных
  const dataLoadedRef = useRef<boolean>(false);
  
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
  
  const handleContactSeller = () => {
    // TODO: Реализовать функцию контакта с продавцом
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
    
    // Добавляем игру, если она указана
    const gameName = listing.item_template?.category?.game_name || '';
    if (gameName) {
      breadcrumbs.push(
        <li key="game">
          <div className="flex items-center">
            <span className="mx-2 text-gray-400">/</span>
            <span className="text-gray-500">{gameName}</span>
          </div>
        </li>
      );
    }
    
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
    
    // Получаем путь категорий
    const categoryPath = buildCategoryPath(listing.item_template?.category || listing.category);
    
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
  const createdAtDate = new Date(listing.created_at);
  
  // Проверяем, является ли текущий пользователь продавцом
  const isOwner = isAuthenticated && user?.id === listing.seller?.id;
  
  return (
    <div className="container mx-auto px-4 py-8">
      {/* Хлебные крошки */}
      {renderBreadcrumbs()}
      
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
          
          {/* Описание и атрибуты */}
          <div className="mt-8 bg-white rounded-lg shadow-sm p-6">
            <h2 className="text-xl font-semibold mb-4">Описание</h2>
            <p className="whitespace-pre-line text-gray-700">{listing.description || 'Описание отсутствует'}</p>
            
            {/* Атрибуты предмета - используем новую функцию renderAttributes */}
            {renderAttributes()}
          </div>
        </div>
        
        {/* Информация о цене и продавце */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-lg shadow-sm p-6 sticky top-4">
            <h1 className="text-2xl font-bold mb-4">{listing.title}</h1>
            
            <div className="text-3xl font-bold text-blue-600 mb-4">
              {new Intl.NumberFormat('ru-RU', {
                style: 'currency',
                currency: listing.currency,
                maximumFractionDigits: 2
              }).format(listing.price)}
            </div>
            
            <div className="text-sm text-gray-500 mb-6">
              Размещено: {formatDistanceToNow(createdAtDate, { addSuffix: true, locale: ru })}
              <br />
              Просмотров: {listing.views_count || 0}
            </div>
            
            {!isOwner && (
              <button
                onClick={handleContactSeller}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-4 rounded mb-4 transition"
              >
                Связаться с продавцом
              </button>
            )}
            
            {isOwner && (
              <div className="flex flex-col space-y-3">
                <button
                  onClick={handleEdit}
                  className="w-full bg-gray-100 hover:bg-gray-200 text-gray-800 font-bold py-3 px-4 rounded transition flex items-center justify-center"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                  </svg>
                  Редактировать
                </button>
                
                <button
                  onClick={() => setIsDeleteModalOpen(true)}
                  className="w-full bg-red-100 hover:bg-red-200 text-red-700 font-bold py-3 px-4 rounded transition flex items-center justify-center"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                  Удалить
                </button>
              </div>
            )}
            
            <div className="border-t mt-6 pt-6">
              <h3 className="font-semibold mb-2">Продавец</h3>
              <div className="flex items-center">
                {listing.seller?.avatar_url ? (
                  <Image
                    src={listing.seller.avatar_url}
                    alt={listing.seller.username}
                    width={40}
                    height={40}
                    className="rounded-full mr-3"
                  />
                ) : (
                  <div className="w-10 h-10 rounded-full bg-gray-300 mr-3 flex items-center justify-center">
                    <span className="text-gray-600">{listing.seller?.username.charAt(0).toUpperCase()}</span>
                  </div>
                )}
                <div>
                  <div className="font-medium">{listing.seller?.username}</div>
                  {listing.seller?.rating && (
                    <div className="flex items-center text-sm">
                      <span className="text-yellow-400 mr-1">★</span>
                      <span>{listing.seller.rating.toFixed(1)}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
            
            {/* Шаблон предмета и категория */}
            <div className="border-t mt-6 pt-6">
              <h3 className="font-semibold mb-2">Информация о предмете</h3>
              <div className="text-sm">
                {listing.item_template && (
                  <div className="mb-2">
                    <span className="text-gray-600">Шаблон:</span> {listing.item_template.name}
                  </div>
                )}
                
                {(listing.item_template?.category || listing.category) && (
                  <div className="mb-2">
                    <span className="text-gray-600">Категория:</span> {listing.item_template?.category?.name || listing.category?.name}
                  </div>
                )}
                
                {listing.status && (
                  <div className="mt-2">
                    <span className="text-gray-600">Статус:</span>{' '}
                    <span className={`px-2 py-1 rounded text-xs ${
                      listing.status === 'active' ? 'bg-green-100 text-green-800' :
                      listing.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                      'bg-gray-100 text-gray-800'
                    }`}>
                      {listing.status === 'active' ? 'Активно' :
                       listing.status === 'pending' ? 'На модерации' :
                       listing.status === 'sold' ? 'Продано' : 
                       listing.status === 'cancelled' ? 'Отменено' : 
                       listing.status}
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>
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
              <div 
                key={item.id} 
                className="bg-white rounded-lg shadow-sm overflow-hidden hover:shadow-md transition"
                onClick={() => router.push(`/marketplace/listings/${item.id}`)}
              >
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
                </div>
                <div className="p-4">
                  <h3 className="text-lg font-semibold mb-2 line-clamp-2">{item.title}</h3>
                  <p className="text-xl font-bold text-blue-600">
                    {new Intl.NumberFormat('ru-RU', {
                      style: 'currency',
                      currency: item.currency,
                      maximumFractionDigits: 2
                    }).format(item.price)}
                  </p>
                  <div className="mt-2 text-sm text-gray-500">
                    Размещено: {formatDistanceToNow(new Date(item.created_at), { addSuffix: true, locale: ru })}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
} 