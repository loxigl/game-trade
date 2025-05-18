'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '../../hooks/auth';
import { ProfileSettings } from '../../components/ProfileSettings';

export default function SettingsPage() {
  const { isLoading, isAuthenticated } = useAuth();
  const router = useRouter();

  // Redirect if not authenticated
  React.useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push('/login');
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="text-center">
          <p className="text-lg">Загрузка...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null; // Редирект происходит в useEffect
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-6">Настройки профиля</h1>
      
      <div className="mb-6">
        <button 
          onClick={() => router.push('/profile')}
          className="text-blue-500 hover:text-blue-700"
        >
          &larr; Вернуться к профилю
        </button>
      </div>
      
      <ProfileSettings 
        onSaved={() => {
          // Можно добавить дополнительное действие после сохранения
        }}
      />
    </div>
  );
} 