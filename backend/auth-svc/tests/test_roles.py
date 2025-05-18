"""
Тесты для системы ролей и разрешений
"""
import unittest
from src.services.roles import (
    Role, Permission, ROLE_PERMISSIONS, get_permissions_for_role,
    get_permissions_for_roles, is_higher_role, get_highest_role,
    has_permission, has_required_role
)
from src.services.client_auth import get_client_permissions, get_ui_permissions

class TestRoleSystem(unittest.TestCase):
    """Тесты для системы ролей и разрешений"""

    def test_role_permissions(self):
        """Тест проверки наличия разрешений для каждой роли"""
        for role in ROLE_PERMISSIONS:
            permissions = get_permissions_for_role(role)
            self.assertIsInstance(permissions, list)
            self.assertTrue(len(permissions) > 0)
        
        # Проверяем, что у администратора больше разрешений, чем у остальных
        admin_permissions = get_permissions_for_role(Role.ADMIN)
        user_permissions = get_permissions_for_role(Role.USER)
        self.assertTrue(len(admin_permissions) > len(user_permissions))
    
    def test_get_permissions_for_roles(self):
        """Тест получения объединенных разрешений для списка ролей"""
        # Пользователь с ролями 'user' и 'seller' должен иметь объединенные разрешения
        roles = [Role.USER, Role.SELLER]
        permissions = get_permissions_for_roles(roles)
        
        user_permissions = set(get_permissions_for_role(Role.USER))
        seller_permissions = set(get_permissions_for_role(Role.SELLER))
        expected_permissions = user_permissions.union(seller_permissions)
        
        self.assertEqual(permissions, expected_permissions)
    
    def test_is_higher_role(self):
        """Тест проверки, что одна роль выше другой"""
        # ADMIN выше USER
        self.assertTrue(is_higher_role(Role.ADMIN, Role.USER))
        # MODERATOR выше USER
        self.assertTrue(is_higher_role(Role.MODERATOR, Role.USER))
        # USER не выше ADMIN
        self.assertFalse(is_higher_role(Role.USER, Role.ADMIN))
    
    def test_get_highest_role(self):
        """Тест определения высшей роли из списка"""
        # Список [USER, SELLER, MODERATOR] - высшая роль MODERATOR
        roles = [Role.USER, Role.SELLER, Role.MODERATOR]
        highest = get_highest_role(roles)
        self.assertEqual(highest, Role.MODERATOR)
        
        # Пустой список
        self.assertIsNone(get_highest_role([]))
        
        # Список с невалидной ролью
        roles = [Role.USER, "invalid_role"]
        self.assertEqual(get_highest_role(roles), Role.USER)
    
    def test_has_permission(self):
        """Тест проверки наличия разрешения у списка ролей"""
        # У админа есть разрешение на управление системой
        roles = [Role.ADMIN]
        self.assertTrue(has_permission(roles, Permission.MANAGE_SYSTEM))
        
        # У обычного пользователя нет разрешения на управление системой
        roles = [Role.USER]
        self.assertFalse(has_permission(roles, Permission.MANAGE_SYSTEM))
        
        # У продавца есть разрешение на создание объявлений
        roles = [Role.SELLER]
        self.assertTrue(has_permission(roles, Permission.CREATE_LISTINGS))
    
    def test_has_required_role(self):
        """Тест проверки наличия требуемой роли или выше"""
        # У пользователя с ролью ADMIN есть роль USER или выше
        roles = [Role.ADMIN]
        self.assertTrue(has_required_role(roles, Role.USER))
        
        # У пользователя с ролью USER нет роли ADMIN или выше
        roles = [Role.USER]
        self.assertFalse(has_required_role(roles, Role.ADMIN))
        
        # У пользователя с ролями [USER, MODERATOR] есть роль MODERATOR или выше
        roles = [Role.USER, Role.MODERATOR]
        self.assertTrue(has_required_role(roles, Role.MODERATOR))
    
    def test_client_permissions(self):
        """Тест получения информации о разрешениях для клиента"""
        # Проверка для администратора
        admin_perms = get_client_permissions([Role.ADMIN])
        self.assertTrue(admin_perms.is_admin)
        self.assertTrue(admin_perms.is_moderator)
        self.assertTrue(admin_perms.is_seller)
        self.assertEqual(admin_perms.highest_role, Role.ADMIN)
        
        # Проверка для обычного пользователя
        user_perms = get_client_permissions([Role.USER])
        self.assertFalse(user_perms.is_admin)
        self.assertFalse(user_perms.is_moderator)
        self.assertFalse(user_perms.is_seller)
        self.assertEqual(user_perms.highest_role, Role.USER)
    
    def test_ui_permissions(self):
        """Тест получения разрешений для UI"""
        # Проверка для администратора
        admin_ui = get_ui_permissions([Role.ADMIN])
        self.assertTrue(admin_ui["can_manage_users"])
        self.assertTrue(admin_ui["can_manage_roles"])
        self.assertTrue(admin_ui["is_admin"])
        
        # Проверка для модератора
        mod_ui = get_ui_permissions([Role.MODERATOR])
        self.assertFalse(mod_ui["can_manage_system"])
        self.assertTrue(mod_ui["can_moderate"])
        self.assertTrue(mod_ui["is_moderator"])
        self.assertFalse(mod_ui["is_admin"])
        
        # Проверка для продавца
        seller_ui = get_ui_permissions([Role.SELLER])
        self.assertTrue(seller_ui["can_create_listing"])
        self.assertTrue(seller_ui["is_seller"])
        self.assertFalse(seller_ui["can_moderate"])

if __name__ == "__main__":
    unittest.main() 