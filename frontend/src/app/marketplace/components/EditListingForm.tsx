'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';
import { useAuth } from '../../hooks/auth';
import { useMarketplace } from '../../hooks/marketplace';
import { useImageUpload, ImageType } from '../../hooks/image-upload';

interface EditListingFormProps {
  listingId: number;
}

interface UploadedImage {
  id: number | string;
  url: string;
  is_main: boolean;
  order_index: number;
  original_filename?: string;
  content_type?: string;
}

interface EditFormData {
  title: string;
  description: string;
  price: number;
  currency: string;
  is_negotiable: boolean;
}

export default function EditListingForm({ listingId }: EditListingFormProps) {
  const { isAuthenticated, user } = useAuth();
  const router = useRouter();
  const { getListingById, updateListing } = useMarketplace();
  const imageUpload = useImageUpload();

  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  
  const [originalListing, setOriginalListing] = useState<any>(null);
  const [formData, setFormData] = useState<EditFormData>({
    title: '',
    description: '',
    price: 0,
    currency: 'USD',
    is_negotiable: false,
  });
  
  const [uploadedImages, setUploadedImages] = useState<UploadedImage[]>([]);
  const [deletedImageIds, setDeletedImageIds] = useState<number[]>([]);
  const [attributeValues, setAttributeValues] = useState<Record<string, any>>({});
  const [draggedImageIndex, setDraggedImageIndex] = useState<number | null>(null);

  // Загрузка данных объявления
  useEffect(() => {
    if (!isAuthenticated || !listingId) return;

    const loadListing = async () => {
      try {
        setIsLoading(true);
        setError(null);
        
        const listing = await getListingById(listingId);
        if (!listing) {
          setError('Объявление не найдено');
          return;
        }

        // Проверяем права доступа
        if (listing.seller_id !== user?.id) {
          setError('У вас нет прав для редактирования этого объявления');
          return;
        }

        setOriginalListing(listing);
        
        // Заполняем форму данными объявления
        setFormData({
          title: listing.title || '',
          description: listing.description || '',
          price: listing.price || 0,
          currency: listing.currency || 'USD',
          is_negotiable: listing.is_negotiable || false,
        });

        // Загружаем изображения
        if (listing.images && listing.images.length > 0) {
          setUploadedImages(listing.images.map(img => ({
            id: img.id,
            url: img.url,
            is_main: img.is_main,
            order_index: img.order_index,
          })));
        }

        // Загружаем значения атрибутов
        const attrValues: Record<string, any> = {};
        
        // Атрибуты категории
        if (listing.item_attributes) {
          listing.item_attributes.forEach(attr => {
            if (attr.value_string !== undefined) attrValues[attr.attribute_id] = attr.value_string;
            else if (attr.value_number !== undefined) attrValues[attr.attribute_id] = attr.value_number;
            else if (attr.value_boolean !== undefined) attrValues[attr.attribute_id] = attr.value_boolean;
          });
        }

        // Атрибуты шаблона
        if (listing.template_attributes) {
          listing.template_attributes.forEach(attr => {
            if (attr.value_string !== undefined) attrValues[attr.template_attribute_id] = attr.value_string;
            else if (attr.value_number !== undefined) attrValues[attr.template_attribute_id] = attr.value_number;
            else if (attr.value_boolean !== undefined) attrValues[attr.template_attribute_id] = attr.value_boolean;
          });
        }

        setAttributeValues(attrValues);

      } catch (err) {
        console.error('Ошибка загрузки объявления:', err);
        setError('Ошибка загрузки объявления');
      } finally {
        setIsLoading(false);
      }
    };

    loadListing();
  }, [isAuthenticated, listingId, user?.id, getListingById]);

  const handleFormChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
    const { name, value, type } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? (e.target as HTMLInputElement).checked : 
              type === 'number' ? parseFloat(value) || 0 : value
    }));
  };

  const handleAttributeChange = (attributeId: number, value: any, attributeType: string) => {
    let processedValue = value;
    
    if (attributeType === 'number') {
      processedValue = parseFloat(value) || 0;
    } else if (attributeType === 'boolean') {
      processedValue = Boolean(value);
    }

    setAttributeValues(prev => ({
      ...prev,
      [attributeId]: processedValue
    }));
  };

  const handleImageUpload = async (files: FileList | null) => {
    if (!files || files.length === 0) return;

    try {
      setIsLoading(true);
      
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const uploadedFile = await imageUpload.uploadImage(file, ImageType.LISTING);
        
        if (uploadedFile) {
          const newImage: UploadedImage = {
            id: uploadedFile.id,
            url: uploadedFile.url,
            is_main: uploadedImages.length === 0 && i === 0, // Первое изображение главное, только если нет других
            order_index: uploadedImages.length + i,
            original_filename: uploadedFile.original_filename,
            content_type: uploadedFile.content_type,
          };
          
          setUploadedImages(prev => {
            const newImages = [...prev, newImage];
            // Пересчитываем порядок и устанавливаем главное изображение
            return newImages.map((img, index) => ({
              ...img,
              order_index: index,
              is_main: index === 0
            }));
          });
        }
      }
    } catch (error) {
      console.error('Ошибка загрузки изображения:', error);
      setError('Не удалось загрузить изображение');
    } finally {
      setIsLoading(false);
    }
  };

  const handleImageDelete = (imageId: string | number) => {
    const numericId = typeof imageId === 'string' ? parseInt(imageId, 10) : imageId;
    
    if (!isNaN(numericId)) {
      setDeletedImageIds(prev => [...prev, numericId]);
      setUploadedImages(prev => prev.filter(img => img.id !== imageId));
    }
  };

  const handleSetMainImage = (id: number | string) => {
    setUploadedImages(prev => 
      prev.map(img => ({
        ...img,
        is_main: img.id === id
      }))
    );
  };

  // Функции для drag and drop
  const handleDragStart = (e: React.DragEvent, index: number) => {
    setDraggedImageIndex(index);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = (e: React.DragEvent, targetIndex: number) => {
    e.preventDefault();
    
    if (draggedImageIndex === null || draggedImageIndex === targetIndex) {
      setDraggedImageIndex(null);
      return;
    }

    setUploadedImages(prev => {
      const newImages = [...prev];
      const draggedImage = newImages[draggedImageIndex];
      
      // Удаляем перетаскиваемое изображение
      newImages.splice(draggedImageIndex, 1);
      
      // Вставляем на новое место
      newImages.splice(targetIndex, 0, draggedImage);
      
      // Обновляем order_index для всех изображений
      return newImages.map((img, index) => ({
        ...img,
        order_index: index,
      }));
    });
    
    setDraggedImageIndex(null);
  };

  const handleDragEnd = () => {
    setDraggedImageIndex(null);
  };

  // Функции для изменения порядка через кнопки (альтернатива для мобильных)
  const moveImageUp = (index: number) => {
    if (index === 0) return;
    
    setUploadedImages(prev => {
      const newImages = [...prev];
      const temp = newImages[index];
      newImages[index] = newImages[index - 1];
      newImages[index - 1] = temp;
      
      // Обновляем order_index и делаем первое изображение главным
      return newImages.map((img, idx) => ({
        ...img,
        order_index: idx,
        is_main: idx === 0
      }));
    });
  };

  const moveImageDown = (index: number) => {
    if (index === uploadedImages.length - 1) return;
    
    setUploadedImages(prev => {
      const newImages = [...prev];
      const temp = newImages[index];
      newImages[index] = newImages[index + 1];
      newImages[index + 1] = temp;
      
      // Обновляем order_index и делаем первое изображение главным
      return newImages.map((img, idx) => ({
        ...img,
        order_index: idx,
        is_main: idx === 0
      }));
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.title.trim() || !formData.description.trim() || formData.price <= 0) {
      setError('Пожалуйста, заполните все обязательные поля');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      // Создаем FormData для отправки всех данных
      const submitData = {
        title: formData.title,
        description: formData.description,
        price: formData.price,
        currency: formData.currency,
        is_negotiable: formData.is_negotiable,
        images: uploadedImages.map((image) => ({
          id: image.id,
          is_main: image.is_main,
          order_index: image.order_index,
        })),
        deleted_image_ids: deletedImageIds
      };

      const result = await updateListing(listingId, submitData);
      
      if (result) {
        router.push(`/marketplace/listings/${listingId}`);
      }
    } catch (error) {
      console.error('Ошибка обновления объявления:', error);
      setError('Не удалось обновить объявление. Попробуйте еще раз.');
    } finally {
      setIsLoading(false);
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="container mx-auto py-8 text-center">
        <h1 className="text-2xl font-bold text-red-500">Необходима авторизация</h1>
        <p className="mt-2 text-gray-600">Для редактирования объявления необходимо войти в систему</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="container mx-auto py-8">
        <div className="flex justify-center items-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
          <span className="ml-3 text-lg">Загрузка объявления...</span>
        </div>
      </div>
    );
  }

  if (error && !originalListing) {
    return (
      <div className="container mx-auto py-8 text-center">
        <h1 className="text-2xl font-bold text-red-500">Ошибка</h1>
        <p className="mt-2 text-gray-600">{error}</p>
        <button
          onClick={() => router.back()}
          className="mt-4 px-4 py-2 bg-gray-500 hover:bg-gray-600 text-white rounded"
        >
          Назад
        </button>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 max-w-4xl">
      <div className="bg-white rounded-lg shadow-lg p-6">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold">Редактирование объявления</h1>
          <button
            onClick={() => router.push(`/marketplace/listings/${listingId}`)}
            className="px-4 py-2 bg-gray-500 hover:bg-gray-600 text-white rounded"
          >
            Отмена
          </button>
        </div>

        {error && (
          <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-md">
            <p className="text-red-700">{error}</p>
          </div>
        )}

        {successMessage && (
          <div className="mb-4 p-4 bg-green-50 border border-green-200 rounded-md">
            <p className="text-green-700">{successMessage}</p>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Основная информация */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="md:col-span-2">
              <label htmlFor="title" className="block text-sm font-medium text-gray-700 mb-1">
                Название объявления *
              </label>
              <input
                type="text"
                id="title"
                name="title"
                value={formData.title}
                onChange={handleFormChange}
                className="block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                required
                maxLength={100}
              />
            </div>

            <div>
              <label htmlFor="price" className="block text-sm font-medium text-gray-700 mb-1">
                Цена *
              </label>
              <input
                type="number"
                id="price"
                name="price"
                value={formData.price}
                onChange={handleFormChange}
                min="0"
                step="0.01"
                className="block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                required
              />
            </div>

            <div>
              <label htmlFor="currency" className="block text-sm font-medium text-gray-700">
                Валюта
              </label>
              <select
                id="currency"
                value={formData.currency}
                onChange={(e) => setFormData(prev => ({ ...prev, currency: e.target.value }))}
                className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500"
              >
                <option value="USD">USD</option>
                <option value="EUR">EUR</option>
                <option value="RUB">RUB</option>
              </select>
            </div>

            {/* Возможность торга */}
            <div className="flex items-center">
              <input
                id="is_negotiable"
                type="checkbox"
                checked={formData.is_negotiable}
                onChange={(e) => setFormData(prev => ({ ...prev, is_negotiable: e.target.checked }))}
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <label htmlFor="is_negotiable" className="ml-2 block text-sm text-gray-900">
                Возможен торг
              </label>
            </div>

            <div className="md:col-span-2">
              <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-1">
                Описание
              </label>
              <textarea
                id="description"
                name="description"
                value={formData.description}
                onChange={handleFormChange}
                rows={4}
                className="block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                maxLength={1000}
              />
            </div>
          </div>

          {/* Атрибуты */}
          {originalListing && (originalListing.all_attributes || []).length > 0 && (
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4">Атрибуты предмета</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {originalListing.all_attributes.map((attr: any) => {
                  const attrId = attr.attribute_id || attr.template_attribute_id;
                  const currentValue = attributeValues[attrId];
                  
                  return (
                    <div key={attrId} className="border rounded-md p-4">
                      <label className="block text-sm font-medium text-gray-700 mb-1">
                        {attr.attribute_name || attr.name}
                        {attr.is_required && <span className="text-red-500 ml-1">*</span>}
                      </label>
                      
                      {attr.attribute_type === 'string' && (
                        <input
                          type="text"
                          value={currentValue || ''}
                          onChange={(e) => handleAttributeChange(attrId, e.target.value, 'string')}
                          className="block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                        />
                      )}
                      
                      {attr.attribute_type === 'number' && (
                        <input
                          type="number"
                          value={currentValue || 0}
                          onChange={(e) => handleAttributeChange(attrId, e.target.value, 'number')}
                          className="block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                        />
                      )}
                      
                      {attr.attribute_type === 'boolean' && (
                        <div className="flex items-center">
                          <input
                            type="checkbox"
                            checked={currentValue || false}
                            onChange={(e) => handleAttributeChange(attrId, e.target.checked, 'boolean')}
                            className="h-4 w-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500"
                          />
                          <span className="ml-2 text-sm text-gray-700">
                            {currentValue ? 'Да' : 'Нет'}
                          </span>
                        </div>
                      )}
                      
                      {attr.attribute_type === 'enum' && attr.options && (
                        <select
                          value={currentValue || ''}
                          onChange={(e) => handleAttributeChange(attrId, e.target.value, 'enum')}
                          className="block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                        >
                          <option value="">Выберите значение</option>
                          {(typeof attr.options === 'string' ? JSON.parse(attr.options) : attr.options).map((option: string, index: number) => (
                            <option key={index} value={option}>
                              {option}
                            </option>
                          ))}
                        </select>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Изображения */}
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-4">Изображения</h3>
            
            <div className="border-2 border-dashed border-gray-300 rounded-md p-6 text-center mb-4">
              <input
                type="file"
                id="image-upload"
                accept="image/*"
                className="hidden"
                onChange={(e) => e.target.files && handleImageUpload(e.target.files)}
              />
              <label
                htmlFor="image-upload"
                className="cursor-pointer flex flex-col items-center justify-center"
              >
                <svg
                  className="mx-auto h-12 w-12 text-gray-400"
                  stroke="currentColor"
                  fill="none"
                  viewBox="0 0 48 48"
                >
                  <path
                    d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
                    strokeWidth={2}
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
                <p className="mt-1 text-sm text-gray-600">
                  Нажмите, чтобы добавить изображение
                </p>
                <p className="mt-1 text-xs text-gray-500">PNG, JPG, GIF до 5MB</p>
              </label>
            </div>

            {uploadedImages.length > 0 && (
              <div>
                <p className="text-sm text-gray-600 mb-2">
                  <strong>Управление изображениями:</strong>
                  <br />• Перетаскивайте изображения для изменения порядка
                  <br />• Используйте кнопки со стрелками для точного позиционирования  
                  <br />• Первое изображение автоматически становится главным
                  <br />• Наведите курсор на изображение для доступа к функциям
                </p>
                <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
                  {uploadedImages.map((image, index) => (
                    <div
                      key={image.id}
                      draggable
                      onDragStart={(e) => handleDragStart(e, index)}
                      onDragOver={handleDragOver}
                      onDragEnter={handleDragEnter}
                      onDrop={(e) => handleDrop(e, index)}
                      onDragEnd={handleDragEnd}
                      className={`relative border rounded-md overflow-hidden cursor-move transition-all duration-200 ${
                        image.is_main ? 'ring-2 ring-blue-500' : ''
                      } ${
                        draggedImageIndex === index ? 'opacity-50 scale-95' : 'hover:shadow-lg'
                      }`}
                    >
                      <div className="w-full h-32 relative">
                        <Image
                          src={image.url || imageUpload.getImageUrl(image.id)}
                          alt=""
                          fill
                          className="object-cover"
                          draggable={false}
                        />
                      </div>
                      
                      {/* Номер порядка */}
                      <div className="absolute top-1 right-1 bg-black bg-opacity-70 text-white text-xs px-2 py-1 rounded">
                        {index + 1}
                      </div>
                      
                      {/* Индикатор главного изображения */}
                      {image.is_main && (
                        <div className="absolute top-1 left-1 bg-blue-500 text-white text-xs px-2 py-1 rounded">
                          Главное
                        </div>
                      )}
                      
                      {/* Индикатор перетаскивания */}
                      <div className="absolute top-1 left-1/2 transform -translate-x-1/2 bg-gray-800 bg-opacity-70 text-white text-xs px-2 py-1 rounded opacity-0 hover:opacity-100 transition-opacity">
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
                        </svg>
                      </div>
                      
                      <div className="absolute inset-0 bg-black bg-opacity-0 hover:bg-opacity-50 transition flex items-center justify-center opacity-0 hover:opacity-100">
                        <div className="flex flex-col items-center space-y-1">
                          {/* Кнопки изменения порядка */}
                          <div className="flex space-x-1 mb-1">
                            <button
                              type="button"
                              onClick={() => moveImageUp(index)}
                              disabled={index === 0}
                              className="bg-gray-700 hover:bg-gray-600 text-white p-1 rounded disabled:opacity-50 disabled:cursor-not-allowed"
                              title="Переместить вверх"
                            >
                              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                              </svg>
                            </button>
                            <button
                              type="button"
                              onClick={() => moveImageDown(index)}
                              disabled={index === uploadedImages.length - 1}
                              className="bg-gray-700 hover:bg-gray-600 text-white p-1 rounded disabled:opacity-50 disabled:cursor-not-allowed"
                              title="Переместить вниз"
                            >
                              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                              </svg>
                            </button>
                          </div>
                          
                          {/* Основные кнопки */}
                          <div className="flex space-x-1">
                            <button
                              type="button"
                              onClick={() => handleSetMainImage(image.id)}
                              className="bg-blue-500 text-white p-1 rounded-full"
                              title="Сделать главным изображением"
                            >
                              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                              </svg>
                            </button>
                            <button
                              type="button"
                              onClick={() => handleImageDelete(image.id)}
                              className="bg-red-500 text-white p-1 rounded-full"
                              title="Удалить изображение"
                            >
                              <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
                                <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
                              </svg>
                            </button>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Кнопки */}
          <div className="flex justify-end space-x-4 pt-6 border-t">
            <button
              type="button"
              onClick={() => router.push(`/marketplace/listings/${listingId}`)}
              className="px-6 py-2 bg-gray-500 hover:bg-gray-600 text-white rounded-md"
              disabled={isSaving}
            >
              Отмена
            </button>
            <button
              type="submit"
              className="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md disabled:opacity-50"
              disabled={isSaving}
            >
              {isSaving ? 'Сохранение...' : 'Сохранить изменения'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
} 