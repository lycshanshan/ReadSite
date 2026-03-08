from django.db import models
from django.contrib.auth.models import User # 导入Django自带的用户模型
from django.utils import timezone

# 1. 书籍模型
class Book(models.Model):
    title = models.CharField(max_length=200, verbose_name="书名")
    author = models.CharField(max_length=100, verbose_name="作者", default="未知")
    # 封面图片，upload_to会自动把图片存到 media/covers 目录下
    cover = models.ImageField(upload_to='covers/', verbose_name="封面", blank=True, null=True)
    description = models.TextField(verbose_name="简介", blank=True)
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

# 2. 章节模型
class Chapter(models.Model):
    # 关联到 Book，如果书被删了，章节也自动删除 (CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='chapters', verbose_name="所属书籍")
    
    title = models.CharField(max_length=200, verbose_name="章节标题")
    content = models.TextField(verbose_name="章节内容")
    
    # 排序索引：用于确定章节的先后顺序。你的txt文件名是数字，我们导入时就把那个数字存到这里
    index = models.IntegerField(default=0, verbose_name="排序索引")

    # 分卷名称; 如果为空，说明这本书没有分卷。
    volume_name = models.CharField(max_length=100, verbose_name="分卷名称", blank=True, null=True)

    def __str__(self):
        return f"{self.book.title} - {self.title}"
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:
            self.book.word_count += len(self.content)
            self.book.save()

    class Meta:
        ordering = ['book', 'index'] # 排序
        verbose_name = "章节"
        verbose_name_plural = verbose_name

# 5. 插图模型
class Illustration(models.Model):
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='illustrations', verbose_name="所属书籍")
    # 图片文件
    image = models.ImageField(upload_to='illustrations/', verbose_name="插图")
    # 索引：用于在一卷内部排序图片 (1, 2, 3...)
    index = models.IntegerField(default=0, verbose_name="排序索引")
    # 分卷名称：用于确定这张图属于哪一卷
    volume_name = models.CharField(max_length=100, verbose_name="分卷名称", blank=True, null=True)

    def __str__(self):
        return f"{self.book.title} - {self.volume_name} - {self.index}"
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new:
            self.book.illustration_count += 1
            self.book.save()

    class Meta:
        ordering = ['book', 'index'] # 排序
        verbose_name = "插图"
        verbose_name_plural = verbose_name

# 3. 阅读进度模型
class UserProgress(models.Model):
    # 关联用户和书籍
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="用户")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, verbose_name="书籍")
    
    # 记录当前读到了哪一章
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, verbose_name="当前章节")
    
    # 最后阅读时间，用于以后在书架按时间排序
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    def __str__(self):
        return f"{self.user.username} - {self.book.title}"

    class Meta:
        # 确保同一个用户对同一本书，只能有一条进度记录
        unique_together = ('user', 'book')
        verbose_name = "阅读进度"
        verbose_name_plural = verbose_name

# 4. 书架模型
class Bookshelf(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="用户")
    book = models.ForeignKey(Book, on_delete=models.CASCADE, verbose_name="书籍")
    added_at = models.DateTimeField(auto_now_add=True, verbose_name="加入时间")

    def __str__(self):
        return f"{self.user.username} - {self.book.title}"

    class Meta:
        unique_together = ('user', 'book') # 防止重复收藏
        verbose_name = "书架"
        verbose_name_plural = verbose_name
        ordering = ['-added_at'] # 新加入的在前面

class Bookmark(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="用户")
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, verbose_name="章节")
    added_at = models.DateTimeField(auto_now_add=True, verbose_name="加入时间")

    def __str__(self):
        return f"{self.user.username} - {self.chapter.book.title} - {self.chapter.title}"

    class Meta:
        unique_together = ('user', 'chapter') # 防止重复收藏
        verbose_name = "书签"
        verbose_name_plural = verbose_name
        ordering = ['-added_at'] # 新加入的在前面

# 6. 全局设置模型 (单例)
class GlobalSettings(models.Model):
    # 定义选项
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

    # 单例模式的小技巧：重写 save 方法，确保ID永远是1
    def save(self, *args, **kwargs):
        self.pk = 1
        super(GlobalSettings, self).save(*args, **kwargs)

    # 方便获取当前单例的方法
    @classmethod
    def load(cls):
        obj, created = cls.objects.get_or_create(pk=1)
        return obj


class UserPoints(models.Model):
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