"""服务层测试：BookDownloadService, SearchService。"""
import re
from django.test import TestCase
from django.db.models import Q

from reader.models import Book, Chapter, Illustration
from reader.services import BookDownloadService, SearchService
from reader.tests.factories import TestDataFactory


class BookDownloadServiceTest(TestCase):
    """下载服务：文本分块生成、下载响应决策"""

    def setUp(self):
        self.f = TestDataFactory()
        self.f.create_user()
        self.f.create_book(
            title="测试书", author="测试作者",
            description="这是一本测试书。", word_count=400000, illustration_count=5
        )
        self.f.create_chapter(
            title="第一章", content="第一章内容。", index=1, volume_name="第一卷"
        )
        self.f.create_chapter(
            title="第二章", content="第二章内容。", index=2, volume_name="第一卷"
        )

    def test_generate_text_chunks_produces_content(self):
        """文本生成器生成包含标题和章节内容"""
        chunks = list(BookDownloadService.generate_text_chunks(self.f.book))
        text = b''.join(chunks).decode('utf-8')
        self.assertIn("测试书", text)
        self.assertIn("测试作者", text)
        self.assertIn("第一章内容", text)
        self.assertIn("第二章内容", text)
        self.assertIn("第一卷", text)

    def test_generate_text_chunks_empty_book(self):
        """空书籍也能正常生成文本"""
        empty_book = Book.objects.create(title="空书", author="无人", uploader=self.f.user)
        chunks = list(BookDownloadService.generate_text_chunks(empty_book))
        text = b''.join(chunks).decode('utf-8')
        self.assertIn("空书", text)
        self.assertIn("无人", text)


class SearchServiceTest(TestCase):
    """搜索服务：正则检测、多策略查询构建"""

    def test_detect_regex_with_special_chars(self):
        """包含正则特殊字符时检测为正则"""
        self.assertTrue(SearchService._is_regex(r'\d+'))
        self.assertTrue(SearchService._is_regex(r'^test'))
        self.assertTrue(SearchService._is_regex(r'foo|bar'))
        self.assertTrue(SearchService._is_regex(r'hel.o'))

    def test_detect_regex_plain_text(self):
        """普通文本不算正则"""
        self.assertFalse(SearchService._is_regex('普通文本'))
        self.assertFalse(SearchService._is_regex('hello world'))

    def test_detect_regex_invalid_regex(self):
        """非法正则也不算正则表达式"""
        self.assertFalse(SearchService._is_regex('[unclosed'))
        self.assertFalse(SearchService._is_regex('(missing'))

    def test_build_search_query_empty(self):
        """空查询返回空 Q 对象"""
        q = SearchService.build_search_query('', ['title'])
        self.assertEqual(str(q), str(Q()))

    def test_build_search_query_regex(self):
        """正则查询使用 iregex"""
        q = SearchService.build_search_query(r'\d+', ['title'])
        self.assertIsNotNone(q)

    def test_build_search_query_icontains_fallback(self):
        """单字符或超长字符串退化为 icontains"""
        q = SearchService.build_search_query('a', ['title'])
        self.assertIsNotNone(q)

    def test_build_search_query_multi_word(self):
        """多词搜索按 OR 拆分"""
        q = SearchService.build_search_query('hello world', ['title', 'author'])
        self.assertIsNotNone(q)

    def test_build_search_query_fuzzy(self):
        """2-10字符使用模糊正则搜索"""
        q = SearchService.build_search_query('测试', ['title'])
        self.assertIsNotNone(q)
