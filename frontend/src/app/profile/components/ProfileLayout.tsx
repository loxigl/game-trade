'use client';

import React, { ReactNode } from 'react';
import { Tabs } from 'antd';
import Link from 'next/link';
import { useAuth } from '../../hooks/auth';
import { UserOutlined, ShoppingOutlined, TagsOutlined, SettingOutlined } from '@ant-design/icons';

interface ProfileLayoutProps {
  children: ReactNode;
  activeTab: string;
}

const ProfileLayout: React.FC<ProfileLayoutProps> = ({ children, activeTab }) => {
  const { user } = useAuth();

  const items = [
    {
      key: 'profile',
      label: <Link href="/profile">Профиль</Link>,
      icon: <UserOutlined />,
    },
    {
      key: 'purchases',
      label: <Link href="/profile/purchases">Мои покупки</Link>,
      icon: <ShoppingOutlined />,
    },
    {
      key: 'listings',
      label: <Link href="/profile/listings">Мои объявления</Link>,
      icon: <TagsOutlined />,
    },
    {
      key: 'settings',
      label: <Link href="/profile/settings">Настройки</Link>,
      icon: <SettingOutlined />,
    },
  ];

  return (
    <div className="profile-layout container mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-2">Личный кабинет</h1>
        {user && (
          <p className="text-gray-600">
            Добро пожаловать, {user.username}!
          </p>
        )}
      </div>

      <Tabs
        defaultActiveKey={activeTab}
        activeKey={activeTab}
        items={items}
        className="mb-6"
      />

      {children}
    </div>
  );
};

export default ProfileLayout; 