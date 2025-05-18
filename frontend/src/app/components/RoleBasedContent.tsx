import React, { ReactNode } from 'react';
import { useAuth } from '../hooks/auth';

type RoleBasedContentProps = {
  /**
   * Роли, для которых контент будет отображаться
   * Если не указано, контент будет отображаться для всех авторизованных пользователей
   */
  roles?: string[];
  
  /**
   * Permissions, которые требуются для доступа к контенту
   * Если есть хотя бы одно совпадение с permissions пользователя, контент будет отображаться
   */
  permissions?: string[];
  
  /**
   * Require all permissions to be present (по умолчанию false - достаточно любого из списка)
   */
  requireAllPermissions?: boolean;
  
  /**
   * Контент, который будет отображаться, если у пользователя есть необходимые роли/разрешения
   */
  children: ReactNode;
  
  /**
   * Контент, который будет отображаться в случае отсутствия необходимых прав
   * Если не указан, то при отсутствии прав ничего не отображается
   */
  fallback?: ReactNode;
};

/**
 * Компонент для отображения контента на основе ролей и разрешений пользователя
 */
export const RoleBasedContent = ({
  roles,
  permissions,
  requireAllPermissions = false,
  children,
  fallback = null,
}: RoleBasedContentProps) => {
  const { user, userPermissions, isLoading } = useAuth();

  // Если загрузка данных пользователя еще идет, не отображаем контент
  if (isLoading) {
    return null;
  }

  // Если пользователь не авторизован, показываем fallback
  if (!user) {
    return <>{fallback}</>;
  }

  // Если не указаны ни роли, ни разрешения, показываем контент всем авторизованным пользователям
  if (!roles && !permissions) {
    return <>{children}</>;
  }

  // Проверка на соответствие ролей
  let hasRequiredRole = false;
  if (roles && roles.length > 0) {
    hasRequiredRole = roles.some(role => user.roles.includes(role));
  } else {
    // Если роли не указаны, то считаем, что роль подходящая
    hasRequiredRole = true;
  }

  // Проверка на соответствие разрешений
  let hasRequiredPermission = false;
  if (permissions && permissions.length > 0 && userPermissions) {
    if (requireAllPermissions) {
      // Нужны все разрешения из списка
      hasRequiredPermission = permissions.every(permission => 
        userPermissions.permissions.includes(permission)
      );
    } else {
      // Достаточно любого разрешения из списка
      hasRequiredPermission = permissions.some(permission => 
        userPermissions.permissions.includes(permission)
      );
    }
  } else {
    // Если разрешения не указаны, то считаем, что разрешения подходящие
    hasRequiredPermission = true;
  }

  // Отображаем контент только если соответствуют и роли, и разрешения
  if (hasRequiredRole && hasRequiredPermission) {
    return <>{children}</>;
  }

  // В противном случае отображаем fallback
  return <>{fallback}</>;
};

/**
 * Проверка наличия у пользователя конкретного разрешения
 */
export const hasPermission = (
  userPermissions: string[] | undefined, 
  permission: string
): boolean => {
  if (!userPermissions) return false;
  return userPermissions.includes(permission);
};

/**
 * Проверка наличия у пользователя конкретной роли
 */
export const hasRole = (
  userRoles: string[] | undefined, 
  role: string
): boolean => {
  if (!userRoles) return false;
  return userRoles.includes(role);
}; 