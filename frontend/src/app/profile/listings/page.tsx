'use client';

import React from 'react';
import { useAuth } from '../../hooks/auth';
import UserListings from '../components/UserListings';
import ProfileLayout from '../components/ProfileLayout';
import { Spin, Alert } from 'antd';
import { redirect } from 'next/navigation';

export default function UserListingsPage() {
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
    <ProfileLayout activeTab="listings">
      <div className="container mx-auto px-4 py-8">
        <UserListings />
      </div>
    </ProfileLayout>
  );
} 