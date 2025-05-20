'use client';

import React, { useState } from 'react';
import { Button, Modal, Form, Input, InputNumber, Select, Upload, message } from 'antd';
import { PlusOutlined, UploadOutlined } from '@ant-design/icons';
import { createListing } from '../../api/market';
import { getGames, getCategoriesByGame } from '../../api/market';
import { useRouter } from 'next/navigation';

const { Option } = Select;
const { TextArea } = Input;

const CreateListingButton: React.FC = () => {
  const [form] = Form.useForm();
  const router = useRouter();
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [games, setGames] = useState<Array<{ id: number; name: string }>>([]);
  const [categories, setCategories] = useState<Array<{ id: number; name: string }>>([]);
  const [fileList, setFileList] = useState<any[]>([]);
  
  // Получение списка игр при открытии модального окна
  const showModal = async () => {
    try {
      const gamesData = await getGames();
      setGames(gamesData);
      setIsModalVisible(true);
    } catch (error) {
      console.error('Ошибка при получении списка игр:', error);
      message.error('Не удалось загрузить список игр');
    }
  };
  
  // Получение категорий при выборе игры
  const handleGameChange = async (gameId: number) => {
    try {
      const categoriesData = await getCategoriesByGame(gameId);
      setCategories(categoriesData);
      form.setFieldsValue({ categoryId: undefined });
    } catch (error) {
      console.error('Ошибка при получении категорий:', error);
      message.error('Не удалось загрузить категории для выбранной игры');
    }
  };
  
  // Обработка загрузки изображений
  const handleFileChange = ({ fileList }: any) => {
    setFileList(fileList);
  };
  
  // Отправка формы создания объявления
  const handleSubmit = async (values: any) => {
    if (fileList.length === 0) {
      message.error('Добавьте хотя бы одно изображение');
      return;
    }
    
    setIsSubmitting(true);
    
    try {
      console.log('Создание объявления. Значения формы:', values);
      
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
      
      // Добавляем файлы изображений
      fileList.forEach((file, index) => {
        // Проверяем, что originFileObj существует
        if (file.originFileObj instanceof File) {
          formData.append('images', file.originFileObj, file.originFileObj.name);
          console.log(`Добавлен файл: ${file.originFileObj.name}, размер: ${file.originFileObj.size} байт`);
        } else {
          console.warn(`Не удалось добавить файл с индексом ${index}, originFileObj не является File`);
        }
        
        if (index === 0) {
          formData.append('mainImageIndex', '0');
        }
      });
      
      // Проверяем содержимое FormData перед отправкой
      const formDataEntries = Array.from(formData.entries()).reduce((obj: any, [key, value]) => {
        obj[key] = typeof value === 'string' ? value : `<File: ${(value as File).name}>`;
        return obj;
      }, {});
      
      console.log('Отправка FormData:', formDataEntries);
      
      // Отправляем данные на сервер
      const result = await createListing(formData);
      
      console.log('Успешно создано объявление:', result);
      
      message.success('Объявление успешно создано');
      setIsModalVisible(false);
      form.resetFields();
      setFileList([]);
      
      // Перенаправляем на страницу созданного объявления
      router.push(`/marketplace/listings/${result.id}`);
      
    } catch (error) {
      console.error('Ошибка при создании объявления:', error);
      message.error('Не удалось создать объявление. Попробуйте позже.');
    } finally {
      setIsSubmitting(false);
    }
  };
  
  return (
    <>
      <Button 
        type="primary" 
        icon={<PlusOutlined />} 
        onClick={showModal}
      >
        Создать объявление
      </Button>
      
      <Modal
        title="Создание нового объявления"
        open={isModalVisible}
        onCancel={() => setIsModalVisible(false)}
        footer={null}
        width={700}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          initialValues={{
            currency: 'RUB'
          }}
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
              placeholder="Выберите категорию" 
              disabled={categories.length === 0}
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
            rules={[{ required: true, message: 'Добавьте хотя бы одно изображение' }]}
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
              Вы можете загрузить до 5 изображений в формате JPG, PNG или WEBP. Первое изображение будет отображаться как основное.
            </div>
          </Form.Item>
          
          <div className="flex justify-end gap-2 mt-4">
            <Button onClick={() => setIsModalVisible(false)}>
              Отмена
            </Button>
            <Button type="primary" htmlType="submit" loading={isSubmitting}>
              Опубликовать
            </Button>
          </div>
        </Form>
      </Modal>
    </>
  );
};

export default CreateListingButton; 