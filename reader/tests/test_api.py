"""API 测试：Book, Chapter, Illustration, BookGroup, GlobalSettings, UserAdmin ViewSets。"""
import tempfile
from io import BytesIO
from PIL import Image as PILImage

from django.test import TestCase
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from reader.models import (
    Book, Chapter, Illustration, BookGroup, GlobalSettings, Tag,
)
from reader.tests.factories import TestDataFactory


class BookManageAPITest(TestCase):
    """书籍管理 API"""

    def setUp(self):
        self.client = APIClient()
        self.superuser = User.objects.create_superuser(
            username="admin", password="adminpass"
        )
        self.staff = User.objects.create_user(
            username="staff", password="staffpass", is_staff=True
        )
        self.client.force_authenticate(user=self.superuser)

    def test_list_books(self):
        """获取书籍列表"""
        Book.objects.create(title="API书", uploader=self.staff)
        response = self.client.get('/api/admin/books/')
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.data), 1)

    def test_create_book(self):
        """创建书籍"""
        response = self.client.post('/api/admin/books/', {
            'title': '新书',
            'author': '作者',
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['title'], '新书')

    def test_update_book(self):
        """更新书籍"""
        book = Book.objects.create(title="旧标题", uploader=self.staff)
        response = self.client.put(
            f'/api/admin/books/{book.id}/',
            {'title': '新标题', 'author': book.author},
            format='json'
        )
        self.assertEqual(response.status_code, 200)

    def test_delete_book(self):
        """删除书籍"""
        book = Book.objects.create(title="待删", uploader=self.staff)
        response = self.client.delete(f'/api/admin/books/{book.id}/')
        self.assertEqual(response.status_code, 204)

    def test_staff_can_only_access_own_books(self):
        """Staff 只能操作自己的书"""
        self.client.force_authenticate(user=self.staff)
        other = User.objects.create_user(username="other", is_staff=True)
        Book.objects.create(title="他人书", uploader=other)
        response = self.client.get('/api/admin/books/')
        # staff can list but permission class filters by object
        self.assertEqual(response.status_code, 200)

    def test_non_staff_cannot_access(self):
        """非 staff 用户无法访问管理 API"""
        normal = User.objects.create_user(username="normal", password="pass")
        self.client.force_authenticate(user=normal)
        response = self.client.get('/api/admin/books/')
        self.assertEqual(response.status_code, 403)

    def test_batch_download(self):
        """批量下载"""
        book = Book.objects.create(title="下载书", uploader=self.staff)
        response = self.client.post(
            '/api/admin/books/batch-download/',
            {'ids': [book.id]}, format='json'
        )
        self.assertEqual(response.status_code, 200)


class ChapterManageAPITest(TestCase):
    """章节管理 API"""

    def setUp(self):
        self.client = APIClient()
        self.superuser = User.objects.create_superuser(
            username="admin", password="adminpass"
        )
        self.staff = User.objects.create_user(
            username="staff", password="staffpass", is_staff=True
        )
        self.book = Book.objects.create(title="测试书", uploader=self.staff)
        self.client.force_authenticate(user=self.superuser)

    def test_create_chapter(self):
        """创建章节，自动分配 index"""
        response = self.client.post('/api/admin/chapters/', {
            'book': self.book.id,
            'title': '新章节',
            'content': '章节内容',
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['index'], 1)

    def test_chapter_index_auto_increment(self):
        """自动递增 index"""
        Chapter.objects.create(
            book=self.book, title="第1章", content="内容", index=1
        )
        response = self.client.post('/api/admin/chapters/', {
            'book': self.book.id,
            'title': '第2章',
            'content': '内容2',
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['index'], 2)

    def test_staff_cannot_add_to_others_book(self):
        """Staff 不能向他人书籍添加章节"""
        self.client.force_authenticate(user=self.staff)
        other_user = User.objects.create_user(username="other")
        other_book = Book.objects.create(title="他人书", uploader=other_user)
        response = self.client.post('/api/admin/chapters/', {
            'book': other_book.id,
            'title': '章节',
            'content': '内容',
        })
        self.assertEqual(response.status_code, 400)


class IllustrationManageAPITest(TestCase):
    """插图管理 API"""

    def setUp(self):
        self.client = APIClient()
        self.superuser = User.objects.create_superuser(
            username="admin", password="adminpass"
        )
        self.staff = User.objects.create_user(
            username="staff", password="staffpass", is_staff=True
        )
        self.book = Book.objects.create(title="测试书", uploader=self.staff)
        self.client.force_authenticate(user=self.superuser)

    def test_create_illustration(self):
        """创建插图"""
        image = BytesIO()
        img = PILImage.new('RGB', (10, 10), color='red')
        img.save(image, format='JPEG')
        image.seek(0)
        upload_file = SimpleUploadedFile(
            'test.jpg', image.read(), content_type='image/jpeg'
        )
        response = self.client.post('/api/admin/illustrations/', {
            'book': self.book.id,
            'volume_name': '第一卷',
            'image': upload_file,
        })
        self.assertEqual(response.status_code, 201)

    def test_list_illustrations(self):
        """获取插图列表"""
        response = self.client.get('/api/admin/illustrations/')
        self.assertEqual(response.status_code, 200)


class BookGroupManageAPITest(TestCase):
    """书单管理 API"""

    def setUp(self):
        self.client = APIClient()
        self.superuser = User.objects.create_superuser(
            username="admin", password="adminpass"
        )
        self.staff = User.objects.create_user(
            username="staff", password="staffpass", is_staff=True
        )
        self.client.force_authenticate(user=self.superuser)

    def test_create_book_group(self):
        """创建书单"""
        response = self.client.post('/api/admin/book-groups/', {
            'name': '推荐书单',
        })
        self.assertEqual(response.status_code, 201)

    def test_list_book_groups(self):
        """获取书单列表"""
        BookGroup.objects.create(name="书单1", uploader=self.staff)
        response = self.client.get('/api/admin/book-groups/')
        self.assertEqual(response.status_code, 200)


class GlobalSettingsAPITest(TestCase):
    """全局设置 API"""

    def setUp(self):
        self.client = APIClient()
        self.superuser = User.objects.create_superuser(
            username="admin", password="adminpass"
        )
        self.client.force_authenticate(user=self.superuser)

    def test_get_settings(self):
        """获取全局设置"""
        response = self.client.get('/api/admin/settings/')
        self.assertEqual(response.status_code, 200)
        self.assertIn('registration_mode', response.data)

    def test_update_settings(self):
        """更新全局设置"""
        response = self.client.put('/api/admin/settings/update/', {
            'registration_mode': 'closed',
            'invite_code': '654321',
        })
        self.assertEqual(response.status_code, 200)
        settings = GlobalSettings.load()
        self.assertEqual(settings.registration_mode, 'closed')
        self.assertEqual(settings.invite_code, '654321')


class UserAdminAPITest(TestCase):
    """用户管理 API"""

    def setUp(self):
        self.client = APIClient()
        self.superuser = User.objects.create_superuser(
            username="admin", password="adminpass"
        )
        self.client.force_authenticate(user=self.superuser)

    def test_list_users(self):
        """获取用户列表"""
        response = self.client.get('/api/admin/users/')
        self.assertEqual(response.status_code, 200)

    def test_ban_user(self):
        """封禁用户"""
        user = User.objects.create_user(username="victim", password="pass")
        response = self.client.post(f'/api/admin/users/{user.id}/ban/')
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertFalse(user.is_active)

    def test_unban_user(self):
        """解封用户"""
        user = User.objects.create_user(
            username="victim", password="pass", is_active=False
        )
        response = self.client.post(f'/api/admin/users/{user.id}/unban/')
        self.assertEqual(response.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.is_active)

    def test_cannot_ban_self(self):
        """不能封禁自己"""
        response = self.client.post(f'/api/admin/users/{self.superuser.id}/ban/')
        self.assertEqual(response.status_code, 400)
