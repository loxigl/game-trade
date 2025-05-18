'use client';

import React, { useState, useEffect } from 'react';
import { useAuth } from '../../hooks/auth';
import { RoleBasedContent } from '../../components/RoleBasedContent';
import Link from 'next/link';

// Типы данных
interface UserWithRoles {
  id: number;
  username: string;
  email: string;
  roles: string[];
  is_active: boolean;
}

interface RoleInfo {
  name: string;
  description: string;
  permissions: string[];
}

const RolesManagementPage = () => {
  const { isLoading } = useAuth();
  const [availableRoles, setAvailableRoles] = useState<RoleInfo[]>([]);
  const [usersByRole, setUsersByRole] = useState<{ [key: string]: UserWithRoles[] | null }>({});
  const [selectedRole, setSelectedRole] = useState<string>('');
  const [selectedUser, setSelectedUser] = useState<UserWithRoles | null>(null);
  const [isAssigningRole, setIsAssigningRole] = useState<boolean>(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error', text: string } | null>(null);

  // API URL
  const API_URL = process.env.NEXT_PUBLIC_AUTH_URL || 'http://localhost:8000';

  // Загрузка доступных ролей
  useEffect(() => {
    const fetchRoles = async () => {
      try {
        const token = localStorage.getItem('accessToken');
        if (!token) return;

        const response = await fetch(`${API_URL}/roles/info`, {
          headers: {
            Authorization: `Bearer ${token}`
          }
        });

        if (!response.ok) {
          throw new Error('Failed to fetch roles');
        }

        const data = await response.json();
        setAvailableRoles(data);

        // Устанавливаем первую роль как выбранную по умолчанию
        if (data.length > 0 && !selectedRole) {
          setSelectedRole(data[0].name);
        }
      } catch (error) {
        console.error('Error fetching roles:', error);
        setMessage({ type: 'error', text: 'Не удалось загрузить список ролей' });
      }
    };

    fetchRoles();
  }, []);

  // Загрузка пользователей с выбранной ролью
  useEffect(() => {
    if (!selectedRole) return;

    const fetchUsersByRole = async () => {
      try {
        const token = localStorage.getItem('accessToken');
        if (!token) return;

        const response = await fetch(`${API_URL}/roles/users/${selectedRole}`, {
          headers: {
            Authorization: `Bearer ${token}`
          }
        });

        if (!response.ok) {
          throw new Error('Failed to fetch users');
        }

        const data = await response.json();
        setUsersByRole(prev => ({ ...prev, [selectedRole]: data }));
      } catch (error) {
        console.error(`Error fetching users with role ${selectedRole}:`, error);
        setMessage({ type: 'error', text: `Не удалось загрузить пользователей с ролью ${selectedRole}` });
      }
    };

    // Если у нас еще нет данных для этой роли, загружаем их
    if (!usersByRole[selectedRole]) {
      fetchUsersByRole();
    }
  }, [selectedRole, API_URL, usersByRole]);

  // Назначение роли пользователю
  const assignRole = async (userId: number, role: string) => {
    try {
      const token = localStorage.getItem('accessToken');
      if (!token) return;

      const response = await fetch(`${API_URL}/roles/assign`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          user_id: userId,
          role
        })
      });

      if (!response.ok) {
        throw new Error('Failed to assign role');
      }

      const data = await response.json();
      setMessage({ type: 'success', text: data.message });

      // Обновляем список пользователей для выбранной роли
      // И сбрасываем кеш для роли, которая была назначена
      setUsersByRole(prev => ({ ...prev, [role]: null }));

      // Обновляем текущую выбранную роль (это обновит список пользователей)
      const currentRole = selectedRole;
      setSelectedRole('');
      setTimeout(() => setSelectedRole(currentRole), 100);

      // Сбрасываем состояние назначения роли
      setIsAssigningRole(false);
      setSelectedUser(null);
    } catch (error) {
      console.error('Error assigning role:', error);
      setMessage({ type: 'error', text: 'Не удалось назначить роль' });
    }
  };

  // Отзыв роли у пользователя
  const revokeRole = async (userId: number, role: string) => {
    try {
      const token = localStorage.getItem('accessToken');
      if (!token) return;

      const response = await fetch(`${API_URL}/roles/revoke`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          user_id: userId,
          role
        })
      });

      if (!response.ok) {
        throw new Error('Failed to revoke role');
      }

      const data = await response.json();
      setMessage({ type: 'success', text: data.message });

      // Обновляем список пользователей для выбранной роли
      // Пользователь исчезнет из списка, если у него больше нет этой роли
      setUsersByRole(prev => ({ ...prev, [role]: null }));

      // Обновляем текущую выбранную роль (это обновит список пользователей)
      const currentRole = selectedRole;
      setSelectedRole('');
      setTimeout(() => setSelectedRole(currentRole), 100);
    } catch (error) {
      console.error('Error revoking role:', error);
      setMessage({ type: 'error', text: 'Не удалось отозвать роль' });
    }
  };

  // Проверка, доступно ли пользователю управление ролями
  if (isLoading) {
    return <div>Загрузка...</div>;
  }

  return (
    <RoleBasedContent roles={['admin']} fallback={<div>У вас нет доступа к этой странице</div>}>
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-3xl font-bold mb-6">Управление ролями пользователей</h1>

        {message && (
          <div className={`p-4 mb-4 rounded-md ${message.type === 'success' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
            {message.text}
            <button
              className="ml-2 text-sm underline"
              onClick={() => setMessage(null)}
            >
              Закрыть
            </button>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Список ролей */}
          <div className="bg-white p-6 rounded-lg shadow-md">
            <h2 className="text-xl font-semibold mb-4">Роли</h2>
            <div className="space-y-2">
              {availableRoles.map(role => (
                <button
                  key={role.name}
                  className={`w-full text-left px-4 py-2 rounded-md ${selectedRole === role.name ? 'bg-blue-500 text-white' : 'bg-gray-100 hover:bg-gray-200'}`}
                  onClick={() => setSelectedRole(role.name)}
                >
                  {role.name.charAt(0).toUpperCase() + role.name.slice(1)}
                </button>
              ))}
            </div>
          </div>

          {/* Информация о выбранной роли */}
          <div className="bg-white p-6 rounded-lg shadow-md">
            <h2 className="text-xl font-semibold mb-4">Информация о роли</h2>
            {selectedRole && availableRoles.find(r => r.name === selectedRole) ? (
              <div>
                <h3 className="text-lg font-medium mb-2">
                  {selectedRole.charAt(0).toUpperCase() + selectedRole.slice(1)}
                </h3>
                <p className="text-gray-600 mb-4">
                  {availableRoles.find(r => r.name === selectedRole)?.description || 'Нет описания'}
                </p>
                <div>
                  <h4 className="font-medium mb-2">Разрешения:</h4>
                  <ul className="list-disc list-inside text-sm">
                    {availableRoles.find(r => r.name === selectedRole)?.permissions.map(permission => (
                      <li key={permission} className="mb-1">
                        {permission}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            ) : (
              <p className="text-gray-500">Выберите роль, чтобы увидеть информацию о ней</p>
            )}
          </div>

          {/* Пользователи с выбранной ролью */}
          <div className="bg-white p-6 rounded-lg shadow-md">
            <h2 className="text-xl font-semibold mb-4">Пользователи с ролью</h2>
            {selectedRole ? (
              <>
                {usersByRole[selectedRole] ? (
                  usersByRole[selectedRole]?.length > 0 ? (
                    <div className="space-y-3">
                      {usersByRole[selectedRole]?.map(user => (
                        <div key={user.id} className="flex justify-between items-center p-3 bg-gray-50 rounded-md">
                          <div>
                            <div className="font-medium">{user.username}</div>
                            <div className="text-sm text-gray-500">{user.email}</div>
                          </div>
                          <button
                            className="px-3 py-1 bg-red-500 text-white rounded-md hover:bg-red-600 text-sm"
                            onClick={() => revokeRole(user.id, selectedRole)}
                          >
                            Отозвать
                          </button>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-gray-500">Нет пользователей с этой ролью</p>
                  )
                ) : (
                  <p className="text-gray-500">Загрузка пользователей...</p>
                )}
                <button
                  className="mt-4 w-full py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600"
                  onClick={() => setIsAssigningRole(true)}
                >
                  Назначить роль пользователю
                </button>
              </>
            ) : (
              <p className="text-gray-500">Выберите роль, чтобы увидеть пользователей</p>
            )}
          </div>
        </div>

        {/* Модальное окно для назначения роли */}
        {isAssigningRole && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4">
            <div className="bg-white p-6 rounded-lg shadow-xl w-full max-w-md">
              <h2 className="text-xl font-semibold mb-4">Назначить роль {selectedRole}</h2>
              <p className="mb-4">Введите ID пользователя, которому хотите назначить роль:</p>
              <input
                type="number"
                className="w-full px-4 py-2 border rounded-md mb-4"
                placeholder="ID пользователя"
                onChange={(e) => {
                  const userId = parseInt(e.target.value);
                  if (!isNaN(userId)) {
                    setSelectedUser({
                      id: userId,
                      username: "Пользователь #" + userId,
                      email: "",
                      roles: [],
                      is_active: true
                    });
                  } else {
                    setSelectedUser(null);
                  }
                }}
              />
              <div className="flex justify-end space-x-2">
                <button
                  className="px-4 py-2 bg-gray-300 rounded-md hover:bg-gray-400"
                  onClick={() => {
                    setIsAssigningRole(false);
                    setSelectedUser(null);
                  }}
                >
                  Отмена
                </button>
                <button
                  className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600"
                  disabled={!selectedUser}
                  onClick={() => selectedUser && assignRole(selectedUser.id, selectedRole)}
                >
                  Назначить
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Ссылка на возврат в админку */}
        <div className="mt-8">
          <Link href="/admin" className="text-blue-500 hover:text-blue-700">
            &larr; Вернуться в панель администратора
          </Link>
        </div>
      </div>
    </RoleBasedContent>
  );
};

export default RolesManagementPage;
