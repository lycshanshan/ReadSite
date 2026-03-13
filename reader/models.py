from django.db import models
from django.db.models.signals import post_save, post_delete
from django.contrib.auth.models import User
from django.utils import timezone
from django.dispatch import receiver

class Book(models.Model):
    """
    书籍核心模型 (Book)
    记录小说的元数据。为了提升前端列表页的加载速度，我们在此处冗余了 `word_count` 
    和 `illustration_count` 字段，避免每次查询都去 COUNT 关联表。
    """
    title = models.CharField(max_length=200, verbose_name="书名")
    author = models.CharField(max_length=100, verbose_name="作者", default="未知")
    cover = models.ImageField(upload_to='covers/', verbose_name="封面", blank=True, null=True)
    description = models.TextField(verbose_name="简介", blank=True)

     # 统计字段 (由 Chapter 和 Illustration 的 save() 钩子自动维护)
    word_count = models.PositiveIntegerField(default=0, verbose_name="总字数")
    illustration_count = models.PositiveIntegerField(default=0, verbose_name="插图数量")

    is_recommended = models.BooleanField(default=False, verbose_name="是否推荐")
    created_at = models.DateTimeField(auto_now=True, verbose_name="收录时间")
    uploader = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="上传者")

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']
        verbose_name = "小说"
        verbose_name_plural = verbose_name

class Chapter(models.Model):
    """
    章节模型 (Chapter)
    记录小说的正文内容。通过 `volume_name` 实现书籍目录的分卷展示；
    通过 `index` 字段确保上一章/下一章的正确排序，而不依赖主键自增ID。
    """
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='chapters', verbose_name="所属书籍")
    title = models.CharField(max_length=200, verbose_name="章节标题")
    content = models.TextField(verbose_name="章节内容")
    index = models.IntegerField(default=0, verbose_name="排序索引")
    volume_name = models.CharField(max_length=100, verbose_name="分卷名称", blank=True, null=True)

    def __str__(self):
        return f"{self.book.title} - {self.title}"

    class Meta:
        ordering = ['book', 'index']
        verbose_name = "章节"
        verbose_name_plural = verbose_name

class Illustration(models.Model):
    """
    插图模型 (Illustration)
    设计逻辑与 Chapter 类似，通过 `volume_name` 实现分卷，通过 `index` 字段排序。
    """
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='illustrations', verbose_name="所属书籍")
    image = models.ImageField(upload_to='illustrations/', verbose_name="插图")
    index = models.IntegerField(default=0, verbose_name="排序索引")
    volume_name = models.CharField(max_length=100, verbose_name="分卷名称", blank=True, null=True)

    def __str__(self):
        return f"{self.book.title} - {self.volume_name} - {self.index}"

    class Meta:
        ordering = ['book', 'index'] # 排序
        verbose_name = "插图"
        verbose_name_plural = verbose_name

class UserProgress(models.Model):
    """
    用户阅读进度模型 (UserProgress)
    每一个条目对应一位用户阅读一本书的进度。
    同时记录更新时间，用于书架中的排序。
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="用户")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, verbose_name="书籍")
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, verbose_name="当前章节")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    def __str__(self):
        return f"{self.user.username} - {self.book.title}"

    class Meta:
        unique_together = ('user', 'book')
        verbose_name = "阅读进度"
        verbose_name_plural = verbose_name

class Bookshelf(models.Model):
    """
    书架/收藏模型 (Bookshelf)
    管理用户收藏的书单列表，每一个条目对应一位用户加入书架的一本书。
    记录了加入时间，可以作为排序依据。（目前未使用）
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="用户")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, verbose_name="书籍")
    added_at = models.DateTimeField(auto_now_add=True, verbose_name="加入时间")

    def __str__(self):
        return f"{self.user.username} - {self.book.title}"

    class Meta:
        unique_together = ('user', 'book')
        verbose_name = "书架"
        verbose_name_plural = verbose_name
        ordering = ['-added_at']

class Bookmark(models.Model):
    """
    书签模型 (Bookmark)
    管理用户收藏的书签列表，每一个条目对应一位用户加入书签的一个章节。
    记录了加入时间，作为排序依据。
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="用户")
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, verbose_name="章节")
    added_at = models.DateTimeField(auto_now_add=True, verbose_name="加入时间")

    def __str__(self):
        return f"{self.user.username} - {self.chapter.book.title} - {self.chapter.title}"

    class Meta:
        unique_together = ('user', 'chapter')
        verbose_name = "书签"
        verbose_name_plural = verbose_name
        ordering = ['-added_at']

class GlobalSettings(models.Model):
    """
    系统全局设置 (GlobalSettings) - 【单例模式实现】
    用于控制站点的宏观行为：是否开放注册、是否需要邀请码等。
    """
    MODE_OPEN = 'open'
    MODE_INVITE = 'invite'
    MODE_CLOSED = 'closed'
    
    MODE_CHOICES = [
        (MODE_OPEN, '完全开放注册'),
        (MODE_INVITE, '仅凭邀请码注册'),
        (MODE_CLOSED, '关闭注册'),
    ]

    registration_mode = models.CharField(
        max_length=10, 
        choices=MODE_CHOICES, 
        default=MODE_OPEN, 
        verbose_name="注册模式"
    )
    
    invite_code = models.CharField(
        max_length=50, 
        blank=True, 
        default='888888', 
        verbose_name="邀请码 (仅在邀请模式下有效)"
    )

    class Meta:
        verbose_name = "系统设置"
        verbose_name_plural = verbose_name

    def __str__(self):
        return "全局系统设置"

    def save(self, *args, **kwargs):
        self.pk = 1
        super(GlobalSettings, self).save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj


class UserPoints(models.Model):
    """
    用户积分与等级模型 (UserPoints)
    用户经验、等级和签到系统。
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="用户")
    point = models.PositiveIntegerField(default=0, verbose_name="积分")
    exp = models.PositiveIntegerField(default=0, verbose_name="经验值")
    last_checkin_time = models.DateTimeField(default=timezone.now, verbose_name="上次签到时间")

    LEVEL_CHOICES = [
        ('LV0', '普通用户'),
        ('LV1', '黑铁会员'),
        ('LV2', '青铜会员'),
        ('LV3', '白银会员'),
        ('LV4', '黄金会员'),
        ('LV5', '铂金会员'),
        ('LV6', '钻石会员'),
    ]
    user_level = models.CharField(
        max_length=10, 
        choices=LEVEL_CHOICES, 
        default='LV0',  
        verbose_name="会员等级"
    )

    def __str__(self):
        return f"{self.user.username} - {self.get_user_level_display()}"
    
    @property
    def next_level_exp(self):
        if self.exp <= 20: return 20
        if self.exp <= 50: return 50
        if self.exp <= 100: return 100
        if self.exp <= 200: return 200
        if self.exp <= 350: return 350
        if self.exp <= 1000: return 1000
        return "Max"

    class Meta:
        verbose_name = "用户积分"
        verbose_name_plural = verbose_name