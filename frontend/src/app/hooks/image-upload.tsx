import { useState } from 'react';
import { useAuth } from './auth';

// Интерфейс для изображения
interface Image {
  id: number;
  url: string;
  is_main: boolean;
  order_index: number;
  original_filename: string;
  content_type: string;
}

// Типы для изображений
export enum ImageType {
  LISTING = 'listing',
  USER = 'user',
  CATEGORY = 'category',
  GAME = 'game',
  OTHER = 'other'
}

// Хук для загрузки и управления изображениями
export const useImageUpload = () => {
  const { isAuthenticated } = useAuth();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState<number>(0);
  
  // API URL для сервиса маркетплейса
  const API_URL = process.env.NEXT_PUBLIC_MARKETPLACE_URL || 'http://localhost:8001/api/marketplace';
  
  // Получение токена авторизации
  const getAuthHeader = () => {
    // Получаем токен из localStorage
    const token = localStorage.getItem('accessToken') || localStorage.getItem('token');
    // Проверяем, есть ли токен
    return token ? { Authorization: `Bearer ${token}` } : undefined;
  };
  
  // Функция для загрузки изображения
  const uploadImage = async (
    file: File,
    imageType: ImageType,
    entityId?: number
  ): Promise<Image | null> => {
    if (!isAuthenticated) {
      setError('Необходимо авторизоваться для загрузки изображений');
      return null;
    }
    
    setIsLoading(true);
    setError(null);
    setProgress(0);
    
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('image_type', imageType);
      
      if (entityId) {
        formData.append('entity_id', entityId.toString());
      }
      
      const headers: HeadersInit = {};
      const authHeader = getAuthHeader();
      if (authHeader) {
        Object.assign(headers, authHeader);
      }
      
      const response = await fetch(`${API_URL}/images`, {
        method: 'POST',
        headers,
        body: formData
      });
      
      if (!response.ok) {
        throw new Error('Failed to upload image');
      }
      
      const data = await response.json();
      return data.data;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Произошла ошибка при загрузке изображения');
      return null;
    } finally {
      setIsLoading(false);
      setProgress(100);
    }
  };
  
  // Функция для получения изображений сущности
  const getEntityImages = async (
    entityId: number,
    imageType: ImageType
  ): Promise<Image[]> => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await fetch(
        `${API_URL}/images/entity/${entityId}?image_type=${imageType}`
      );
      
      if (!response.ok) {
        throw new Error('Failed to fetch entity images');
      }
      
      const data = await response.json();
      return data.data || [];
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Произошла ошибка при загрузке изображений');
      return [];
    } finally {
      setIsLoading(false);
    }
  };
  
  // Функция для установки основного изображения
  const setMainImage = async (
    imageId: number,
    entityId: number,
    imageType: ImageType
  ): Promise<boolean> => {
    if (!isAuthenticated) {
      setError('Необходимо авторизоваться для управления изображениями');
      return false;
    }
    
    setIsLoading(true);
    setError(null);
    
    try {
      const headers: HeadersInit = {
        'Content-Type': 'application/json'
      };
      
      const authHeader = getAuthHeader();
      if (authHeader) {
        Object.assign(headers, authHeader);
      }
      
      const response = await fetch(`${API_URL}/images/${imageId}/main`, {
        method: 'PUT',
        headers,
        body: JSON.stringify({
          entity_id: entityId,
          image_type: imageType
        })
      });
      
      if (!response.ok) {
        throw new Error('Failed to set main image');
      }
      
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Произошла ошибка при установке основного изображения');
      return false;
    } finally {
      setIsLoading(false);
    }
  };
  
  // Функция для удаления изображения
  const deleteImage = async (imageId: number): Promise<boolean> => {
    if (!isAuthenticated) {
      setError('Необходимо авторизоваться для удаления изображений');
      return false;
    }
    
    setIsLoading(true);
    setError(null);
    
    try {
      const headers: HeadersInit = {};
      
      const authHeader = getAuthHeader();
      if (authHeader) {
        Object.assign(headers, authHeader);
      }
      
      const response = await fetch(`${API_URL}/images/${imageId}`, {
        method: 'DELETE',
        headers
      });
      
      if (!response.ok) {
        throw new Error('Failed to delete image');
      }
      
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Произошла ошибка при удалении изображения');
      return false;
    } finally {
      setIsLoading(false);
    }
  };
  
  // Функция для обновления порядка изображения
  const updateImageOrder = async (
    imageId: number,
    orderIndex: number
  ): Promise<boolean> => {
    if (!isAuthenticated) {
      setError('Необходимо авторизоваться для управления изображениями');
      return false;
    }
    
    setIsLoading(true);
    setError(null);
    
    try {
      const headers: HeadersInit = {
        'Content-Type': 'application/json'
      };
      
      const authHeader = getAuthHeader();
      if (authHeader) {
        Object.assign(headers, authHeader);
      }
      
      const response = await fetch(`${API_URL}/images/${imageId}/order`, {
        method: 'PUT',
        headers,
        body: JSON.stringify({
          order_index: orderIndex
        })
      });
      
      if (!response.ok) {
        throw new Error('Failed to update image order');
      }
      
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Произошла ошибка при обновлении порядка изображения');
      return false;
    } finally {
      setIsLoading(false);
    }
  };
  
  // Получение URL для изображения
  const getImageUrl = (imageId: number | string): string => {
    // Преобразуем id в number, если это строка
    const numericId = typeof imageId === 'string' ? parseInt(imageId) : imageId;
    return `${API_URL}/images/${numericId}/file`;
  };
  
  // Функция для привязки изображения к сущности
  const linkImage = async (
    imageId: number,
    entityId: number,
    imageType: ImageType,
    isMain: boolean = false
  ): Promise<boolean> => {
    if (!isAuthenticated) {
      setError('Необходимо авторизоваться для управления изображениями');
      return false;
    }
    
    setIsLoading(true);
    setError(null);
    
    try {
      const headers: HeadersInit = {
        'Content-Type': 'application/json'
      };
      
      const authHeader = getAuthHeader();
      if (authHeader) {
        Object.assign(headers, authHeader);
      }
      
      // Привязываем изображение к сущности
      const attachResponse = await fetch(`${API_URL}/images/${imageId}/attach`, {
        method: 'PUT',
        headers,
        body: JSON.stringify({
          entity_id: entityId,
          image_type: imageType
        })
      });
      
      if (!attachResponse.ok) {
        throw new Error('Не удалось привязать изображение к объявлению');
      }
      
      // Если нужно установить изображение как главное
      if (isMain) {
        const mainResponse = await fetch(`${API_URL}/images/${imageId}/main`, {
          method: 'PUT',
          headers,
          body: JSON.stringify({
            entity_id: entityId,
            image_type: imageType
          })
        });
        
        if (!mainResponse.ok) {
          console.warn('Не удалось установить изображение как главное');
        }
      }
      
      return true;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Произошла ошибка при привязке изображения');
      return false;
    } finally {
      setIsLoading(false);
    }
  };
  
  return {
    isLoading,
    error,
    progress,
    uploadImage,
    getEntityImages,
    setMainImage,
    deleteImage,
    updateImageOrder,
    getImageUrl,
    linkImage
  };
}; 