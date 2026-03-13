from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Book, Chapter, Illustration

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