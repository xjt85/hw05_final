import shutil
import tempfile
from datetime import date

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Follow, Group, Post

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

User = get_user_model()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostViewsTests(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user1 = User.objects.create_user(username='TestUser1')
        cls.user2 = User.objects.create_user(username='TestUser2')
        cls.user3 = User.objects.create_user(username='TestUser3')
        cls.group0 = Group.objects.create(
            title='Тестовая группа',
            slug='group0',
            description='Группа 0',
        )
        cls.group1 = Group.objects.create(
            title='Тестовая группа',
            slug='group1',
            description='Группа 1',
        )

        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )

        cls.post0 = Post.objects.create(
            text='Текст тестового поста.',
            author=cls.user1,
            group=cls.group0,
            pub_date=date(2021, 10, 20),
            image=cls.uploaded
        )
        cls.post1 = Post.objects.create(
            text='Текст тестового поста.',
            author=cls.user2,
            group=cls.group1,
            pub_date=date(2021, 10, 22)
        )
        cls.post2 = Post.objects.create(
            text='Текст тестового поста.',
            author=cls.user1,
            group=cls.group0,
            pub_date=date(2021, 10, 24),
            image=cls.uploaded
        )
        cls.post3 = Post.objects.create(
            text='Текст тестового поста.',
            author=cls.user2,
            group=cls.group1,
            pub_date=date(2021, 10, 26)
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_user = Client()
        self.authorized_user3 = Client()
        self.authorized_user.force_login(self.user1)
        self.authorized_user3.force_login(self.user3)

    def test_pages_uses_correct_templates(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list', kwargs={'slug': self.group0.slug}):
            'posts/group_list.html',
            reverse('posts:profile', kwargs={'username': self.user1.username}):
            'posts/profile.html',
            reverse('posts:post_detail', kwargs={'post_id': self.post0.pk}):
            'posts/post_detail.html',
            reverse('posts:post_edit', kwargs={'post_id': self.post0.pk}):
            'posts/create_post.html',
            reverse('posts:create_post'): 'posts/create_post.html',
        }

        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_user.get(reverse_name)
                self.assertTemplateUsed(response, template, reverse_name)

    def test_index_page_show_correct_context(self):
        """Шаблон 'index' сформирован с правильным контекстом."""
        response = self.authorized_user.get(reverse('posts:index'))
        posts = response.context['page_obj']
        for post in posts:
            with self.subTest(post=post):
                post_from_db = Post.objects.get(pk=post.pk)
                self.assertEqual(post.pk, post_from_db.pk)
                self.assertEqual(post.text, post_from_db.text)
                self.assertEqual(post.author.username,
                                 post_from_db.author.username)
                self.assertEqual(post.group.slug,
                                 post_from_db.group.slug)
                if post_from_db.image:
                    self.assertEqual(post.image, post_from_db.image)

    def test_index_page_caching(self):
        """Проверка кэширования страницы 'index'"""
        response = self.authorized_user.get(reverse('posts:index'))
        content_before = response.content
        self.post3.delete()
        response = self.authorized_user.get(reverse('posts:index'))
        content_after = response.content
        self.assertEqual(content_after, content_before)

        cache.clear()
        response = self.authorized_user.get(reverse('posts:index'))
        content_after = len(response.content)
        self.assertNotEqual(content_after, content_before)

    def test_group_list_page_show_correct_context(self):
        """Шаблон 'group_list' сформирован с правильным контекстом."""
        response = self.authorized_user.get(
            reverse('posts:group_list', kwargs={'slug': self.group0.slug}))
        posts = response.context['page_obj']
        for post in posts:
            with self.subTest(post=post):
                # А здесь я лишь сверяю, что у каждого из выданных на странице
                # post_list постов нужная группа
                post_from_db = Post.objects.get(pk=post.pk)
                self.assertEqual(post.pk, post_from_db.pk)
                self.assertEqual(post.group.slug,
                                 post_from_db.group.slug)
                if post_from_db.image:
                    self.assertEqual(post.image, post_from_db.image)

    def test_profile_page_show_correct_context(self):
        """Шаблон 'profile/user' сформирован с правильным контекстом."""
        username = self.user1.username
        response = self.authorized_user.get(
            reverse('posts:profile', kwargs={'username': username}))
        posts = response.context['page_obj']
        for post in posts:
            with self.subTest(post=post):
                self.assertEqual(post.author.username, username)
                self.assertIsNotNone(post.group)
                post_from_db = Post.objects.get(pk=post.pk)
                if post_from_db.image:
                    self.assertEqual(post.image, post_from_db.image)

    def test_post_detail_page_show_correct_context(self):
        """Шаблон 'post_detail' сформирован с правильным контекстом."""
        response = self.authorized_user.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post0.pk}))
        post = response.context['post']
        self.assertEqual(post.pk, self.post0.pk)
        self.assertEqual(post.text, self.post0.text)
        self.assertEqual(post.author.username, self.post0.author.username)
        self.assertEqual(post.group.pk, self.post0.group.pk)
        self.assertEqual(post.pub_date, self.post0.pub_date)
        post_from_db = Post.objects.get(pk=post.pk)
        if post_from_db.image:
            self.assertEqual(post.image, post_from_db.image)

    def test_post_edit_page_show_correct_context(self):
        """Шаблон 'post_edit' сформирован с правильным контекстом."""
        response = self.authorized_user.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post0.pk}))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(
                    form_field, expected,
                    f'{form_field} в поле {value} '
                    f'не является экземпляром'
                    f' указанного класса.')

    def test_create_post_page_show_correct_context(self):
        """Шаблон 'create_post' сформирован с правильным контекстом."""
        response = self.authorized_user.get(reverse('posts:create_post'))

        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField
        }

        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(
                    form_field,
                    expected,
                    f'{form_field} в поле {value}'
                    f' не является экземпляром '
                    f'указанного класса.'
                )

    def test_follow_only_by_authorized(self):
        """Подписаться на авторов может только авторизованный пользователь."""
        follows_count = Follow.objects.filter(user=self.user1).count()
        self.authorized_user.get(reverse('posts:profile_follow',
                                 kwargs={'username': self.user2.username}))
        follows_count_after = Follow.objects.filter(user=self.user1).count()
        self.assertEqual(follows_count_after, follows_count + 1)

    def test_new_follow_viewed_only_by_follower(self):
        """Новые посты автора появляются в ленте только у подписчика."""
        following_user_posts_count = Post.objects.filter(
            author=self.user2.id).count()

        self.authorized_user.get(reverse('posts:profile_follow',
                                 kwargs={'username': self.user2.username}))

        Post.objects.create(
            text='Тест подписки.',
            author=self.user2,
            group=self.group1
        )

        response_follower = self.authorized_user.get(
            reverse('posts:follow_index'))
        response_nofollower = self.authorized_user3.get(
            reverse('posts:follow_index'))

        posts_list_lentgh_follower = len(
            response_follower.context['page_obj'])
        posts_list_lentgh_nofollower = len(
            response_nofollower.context['page_obj'])

        self.assertEqual(posts_list_lentgh_follower,
                         following_user_posts_count + 1)
        self.assertEqual(posts_list_lentgh_nofollower, 0)


class PaginatorViewsTest(TestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user1 = User.objects.create_user(username='TestUser1')
        cls.group0 = Group.objects.create(
            title='Тестовая группа',
            slug='group0',
            description='Группа 0',
        )
        # cls.posts = []
        # for i in range(13):
        #     cls.posts.append(Post(
        #         text='Текст тестового поста.',
        #         author=cls.user1,
        #         group=cls.group0
        #     ))

        # Post.objects.bulk_create(cls.posts)
        cls.posts = Post.objects.bulk_create(Post(
            text='Текст тестового поста.',
            author=cls.user1,
            group=cls.group0
        )
            for i in range(13))

    def setUp(self):
        self.unauthorized_user = Client()
        cache.clear()

    def test_first_page_contains_ten_records(self):
        """Паджинатор. Первая страница содержит 10 записей."""
        response = self.client.get(reverse('posts:index'))
        self.assertEqual(
            len(response.context['page_obj']), settings.POSTS_PER_PAGE)
        response = self.client.get(
            reverse('posts:group_list', kwargs={'slug': self.group0.slug}))
        self.assertEqual(
            len(response.context['page_obj']), settings.POSTS_PER_PAGE)
        response = self.client.get(reverse('posts:profile', kwargs={
                                   'username': self.user1.username}))
        self.assertEqual(
            len(response.context['page_obj']), settings.POSTS_PER_PAGE)

    def test_second_page_contains_three_records(self):
        """Паджинатор. Вторая страница содержит 3 записи."""
        page_number = 2
        posts_on_current_page = 3
        response = self.client.get(
            reverse('posts:index') + f'?page={page_number}')
        self.assertEqual(len(response.context['page_obj']),
                         posts_on_current_page)
        response = self.client.get(reverse('posts:group_list', kwargs={'slug':
                                   self.group0.slug}) + f'?page={page_number}')
        self.assertEqual(len(response.context['page_obj']),
                         posts_on_current_page)
        response = self.client.get(reverse('posts:profile',
                                   kwargs={'username': self.user1.username})
                                   + f'?page={page_number}')
        self.assertEqual(len(response.context['page_obj']),
                         posts_on_current_page)
