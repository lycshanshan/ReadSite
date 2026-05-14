"""权限测试：IsUploaderOrSuperUser, IsSuperUser。"""
from django.test import TestCase
from django.contrib.auth.models import User
from unittest.mock import Mock

from reader.models import Book, Chapter, BookGroup
from reader.permissions import IsSuperUser, IsUploaderOrSuperUser


class IsSuperUserTest(TestCase):
    """超级管理员权限"""

    def test_superuser_has_permission(self):
        """超管有权限"""
        user = User.objects.create_user(username="admin", is_superuser=True)
        request = Mock(user=user)
        view = Mock()
        perm = IsSuperUser()
        self.assertTrue(perm.has_permission(request, view))

    def test_normal_user_no_permission(self):
        """普通用户无权限"""
        user = User.objects.create_user(username="normal")
        request = Mock(user=user)
        view = Mock()
        perm = IsSuperUser()
        self.assertFalse(perm.has_permission(request, view))

    def test_anonymous_no_permission(self):
        """匿名用户无权限"""
        request = Mock(user=None)
        view = Mock()
        perm = IsSuperUser()
        self.assertFalse(perm.has_permission(request, Mock()))
        # anonymous
        request = Mock()
        type(request).user = Mock()
        request.user = None
        self.assertFalse(perm.has_permission(request, view))


class IsUploaderOrSuperUserTest(TestCase):
    """上传者或超管权限"""

    def setUp(self):
        self.superuser = User.objects.create_user(
            username="super", is_superuser=True
        )
        self.staff = User.objects.create_user(
            username="staff", is_staff=True
        )
        self.other_staff = User.objects.create_user(
            username="other", is_staff=True
        )
        self.book = Book.objects.create(
            title="测试", uploader=self.staff
        )
        self.chapter = Chapter.objects.create(
            book=self.book, title="章节", content="内容", index=1
        )

    def test_superuser_can_access_any_object(self):
        """超管可操作任意对象"""
        perm = IsUploaderOrSuperUser()
        request = Mock(user=self.superuser)
        view = Mock()
        self.assertTrue(perm.has_object_permission(request, view, self.book))
        self.assertTrue(perm.has_object_permission(request, view, self.chapter))

    def test_uploader_can_access_own_book(self):
        """上传者可操作自己的书籍"""
        perm = IsUploaderOrSuperUser()
        request = Mock(user=self.staff)
        view = Mock()
        self.assertTrue(perm.has_object_permission(request, view, self.book))

    def test_non_uploader_cannot_access_book(self):
        """非上传者不能操作他人的书籍"""
        perm = IsUploaderOrSuperUser()
        request = Mock(user=self.other_staff)
        view = Mock()
        self.assertFalse(perm.has_object_permission(request, view, self.book))

    def test_staff_can_access_chapter_of_own_book(self):
        """Staff可操作自己上传的书籍的章节"""
        perm = IsUploaderOrSuperUser()
        request = Mock(user=self.staff)
        view = Mock()
        self.assertTrue(perm.has_object_permission(request, view, self.chapter))

    def test_staff_cannot_access_chapter_of_others_book(self):
        """Staff不能操作他人上传的书籍的章节"""
        perm = IsUploaderOrSuperUser()
        request = Mock(user=self.other_staff)
        view = Mock()
        self.assertFalse(perm.has_object_permission(request, view, self.chapter))
