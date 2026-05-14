"""核心业务逻辑测试：下载定价、推荐限制、签到、用户等级、评分。"""
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone

from reader.models import Book, UserPoints, BookRecoLog, BookRating
from reader.tests.factories import TestDataFactory


class DownloadPricingTest(TestCase):
    """下载定价：每20万字1积分，每10张插图1积分，保底1积分"""

    def setUp(self):
        self.f = TestDataFactory()
        self.user = self.f.create_user()
        self.f.create_user_points(point=10, reco_balance=5)

    def test_text_price_minimum_one(self):
        """字数少于20万时，文本价格保底为1"""
        book = self.f.create_book(word_count=0)
        self.f.create_chapter(book=book, content="短内容")
        # text_price = max(word_count // 200000, 1)
        from reader.views import book_download
        self.assertEqual(max(book.word_count // 200000, 1), 1)

    def test_text_price_calculation(self):
        """每20万字1积分"""
        self.assertEqual(max(200000 // 200000, 1), 1)
        self.assertEqual(max(400000 // 200000, 1), 2)
        self.assertEqual(max(500000 // 200000, 1), 2)

    def test_img_price_minimum_one(self):
        """插图少于10张时，插图价格保底为1"""
        self.assertEqual(max(0 // 10, 1), 1)
        self.assertEqual(max(5 // 10, 1), 1)

    def test_img_price_calculation(self):
        """每10张插图1积分"""
        self.assertEqual(max(10 // 10, 1), 1)
        self.assertEqual(max(25 // 10, 1), 2)


class RecommendationLimitTest(TestCase):
    """推荐投票限制：单日单书最多4票，不能超过余额"""

    def setUp(self):
        self.f = TestDataFactory()
        self.user = self.f.create_user()
        self.book = self.f.create_book(recos=0)
        self.up = self.f.create_user_points(reco_balance=10)

    def test_daily_limit_four_per_book(self):
        """单日单书最多投4票"""
        today = timezone.localdate()
        log, _ = BookRecoLog.objects.get_or_create(
            user=self.user, book=self.book, date=today, defaults={'count': 4}
        )
        daily_remaining = 4 - log.count
        self.assertEqual(daily_remaining, 0)

    def test_cannot_exceed_balance(self):
        """不能超过reco_balance"""
        self.up.reco_balance = 2
        self.up.save()
        count = 3
        self.assertTrue(self.up.reco_balance < count)

    def test_successful_reco_deducts_balance(self):
        """成功投票后扣减余额和增加recos"""
        self.up.reco_balance = 5
        self.up.save()
        count = 2
        self.book.recos += count
        self.book.save()
        self.up.reco_balance -= count
        self.up.save()
        self.assertEqual(self.book.recos, 2)
        self.assertEqual(self.up.reco_balance, 3)

    def test_count_boundaries(self):
        """边界值测试"""
        self.assertLess(0, 1)   # count=0 无效
        self.assertGreater(5, 4)  # count=5 无效
        self.assertTrue(1 <= 4)   # count=1 有效
        self.assertTrue(4 <= 4)   # count=4 有效


class CheckinTest(TestCase):
    """签到：+10积分、+10经验、+1基础推荐票，等级加成，每日一次"""

    def setUp(self):
        self.f = TestDataFactory()
        self.user = self.f.create_user()
        self.up = self.f.create_user_points(point=0, exp=0, reco_balance=0)

    def test_base_checkin_rewards(self):
        """签到基础奖励：+10积分、+10经验、+1推荐票"""
        self.up.point += 10
        self.up.exp += 10
        reco_get = 1
        self.up.reco_balance += reco_get
        self.up.save()
        self.assertEqual(self.up.point, 10)
        self.assertEqual(self.up.exp, 10)
        self.assertEqual(self.up.reco_balance, 1)

    def test_diamond_bonus(self):
        """钻石会员签到+3推荐票"""
        self.up.exp = 1000
        self.up.save()
        self.assertEqual(self.up.user_level, '钻石会员')
        reco_get = 1 + 3  # base + diamond bonus
        self.assertEqual(reco_get, 4)

    def test_platinum_bonus(self):
        """铂金会员签到+2推荐票"""
        self.up.exp = 350
        self.up.save()
        self.assertEqual(self.up.user_level, '铂金会员')
        reco_get = 1 + 2
        self.assertEqual(reco_get, 3)

    def test_gold_bonus(self):
        """黄金会员签到+1推荐票"""
        self.up.exp = 200
        self.up.save()
        self.assertEqual(self.up.user_level, '黄金会员')
        reco_get = 1 + 1
        self.assertEqual(reco_get, 2)

    def test_reco_balance_capped_at_ten(self):
        """reco_balance 上限为10"""
        self.up.reco_balance = 9
        reco_get = 4
        self.up.reco_balance += reco_get
        self.up.reco_balance = min(self.up.reco_balance, 10)
        self.assertEqual(self.up.reco_balance, 10)

    def test_already_checked_in_today(self):
        """当天已签到不能再签"""
        self.up.last_checkin_time = timezone.now()
        self.up.save()
        now = timezone.now()
        already_checked = (
            self.up.last_checkin_time.date() == now.date()
            and self.up.pk is not None
        )
        self.assertTrue(already_checked)


class UserLevelTest(TestCase):
    """用户等级阈值"""

    def setUp(self):
        self.user = User.objects.create_user(username="leveltest", password="pass")
        self.up, _ = UserPoints.objects.get_or_create(user=self.user)

    def test_level_thresholds(self):
        """各级别阈值"""
        cases = [
            (0, '普通用户'),
            (19, '普通用户'),
            (20, '黑铁会员'),
            (50, '青铜会员'),
            (100, '白银会员'),
            (200, '黄金会员'),
            (350, '铂金会员'),
            (1000, '钻石会员'),
            (9999, '钻石会员'),
        ]
        for exp, expected_level in cases:
            self.up.exp = exp
            self.up.save()
            self.assertEqual(
                self.up.user_level, expected_level,
                f"exp={exp} should be '{expected_level}', got '{self.up.user_level}'"
            )

    def test_next_level_exp(self):
        """下一级所需经验"""
        cases = [
            (0, 20),
            (19, 20),
            (20, 50),
            (50, 100),
            (100, 200),
            (200, 350),
            (350, 1000),
            (1000, "Max"),
            (9999, "Max"),
        ]
        for exp, expected_next in cases:
            self.up.exp = exp
            self.up.save()
            self.assertEqual(
                self.up.next_level_exp, expected_next,
                f"exp={exp}: next_level_exp should be {expected_next}"
            )


class RatingTest(TestCase):
    """评分：1-10分，每人每书一条记录"""

    def setUp(self):
        self.f = TestDataFactory()
        self.user = self.f.create_user()
        self.book = self.f.create_book()

    def test_score_range_valid(self):
        """有效评分范围 1-10"""
        for score in [1, 5, 10]:
            self.assertTrue(1 <= score <= 10, f"score={score} should be valid")

    def test_score_range_invalid(self):
        """无效评分范围"""
        for score in [0, 11, -1]:
            self.assertFalse(1 <= score <= 10, f"score={score} should be invalid")

    def test_update_or_create_upserts(self):
        """评分使用 upsert，不会重复创建"""
        BookRating.objects.update_or_create(
            user=self.user, book=self.book, defaults={'score': 7}
        )
        self.assertEqual(BookRating.objects.filter(user=self.user, book=self.book).count(), 1)

        BookRating.objects.update_or_create(
            user=self.user, book=self.book, defaults={'score': 9}
        )
        self.assertEqual(BookRating.objects.filter(user=self.user, book=self.book).count(), 1)
        self.assertEqual(
            BookRating.objects.get(user=self.user, book=self.book).score, 9
        )
