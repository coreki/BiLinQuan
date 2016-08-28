import unittest
from app.models import Permission,Role,User,AnonymousUser


class UserTestModelTestCase(unittest.TestCase):
    def test_roles_and_permissions(self):
        Role.insert_roles()
        u = User(email='test@go.com',password='cat')
        self.assertTrue(u.can(Permission.WRITE_ARTICLES))
        self.assertFalse(u.can(Permission.MODERATE_COMMENTS))

    def test_anonymous_user(self):
        u = AnonymousUser()
        self.assertFalse(u.can(Permission.COMMENT))