from django.contrib.auth.models import User
from django.utils import timezone

from reader.models import (
    Book, Chapter, Illustration, Tag, BookGroup,
    UserPoints, BookRecoLog, BookRating,
    Bookshelf, Bookmark, UserProgress,
    GlobalSettings, StaffApplication,
)


class TestDataFactory:
    """Create test data for a single test case."""

    def __init__(self):
        self.user = None
        self.book = None
        self.chapters = []
        self._chapter_idx = 0

    def create_user(self, username="testuser", password="testpass", **kwargs):
        self.user = User.objects.create_user(
            username=username, password=password, **kwargs
        )
        return self.user

    def create_book(self, title="测试书籍", author="测试作者", word_count=0,
                    illustration_count=0, recos=0, uploader=None, **kwargs):
        self.book = Book.objects.create(
            title=title, author=author,
            word_count=word_count, illustration_count=illustration_count,
            recos=recos, uploader=uploader or self.user, **kwargs
        )
        return self.book

    def create_tag(self, name="测试标签"):
        tag, _ = Tag.objects.get_or_create(name=name)
        return tag

    def create_chapter(self, book=None, title="第一章", content="章节内容",
                       index=None, volume_name=None):
        book = book or self.book
        if index is None:
            self._chapter_idx += 1
            index = self._chapter_idx
        chapter = Chapter.objects.create(
            book=book, title=title, content=content,
            index=index, volume_name=volume_name
        )
        self.chapters.append(chapter)
        return chapter

    def create_illustration(self, book=None, index=1, volume_name=None):
        book = book or self.book
        illum = Illustration.objects.create(
            book=book, index=index, volume_name=volume_name or ""
        )
        return illum

    def create_user_points(self, user=None, point=0, exp=0, reco_balance=0):
        user = user or self.user
        up, _ = UserPoints.objects.get_or_create(user=user, defaults={
            'point': point, 'exp': exp, 'reco_balance': reco_balance
        })
        return up

    def create_book_reco_log(self, user=None, book=None, date=None, count=0):
        from django.utils import timezone
        user = user or self.user
        book = book or self.book
        date = date or timezone.localdate()
        log, _ = BookRecoLog.objects.get_or_create(
            user=user, book=book, date=date, defaults={'count': count}
        )
        return log

    def create_book_rating(self, user=None, book=None, score=5):
        user = user or self.user
        book = book or self.book
        rating, _ = BookRating.objects.update_or_create(
            user=user, book=book, defaults={'score': score}
        )
        return rating

    def create_bookshelf(self, user=None, book=None):
        user = user or self.user
        book = book or self.book
        shelf, _ = Bookshelf.objects.get_or_create(user=user, book=book)
        return shelf

    def create_bookmark(self, user=None, chapter=None):
        user = user or self.user
        chapter = chapter or (self.chapters[0] if self.chapters else None)
        mark, _ = Bookmark.objects.get_or_create(user=user, chapter=chapter)
        return mark

    def create_user_progress(self, user=None, book=None, chapter=None):
        user = user or self.user
        book = book or self.book
        chapter = chapter or (self.chapters[0] if self.chapters else None)
        progress, _ = UserProgress.objects.update_or_create(
            user=user, book=book, defaults={'chapter': chapter}
        )
        return progress

    def create_staff_application(self, user=None, status='pending', reason=''):
        user = user or self.user
        app, _ = StaffApplication.objects.update_or_create(
            user=user, defaults={'status': status, 'reason': reason}
        )
        return app
