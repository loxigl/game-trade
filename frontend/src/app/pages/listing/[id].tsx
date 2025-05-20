import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { GetServerSideProps } from 'next';
import Head from 'next/head';
import {
  Button,
  Card,
  Spin,
  Typography,
  message,
  Divider
} from 'antd';
import MainLayout from '@/components/layout/MainLayout';
import { apiClient } from '@/api/client';

const { Title, Text, Paragraph } = Typography;

// Простая страница детального просмотра
const ListingDetailPage = ({ initialData = null, error = null }) => {
  const router = useRouter();
  const { id } = router.query;
  const [listing, setListing] = useState(initialData);
  const [loading, setLoading] = useState(!initialData);

  // Загрузка данных объявления
  useEffect(() => {
    if (!initialData && id) {
      fetchListingData();
    }
  }, [id, initialData]);

  // Загрузка данных объявления с сервера
  const fetchListingData = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get(`/api/marketplace/listings/${id}`);
      setListing(response.data.data);
    } catch (err) {
      message.error('Не удалось загрузить данные объявления');
      console.error('Ошибка загрузки объявления:', err);
    } finally {
      setLoading(false);
    }
  };

  // Если данные загружаются, отображаем спиннер
  if (loading) {
    return (
      <MainLayout>
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '500px' }}>
          <Spin size="large" tip="Загрузка объявления..." />
        </div>
      </MainLayout>
    );
  }

  // Если произошла ошибка или объявление не найдено
  if (error || !listing) {
    return (
      <MainLayout>
        <div style={{ textAlign: 'center', marginTop: '100px' }}>
          <Title level={3}>Объявление не найдено</Title>
          <Paragraph>Объявление не существует или было удалено.</Paragraph>
          <Button type="primary" onClick={() => router.push('/listings')}>
            Вернуться к списку объявлений
          </Button>
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout>
      <Head>
        <title>{listing.title} | GameTrade</title>
        <meta name="description" content={listing.description?.substring(0, 160) || 'Игровой предмет на площадке GameTrade'} />
      </Head>

      <Button 
        style={{ marginBottom: '16px' }} 
        onClick={() => router.back()}
      >
        Назад
      </Button>

      <Card>
        <Title level={2}>{listing.title}</Title>
        <Divider />
        
        <div style={{ marginBottom: '20px' }}>
          <Title level={3}>Цена: {listing.price} {listing.currency}</Title>
          {listing.is_negotiable && (
            <Text type="secondary">Цена обсуждается</Text>
          )}
        </div>
        
        <div style={{ marginBottom: '20px' }}>
          <Title level={4}>Описание</Title>
          <Paragraph>
            {listing.description || 'Описание отсутствует'}
          </Paragraph>
        </div>

        <div style={{ marginBottom: '20px' }}>
          <Title level={4}>Продавец</Title>
          <Paragraph>
            {listing.seller?.username || 'Неизвестный продавец'}
          </Paragraph>
        </div>
        
        <Divider />
        
        <Button type="primary" size="large">
          Связаться с продавцом
        </Button>
      </Card>
    </MainLayout>
  );
};

// Предварительная загрузка данных на сервере
export const getServerSideProps: GetServerSideProps = async (context) => {
  const { id } = context.params;

  try {
    const response = await apiClient.get(`/marketplace/listings/${id}`);
    return {
      props: {
        initialData: response.data.data
      }
    };
  } catch (error) {
    return {
      props: {
        error: 'Не удалось загрузить объявление',
        initialData: null
      }
    };
  }
};

export default ListingDetailPage; 