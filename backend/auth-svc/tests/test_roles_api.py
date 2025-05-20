import pytest
from fastapi import status
from unittest.mock import patch
from src.services.roles import Role, Permission

class TestRolesAPI:
    """
    Тесты для API управления ролями пользователей
    """
    
    def test_get_available_roles(self, client, admin_token):
        """
        Тест получения списка доступных ролей
        """
        # Отправляем запрос на получение ролей
        response = client.get(
            "/roles/",
            headers={"Authorization": f"Bearer {admin_token['access_token']}"}
        )
        
        # Проверяем ответ
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        # Проверяем, что в списке есть базовые роли
        assert "user" in data
        assert "admin" in data
        # Проверяем, что гостевая роль отсутствует
        assert "guest" not in data
    
    def test_get_available_roles_unauthorized(self, client):
        """
        Тест получения списка ролей без авторизации
        """
        # Отправляем запрос без токена
        response = client.get("/roles/")
        
        # Проверяем ответ
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "detail" in data
    
    def test_get_available_roles_forbidden(self, client, user_token):
        """
        Тест получения списка ролей с недостаточными правами
        """
        # Отправляем запрос с токеном обычного пользователя
        response = client.get(
            "/roles/",
            headers={"Authorization": f"Bearer {user_token['access_token']}"}
        )
        
        # Проверяем ответ
        assert response.status_code == status.HTTP_403_FORBIDDEN
        data = response.json()
        assert "detail" in data
    
    def test_get_roles_info(self, client, admin_token):
        """
        Тест получения подробной информации о ролях
        """
        # Отправляем запрос на получение информации о ролях
        response = client.get(
            "/roles/info",
            headers={"Authorization": f"Bearer {admin_token['access_token']}"}
        )
        
        # Проверяем ответ
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        
        # Проверяем структуру данных для каждой роли
        for role_info in data:
            assert "name" in role_info
            assert "description" in role_info
            assert "permissions" in role_info
            assert isinstance(role_info["permissions"], list)
    
    def test_assign_role(self, client, admin_token, test_user, test_db):
        """
        Тест назначения роли пользователю
        """
        # Данные для запроса
        role_data = {
            "user_id": test_user.id,
            "role": "seller"
        }
        
        # Отправляем запрос на назначение роли
        response = client.post(
            "/roles/assign",
            json=role_data,
            headers={"Authorization": f"Bearer {admin_token['access_token']}"}
        )
        
        # Проверяем ответ
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "message" in data
        assert "успешно назначена" in data["message"]
        
        # Проверяем, что роль добавлена пользователю в БД
        test_db.refresh(test_user)
        assert "seller" in test_user.roles
    
    def test_assign_role_nonexistent_user(self, client, admin_token):
        """
        Тест назначения роли несуществующему пользователю
        """
        # Данные для запроса с несуществующим ID пользователя
        role_data = {
            "user_id": 9999,  # Несуществующий ID
            "role": "seller"
        }
        
        # Отправляем запрос на назначение роли
        response = client.post(
            "/roles/assign",
            json=role_data,
            headers={"Authorization": f"Bearer {admin_token['access_token']}"}
        )
        
        # Проверяем ответ
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "detail" in data
        assert "не найден" in data["detail"]
    
    def test_assign_invalid_role(self, client, admin_token, test_user):
        """
        Тест назначения несуществующей роли
        """
        # Данные для запроса с несуществующей ролью
        role_data = {
            "user_id": test_user.id,
            "role": "invalid_role"  # Несуществующая роль
        }
        
        # Отправляем запрос на назначение роли
        response = client.post(
            "/roles/assign",
            json=role_data,
            headers={"Authorization": f"Bearer {admin_token['access_token']}"}
        )
        
        # Проверяем ответ
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "detail" in data
        assert "не существует" in data["detail"]
    
    def test_revoke_role(self, client, admin_token, test_db):
        """
        Тест отзыва роли у пользователя
        """
        # Создаем пользователя с несколькими ролями
        from src.models.user import User
        from src.services.password import hash_password
        
        user = User(
            username="multi_role",
            email="multi_role@example.com",
            hashed_password=hash_password("password123"),
            is_active=True,
            is_verified=True,
            roles=["user", "seller"]
        )
        test_db.add(user)
        test_db.commit()
        
        # Данные для запроса
        role_data = {
            "user_id": user.id,
            "role": "seller"
        }
        
        # Отправляем запрос на отзыв роли
        response = client.post(
            "/roles/revoke",
            json=role_data,
            headers={"Authorization": f"Bearer {admin_token['access_token']}"}
        )
        
        # Проверяем ответ
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "message" in data
        assert "успешно отозвана" in data["message"]
        
        # Проверяем, что роль удалена у пользователя в БД
        test_db.refresh(user)
        assert "seller" not in user.roles
        assert "user" in user.roles  # Базовая роль должна остаться
    
    def test_revoke_last_role(self, client, admin_token, test_user, test_db):
        """
        Тест отзыва последней роли у пользователя (должна остаться роль 'user')
        """
        # Данные для запроса
        role_data = {
            "user_id": test_user.id,
            "role": "user"  # Пытаемся отозвать базовую роль
        }
        
        # Отправляем запрос на отзыв роли
        response = client.post(
            "/roles/revoke",
            json=role_data,
            headers={"Authorization": f"Bearer {admin_token['access_token']}"}
        )
        
        # Проверяем ответ
        assert response.status_code == status.HTTP_200_OK
        
        # Проверяем, что у пользователя все равно осталась роль 'user'
        test_db.refresh(test_user)
        assert "user" in test_user.roles
    
    def test_get_users_by_role(self, client, admin_token, test_user, test_admin):
        """
        Тест получения списка пользователей с указанной ролью
        """
        # Отправляем запрос на получение пользователей с ролью 'user'
        response = client.get(
            "/roles/users/user",
            headers={"Authorization": f"Bearer {admin_token['access_token']}"}
        )
        
        # Проверяем ответ
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        
        # Проверяем, что в списке есть наши тестовые пользователи
        user_ids = [user["id"] for user in data]
        assert test_user.id in user_ids
        assert test_admin.id in user_ids  # У админа тоже есть роль 'user'
        
        # Проверяем структуру данных пользователя
        for user_data in data:
            assert "id" in user_data
            assert "username" in user_data
            assert "email" in user_data
            assert "roles" in user_data
            assert "is_active" in user_data
            assert "user" in user_data["roles"]

class TestPermissionsAPI:
    """
    Тесты для API управления разрешениями
    """
    
    def test_get_all_permissions(self, client, admin_token):
        """
        Тест получения списка всех разрешений
        """
        # Отправляем запрос на получение разрешений
        response = client.get(
            "/permissions/",
            headers={"Authorization": f"Bearer {admin_token['access_token']}"}
        )
        
        # Проверяем ответ
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        
        # Проверяем, что в списке есть базовые разрешения
        assert Permission.READ_PUBLIC in data
        assert Permission.MANAGE_USERS in data
    
    def test_get_permissions_info(self, client, admin_token):
        """
        Тест получения подробной информации о разрешениях
        """
        # Отправляем запрос на получение информации о разрешениях
        response = client.get(
            "/permissions/info",
            headers={"Authorization": f"Bearer {admin_token['access_token']}"}
        )
        
        # Проверяем ответ
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        
        # Проверяем структуру данных для каждого разрешения
        for permission_info in data:
            assert "name" in permission_info
            assert "description" in permission_info
    
    def test_get_permissions_by_role(self, client, admin_token):
        """
        Тест получения списка разрешений для указанной роли
        """
        # Отправляем запрос на получение разрешений для роли 'admin'
        response = client.get(
            "/permissions/role/admin",
            headers={"Authorization": f"Bearer {admin_token['access_token']}"}
        )
        
        # Проверяем ответ
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        
        # Проверяем, что у админа есть все разрешения
        assert Permission.READ_PUBLIC in data
        assert Permission.MANAGE_USERS in data
        assert Permission.MANAGE_ROLES in data
        assert Permission.MANAGE_SYSTEM in data
    
    def test_get_permissions_by_invalid_role(self, client, admin_token):
        """
        Тест получения разрешений для несуществующей роли
        """
        # Отправляем запрос с несуществующей ролью
        response = client.get(
            "/permissions/role/invalid_role",
            headers={"Authorization": f"Bearer {admin_token['access_token']}"}
        )
        
        # Проверяем ответ
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "detail" in data
        assert "не существует" in data["detail"]
    
    def test_check_user_permission(self, client, admin_token):
        """
        Тест проверки наличия разрешений у пользователя
        """
        # Отправляем запрос на проверку разрешений
        response = client.get(
            "/permissions/check",
            headers={"Authorization": f"Bearer {admin_token['access_token']}"}
        )
        
        # Проверяем ответ
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        # Проверяем, что у админа есть все разрешения
        for permission in Permission:
            assert permission in data
            assert data[permission] is True 