import { useState } from 'react';
import { useAuth } from '../hooks/auth';
import { RoleBasedContent } from './RoleBasedContent';

interface SettingsProps {
  onSaved?: () => void;
}

export const ProfileSettings = ({ onSaved }: SettingsProps) => {
  const { user, isLoading } = useAuth();
  const [notifications, setNotifications] = useState({
    emailNotifications: true,
    siteNotifications: true,
    marketingEmails: false,
  });
  const [darkMode, setDarkMode] = useState(false);
  const [language, setLanguage] = useState('ru');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

  // В реальном приложении здесь будет API-запрос для получения настроек
  const fetchSettings = async () => {
    // Имитация загрузки настроек с сервера
    return new Promise<void>(resolve => {
      setTimeout(() => {
        setNotifications({
          emailNotifications: true,
          siteNotifications: true,
          marketingEmails: false,
        });
        setDarkMode(true);
        setLanguage('ru');
        resolve();
      }, 500);
    });
  };

  const handleToggle = (setting: keyof typeof notifications) => {
    setNotifications(prev => ({
      ...prev,
      [setting]: !prev[setting]
    }));
  };

  const handleLanguageChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setLanguage(e.target.value);
  };

  const saveSettings = async () => {
    setIsSubmitting(true);
    setMessage(null);

    try {
      // Имитация сохранения настроек на сервере
      await new Promise(resolve => setTimeout(resolve, 1000));

      setMessage({ type: 'success', text: 'Настройки успешно сохранены' });

      if (onSaved) {
        onSaved();
      }
    } catch (error) {
      setMessage({ type: 'error', text: 'Ошибка при сохранении настроек' });
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return <div className="text-center py-4">Загрузка настроек...</div>;
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-xl font-semibold mb-6">Настройки</h2>

      {message && (
        <div className={`p-3 mb-4 rounded-md ${message.type === 'success' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
          {message.text}
        </div>
      )}

      <div className="space-y-6">
        <div>
          <h3 className="text-lg font-medium mb-3">Уведомления</h3>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label htmlFor="emailNotifications" className="text-gray-700">
                Уведомления по email
              </label>
              <div className="relative inline-block w-10 mr-2 align-middle select-none">
                <input
                  type="checkbox"
                  id="emailNotifications"
                  checked={notifications.emailNotifications}
                  onChange={() => handleToggle('emailNotifications')}
                  className="toggle-checkbox absolute block w-6 h-6 rounded-full bg-white border-4 appearance-none cursor-pointer"
                />
                <label
                  htmlFor="emailNotifications"
                  className={`toggle-label block overflow-hidden h-6 rounded-full cursor-pointer ${notifications.emailNotifications ? 'bg-blue-500' : 'bg-gray-300'}`}
                ></label>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <label htmlFor="siteNotifications" className="text-gray-700">
                Уведомления на сайте
              </label>
              <div className="relative inline-block w-10 mr-2 align-middle select-none">
                <input
                  type="checkbox"
                  id="siteNotifications"
                  checked={notifications.siteNotifications}
                  onChange={() => handleToggle('siteNotifications')}
                  className="toggle-checkbox absolute block w-6 h-6 rounded-full bg-white border-4 appearance-none cursor-pointer"
                />
                <label
                  htmlFor="siteNotifications"
                  className={`toggle-label block overflow-hidden h-6 rounded-full cursor-pointer ${notifications.siteNotifications ? 'bg-blue-500' : 'bg-gray-300'}`}
                ></label>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <label htmlFor="marketingEmails" className="text-gray-700">
                Маркетинговые рассылки
              </label>
              <div className="relative inline-block w-10 mr-2 align-middle select-none">
                <input
                  type="checkbox"
                  id="marketingEmails"
                  checked={notifications.marketingEmails}
                  onChange={() => handleToggle('marketingEmails')}
                  className="toggle-checkbox absolute block w-6 h-6 rounded-full bg-white border-4 appearance-none cursor-pointer"
                />
                <label
                  htmlFor="marketingEmails"
                  className={`toggle-label block overflow-hidden h-6 rounded-full cursor-pointer ${notifications.marketingEmails ? 'bg-blue-500' : 'bg-gray-300'}`}
                ></label>
              </div>
            </div>
          </div>
        </div>

        <div>
          <h3 className="text-lg font-medium mb-3">Внешний вид</h3>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label htmlFor="darkMode" className="text-gray-700">
                Темная тема
              </label>
              <div className="relative inline-block w-10 mr-2 align-middle select-none">
                <input
                  type="checkbox"
                  id="darkMode"
                  checked={darkMode}
                  onChange={() => setDarkMode(!darkMode)}
                  className="toggle-checkbox absolute block w-6 h-6 rounded-full bg-white border-4 appearance-none cursor-pointer"
                />
                <label
                  htmlFor="darkMode"
                  className={`toggle-label block overflow-hidden h-6 rounded-full cursor-pointer ${darkMode ? 'bg-blue-500' : 'bg-gray-300'}`}
                ></label>
              </div>
            </div>
          </div>
        </div>

        <div>
          <h3 className="text-lg font-medium mb-3">Язык</h3>
          <select
            value={language}
            onChange={handleLanguageChange}
            className="block w-full p-2 border border-gray-300 rounded-md"
          >
            <option value="ru">Русский</option>
            <option value="en">English</option>
            <option value="es">Español</option>
          </select>
        </div>

        <RoleBasedContent roles={['seller', 'admin']}>
          <div>
            <h3 className="text-lg font-medium mb-3">Настройки продавца</h3>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <label htmlFor="autoAcceptOffers" className="text-gray-700">
                  Автоматически принимать предложения
                </label>
                <div className="relative inline-block w-10 mr-2 align-middle select-none">
                  <input
                    type="checkbox"
                    id="autoAcceptOffers"
                    checked={false}
                    onChange={() => {}}
                    className="toggle-checkbox absolute block w-6 h-6 rounded-full bg-white border-4 appearance-none cursor-pointer"
                  />
                  <label
                    htmlFor="autoAcceptOffers"
                    className="toggle-label block overflow-hidden h-6 rounded-full bg-gray-300 cursor-pointer"
                  ></label>
                </div>
              </div>
            </div>
          </div>
        </RoleBasedContent>

        <div className="pt-4 border-t border-gray-200">
          <button
            onClick={saveSettings}
            disabled={isSubmitting}
            className="w-full py-2 px-4 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:bg-blue-300"
          >
            {isSubmitting ? 'Сохранение...' : 'Сохранить настройки'}
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
      `}</style>
    </div>
  );
};
