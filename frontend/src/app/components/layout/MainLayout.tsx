import React, { ReactNode } from 'react';
import { Layout, Menu, Button, Typography, Avatar, Dropdown } from 'antd';
import Link from 'next/link';
import { useRouter } from 'next/router';
import { 
  HomeOutlined, 
  ShoppingOutlined, 
  TagsOutlined, 
  UserOutlined,
  PlusCircleOutlined,
  BellOutlined,
  MessageOutlined,
  SearchOutlined,
  AppstoreOutlined
} from '@ant-design/icons';

const { Header, Content, Footer } = Layout;
const { Title } = Typography;

interface MainLayoutProps {
  children: ReactNode;
}

const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
  const router = useRouter();
  
  const menuItems = [
    {
      key: '/',
      icon: <HomeOutlined />,
      label: <Link href="/">Главная</Link>,
    },
    {
      key: '/listings',
      icon: <ShoppingOutlined />,
      label: <Link href="/listings">Объявления</Link>,
    },
    {
      key: '/categories',
      icon: <TagsOutlined />,
      label: <Link href="/categories">Категории</Link>,
    },
    {
      key: '/games',
      icon: <AppstoreOutlined />,
      label: <Link href="/games">Игры</Link>,
    },
  ];
  
  const userMenuItems = [
    {
      key: '/profile',
      label: 'Профиль',
    },
    {
      key: '/my-listings',
      label: 'Мои объявления',
    },
    {
      key: '/settings',
      label: 'Настройки',
    },
    {
      key: 'logout',
      label: 'Выйти',
    },
  ];
  
  // Функция для определения текущего активного пункта меню
  const getSelectedKey = () => {
    const path = router.pathname;
    if (path === '/') return ['/'];
    
    for (const item of menuItems) {
      if (path.startsWith(item.key) && item.key !== '/') {
        return [item.key];
      }
    }
    
    return ['/'];
  };
  
  return (
    <Layout className="main-layout">
      <Header style={{ position: 'fixed', zIndex: 1, width: '100%', padding: '0 50px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div className="logo" style={{ display: 'flex', alignItems: 'center' }}>
          <Title level={3} style={{ color: 'white', margin: 0 }}>GameTrade</Title>
        </div>
        
        <div className="menu-container" style={{ flex: 1, display: 'flex', justifyContent: 'center' }}>
          <Menu
            theme="dark"
            mode="horizontal"
            selectedKeys={getSelectedKey()}
            items={menuItems}
            style={{ minWidth: 400 }}
          />
        </div>
        
        <div className="actions" style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
          <Button type="text" icon={<SearchOutlined />} style={{ color: 'white' }} />
          <Button type="text" icon={<BellOutlined />} style={{ color: 'white' }} />
          <Button type="text" icon={<MessageOutlined />} style={{ color: 'white' }} />
          
          <Button 
            type="primary" 
            icon={<PlusCircleOutlined />}
            onClick={() => router.push('/listings/create')}
          >
            Создать объявление
          </Button>
          
          <Dropdown 
            menu={{ items: userMenuItems, onClick: ({ key }) => {
              if (key === 'logout') {
                // Логика выхода
              } else {
                router.push(key as string);
              }
            }}} 
            placement="bottomRight"
            arrow
          >
            <Avatar icon={<UserOutlined />} style={{ cursor: 'pointer' }} />
          </Dropdown>
        </div>
      </Header>
      
      <Content style={{ padding: '0 50px', marginTop: 64 }}>
        <div className="site-layout-content" style={{ padding: 24, minHeight: 'calc(100vh - 64px - 69px)' }}>
          {children}
        </div>
      </Content>
      
      <Footer style={{ textAlign: 'center' }}>
        GameTrade ©{new Date().getFullYear()} - Платформа для торговли игровыми предметами
      </Footer>
    </Layout>
  );
};

export default MainLayout; 