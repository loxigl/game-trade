'use client';

import './globals.css';
import { ReactNode, useEffect } from 'react';
import { AuthProvider } from './hooks/auth';
import { Navigation } from './components/Navigation';

// Скрипт для установки темной/светлой темы при загрузке страницы
const ThemeInitializer = () => {
  useEffect(() => {
    // Проверяем настройки пользователя
    const USER_SETTINGS_KEY = 'user-settings';
    try {
      const savedSettings = localStorage.getItem(USER_SETTINGS_KEY);
      if (savedSettings) {
        const parsedSettings = JSON.parse(savedSettings);
        // Применяем темную тему, если она настроена пользователем
        if (parsedSettings.appearance?.darkMode) {
          document.documentElement.classList.add('dark');
          document.documentElement.classList.remove('light');
        } else {
          document.documentElement.classList.remove('dark');
          document.documentElement.classList.add('light');
        }
      } else {
        // Если настроек нет, проверяем предпочтения системы
        if (window.matchMedia('(prefers-color-scheme: dark)').matches) {
          document.documentElement.classList.add('dark');
          document.documentElement.classList.remove('light');
        } else {
          document.documentElement.classList.remove('dark');
          document.documentElement.classList.add('light');
        }
      }
    } catch (error) {
      console.error('Ошибка при установке темы:', error);
    }
    
    // Добавляем слушатель для изменения системных предпочтений
    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    const handleSystemThemeChange = (e: MediaQueryListEvent) => {
      // Проверяем сохраненные настройки пользователя перед изменением темы
      const savedSettings = localStorage.getItem(USER_SETTINGS_KEY);
      if (savedSettings) {
        // Если у пользователя есть настройки, не меняем тему
        return;
      }
      
      // Иначе следуем системным предпочтениям
      if (e.matches) {
        document.documentElement.classList.add('dark');
        document.documentElement.classList.remove('light');
      } else {
        document.documentElement.classList.remove('dark');
        document.documentElement.classList.add('light');
      }
    };
    
    mediaQuery.addEventListener('change', handleSystemThemeChange);
    return () => {
      mediaQuery.removeEventListener('change', handleSystemThemeChange);
    };
  }, []);

  return null;
};

export default function RootLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <html lang="ru">
      <head>
        <title>GameTrade - Платформа для обмена игровыми товарами</title>
        <meta name="description" content="GameTrade - площадка для купли-продажи игр, консолей и аксессуаров" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </head>
      <body className="min-h-screen bg-gray-50  transition-colors duration-200">
        <AuthProvider>
          <ThemeInitializer />
          <Navigation />
          <main className="">{children}</main>
          <footer className="bg-gray-800 text-white py-8 mt-12">
            <div className="container mx-auto px-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
                <div>
                  <h3 className="text-lg font-semibold mb-4">О GameTrade</h3>
                  <p className="text-gray-400">
                    GameTrade - платформа для продажи и обмена видеоигр, 
                    консолей и аксессуаров между геймерами.
                  </p>
                </div>
                <div>
                  <h3 className="text-lg font-semibold mb-4">Ссылки</h3>
                  <ul className="space-y-2 text-gray-400">
                    <li><a href="/about" className="hover:text-white">О нас</a></li>
                    <li><a href="/privacy" className="hover:text-white">Конфиденциальность</a></li>
                    <li><a href="/terms" className="hover:text-white">Условия использования</a></li>
                    <li><a href="/contact" className="hover:text-white">Связаться с нами</a></li>
                  </ul>
                </div>
                <div>
                  <h3 className="text-lg font-semibold mb-4">Поддержка</h3>
                  <ul className="space-y-2 text-gray-400">
                    <li><a href="/faq" className="hover:text-white">FAQ</a></li>
                    <li><a href="/help" className="hover:text-white">Центр поддержки</a></li>
                    <li><a href="/security" className="hover:text-white">Безопасные сделки</a></li>
                  </ul>
                </div>
              </div>
              <div className="border-t border-gray-700 mt-8 pt-6 text-center text-gray-500">
                <p>&copy; {new Date().getFullYear()} GameTrade. Все права защищены.</p>
              </div>
            </div>
          </footer>
        </AuthProvider>
      </body>
    </html>
  );
}
