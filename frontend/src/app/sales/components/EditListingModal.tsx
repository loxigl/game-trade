'use client';

import React, { useState, useEffect } from 'react';
import { Modal, Form, Input, InputNumber, Select, Upload, message, Button } from 'antd';
import { UploadOutlined, LoadingOutlined } from '@ant-design/icons';
import { getGames, getCategoriesByGame, updateListing } from '../../api/market';
import { Listing } from '../../api/market';

const { Option } = Select;
const { TextArea } = Input;

interface EditListingModalProps {
  listing: Listing | null;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

interface Game {
  id: number;
  name: string;
}

interface ApiResponse<T> {
  success: boolean;
  data: T;
  meta?: {
    total: number;
    page: number;
    limit: number;
    pages: number;
  };
}

const EditListingModal: React.FC<EditListingModalProps> = ({ listing, isOpen, onClose, onSuccess }) => {
  const [form] = Form.useForm();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [games, setGames] = useState<Game[]>([]);
  const [categories, setCategories] = useState<Array<{ id: number; name: string }>>([]);
  const [fileList, setFileList] = useState<any[]>([]);
  const [isLoadingCategories, setIsLoadingCategories] = useState(false);
  
  
  // Инициализация формы при открытии модального окна
  useEffect(() => {
    if (isOpen && listing) {
      // Загружаем список игр
      const fetchGames = async () => {
        try {
          const gamesData = await getGames();
          setGames(gamesData);
          
          // Если у объявления есть игра, загружаем категории для этой игры
          if (listing.game?.id) {
            setIsLoadingCategories(true);
            try {
              const categoriesData = await getCategoriesByGame(listing.game.id);
              setCategories(categoriesData);
            } catch (error) {
              console.error('Ошибка при получении категорий:', error);
            } finally {
              setIsLoadingCategories(false);
            }
          }
        } catch (error) {
          console.error('Ошибка при получении списка игр:', error);
          message.error('Не удалось загрузить список игр');
        }
      };
      
      fetchGames();
      
      // Инициализируем форму данными из объявления
      form.setFieldsValue({
        title: listing.title,
        description: listing.description,
        price: listing.price,
        currency: listing.currency,
        gameId: listing.game?.id,
        categoryId: listing.category?.id,
      });
      
      // Инициализируем список изображений
      const initialFileList = listing.images.map((image, index) => ({
        uid: `-${index}`,
        name: `Image ${index + 1}`,
        status: 'done',
        url: image.url,
        thumbUrl: image.url,
        isMain: image.isMain
      }));
      
      setFileList(initialFileList);
    }
  }, [isOpen, listing, form]);
  
  // Получение категорий при выборе игры
  const handleGameChange = async (gameId: number) => {
    form.setFieldsValue({ categoryId: undefined });
    setIsLoadingCategories(true);
    
    try {
      const categoriesData = await getCategoriesByGame(gameId);
      setCategories(categoriesData);
    } catch (error) {
      console.error('Ошибка при получении категорий:', error);
      message.error('Не удалось загрузить категории для выбранной игры');
    } finally {
      setIsLoadingCategories(false);
    }
  };
  
  // Обработка загрузки изображений
  const handleFileChange = ({ fileList }: any) => {
    setFileList(fileList);
  };
  
  // Отправка формы редактирования объявления
  const handleSubmit = async (values: any) => {
    if (!listing) return;
    
    setIsSubmitting(true);
    
    try {
      const formData = new FormData();
      
      // Добавляем основные поля в FormData
      formData.append('title', values.title);
      formData.append('description', values.description);
      formData.append('price', values.price.toString());
      formData.append('currency', values.currency);
      formData.append('gameId', values.gameId.toString());
      if (values.categoryId) {
        formData.append('categoryId', values.categoryId.toString());
      }
      
      // Обработка изображений
      // Здесь мы отправляем только новые изображения и указываем, какие существующие нужно сохранить
      const existingImages: string[] = [];
      let mainImageIndex = 0;
      
      fileList.forEach((file, index) => {
        // Если это существующее изображение (имеет URL)
        if (file.url) {
          // Находим ID изображения по URL
          const imageId = listing.images.find(img => img.url === file.url)?.id;
          if (imageId) {
            existingImages.push(imageId.toString());
            
            // Если это основное изображение, запоминаем его индекс
            if (file.isMain) {
              mainImageIndex = existingImages.length - 1;
            }
          }
        } else if (file.originFileObj) {
          // Если это новое изображение
          formData.append('new_images', file.originFileObj);
        }
      });
      
      // Добавляем список существующих изображений, которые нужно сохранить
      if (existingImages.length > 0) {
        formData.append('existing_images', existingImages.join(','));
        formData.append('main_image_index', mainImageIndex.toString());
      }
      
      // Отправляем данные на сервер
      await updateListing(listing.id, formData);
      
      message.success('Объявление успешно обновлено');
      onSuccess();
      onClose();
      
    } catch (error) {
      console.error('Ошибка при обновлении объявления:', error);
      message.error('Не удалось обновить объявление. Попробуйте позже.');
    } finally {
      setIsSubmitting(false);
    }
  };
  
  if (!listing) return null;
  
  return (
    <Modal
      title="Редактирование объявления"
      open={isOpen}
      onCancel={onClose}
      footer={null}
      width={700}
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
      >
        <Form.Item
          name="title"
          label="Название"
          rules={[{ required: true, message: 'Введите название объявления' }]}
        >
          <Input placeholder="Введите название товара или услуги" maxLength={100} />
        </Form.Item>
        
        <Form.Item
          name="gameId"
          label="Игра"
          rules={[{ required: true, message: 'Выберите игру' }]}
        >
          <Select 
            placeholder="Выберите игру" 
            onChange={handleGameChange}
          >
            {games.map(game => (
              <Option key={game.id} value={game.id}>{game.name}</Option>
            ))}
          </Select>
        </Form.Item>
        
        <Form.Item
          name="categoryId"
          label="Категория"
        >
          <Select 
            placeholder={isLoadingCategories ? 'Загрузка категорий...' : 'Выберите категорию'} 
            disabled={categories.length === 0 || isLoadingCategories}
            loading={isLoadingCategories}
          >
            {categories.map(category => (
              <Option key={category.id} value={category.id}>{category.name}</Option>
            ))}
          </Select>
        </Form.Item>
        
        <Form.Item
          name="description"
          label="Описание"
          rules={[{ required: true, message: 'Введите описание объявления' }]}
        >
          <TextArea 
            placeholder="Подробно опишите товар, его состояние, особенности и условия продажи" 
            rows={4} 
            maxLength={2000} 
          />
        </Form.Item>
        
        <div className="flex flex-wrap gap-4">
          <Form.Item
            name="price"
            label="Цена"
            rules={[{ required: true, message: 'Укажите цену' }]}
            className="w-full sm:w-auto sm:flex-1"
          >
            <InputNumber 
              placeholder="0.00" 
              min={0} 
              precision={2} 
              style={{ width: '100%' }}
            />
          </Form.Item>
          
          <Form.Item
            name="currency"
            label="Валюта"
            className="w-full sm:w-auto"
          >
            <Select style={{ width: 100 }}>
              <Option value="RUB">₽</Option>
              <Option value="USD">$</Option>
              <Option value="EUR">€</Option>
            </Select>
          </Form.Item>
        </div>
        
        <Form.Item
          label="Изображения"
        >
          <Upload
            listType="picture-card"
            fileList={fileList}
            onChange={handleFileChange}
            beforeUpload={() => false}
            multiple
          >
            {fileList.length < 5 && (
              <div>
                <UploadOutlined />
                <div style={{ marginTop: 8 }}>Загрузить</div>
              </div>
            )}
          </Upload>
          <div className="text-gray-500 text-xs mt-1">
            Вы можете загрузить до 5 изображений в формате JPG, PNG или WEBP.
          </div>
        </Form.Item>
        
        <div className="flex justify-end gap-2 mt-4">
          <Button onClick={onClose}>
            Отмена
          </Button>
          <Button type="primary" htmlType="submit" loading={isSubmitting}>
            Сохранить изменения
          </Button>
        </div>
      </Form>
    </Modal>
  );
};

export default EditListingModal; 