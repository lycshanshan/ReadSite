"""视图测试：index, library, book_detail, read_chapter, signup, profile, my_bookshelf, etc."""
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone

from reader.models import (
    Book, Chapter, Tag, BookGroup, UserPoints, BookRecoLog,
    Bookshelf, Bookmark, UserProgress, GlobalSettings, Illustration,
)
from reader.tests.factories import TestDataFactory


class IndexViewTest(TestCase):
    """首页：书籍列表，推荐，分页"""

    def setUp(self):
        self.f = TestDataFactory()

    def test_index_loads(self):
        """首页正常加载"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'index.html')

    def test_index_with_search(self):
        """首页搜索"""
        user = User.objects.create_user(username="u", password="p")
        Book.objects.create(title="独一无二的书名", author="作者", uploader=user)
        response = self.client.get('/?q=独一无二')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '独一无二的书名')

    def test_index_shows_recommended(self):
        """首页显示推荐书籍"""
        user = User.objects.create_user(username="u", password="p")
        for i in range(5):
            Book.objects.create(title=f"书{i}", author="作者", recos=i, uploader=user)
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)


class LibraryViewTest(TestCase):
    """书库：标签、分组、筛选、排序、分页"""

    def setUp(self):
        self.f = TestDataFactory()
        self.user = User.objects.create_user(username="u", password="p")

    def test_library_loads(self):
        """书库正常加载"""
        response = self.client.get('/library/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'library.html')

    def test_library_with_tag_filter(self):
        """按标签筛选"""
        tag, _ = Tag.objects.get_or_create(name="科幻")
        book = Book.objects.create(title="科幻书", author="作者", uploader=self.user)
        book.tags.add(tag)
        response = self.client.get(f'/library/?tags=科幻')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "科幻书")

    def test_library_with_sort(self):
        """排序参数"""
        response = self.client.get('/library/?sort=word_count&order=desc')
        self.assertEqual(response.status_code, 200)

    def test_library_with_group(self):
        """书单筛选"""
        book = Book.objects.create(title="书单书", uploader=self.user)
        group = BookGroup.objects.create(name="精选", uploader=self.user)
        group.books.add(book)
        response = self.client.get(f'/library/?group_id={group.id}')
        self.assertEqual(response.status_code, 200)


class BookDetailViewTest(TestCase):
    """书籍详情：卷分组、插图检查、进度"""

    def setUp(self):
        self.f = TestDataFactory()
        self.user = self.f.create_user()

    def test_book_detail_loads(self):
        """书籍详情正常加载"""
        book = self.f.create_book()
        self.f.create_chapter(book=book, volume_name="第一卷", index=1)
        response = self.client.get(f'/book/{book.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'book_detail.html')

    def test_book_detail_shows_volume_grouping(self):
        """章节按卷分组显示"""
        book = self.f.create_book()
        self.f.create_chapter(book=book, title="第一章", volume_name="第一卷", index=1)
        self.f.create_chapter(book=book, title="第二章", volume_name="第一卷", index=2)
        self.f.create_chapter(book=book, title="第三章", volume_name="第二卷", index=3)
        response = self.client.get(f'/book/{book.id}/')
        self.assertContains(response, '第一卷')
        self.assertContains(response, '第二卷')


class ReadChapterViewTest(TestCase):
    """章节阅读：导航、进度、书签"""

    def setUp(self):
        self.f = TestDataFactory()
        self.user = self.f.create_user()
        self.book = self.f.create_book()

    def test_read_chapter_loads(self):
        """章节阅读正常加载"""
        ch = self.f.create_chapter(book=self.book, title="第一章", index=1)
        response = self.client.get(f'/read/{ch.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'read_chapter.html')
        self.assertContains(response, '第一章')

    def test_read_chapter_navigation(self):
        """前后章节导航"""
        ch1 = self.f.create_chapter(book=self.book, title="第1章", index=1)
        ch2 = self.f.create_chapter(book=self.book, title="第2章", index=2)
        response = self.client.get(f'/read/{ch2.id}/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '第2章')


class SignupViewTest(TestCase):
    """注册：开放/邀请/关闭模式"""

    def test_signup_page_loads(self):
        """注册页面加载"""
        response = self.client.get('/signup/')
        self.assertEqual(response.status_code, 200)

    def test_signup_closed_mode(self):
        """关闭注册模式"""
        settings = GlobalSettings.load()
        settings.registration_mode = GlobalSettings.MODE_CLOSED
        settings.save()
        response = self.client.get('/signup/')
        self.assertTemplateUsed(response, 'signup_closed.html')

    def test_signup_invite_mode(self):
        """邀请码模式"""
        settings = GlobalSettings.load()
        settings.registration_mode = GlobalSettings.MODE_INVITE
        settings.invite_code = '123456'
        settings.save()
        response = self.client.get('/signup/')
        self.assertEqual(response.status_code, 200)


class ProfileViewTest(TestCase):
    """个人中心"""

    def test_profile_requires_login(self):
        """未登录重定向"""
        response = self.client.get('/profile/')
        self.assertEqual(response.status_code, 302)

    def test_profile_loads_for_authenticated_user(self):
        """登录后可访问"""
        user = User.objects.create_user(username="puser", password="pass")
        self.client.login(username="puser", password="pass")
        response = self.client.get('/profile/')
        self.assertEqual(response.status_code, 200)


class MyBookshelfViewTest(TestCase):
    """书架：书籍、书签、进度"""

    def setUp(self):
        self.user = User.objects.create_user(username="shelfuser", password="pass")
        self.client.login(username="shelfuser", password="pass")
        self.book = Book.objects.create(title="书架书", uploader=self.user)
        self.chapter = Chapter.objects.create(
            book=self.book, title="第一章", content="内容", index=1
        )

    def test_bookshelf_requires_login(self):
        """未登录重定向"""
        self.client.logout()
        response = self.client.get('/bookshelf/')
        self.assertEqual(response.status_code, 302)

    def test_bookshelf_loads(self):
        """书架正常加载"""
        response = self.client.get('/bookshelf/')
        self.assertEqual(response.status_code, 200)

    def test_bookshelf_shows_items(self):
        """书架显示已收藏的书籍"""
        Bookshelf.objects.create(user=self.user, book=self.book)
        response = self.client.get('/bookshelf/')
        self.assertContains(response, '书架书')
