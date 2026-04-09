from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from django.db.models import Avg
from .models import Book, Chapter, Illustration, BookRating

@receiver(m2m_changed, sender=Book.tags.through)
def limit_book_tags(sender, instance, action, pk_set, **kwargs):
    """
    限制每本书最多只能绑定 6 个标签。
    适用于所有途径：API、Django Admin、ORM。
    """
    if action == "pre_add":
        current_count = instance.tags.count()
        add_count = len(pk_set)
        
        # 如果当前数量 + 准备新增的数量超过 6，则抛出验证错误
        if current_count + add_count > 6:
            raise ValidationError(f"一本书最多只能绑定 6 个标签！当前已有 {current_count} 个，尝试新增 {add_count} 个。")

@receiver(post_delete, sender=Book)
def auto_delete_cover_on_delete(sender, instance, **kwargs):
    """
    删除书籍时，自动删除 media 目录下的封面文件
    """
    if instance.cover:
        instance.cover.delete(save=False)

@receiver(post_save, sender=Chapter)
def update_word_count_on_save(sender, instance, created, **kwargs):
    """
    监听章节的保存事件 (post_save)
    保存章节时，增加书籍总字数。
    """
    if created:
        instance.book.word_count += len(instance.content)
        instance.book.save(update_fields=['word_count'])

@receiver(post_delete, sender=Chapter)
def update_word_count_on_delete(sender, instance, **kwargs):
    """
    监听章节的删除事件 (post_delete)
    删除章节时，减少书籍总字数。
    """
    book = instance.book
    if book.id: # 确保书籍实体还没被级联删除销毁
        book.word_count = max(0, book.word_count - len(instance.content))
        book.save(update_fields=['word_count'])

@receiver(post_save, sender=Illustration)
def update_illustration_count_on_save(sender, instance, created, **kwargs):
    """监听插图的新增"""
    if created:
        instance.book.illustration_count += 1
        instance.book.save(update_fields=['illustration_count'])

@receiver(post_delete, sender=Illustration)
def update_illustration_count_on_delete(sender, instance, **kwargs):
    """监听插图的删除"""
    book = instance.book
    if instance.image:
        instance.image.delete(save=False)
    if book.id:
        book.illustration_count = max(0, book.illustration_count - 1)
        book.save(update_fields=['illustration_count'])


def _refresh_book_rating(book):
    """重新计算书籍平均评分和评分人数, 写入缓存字段。"""
    result = BookRating.objects.filter(book=book).aggregate(avg=Avg('score'))
    avg = result['avg']
    book.rating_avg = round(avg, 2) if avg is not None else 0.00
    book.rating_count = BookRating.objects.filter(book=book).count()
    book.save(update_fields=['rating_avg', 'rating_count'])

@receiver(post_save, sender=BookRating)
def update_book_rating_on_save(sender, instance, **kwargs):
    """监听评分的保存 (新增和修改), 重新计算平均分。"""
    _refresh_book_rating(instance.book)

@receiver(post_delete, sender=BookRating)
def update_book_rating_on_delete(sender, instance, **kwargs):
    """监听评分的删除, 重新计算平均分。"""
    book = instance.book
    if book.id:
        _refresh_book_rating(book)