"""序列化器测试：标签处理、书籍ID解析、跨书移动保护、密码哈希。"""
from django.test import TestCase
from django.contrib.auth.models import User

from reader.models import Book, Chapter, Illustration, Tag, BookGroup
from reader.serializers import (
    BookSerializer, ChapterSerializer, IllustrationSerializer,
    BookGroupSerializer, UserAdminSerializer,
)
from reader.tests.factories import TestDataFactory


class BookSerializerTest(TestCase):
    """BookSerializer：标签处理（逗号分割、去重、上限6、自动创建）"""

    def setUp(self):
        self.f = TestDataFactory()
        self.user = self.f.create_user()

    def test_handle_tags_comma_split(self):
        """逗号分隔的标签字符串正确拆分"""
        book = Book.objects.create(title="测试", uploader=self.user)
        serializer = BookSerializer()
        serializer._handle_tags(book, ["科幻, 冒险, 热血"])
        self.assertEqual(book.tags.count(), 3)

    def test_handle_tags_dedup(self):
        """重复标签去重"""
        book = Book.objects.create(title="测试", uploader=self.user)
        serializer = BookSerializer()
        serializer._handle_tags(book, ["科幻", "科幻", "冒险"])
        self.assertEqual(book.tags.count(), 2)

    def test_handle_tags_max_six(self):
        """标签上限为6"""
        book = Book.objects.create(title="测试", uploader=self.user)
        serializer = BookSerializer()
        serializer._handle_tags(book, [f"标签{i}" for i in range(10)])
        self.assertLessEqual(book.tags.count(), 6)

    def test_handle_tags_auto_create(self):
        """不存在的标签自动创建"""
        book = Book.objects.create(title="测试", uploader=self.user)
        serializer = BookSerializer()
        serializer._handle_tags(book, ["不存在的标签名称"])
        self.assertTrue(Tag.objects.filter(name="不存在的标签名称").exists())

    def test_get_tags_returns_name_list(self):
        """get_tags 返回标签名列表"""
        book = Book.objects.create(title="测试", uploader=self.user)
        tag1, _ = Tag.objects.get_or_create(name="标签A")
        tag2, _ = Tag.objects.get_or_create(name="标签B")
        book.tags.set([tag1, tag2])
        serializer = BookSerializer()
        result = serializer.get_tags(book)
        self.assertEqual(result, ["标签A", "标签B"])


class ChapterSerializerTest(TestCase):
    """ChapterSerializer：禁止跨书移动"""

    def setUp(self):
        self.f = TestDataFactory()
        self.user = self.f.create_user()
        self.book1 = self.f.create_book(title="书1")
        self.book2 = Book.objects.create(title="书2", uploader=self.user)
        self.chapter = Chapter.objects.create(
            book=self.book1, title="章节", content="内容", index=1
        )

    def test_cannot_move_chapter_to_other_book(self):
        """更新时不能将章节移到其他书"""
        data = {'book': self.book2.pk, 'title': '新标题'}
        serializer = ChapterSerializer(self.chapter, data=data, partial=True)
        self.assertTrue(serializer.is_valid())
        updated = serializer.save()
        self.assertEqual(updated.book, self.book1)  # book 没变


class IllustrationSerializerTest(TestCase):
    """IllustrationSerializer：禁止跨书移动"""

    def setUp(self):
        self.f = TestDataFactory()
        self.user = self.f.create_user()
        self.book1 = self.f.create_book(title="书1")
        self.book2 = Book.objects.create(title="书2", uploader=self.user)
        self.illum = Illustration.objects.create(
            book=self.book1, index=1, volume_name=""
        )

    def test_cannot_move_illustration_to_other_book(self):
        """更新时不能将插图移到其他书"""
        data = {'book': self.book2.pk, 'index': 5}
        serializer = IllustrationSerializer(self.illum, data=data, partial=True)
        self.assertTrue(serializer.is_valid())
        updated = serializer.save()
        self.assertEqual(updated.book, self.book1)


class BookGroupSerializerTest(TestCase):
    """BookGroupSerializer：书籍ID解析"""

    def setUp(self):
        self.f = TestDataFactory()
        self.user = self.f.create_user()
        self.book1 = self.f.create_book(title="书1")
        self.book2 = Book.objects.create(title="书2", uploader=self.user)

    def test_handle_books_parse_ids(self):
        """解析书籍 ID 列表"""
        group = BookGroup.objects.create(name="测试书单", uploader=self.user)
        serializer = BookGroupSerializer()
        serializer._handle_books(group, [str(self.book1.id), str(self.book2.id)])
        self.assertEqual(group.books.count(), 2)

    def test_handle_books_comma_split(self):
        """逗号分隔的ID字符串"""
        group = BookGroup.objects.create(name="测试书单", uploader=self.user)
        serializer = BookGroupSerializer()
        serializer._handle_books(group, [f"{self.book1.id},{self.book2.id}"])
        self.assertEqual(group.books.count(), 2)

    def test_handle_books_ignore_invalid(self):
        """无效ID被忽略"""
        group = BookGroup.objects.create(name="测试书单", uploader=self.user)
        serializer = BookGroupSerializer()
        serializer._handle_books(group, ["not_a_number", str(self.book1.id)])
        self.assertEqual(group.books.count(), 1)

    def test_get_books_returns_id_title_list(self):
        """get_books 返回 id+title 列表"""
        group = BookGroup.objects.create(name="测试书单", uploader=self.user)
        group.books.set([self.book1])
        serializer = BookGroupSerializer()
        result = serializer.get_books(group)
        self.assertEqual(result, [{"id": self.book1.id, "title": self.book1.title}])


class UserAdminSerializerTest(TestCase):
    """UserAdminSerializer：密码哈希"""

    def test_create_hashes_password(self):
        """创建用户时密码被哈希"""
        data = {'username': 'newadmin', 'password': 'secret123'}
        serializer = UserAdminSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        user = serializer.save()
        self.assertTrue(user.check_password('secret123'))
        self.assertNotEqual(user.password, 'secret123')

    def test_update_hashes_password(self):
        """更新用户时密码被哈希"""
        user = User.objects.create_user(username="existing", password="oldpass")
        data = {'password': 'newsecret'}
        serializer = UserAdminSerializer(user, data=data, partial=True)
        self.assertTrue(serializer.is_valid())
        updated = serializer.save()
        self.assertTrue(updated.check_password('newsecret'))
