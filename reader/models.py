from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Tag(models.Model):
    """
    标签模型 (Tag)  
    记录当前存在的所有小说标签。
    
    字段说明：
    - `name` (CharField): 标签名, 最大长度50。
    """
    name = models.CharField(max_length=50, unique=True, verbose_name="标签名称")
    def __str__(self):
        return self.name
    class Meta:
        verbose_name = "标签"
        verbose_name_plural = verbose_name


class Book(models.Model):
    """
    书籍模型 (Book)  
    记录小说的元数据。
    
    字段说明：
    - `title` (CharField): 书名, 最大长度200。
    - `author` (CharField): 作者名, 最大长度100, 默认"未知"。
    - `cover` (ImageField): 封面图片, 上传至'covers/'目录, 允许为空。
    - `description` (TextField): 小说简介说明, 允许为空。
    - `tags` (ManyToManyField): 作品标签, 允许为空。
    - `word_count` (PositiveIntegerField): 总字数, 由信号机制自动统计, 默认0。
    - `illustration_count` (PositiveIntegerField): 插图数量, 由信号机制自动统计, 默认0。
    - `recos` (PositiveIntegerField): 推荐数, 这本书收到的推荐数量。
    - `created_at` (DateTimeField): 收录时间, 每次保存自动更新。
    - `uploader` (ForeignKey to User): 上传该书的员工/管理员, 用于API的权限验证。允许为空, 级联设置为NULL。
    """
    title = models.CharField(max_length=200, verbose_name="书名")
    author = models.CharField(max_length=100, verbose_name="作者", default="未知")
    cover = models.ImageField(upload_to='covers/', verbose_name="封面", blank=True, null=True)
    description = models.TextField(verbose_name="简介", blank=True)
    tags = models.ManyToManyField(Tag, verbose_name="标签", blank=True)

    # 统计字段 (由 Chapter 和 Illustration 的 save() 钩子自动维护)
    word_count = models.PositiveIntegerField(default=0, verbose_name="总字数")
    illustration_count = models.PositiveIntegerField(default=0, verbose_name="插图数量")

    recos = models.PositiveIntegerField(default=0, verbose_name="Reco数")
    created_at = models.DateTimeField(auto_now=True, verbose_name="收录时间")
    uploader = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="上传者")

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at', '-recos']
        verbose_name = "小说"
        verbose_name_plural = verbose_name


class Chapter(models.Model):
    """
    章节模型 (Chapter)  
    通过 `index` 字段排序章节, 而不依赖主键自增ID。

    字段说明：
    - `book` (ForeignKey to Book): 所属书籍, 级联删除。反向查询名为'chapters'。
    - `title` (CharField): 章节标题, 最大长度200。
    - `content` (TextField): 章节正文文本。
    - `index` (IntegerField): 章节排序索引。
    - `volume_name` (CharField): 分卷名称, 用于目录分组, 允许为空。
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

    字段说明：
    - `book` (ForeignKey to Book): 所属书籍, 级联删除。反向查询名为'illustrations'。
    - `image` (ImageField): 插图文件, 上传至'illustrations/'目录。
    - `index` (IntegerField): 插图排序索引。
    - `volume_name` (CharField): 分卷名称, 用于目录分组, 允许为空。
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
    记录更新时间, 用于书架中的排序。

    字段说明：
    - `user` (ForeignKey to User): 对应的系统用户, 级联删除。
    - `book` (ForeignKey to Book): 用户正在阅读的书籍, 级联删除。
    - `chapter` (ForeignKey to Chapter): 用户读到的最新章节, 级联删除。
    - `updated_at` (DateTimeField): 更新时间, 每次阅读新章节时自动更新, 用于书架按最近阅读排序。
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
    管理用户收藏的书单列表, 每一个条目对应一位用户加入书架的一本书。

    字段说明：
    - `user` (ForeignKey to User): 收藏该书的用户, 级联删除。
    - `book` (ForeignKey to Book): 被收藏的书籍, 级联删除。
    - `added_at` (DateTimeField): 加入时间, 自动生成, 可作为列表排序依据（目前未采用）。
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
    管理用户收藏的书签列表, 每一个条目对应一位用户加入书签的一个章节。

    字段说明：
    - `user` (ForeignKey to User): 添加书签的用户, 级联删除。
    - `chapter` (ForeignKey to Chapter): 被标记为书签的具体章节, 级联删除。
    - `added_at` (DateTimeField): 书签加入时间, 作为列表排序依据。
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
    重写了 save() 方法, 强制主键 pk=1, 保证整个数据库仅存一条记录。

    字段说明：
    - `registration_mode` (CharField): 注册模式控制开关, 选项见 MODE_CHOICES (`'open'`/`'invite'`/`'closed'`)。
    - `invite_code` (CharField): 邀请码文本, 最大长度50, 仅在邀请模式下生效。
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
    管理用户的经验、等级和签到系统信息, 与用户模型是一对一关系。

    字段说明：
    - `user` (OneToOneField to User): 绑定的系统用户, 级联删除。
    - `point` (PositiveIntegerField): 积分, 可用于消费/兑换, 默认0。
    - `exp` (PositiveIntegerField): 经验值, 决定用户等级, 只增不减, 默认0。
    - `reco_balance` (PositiveIntegerField): 推荐数, 当前用户拥有的推荐数量。
    - `last_checkin_time` (DateTimeField): 上次签到时间, 用于校验每日签到状态。
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="用户")
    point = models.PositiveIntegerField(default=0, verbose_name="积分")
    exp = models.PositiveIntegerField(default=0, verbose_name="经验值")
    reco_balance = models.PositiveIntegerField(default=0, verbose_name="Recos")
    last_checkin_time = models.DateTimeField(default=timezone.now, verbose_name="上次签到时间")

    def __str__(self):
        return f"{self.user.username} - {self.user_level}"
    
    @property
    def user_level(self):
        if self.exp >= 1000: return '钻石会员'
        elif self.exp >= 350: return '铂金会员'
        elif self.exp >= 200: return '黄金会员'
        elif self.exp >= 100: return '白银会员'
        elif self.exp >= 50: return '青铜会员'
        elif self.exp >= 20: return '黑铁会员'
        return '普通用户'

    @property
    def next_level_exp(self):
        if self.exp < 20: return 20
        if self.exp < 50: return 50
        if self.exp < 100: return 100
        if self.exp < 200: return 200
        if self.exp < 350: return 350
        if self.exp < 1000: return 1000
        return "Max"

    class Meta:
        verbose_name = "用户积分"
        verbose_name_plural = verbose_name


class StaffApplication(models.Model):
    """
    员工申请 (StaffApplication)
    管理普通用户成为Staff的申请。

    字段说明：
    - `user` (OneToOneField to User): 绑定的系统用户, 级联删除。
    - `reason` (TextField): 申请理由, 允许为空。
    - `status` (CharField): 申请状态, 绑定到选项列表 STATUS_CHOICES
    - `created_at` (DateTimeField): 申请时间。
    """
    STATUS_CHOICES = [
        ('pending', '待审批'),
        ('approved', '已通过'),
        ('rejected', '已拒绝'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="申请用户")
    reason = models.TextField(verbose_name="申请理由", blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="状态")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="申请时间")
    
    class Meta:
        verbose_name = "Staff 申请"
        verbose_name_plural = verbose_name
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} 的申请"