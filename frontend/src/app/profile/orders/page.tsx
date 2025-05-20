'use client';

import React from 'react';
import { useAuth } from '../../hooks/auth';
import AllOrdersList from '../components/AllOrdersList';
import ProfileLayout from '../components/ProfileLayout';
import { Spin } from 'antd';
import { redirect } from 'next/navigation';

export default function OrdersPage() {
  const { isAuthenticated, isLoading } = useAuth();

  // Если пользователь не авторизован и загрузка завершена, перенаправляем на страницу входа
  if (!isLoading && !isAuthenticated) {
    redirect('/login');
  }

  // Показываем спиннер загрузки, пока проверяем аутентификацию
  if (isLoading) {
    return (
      <div className="flex justify-center items-center min-h-screen">
        <Spin size="large" />
      </div>
    );
  }

  return (
    <ProfileLayout activeTab="purchases">
      <div className="container mx-auto px-4 py-8">
        <AllOrdersList />
      </div>
    </ProfileLayout>
  );
} 