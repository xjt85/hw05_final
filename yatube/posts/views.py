from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CommentForm, PostForm
from .models import Comment, Follow, Group, Post, User


def index(request):
    template = 'posts/index.html'
    posts = cache.get('index_page')
    if posts is None:
        posts = Post.objects.all() # замечание 1. Использовать select_related()
        cache.set('index_page', posts, timeout=20)
    paginator = Paginator(posts, settings.POSTS_PER_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj,
        'index': True
    }
    return render(request, template, context)


def group_list(request, slug):
    template = 'posts/group_list.html'
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.all()
    paginator = Paginator(posts, settings.POSTS_PER_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'group': group,
        'page_obj': page_obj
    }
    return render(request, template, context)


def profile(request, username):
    author = get_object_or_404(User, username=username)
    current_user = request.user

    if current_user.is_authenticated:
        following = current_user.follower.filter(author=author).exists()
    else:
        following = False

    posts = Post.objects.filter(author=author.id)
    posts_count = posts.count()

    paginator = Paginator(posts, settings.POSTS_PER_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'author': author,
        'page_obj': page_obj,
        'posts_count': posts_count,
        'following': following
    }

    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    comments = Comment.objects.filter(post=post)
    author = post.author
    author_posts_count = Post.objects.filter(author=post.author).count()
    form = CommentForm(request.POST or None)

    context = {
        'post': post,
        'author': author,
        'author_posts_count': author_posts_count,
        'form': form,
        'comments': comments
    }

    return render(request, 'posts/post_detail.html', context)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def post_create(request):
    author = request.user
    form = PostForm(
        request.POST or None,
        files=request.FILES or None
    )

    if form.is_valid():
        form.instance.author = author
        form.save()
        return redirect('posts:profile', author)

    context = {
        'form': form,
        'is_edit': False
    }

    return render(request, 'posts/create_post.html', context)


@login_required
def post_edit(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if post.author == request.user:
        form = PostForm(
            request.POST or None,
            files=request.FILES or None,
            instance=post
        )

        if request.method == 'POST' and form.is_valid():
            form.save()
            return redirect('posts:post_detail', post_id)

        context = {
            'form': form,
            'is_edit': True
        }

        return render(request, 'posts/create_post.html', context)

    return redirect('posts:post_detail', post_id)


@login_required
def follow_index(request):
    posts = Post.objects.filter(author__following__user=request.user)
    paginator = Paginator(posts, settings.POSTS_PER_PAGE)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'follow': True
    }

    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    is_following_exists = Follow.objects.filter(author=author).exists()
    if author != request.user and not is_following_exists:  # замечание 2. Использовать get_or_create()
        Follow.objects.create(user=request.user, author=author)
    return redirect('posts:profile', username)


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    Follow.objects.filter(user=request.user, author=author).delete()
    return redirect('posts:profile', username)
