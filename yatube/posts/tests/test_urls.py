from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Group, Post

User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_author = User.objects.create_user(username='TestUserAuthor')
        cls.user = User.objects.create_user(username='TestUser')
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='test-slug',
            description='Тестовое описание'
        )
        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user_author
        )

    def setUp(self):
        self.authorized_user = Client()
        self.authorized_author = Client()
        self.authorized_user.force_login(self.user)
        self.authorized_author.force_login(self.user_author)

    def test_pages_authorized(self):
        urls_list = [
            '/',
            f'/group/{PostURLTests.group.slug}/',
            f'/profile/{PostURLTests.user.username}/',
            f'/posts/{PostURLTests.post.pk}/',
            f'/posts/{PostURLTests.post.pk}/edit/',
            '/create/'
        ]
        for url in urls_list:
            with self.subTest(url=url):
                response = self.authorized_author.get(url)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_pages_unauthorized(self):
        urls_list = [
            f'/posts/{PostURLTests.post.pk}/edit/',
            '/create/'
        ]
        for url in urls_list:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_post_edit_page_not_author(self):
        """Проверка доступности адреса /posts/post_id/edit/
        только автору поста"""
        response = self.authorized_user.get(f'/posts'
                                            f'/{PostURLTests.post.pk}/edit/')
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_add_comment_authorized(self):
        response = self.authorized_user.get(f'/posts/'
                                            f'{PostURLTests.post.pk}/comment/')
        self.assertRedirects(response, reverse('posts:post_detail',
                             kwargs={'post_id': PostURLTests.post.pk}))

    def test_add_comment_unauthorized(self):
        response = self.client.get(f'/posts/{PostURLTests.post.pk}/comment/')
        self.assertEqual(response.url, f'/auth/login/?next='
                         f'/posts/{PostURLTests.post.pk}/comment/')

    def test_unexisting_page(self):
        """Проверка перенаправления всех клиентов
        с несуществующей страницы на 404"""
        response = self.client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            '/': 'posts/index.html',
            f'/group/{PostURLTests.group.slug}/': 'posts/group_list.html',
            f'/profile/{PostURLTests.user.username}/': 'posts/profile.html',
            f'/posts/{PostURLTests.post.pk}/': 'posts/post_detail.html',
            f'/posts/{PostURLTests.post.pk}/edit/': 'posts/create_post.html',
            '/create/': 'posts/create_post.html',
            '/unexisting_page/': 'core/404.html',
        }
        for address, template in templates_url_names.items():
            with self.subTest(adress=address):
                response = self.authorized_author.get(address)
                self.assertTemplateUsed(response, template)
