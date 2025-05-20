'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useAuth } from '../hooks/auth';
import { RoleBasedContent } from './RoleBasedContent';
import { usePathname } from 'next/navigation';
import { useWallets } from '../hooks/wallet';
import formatPrice from '../utils/formatPrice';
import { Currency } from '../types/wallet';

export const Navigation = () => {
  const { user, isAuthenticated, logout, isLoading } = useAuth();
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const [isProfileMenuOpen, setIsProfileMenuOpen] = useState(false);
  const pathname = usePathname();
  const [isDarkMode, setIsDarkMode] = useState(false);
  
  // Получаем информацию о кошельках пользователя
  const { wallets, loading: walletsLoading, authError } = useWallets();
  const [defaultWallet, setDefaultWallet] = useState<any>(null);
  
  // При загрузке кошельков находим основной
  useEffect(() => {
    // Проверяем, что wallets существует, не пуст и нет ошибки аутентификации
    if (wallets?.length > 0 && !authError) {
      const defaultWallet = wallets.find(wallet => wallet.is_default) || wallets[0];
      setDefaultWallet(defaultWallet);
    } else {
      // Сбрасываем дефолтный кошелек, если нет доступных кошельков или произошла ошибка авторизации
      setDefaultWallet(null);
    }
  }, [wallets, authError]);

  // Загрузка предпочтений темы при монтировании
  useEffect(() => {
    // Проверяем текущий класс документа при монтировании
    setIsDarkMode(document.documentElement.classList.contains('dark'));
    
    // Добавляем слушатель для отслеживания изменений в localStorage
    const handleStorageChange = () => {
      try {
        const savedSettings = localStorage.getItem('user-settings');
        if (savedSettings) {
          const parsedSettings = JSON.parse(savedSettings);
          setIsDarkMode(parsedSettings.appearance?.darkMode || false);
        }
      } catch (error) {
        console.error('Ошибка при обновлении состояния темы:', error);
      }
    };
    
    window.addEventListener('storage', handleStorageChange);
    return () => {
      window.removeEventListener('storage', handleStorageChange);
    };
  }, []);

  // Определение активности пункта меню на основе текущего пути
  const isActive = (path: string) => {
    return pathname === path || pathname?.startsWith(path + '/');
  };

  const toggleMenu = () => {
    setIsMenuOpen(prev => !prev);
  };

  const toggleProfileMenu = () => {
    setIsProfileMenuOpen(prev => !prev);
  };

  const handleLogout = async () => {
    await logout();
    setIsProfileMenuOpen(false);
  };

  // Обработчик переключения темы
  const toggleDarkMode = () => {
    const newDarkMode = !isDarkMode;
    setIsDarkMode(newDarkMode);
    
    // Применяем темную тему к документу
    if (newDarkMode) {
      document.documentElement.classList.add('dark');
      document.documentElement.classList.remove('light');
    } else {
      document.documentElement.classList.remove('dark');
      document.documentElement.classList.add('light');
    }
    
    // Сохраняем настройку в localStorage
    try {
      const savedSettings = localStorage.getItem('user-settings');
      let settings = savedSettings ? JSON.parse(savedSettings) : {};
      
      settings = {
        ...settings,
        appearance: {
          ...(settings.appearance || {}),
          darkMode: newDarkMode
        }
      };
      
      localStorage.setItem('user-settings', JSON.stringify(settings));
    } catch (error) {
      console.error('Ошибка при сохранении настроек темы:', error);
    }
  };

  return (
    <nav className="bg-white shadow-sm  transition-colors duration-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex">
            <div className="flex-shrink-0 flex items-center">
              <Link href="/" className="text-xl font-bold text-blue-600 ">
                GameTrade
              </Link>
            </div>
            <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
              <Link 
                href="/" 
                className={`${isActive('/') ? 'border-blue-500 text-blue-600  font-semibold' : 'border-transparent text-gray-700  hover:text-gray-900 '} hover:border-gray-300 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium transition-colors duration-200`}
              >
                Главная
              </Link>
              <Link 
                href="/transactions" 
                className={`${isActive('/games') ? 'border-blue-500 text-blue-600  font-semibold' : 'border-transparent text-gray-700  hover:text-gray-900 '} hover:border-gray-300 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium transition-colors duration-200`}
              >
                Транзакции
              </Link>
              <Link 
                href="/marketplace/listings" 
                className={`${isActive('/marketplace/listings') ? 'border-blue-500 text-blue-600  font-semibold' : 'border-transparent text-gray-700  hover:text-gray-900 '} hover:border-gray-300 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium transition-colors duration-200`}
              >
                Лоты
              </Link>
              {isAuthenticated && (
                <Link 
                  href="/orders" 
                  className={`${isActive('/orders') ? 'border-blue-500 text-blue-600  font-semibold' : 'border-transparent text-gray-700  hover:text-gray-900 '} hover:border-gray-300 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium transition-colors duration-200`}
                >
                  Мои заказы
                </Link>
              )}
              <Link 
                href="/wallet" 
                className={`${isActive('/wallet') ? 'border-blue-500 text-blue-600  font-semibold' : 'border-transparent text-gray-700  hover:text-gray-900 '} hover:border-gray-300 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium transition-colors duration-200`}
              >
                Кошелек
                {isAuthenticated && defaultWallet && !walletsLoading && (
                  <span className="ml-2 text-xs font-medium px-2 py-1 bg-green-100 text-green-800 rounded-full">
                    {formatPrice(defaultWallet.balances?.[Currency.USD] || 0, Currency.USD)}
                  </span>
                )}
              </Link>
              <RoleBasedContent roles={['seller', 'admin']}>
                <Link 
                  href="/sales" 
                  className={`${isActive('/sales') ? 'border-blue-500 text-blue-600  font-semibold' : 'border-transparent text-gray-700  hover:text-gray-900 '} hover:border-gray-300 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium transition-colors duration-200`}
                >
                  Мои продажи
                </Link>
              </RoleBasedContent>
              <RoleBasedContent permissions={['can_access_dashboard']}>
                <Link 
                  href="/admin" 
                  className={`${isActive('/admin') ? 'border-blue-500 text-blue-600  font-semibold' : 'border-transparent text-gray-700  hover:text-gray-900 '} hover:border-gray-300 inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium transition-colors duration-200`}
                >
                  Администрирование
                </Link>
              </RoleBasedContent>
            </div>
          </div>
          <div className="hidden sm:ml-6 sm:flex sm:items-center">
            {/* Кнопка переключения темы */}
            <button
              onClick={toggleDarkMode}
              className="mr-3 p-2 rounded-md text-gray-700  hover:bg-gray-100  transition-colors"
              aria-label={isDarkMode ? "Переключить на светлую тему" : "Переключить на темную тему"}
            >
              {isDarkMode ? (
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v2.25m6.364.386-1.591 1.591M21 12h-2.25m-.386 6.364-1.591-1.591M12 18.75V21m-4.773-4.227-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0Z" />
                </svg>
              ) : (
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M21.752 15.002A9.72 9.72 0 0 1 18 15.75c-5.385 0-9.75-4.365-9.75-9.75 0-1.33.266-2.597.748-3.752A9.753 9.753 0 0 0 3 11.25C3 16.635 7.365 21 12.75 21a9.753 9.753 0 0 0 9.002-5.998Z" />
                </svg>
              )}
            </button>
            
            {isAuthenticated ? (
              <div className="ml-3 relative">
                <div>
                  <button
                    type="button"
                    onClick={toggleProfileMenu}
                    className="bg-white  flex text-sm rounded-full focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                    id="user-menu-button"
                    aria-expanded="false"
                    aria-haspopup="true"
                  >
                    <span className="sr-only">Открыть меню пользователя</span>
                    <div className="h-8 w-8 rounded-full bg-blue-100  flex items-center justify-center text-blue-600 ">
                      {user?.username?.charAt(0).toUpperCase() || 'U'}
                    </div>
                  </button>
                </div>
                
                {isProfileMenuOpen && (
                  <div 
                    className="origin-top-right absolute right-0 mt-2 w-48 rounded-md shadow-lg py-1 bg-white  ring-1 ring-black ring-opacity-5 focus:outline-none z-10"
                    role="menu"
                    aria-orientation="vertical"
                    aria-labelledby="user-menu-button"
                    tabIndex={-1}
                  >
                    <div className="px-4 py-2 text-xs text-gray-600 ">
                      Вы вошли как <span className="font-semibold">{user?.username}</span>
                    </div>
                    <Link 
                      href="/profile" 
                      className="block px-4 py-2 text-sm text-gray-700  hover:bg-gray-100 "
                      role="menuitem"
                      tabIndex={-1}
                      onClick={() => setIsProfileMenuOpen(false)}
                    >
                      Мой профиль
                    </Link>
                    <Link 
                      href="/profile/settings" 
                      className="block px-4 py-2 text-sm text-gray-700  hover:bg-gray-100 "
                      role="menuitem"
                      tabIndex={-1}
                      onClick={() => setIsProfileMenuOpen(false)}
                    >
                      Настройки
                    </Link>
                    <button
                      onClick={handleLogout}
                      className="w-full text-left block px-4 py-2 text-sm text-gray-700  hover:bg-gray-100 "
                      role="menuitem"
                      tabIndex={-1}
                    >
                      Выйти
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <div className="flex space-x-4">
                <Link 
                  href="/login" 
                  className="text-gray-700  hover:text-gray-900  px-3 py-2 rounded-md text-sm font-medium transition-colors duration-200"
                >
                  Войти
                </Link>
                <Link 
                  href="/register" 
                  className="bg-blue-600 text-white hover:bg-blue-700 px-3 py-2 rounded-md text-sm font-medium transition-colors duration-200"
                >
                  Регистрация
                </Link>
              </div>
            )}
          </div>
          <div className="-mr-2 flex items-center sm:hidden">
            {/* Кнопка переключения темы для мобильной версии */}
            <button
              onClick={toggleDarkMode}
              className="p-2 rounded-md text-gray-700  hover:bg-gray-100  transition-colors"
              aria-label={isDarkMode ? "Переключить на светлую тему" : "Переключить на темную тему"}
            >
              {isDarkMode ? (
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v2.25m6.364.386-1.591 1.591M21 12h-2.25m-.386 6.364-1.591-1.591M12 18.75V21m-4.773-4.227-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0Z" />
                </svg>
              ) : (
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M21.752 15.002A9.72 9.72 0 0 1 18 15.75c-5.385 0-9.75-4.365-9.75-9.75 0-1.33.266-2.597.748-3.752A9.753 9.753 0 0 0 3 11.25C3 16.635 7.365 21 12.75 21a9.753 9.753 0 0 0 9.002-5.998Z" />
                </svg>
              )}
            </button>
            
            <button
              onClick={toggleMenu}
              className="inline-flex items-center justify-center p-2 rounded-md text-gray-500  hover:text-gray-700 hover:bg-gray-100   focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500"
              aria-expanded="false"
            >
              <span className="sr-only">Открыть главное меню</span>
              <svg
                className={`${isMenuOpen ? 'hidden' : 'block'} h-6 w-6`}
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 6h16M4 12h16M4 18h16"
                />
              </svg>
              <svg
                className={`${isMenuOpen ? 'block' : 'hidden'} h-6 w-6`}
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>
        </div>
      </div>

      {/* Мобильное меню */}
      <div className={`${isMenuOpen ? 'block' : 'hidden'} sm:hidden`}>
        <div className="pt-2 pb-3 space-y-1">
          <Link 
            href="/" 
            className={`block pl-3 pr-4 py-2 border-l-4 ${isActive('/') ? 'border-blue-500 text-blue-600  font-semibold' : 'border-transparent text-gray-700 '} hover:bg-gray-50  hover:border-gray-300 hover:text-gray-900  text-base font-medium transition-colors duration-200`}
            onClick={() => setIsMenuOpen(false)}
          >
            Главная
          </Link>
          <Link 
            href="/games" 
            className={`block pl-3 pr-4 py-2 border-l-4 ${isActive('/games') ? 'border-blue-500 text-blue-600  font-semibold' : 'border-transparent text-gray-700 '} hover:bg-gray-50  hover:border-gray-300 hover:text-gray-900  text-base font-medium transition-colors duration-200`}
            onClick={() => setIsMenuOpen(false)}
          >
            Лоты
          </Link>
          <Link 
            href="/marketplace/listings" 
            className={`block pl-3 pr-4 py-2 border-l-4 ${isActive('/marketplace/listings') ? 'border-blue-500 text-blue-600  font-semibold' : 'border-transparent text-gray-700 '} hover:bg-gray-50  hover:border-gray-300 hover:text-gray-900  text-base font-medium transition-colors duration-200`}
            onClick={() => setIsMenuOpen(false)}
          >
            Транзакции
          </Link>
          {isAuthenticated && (
            <Link 
              href="/orders" 
              className={`block pl-3 pr-4 py-2 border-l-4 ${isActive('/orders') ? 'border-blue-500 text-blue-600  font-semibold' : 'border-transparent text-gray-700 '} hover:bg-gray-50  hover:border-gray-300 hover:text-gray-900  text-base font-medium transition-colors duration-200`}
              onClick={() => setIsMenuOpen(false)}
            >
              Мои заказы
            </Link>
          )}
          <Link 
            href="/wallet" 
            className={`block pl-3 pr-4 py-2 border-l-4 ${isActive('/wallet') ? 'border-blue-500 text-blue-600  font-semibold' : 'border-transparent text-gray-700 '} hover:bg-gray-50  hover:border-gray-300 hover:text-gray-900  text-base font-medium transition-colors duration-200`}
            onClick={() => setIsMenuOpen(false)}
          >
            Кошелек
            {isAuthenticated && defaultWallet && !walletsLoading && (
              <span className="ml-2 text-xs font-medium px-2 py-1 bg-green-100 text-green-800 rounded-full">
                {formatPrice(defaultWallet.balances?.[Currency.USD] || 0, Currency.USD)}
              </span>
            )}
          </Link>
          <RoleBasedContent roles={['seller', 'admin']}>
            <Link 
              href="/sales" 
              className={`block pl-3 pr-4 py-2 border-l-4 ${isActive('/sales') ? 'border-blue-500 text-blue-600  font-semibold' : 'border-transparent text-gray-700 '} hover:bg-gray-50  hover:border-gray-300 hover:text-gray-900  text-base font-medium transition-colors duration-200`}
              onClick={() => setIsMenuOpen(false)}
            >
              Мои продажи
            </Link>
          </RoleBasedContent>
          <RoleBasedContent permissions={['can_access_dashboard']}>
            <Link 
              href="/admin" 
              className={`block pl-3 pr-4 py-2 border-l-4 ${isActive('/admin') ? 'border-blue-500 text-blue-600  font-semibold' : 'border-transparent text-gray-700 '} hover:bg-gray-50  hover:border-gray-300 hover:text-gray-900  text-base font-medium transition-colors duration-200`}
              onClick={() => setIsMenuOpen(false)}
            >
              Администрирование
            </Link>
          </RoleBasedContent>
        </div>
        <div className="pt-4 pb-3 border-t border-gray-200 ">
          {isAuthenticated ? (
            <>
              <div className="flex items-center px-4">
                <div className="flex-shrink-0">
                  <div className="h-10 w-10 rounded-full bg-blue-100  flex items-center justify-center text-blue-600 ">
                    {user?.username?.charAt(0).toUpperCase() || 'U'}
                  </div>
                </div>
                <div className="ml-3">
                  <div className="text-base font-medium text-gray-800 ">{user?.username}</div>
                  <div className="text-sm font-medium text-gray-500 ">{user?.email}</div>
                </div>
              </div>
              <div className="mt-3 space-y-1">
                <Link 
                  href="/profile" 
                  className="block px-4 py-2 text-base font-medium text-gray-700  hover:text-gray-900 hover:bg-gray-100   transition-colors duration-200"
                  onClick={() => setIsMenuOpen(false)}
                >
                  Мой профиль
                </Link>
                <Link 
                  href="/profile/settings" 
                  className="block px-4 py-2 text-base font-medium text-gray-700  hover:text-gray-900 hover:bg-gray-100   transition-colors duration-200"
                  onClick={() => setIsMenuOpen(false)}
                >
                  Настройки
                </Link>
                <button
                  onClick={handleLogout}
                  className="w-full text-left block px-4 py-2 text-base font-medium text-gray-700  hover:text-gray-900 hover:bg-gray-100   transition-colors duration-200"
                >
                  Выйти
                </button>
              </div>
            </>
          ) : (
            <div className="mt-3 space-y-1">
              <Link 
                href="/login" 
                className="block px-4 py-2 text-base font-medium text-gray-700  hover:text-gray-900 hover:bg-gray-100   transition-colors duration-200"
                onClick={() => setIsMenuOpen(false)}
              >
                Войти
              </Link>
              <Link 
                href="/register" 
                className="block px-4 py-2 text-base font-medium text-gray-700  hover:text-gray-900 hover:bg-gray-100   transition-colors duration-200"
                onClick={() => setIsMenuOpen(false)}
              >
                Регистрация
              </Link>
            </div>
          )}
        </div>
      </div>
    </nav>
  );
}; 