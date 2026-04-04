import json
from random import randint
from urllib.parse import unquote

from django.contrib import messages
from django.utils import timezone
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST

from .models import *
from .services import BookDownloadService


def get_recommend_books(booklist):
    if len(booklist) <= 4:
        return booklist
    
    rec = []
    weight = [(idx, (obj.recos + 0.1) * 10) for idx, obj in enumerate(booklist)]

    while len(rec) < 4:
        total = int(sum(w[1] for w in weight))
        big_int = randint(0, total)
        for i in range(len(weight)):
            idx, w = weight[i]
            big_int -= w
            if big_int <= 0:
                rec.append(booklist[idx])
                weight.pop(i)
                break
    return rec

def index(request):
    """
    处理首页的 GET 请求。
    功能：展示书籍列表（支持分页）、处理顶部搜索框的搜索请求、展示推荐书籍。
    """
    query = request.GET.get('q', '')
    if query:
        book_list = Book.objects.filter(
            Q(title__icontains=query) | 
            Q(author__icontains=query) |
            Q(tags__name__icontains=query)
        ).order_by('-created_at')
        is_search = True
        recommended_books = []
    else:
        book_list = Book.objects.all().order_by('-recos')
        # 推荐书籍取用逻辑：取前四本推荐书籍，若不满四本则从其他书籍中随机抽取，尽可能填满4本
        recommended_books = get_recommend_books(list(book_list))
        is_search = False

    paginator = Paginator(book_list, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj,  # 分页后的书籍列表
        'recommended_books': recommended_books,  # 推荐书籍
        'is_search': is_search,  # 是否处于搜索状态
        'search_query': query,  # 搜索词回填
    }
    return render(request, 'index.html', context)


def library(request):
    """
    图书馆页面。
    以卡片形式(类似bookshelf)列出所有书籍, 方便地加入书架、开始阅读。
    提供点选标签筛选书籍的功能。
    """
    tags = Tag.objects.all()
    books = Book.objects.all()

    query = request.GET.get('q', '').strip()
    tags_param = request.GET.get('tags', '').strip()
    selected_tags = [t for t in tags_param.split(',') if t]

    if query:
        books = books.filter(
            Q(title__icontains=query) | 
            Q(author__icontains=query) |
            Q(tags__name__icontains=query)
        ).distinct()

    for tag_name in selected_tags:
        books = books.filter(tags__name=tag_name)

    books = books.distinct()

    # 获取用户书架里的书籍ID，用于前端判断是否已在书架
    user_bookshelf_ids = []
    if request.user.is_authenticated:
        user_bookshelf_ids = Bookshelf.objects.filter(user=request.user).values_list('book_id', flat=True)

    context = {
        'books': books,
        'tags': tags,
        'search_query': query,
        'current_tag': selected_tags,
        'user_bookshelf_ids': user_bookshelf_ids,
    }
    return render(request, 'library.html', context)


def book_detail(request, book_id):
    """
    处理书籍详情页请求。
    功能：章节按卷分组、插图检查、获取阅读进度和是否在书架
    """
    book = get_object_or_404(Book, pk=book_id)
    query = request.GET.get('q', '')

    chapters = book.chapters.all().order_by('index')
    if query:
        chapters = chapters.filter(title__icontains=query)
    first_chapter = chapters.first()

    # 将章节按卷名分组
    volumes = {}
    grouped_chapters = []

    for chapter in chapters:
        vol_name = chapter.volume_name
        if vol_name not in volumes:
            volumes[vol_name] = []
        volumes[vol_name].append(chapter)

    for volume_name, chapter_list in volumes.items():
        # 检查插图
        has_illustration = (query in f"{volume_name} 插图") and Illustration.objects.filter(book=book,
                                                                                            volume_name=volume_name).exists()
        grouped_chapters.append({
            'volume_name': volume_name,
            'chapters': chapter_list,
            'has_illustration': has_illustration,
        })

    # 获取阅读进度
    progress = None
    if request.user.is_authenticated:
        try:
            progress = UserProgress.objects.get(user=request.user, book=book)
        except UserProgress.DoesNotExist:
            pass

    # 检查是否在书架
    in_bookshelf = False
    if request.user.is_authenticated:
        in_bookshelf = Bookshelf.objects.filter(user=request.user, book=book).exists()

    context = {
        'book': book,
        'grouped_chapters': grouped_chapters,
        'first_chapter': first_chapter,
        'progress': progress,
        'in_bookshelf': in_bookshelf,
        'search_query': query,
    }
    return render(request, 'book_detail.html', context)


@login_required
def book_download(request, book_id):
    """
    处理小说下载请求。
    功能：价格计算、积分校验、扣费。
    GET请求返回价格信息到前端, POST请求扣费并下载。
    """
    book = get_object_or_404(Book, pk=book_id)
    user_points, created = UserPoints.objects.get_or_create(user=request.user)

    # 计费规则：每 20 万字 1 积分，每 10 张插图 1 积分（保底 1 积分）
    text_price = max(book.word_count // 200000, 1)
    img_price = max(book.illustration_count // 10, 1)

    # 收到 POST 请求，表明用户确认支付并下载
    if request.method == 'POST':
        need_text = request.POST.get('need_text') == 'on' or book.illustration_count == 0
        need_img = request.POST.get('need_img') == 'on'
        if not (need_text or need_img):
            return JsonResponse({'status': 'fail', 'msg': '请至少选择一项下载内容！'})

        # 计算总金额、校验余额、扣费
        price = 0
        if need_text:
            price += text_price
        if need_img:
            price += img_price

        if user_points.point < price:
            return JsonResponse({'status': 'fail', 'msg': '积分不足！'})
        if price > 0:
            user_points.point -= price
            user_points.save()

        return BookDownloadService.generate_download_response(book, need_text=need_text, need_img=need_img)
    
    # 收到 GET 请求，返回价格信息给前端弹窗用
    return JsonResponse({
        'status': 'ok',
        'word_count': book.word_count,
        'illustration_count': book.illustration_count,
        'text_price': text_price,
        'img_price': img_price,
        'user_point': user_points.point
    })


@login_required
def book_reco(request, book_id):
    book = get_object_or_404(Book, pk=book_id)
    user_points, _ = UserPoints.objects.get_or_create(user=request.user)
    today = timezone.localdate()
    log, _ = BookRecoLog.objects.get_or_create(user=request.user, book=book, date=today)

    daily_remaining = 4 - log.count
    max_reco = min(user_points.reco_balance, daily_remaining)

    if request.method != 'POST':
        return JsonResponse({
            'status': 'ok',
            'user_recos': user_points.reco_balance,
            'cur_bookreco': book.recos,
            'daily_sent': log.count,
            'daily_remaining': daily_remaining,
            'max_reco': max_reco,
            'reco_able': max_reco > 0,
        })

    try:
        data = json.loads(request.body)
        count = int(data.get('count', 1))
    except (json.JSONDecodeError, ValueError, TypeError):
        count = 1

    if count < 1:
        return JsonResponse({'status': 'fail', 'msg': '推荐数量不能小于1！'})
    if count > 4:
        return JsonResponse({'status': 'fail', 'msg': '单次推荐不能超过4个！'})
    if user_points.reco_balance < count:
        return JsonResponse({'status': 'fail', 'msg': f'您的推荐次数不足，当前剩余 {user_points.reco_balance} 个。'})
    if daily_remaining < count:
        return JsonResponse({'status': 'fail', 'msg': f'今日对本书推荐已达上限，今日还可投 {daily_remaining} 个。'})

    book.recos += count
    book.save(update_fields=['recos'])
    user_points.reco_balance -= count
    user_points.save()
    log.count += count
    log.save()

    return JsonResponse({
        'status': 'ok',
        'msg': f'成功投出 {count} 个推荐！\n本书共获得 {book.recos} 个推荐。\n您当前剩余 {user_points.reco_balance} 次推荐机会。',
        'user_recos': user_points.reco_balance,
        'daily_remaining': 4 - log.count,
    })


def read_chapter(request, chapter_id):
    """
    处理阅读页面请求。
    功能：获取当前正文、下一章、上一章信息；保存阅读进度。
    """
    chapter = get_object_or_404(Chapter, pk=chapter_id)
    book = chapter.book

    # 保存进度 (仅登录时)
    is_bookmarked = False
    if request.user.is_authenticated:
        UserProgress.objects.update_or_create(
            user=request.user,
            book=book,
            defaults={'chapter': chapter}
        )
        is_bookmarked = Bookmark.objects.filter(user=request.user, chapter=chapter).exists()

    # 查找上一章和下一章
    prev_chapter = Chapter.objects.filter(
        book=book,
        index__lt=chapter.index
    ).order_by('-index').first()
    next_chapter = Chapter.objects.filter(
        book=book,
        index__gt=chapter.index
    ).order_by('index').first()

    context = {
        'book': book,
        'chapter': chapter,
        'prev_chapter': prev_chapter,
        'next_chapter': next_chapter,
        'is_bookmarked': is_bookmarked,
    }
    return render(request, 'read_chapter.html', context)


def view_illustration(request, book_id, volume_name):
    """
    处理插图页面请求。
    功能：展示某一分卷内的所有插图。
    """
    # URL 解码
    if volume_name == '_default_':
        volume_name = ""
    else:
        volume_name = unquote(volume_name)

    book = get_object_or_404(Book, pk=book_id)
    images = Illustration.objects.filter(book=book, volume_name=volume_name).order_by('index')

    context = {
        'book': book,
        'volume_name': volume_name,
        'images': images,
    }
    return render(request, 'illustration_gallery.html', context)


def signup(request):
    """
    用户注册视图，受 GlobalSettings (全站设置) 控制。
    """
    settings = GlobalSettings.load()
    mode = settings.registration_mode

    if mode == GlobalSettings.MODE_CLOSED:
        return render(request, 'signup_closed.html')

    # POST 请求为提交了注册表单，GET请求为访问页面
    if request.method == 'POST':
        form = UserCreationForm(request.POST)

        # 如果是邀请码模式，校验邀请码
        if mode == GlobalSettings.MODE_INVITE:
            user_code = request.POST.get('invite_code', '').strip()
            correct_code = settings.invite_code
            if user_code != correct_code:
                messages.error(request, "邀请码错误！")
                return render(request, 'signup.html', {
                    'form': form,
                    'mode': mode
                })

        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('index')
    else:
        form = UserCreationForm()

    return render(request, 'signup.html', {'form': form, 'mode': mode})


@login_required
def profile(request):
    user_points, created = UserPoints.objects.get_or_create(user=request.user)
    context = {
        'user': request.user,
        'user_points': user_points
    }
    return render(request, 'profile.html', context)


@login_required
@require_POST
def delete_account(request):
    user = request.user
    logout(request)
    user.delete()
    return redirect('index')


# 书架列表页
@login_required
def my_bookshelf(request):
    """
    用户书架视图。
    功能：展示加入书架的书籍和阅读进度、书签。
    """
    query = request.GET.get('q', '')

    # 获取用户书架记录
    shelf_items = Bookshelf.objects.filter(user=request.user).select_related('book').order_by('-added_at')
    mark_items = Bookmark.objects.filter(user=request.user).select_related('chapter').order_by('-added_at')

    if query:
        shelf_items = shelf_items.filter(
            Q(book__title__icontains=query) | 
            Q(book__author__icontains=query) |
            Q(book__tags__name__icontains=query)
        )
        mark_items = mark_items.filter(
            Q(chapter__book__title__icontains=query) |
            Q(chapter__book__author__icontains=query) |
            Q(chapter__title__icontains=query) |
            Q(chapter__book__tags__name__icontains=query)
        )

    # 查询阅读进度
    books_with_progress = []
    book_ids = [item.book_id for item in shelf_items]
    progresses = {p.book_id: p for p in UserProgress.objects.filter(user=request.user, book_id__in=book_ids)}
    for item in shelf_items:
        book = item.book
        progress = progresses.get(book.id)
        books_with_progress.append({
            'book': book,
            'progress': progress,
        })

    content = {
        'books': books_with_progress,
        'marks': mark_items,
        'search_query': query,
    }

    return render(request, 'bookshelf.html', content)


@login_required
def joinus(request):
    """
    joinus 视图。
    """
    if request.user.is_staff or request.user.is_superuser:
        return redirect('/admin/')
    application = StaffApplication.objects.filter(user=request.user).first()
    
    if request.method == 'POST':
        if application and application.status != 'rejected':
            messages.warning(request, "您已经提交过申请，请耐心等待管理员审批。")
            return redirect('index')
        reason = request.POST.get('reason', '').strip()
        
        if application:
            application.reason = reason
            application.status = 'pending'
            application.save()
        else:
            StaffApplication.objects.create(
                user=request.user,
                reason=reason,
                status='pending'
            )
        
        messages.success(request, "申请已提交！请等待管理员审批。")
        return redirect('index')
    
    context = {
        'has_applied': application is not None and application.status == 'pending'
    }
    return render(request, 'joinus.html', context)


# 加入/移出书架
@login_required
@require_POST
def toggle_bookshelf(request, book_id):
    """
    切换加入/移出书架状态（Toggle逻辑）。
    支持通过前端 AJAX 异步调用，或直接 HTML 表单提交。
    """
    book = get_object_or_404(Book, pk=book_id)
    shelf_item = Bookshelf.objects.filter(user=request.user, book=book).first()

    if shelf_item:
        shelf_item.delete()
        in_bookshelf = False
    else:
        Bookshelf.objects.create(user=request.user, book=book)
        in_bookshelf = True

    return JsonResponse({
        'status': 'success',
        'in_bookshelf': in_bookshelf,
        'msg': "已加入书架" if in_bookshelf else "已移出书架"
    })


@login_required
@require_POST
def toggle_bookmark(request, chapter_id):
    """
    切换加入/移出书签状态，逻辑与书架相同。
    """
    chapter = get_object_or_404(Chapter, pk=chapter_id)
    mark_item = Bookmark.objects.filter(user=request.user, chapter=chapter).first()

    if mark_item:
        mark_item.delete()
        in_bookmark = False
    else:
        Bookmark.objects.create(user=request.user, chapter=chapter)
        in_bookmark = True

    return JsonResponse({
        'status': 'success',
        'in_bookmark': in_bookmark,
        'msg': "已加入书签" if in_bookmark else "已移除书签"
    })


@login_required
@require_POST
def checkin(request):
    user_points, created = UserPoints.objects.get_or_create(user=request.user)

    now = timezone.now()
    if created or user_points.last_checkin_time.date() != now.date():
        user_points.point += 10
        user_points.exp += 10
        user_points.last_checkin_time = now

        reco_get = 1
        if user_points.user_level == '钻石会员':
            reco_get += 3
        elif user_points.user_level == '铂金会员':
            reco_get += 2
        elif user_points.user_level == '黄金会员':
            reco_get += 1

        user_points.reco_balance += reco_get
        user_points.reco_balance = min(user_points.reco_balance, 10)

        user_points.save()
        return JsonResponse({
            'status': 'success',
            'msg': f"""签到成功！积分+10，经验+10，推荐次数+{reco_get}
            当前等级：{user_points.user_level}
            当前推荐次数：{user_points.reco_balance}{' 已溢出!' if user_points.reco_balance >= 10 else ''}""",
            'current_point': user_points.point,
            'current_reco': user_points.reco_balance,
            'current_level_str': f"{user_points.user_level}({user_points.exp}/{user_points.next_level_exp})"
        })
    else:
        return JsonResponse({'status': 'fail', 'msg': '今天已经签到过了，明天再来吧！'})
