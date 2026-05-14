"""信号处理测试：word_count、illustration_count、rating 缓存字段、标签限制。"""
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User

from reader.models import Book, Chapter, Illustration, Tag, BookRating
from reader.tests.factories import TestDataFactory


class WordCountSignalTest(TestCase):
    """章节保存/删除时自动维护 word_count"""

    def setUp(self):
        self.f = TestDataFactory()
        self.f.create_user()
        self.f.create_book()

    def test_word_count_increases_on_chapter_create(self):
        """创建章节时 word_count 增加"""
        before = self.f.book.word_count
        content = "这是一段测试内容，共十二个汉字。"
        self.f.create_chapter(content=content)
        self.f.book.refresh_from_db()
        self.assertEqual(self.f.book.word_count, before + len(content))

    def test_word_count_decreases_on_chapter_delete(self):
        """删除章节时 word_count 减少"""
        content = "测试内容"
        chapter = self.f.create_chapter(content=content)
        self.f.book.refresh_from_db()
        before = self.f.book.word_count
        chapter.delete()
        self.f.book.refresh_from_db()
        self.assertEqual(self.f.book.word_count, max(0, before - len(content)))

    def test_word_count_floor_zero(self):
        """word_count 不会低于 0"""
        self.f.book.word_count = 0
        self.f.book.save(update_fields=['word_count'])
        content = "测试"
        chapter = self.f.create_chapter(content=content)
        self.f.book.refresh_from_db()
        self.assertGreaterEqual(self.f.book.word_count, 0)


class IllustrationCountSignalTest(TestCase):
    """插图保存/删除时自动维护 illustration_count"""

    def setUp(self):
        self.f = TestDataFactory()
        self.f.create_user()
        self.f.create_book()

    def test_illustration_count_increases_on_create(self):
        """创建插图时 illustration_count 增加"""
        before = self.f.book.illustration_count
        self.f.create_illustration()
        self.f.book.refresh_from_db()
        self.assertEqual(self.f.book.illustration_count, before + 1)

    def test_illustration_count_decreases_on_delete(self):
        """删除插图时 illustration_count 减少（下限保护）"""
        self.f.create_illustration()
        self.f.book.refresh_from_db()
        before = self.f.book.illustration_count
        illum = Illustration.objects.filter(book=self.f.book).first()
        if illum:
            illum.delete()
        self.f.book.refresh_from_db()
        self.assertEqual(self.f.book.illustration_count, max(0, before - 1))


class RatingSignalTest(TestCase):
    """评分变更时自动重新计算 rating_avg / rating_count"""

    def setUp(self):
        self.f = TestDataFactory()
        self.f.create_user()
        self.f.create_book()

    def test_rating_avg_updates_on_save(self):
        """保存评分后 rating_avg 更新"""
        self.f.create_book_rating(score=8)
        self.f.book.refresh_from_db()
        self.assertEqual(float(self.f.book.rating_avg), 8.0)
        self.assertEqual(self.f.book.rating_count, 1)

    def test_rating_avg_with_multiple_users(self):
        """多个用户评分时计算平均值"""
        user2 = User.objects.create_user(username="user2", password="pass")
        self.f.create_book_rating(score=6)
        BookRating.objects.update_or_create(
            user=user2, book=self.f.book, defaults={'score': 10}
        )
        self.f.book.refresh_from_db()
        self.assertEqual(self.f.book.rating_count, 2)
        self.assertEqual(float(self.f.book.rating_avg), 8.0)

    def test_rating_recalculates_on_delete(self):
        """删除评分后重新计算"""
        self.f.create_book_rating(score=6)
        rating = BookRating.objects.get(user=self.f.user, book=self.f.book)
        rating.delete()
        self.f.book.refresh_from_db()
        self.assertEqual(self.f.book.rating_count, 0)
        self.assertEqual(float(self.f.book.rating_avg), 0.0)


class TagLimitSignalTest(TestCase):
    """标签数量限制：每本书最多 6 个标签"""

    def setUp(self):
        self.f = TestDataFactory()
        self.f.create_user()
        self.f.create_book()

    def test_tag_limit_enforced(self):
        """超过6个标签时抛出 ValidationError"""
        tags = [Tag.objects.get_or_create(name=f"标签{i}")[0] for i in range(6)]
        self.f.book.tags.set(tags)
        self.assertEqual(self.f.book.tags.count(), 6)

        # 不能再添加第7个
        tag7, _ = Tag.objects.get_or_create(name="标签7")
        with self.assertRaises(ValidationError):
            # 触发 m2m_changed pre_add 信号
            self.f.book.tags.add(tag7)

    def test_within_limit_allowed(self):
        """6个以内标签正常添加"""
        tags = [Tag.objects.get_or_create(name=f"标签{i}")[0] for i in range(3)]
        self.f.book.tags.set(tags)
        self.assertEqual(self.f.book.tags.count(), 3)
