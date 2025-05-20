import { useState, useEffect } from 'react';
import { useAuth } from '../hooks/auth';
import { RoleBasedContent } from './RoleBasedContent';

interface SettingsProps {
  onSaved?: () => void;
}

// Интерфейс для настроек пользователя
interface UserSettings {
  notifications: {
    emailNotifications: boolean;
    siteNotifications: boolean;
    marketingEmails: boolean;
  };
  appearance: {
    darkMode: boolean;
    language: string;
  };
  seller?: {
    autoAcceptOffers: boolean;
    instantPayoutEnabled: boolean;
  };
}

// Ключ для хранения настроек в localStorage
const USER_SETTINGS_KEY = 'user-settings';

export const ProfileSettings = ({ onSaved }: SettingsProps) => {
  const { user, isLoading } = useAuth();
  const [settings, setSettings] = useState<UserSettings>({
    notifications: {
      emailNotifications: true,
      siteNotifications: true,
      marketingEmails: false,
    },
    appearance: {
      darkMode: false,
      language: 'ru',
    },
    seller: {
      autoAcceptOffers: false,
      instantPayoutEnabled: false,
    }
  });
  
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);
  const [settingsLoaded, setSettingsLoaded] = useState(false);

  // Загрузка настроек из localStorage при монтировании компонента
  useEffect(() => {
    const loadSettings = () => {
      try {
        const savedSettings = localStorage.getItem(USER_SETTINGS_KEY);
        if (savedSettings) {
          const parsedSettings = JSON.parse(savedSettings);
          setSettings(parsedSettings);
          
          // Применяем темную тему, если она включена
          if (parsedSettings.appearance?.darkMode) {
            document.documentElement.classList.add('dark');
          } else {
            document.documentElement.classList.remove('dark');
          }
        }
        setSettingsLoaded(true);
      } catch (error) {
        console.error('Ошибка при загрузке настроек:', error);
        setSettingsLoaded(true);
      }
    };

    loadSettings();
  }, []);

  // Обработчик изменения настроек уведомлений
  const handleNotificationToggle = (setting: keyof typeof settings.notifications) => {
    setSettings(prev => ({
      ...prev,
      notifications: {
        ...prev.notifications,
        [setting]: !prev.notifications[setting]
      }
    }));
  };

  // Обработчик изменения настроек продавца
  const handleSellerToggle = (setting: keyof NonNullable<typeof settings.seller>) => {
    setSettings(prev => ({
      ...prev,
      seller: {
        ...prev.seller!,
        [setting]: !prev.seller?.[setting]
      }
    }));
  };

  // Обработчик переключения темной темы
  const handleDarkModeToggle = () => {
    setSettings(prev => {
      const newDarkMode = !prev.appearance.darkMode;
      
      // Применяем темную тему к документу
      if (newDarkMode) {
        document.documentElement.classList.add('dark');
        document.documentElement.classList.remove('light');
      } else {
        document.documentElement.classList.remove('dark');
        document.documentElement.classList.add('light');
      }
      
      // Немедленно сохраняем изменение темы в localStorage
      const updatedSettings = {
        ...prev,
        appearance: {
          ...prev.appearance,
          darkMode: newDarkMode
        }
      };
      
      try {
        localStorage.setItem(USER_SETTINGS_KEY, JSON.stringify(updatedSettings));
      } catch (error) {
        console.error('Ошибка при сохранении настроек темы:', error);
      }
      
      return updatedSettings;
    });
  };

  // Обработчик изменения языка
  const handleLanguageChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newLanguage = e.target.value;
    setSettings(prev => ({
      ...prev,
      appearance: {
        ...prev.appearance,
        language: newLanguage
      }
    }));
  };

  // Сохранение настроек
  const saveSettings = async () => {
    setIsSubmitting(true);
    setMessage(null);

    try {
      // Сохраняем настройки в localStorage
      localStorage.setItem(USER_SETTINGS_KEY, JSON.stringify(settings));
      
      // В реальном приложении здесь был бы API-запрос
      await new Promise(resolve => setTimeout(resolve, 500));

      setMessage({ type: 'success', text: 'Настройки успешно сохранены' });

      if (onSaved) {
        onSaved();
      }
    } catch (error) {
      console.error('Ошибка при сохранении настроек:', error);
      setMessage({ type: 'error', text: 'Ошибка при сохранении настроек' });
    } finally {
      setIsSubmitting(false);
    }
  };

  // Сброс настроек к значениям по умолчанию
  const resetSettings = () => {
    const defaultSettings: UserSettings = {
      notifications: {
        emailNotifications: true,
        siteNotifications: true,
        marketingEmails: false,
      },
      appearance: {
        darkMode: false,
        language: 'ru',
      },
      seller: {
        autoAcceptOffers: false,
        instantPayoutEnabled: false,
      }
    };
    
    setSettings(defaultSettings);
    
    // Применяем сброс темной темы
    document.documentElement.classList.remove('dark');
    
    setMessage({ type: 'success', text: 'Настройки сброшены к значениям по умолчанию' });
  };

  if (isLoading || !settingsLoaded) {
    return <div className="text-center py-4 text-gray-700 ">Загрузка настроек...</div>;
  }

  return (
    <div className="bg-white  rounded-lg shadow-md p-6 transition-colors duration-200">
      <h2 className="text-xl font-semibold mb-6 text-gray-900 ">Настройки</h2>

      {message && (
        <div className={`p-3 mb-4 rounded-md ${message.type === 'success' ? 'bg-green-100  text-green-700 ' : 'bg-red-100  text-red-700 '}`}>
          {message.text}
        </div>
      )}

      <div className="space-y-6">
        <div>
          <h3 className="text-lg font-medium mb-3 text-gray-800 ">Уведомления</h3>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <label htmlFor="emailNotifications" className="text-gray-700 ">
                Уведомления по email
              </label>
              <div className="relative inline-block w-12 mr-2 align-middle select-none">
                <input
                  type="checkbox"
                  id="emailNotifications"
                  checked={settings.notifications.emailNotifications}
                  onChange={() => handleNotificationToggle('emailNotifications')}
                  className="toggle-checkbox absolute block w-6 h-6 rounded-full bg-white  border-4 appearance-none cursor-pointer"
                />
                <label
                  htmlFor="emailNotifications"
                  className={`toggle-label block overflow-hidden h-6 rounded-full cursor-pointer ${settings.notifications.emailNotifications ? 'bg-blue-500' : 'bg-gray-300 '}`}
                ></label>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <label htmlFor="siteNotifications" className="text-gray-700 ">
                Уведомления на сайте
              </label>
              <div className="relative inline-block w-12 mr-2 align-middle select-none">
                <input
                  type="checkbox"
                  id="siteNotifications"
                  checked={settings.notifications.siteNotifications}
                  onChange={() => handleNotificationToggle('siteNotifications')}
                  className="toggle-checkbox absolute block w-6 h-6 rounded-full bg-white  border-4 appearance-none cursor-pointer"
                />
                <label
                  htmlFor="siteNotifications"
                  className={`toggle-label block overflow-hidden h-6 rounded-full cursor-pointer ${settings.notifications.siteNotifications ? 'bg-blue-500' : 'bg-gray-300 '}`}
                ></label>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <label htmlFor="marketingEmails" className="text-gray-700 ">
                Маркетинговые рассылки
              </label>
              <div className="relative inline-block w-12 mr-2 align-middle select-none">
                <input
                  type="checkbox"
                  id="marketingEmails"
                  checked={settings.notifications.marketingEmails}
                  onChange={() => handleNotificationToggle('marketingEmails')}
                  className="toggle-checkbox absolute block w-6 h-6 rounded-full bg-white  border-4 appearance-none cursor-pointer"
                />
                <label
                  htmlFor="marketingEmails"
                  className={`toggle-label block overflow-hidden h-6 rounded-full cursor-pointer ${settings.notifications.marketingEmails ? 'bg-blue-500' : 'bg-gray-300 '}`}
                ></label>
              </div>
            </div>
          </div>
        </div>

        <div className="border-t border-gray-200  pt-6">
          <h3 className="text-lg font-medium mb-3 text-gray-800 ">Внешний вид</h3>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <label htmlFor="darkMode" className="text-gray-700 ">
                Темная тема
              </label>
              <div className="relative inline-block w-12 mr-2 align-middle select-none">
                <input
                  type="checkbox"
                  id="darkMode"
                  checked={settings.appearance.darkMode}
                  onChange={handleDarkModeToggle}
                  className="toggle-checkbox absolute block w-6 h-6 rounded-full bg-white  border-4 appearance-none cursor-pointer"
                />
                <label
                  htmlFor="darkMode"
                  className={`toggle-label block overflow-hidden h-6 rounded-full cursor-pointer ${settings.appearance.darkMode ? 'bg-blue-500' : 'bg-gray-300 '}`}
                ></label>
              </div>
            </div>
            
            <div className="mt-4">
              <label htmlFor="language" className="block text-gray-700  mb-2">
                Язык интерфейса
              </label>
              <select
                id="language"
                value={settings.appearance.language}
                onChange={handleLanguageChange}
                className="block w-full p-2 border border-gray-300  rounded-md  "
              >
                <option value="ru">Русский</option>
                <option value="en">English</option>
                <option value="es">Español</option>
              </select>
            </div>
          </div>
        </div>

        <RoleBasedContent roles={['seller', 'admin']}>
          <div className="border-t border-gray-200  pt-6">
            <h3 className="text-lg font-medium mb-3 text-gray-800 ">Настройки продавца</h3>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <label htmlFor="autoAcceptOffers" className="text-gray-700 ">
                  Автоматически принимать предложения
                </label>
                <div className="relative inline-block w-12 mr-2 align-middle select-none">
                  <input
                    type="checkbox"
                    id="autoAcceptOffers"
                    checked={settings.seller?.autoAcceptOffers || false}
                    onChange={() => handleSellerToggle('autoAcceptOffers')}
                    className="toggle-checkbox absolute block w-6 h-6 rounded-full bg-white  border-4 appearance-none cursor-pointer"
                  />
                  <label
                    htmlFor="autoAcceptOffers"
                    className={`toggle-label block overflow-hidden h-6 rounded-full cursor-pointer ${settings.seller?.autoAcceptOffers ? 'bg-blue-500' : 'bg-gray-300 '}`}
                  ></label>
                </div>
              </div>
              
              <div className="flex items-center justify-between">
                <label htmlFor="instantPayoutEnabled" className="text-gray-700 ">
                  Мгновенные выплаты
                </label>
                <div className="relative inline-block w-12 mr-2 align-middle select-none">
                  <input
                    type="checkbox"
                    id="instantPayoutEnabled"
                    checked={settings.seller?.instantPayoutEnabled || false}
                    onChange={() => handleSellerToggle('instantPayoutEnabled')}
                    className="toggle-checkbox absolute block w-6 h-6 rounded-full bg-white  border-4 appearance-none cursor-pointer"
                  />
                  <label
                    htmlFor="instantPayoutEnabled"
                    className={`toggle-label block overflow-hidden h-6 rounded-full cursor-pointer ${settings.seller?.instantPayoutEnabled ? 'bg-blue-500' : 'bg-gray-300 '}`}
                  ></label>
                </div>
              </div>
            </div>
          </div>
        </RoleBasedContent>

        <div className="border-t border-gray-200  pt-6 flex flex-wrap gap-4">
          <button
            onClick={saveSettings}
            disabled={isSubmitting}
            className="flex-1 py-2 px-4 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:bg-blue-300  transition-colors"
          >
            {isSubmitting ? 'Сохранение...' : 'Сохранить настройки'}
          </button>
          
          <button
            onClick={resetSettings}
            disabled={isSubmitting}
            className="flex-1 py-2 px-4 bg-gray-200  text-gray-800  rounded-md hover:bg-gray-300  disabled:bg-gray-100  transition-colors"
          >
            Сбросить настройки
          </button>
        </div>
      </div>

      <style jsx>{`
        .toggle-checkbox:checked {
          right: 0;
          border-color: #3B82F6;
        }
        .toggle-checkbox:checked + .toggle-label {
          background-color: #3B82F6;
        }
        .toggle-label {
          transition: background-color 0.2s ease;
        }
        .toggle-checkbox {
          right: 0;
          z-index: 1;
          transition: all 0.3s ease;
        }
        .toggle-checkbox:checked {
          right: 6px;
        }
      `}</style>
    </div>
  );
};
