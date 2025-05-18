'use client';

import React from 'react';
import Link from 'next/link';
import { useAuth } from '../hooks/auth';
import { RoleBasedContent } from '../components/RoleBasedContent';

interface AdminModuleProps {
  title: string;
  description: string;
  icon: React.ReactNode;
  href: string;
  permissions?: string[];
  roles?: string[];
}

const AdminModule: React.FC<AdminModuleProps> = ({ 
  title, 
  description, 
  icon, 
  href,
  permissions,
  roles 
}) => {
  return (
    <RoleBasedContent 
      permissions={permissions} 
      roles={roles} 
      fallback={null}
    >
      <Link href={href}>
        <div className="border rounded-lg p-6 hover:bg-gray-50 transition-colors duration-200 h-full">
          <div className="flex items-start mb-4">
            <div className="mr-4 text-blue-500 text-2xl">{icon}</div>
            <h3 className="font-semibold text-lg">{title}</h3>
          </div>
          <p className="text-gray-600">{description}</p>
        </div>
      </Link>
    </RoleBasedContent>
  );
};

const AdminPage = () => {
  const { isLoading } = useAuth();

  if (isLoading) {
    return <div>Загрузка...</div>;
  }

  return (
    <RoleBasedContent 
      roles={['admin', 'moderator']} 
      fallback={<div className="container mx-auto px-4 py-16 text-center">У вас нет доступа к административной панели</div>}
    >
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold mb-2">Панель администратора</h1>
        <p className="text-gray-600 mb-8">Управление системой GameTrade</p>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
          {/* Управление пользователями */}
          <AdminModule
            title="Пользователи"
            description="Просмотр и управление учетными записями пользователей"
            icon={<span>👤</span>}
            href="/admin/users"
            permissions={['manage:users']}
          />
          
          {/* Управление ролями */}
          <AdminModule
            title="Роли и права"
            description="Управление ролями пользователей и правами доступа"
            icon={<span>🔐</span>}
            href="/admin/roles"
            permissions={['manage:roles']}
          />
          
          {/* Модерация контента */}
          <AdminModule
            title="Модерация"
            description="Просмотр и модерация пользовательского контента"
            icon={<span>📋</span>}
            href="/admin/moderation"
            permissions={['moderate:content']}
          />
          
          {/* Управление товарами */}
          <AdminModule
            title="Товары"
            description="Просмотр и управление товарами на платформе"
            icon={<span>🎮</span>}
            href="/admin/products"
            roles={['admin', 'moderator']}
          />
          
          {/* Управление заказами */}
          <AdminModule
            title="Заказы"
            description="Просмотр и управление заказами пользователей"
            icon={<span>📦</span>}
            href="/admin/orders"
            roles={['admin']}
          />
          
          {/* Настройки системы */}
          <AdminModule
            title="Настройки"
            description="Управление настройками и конфигурацией системы"
            icon={<span>⚙️</span>}
            href="/admin/settings"
            permissions={['manage:system']}
          />
        </div>

        <div className="border-t pt-6">
          <Link href="/" className="text-blue-500 hover:text-blue-700">
            &larr; Вернуться на главную страницу
          </Link>
        </div>
      </div>
    </RoleBasedContent>
  );
};

export default AdminPage; 