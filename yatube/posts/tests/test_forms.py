import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..forms import PostForm
from ..models import Comment, Group, Post

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

User = get_user_model()


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user1 = User.objects.create_user(username='testuser1')
        cls.group0 = Group.objects.create(
            title='Тестовая группа',
            slug='group0',
            description='Группа 0',
        )

        cls.post0 = Post.objects.create(
            text='Текст тестового поста.',
            author=cls.user1,
            group=cls.group0,
        )
        cls.form = PostForm()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_user = Client()
        self.authorized_user.force_login(self.user1)

    def test_create_form_makes_new_record(self):
        posts_count = Post.objects.count()

        form_data = {
            'text': 'Тестпост',
            'group': self.group0.pk
        }

        response = self.authorized_user.post(
            reverse('posts:create_post'),
            data=form_data,
            follow=True
        )

        self.assertRedirects(response, reverse('posts:profile',
                             kwargs={'username': self.user1.username}))
        self.assertEqual(Post.objects.count(), posts_count + 1)

        post = Post.objects.order_by('pk').last()
        post_text_value = getattr(post, 'text')
        post_group = getattr(post, 'group')

        self.assertEqual(post_text_value, form_data['text'])
        self.assertEqual(post_group.pk, form_data['group'])

    def test_create_form_with_img_makes_new_record(self):
        posts_count = Post.objects.count()

        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'text': 'Тестпост',
            'group': self.group0.pk,
            'image': uploaded
        }
        self.authorized_user.post(
            reverse('posts:create_post'),
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)

    def test_post_edit_changes_record(self):
        posts_count = Post.objects.count()

        form_data = {
            'text': 'Тестпост_изм',
            'group': self.group0.pk,
        }

        response = self.authorized_user.post(
            reverse('posts:post_edit', args={self.post0.pk}),
            data=form_data,
            follow=True
        )

        self.assertRedirects(response, reverse('posts:post_detail',
                             args={self.post0.pk}))
        self.assertEqual(Post.objects.count(), posts_count)

        post = Post.objects.get(pk=self.post0.pk)
        post_text_value = getattr(post, 'text')
        post_group = getattr(post, 'group')

        self.assertEqual(post_text_value, form_data['text'])
        self.assertEqual(post_group.pk, form_data['group'])

    def test_post_edit_unauthorized_user(self):
        form_data = {
            'text': 'Тестпост_изм',
            'group': self.group0.pk,
        }

        self.client.post(
            reverse('posts:post_edit', args={self.post0.pk}),
            data=form_data,
            follow=True
        )

        post = Post.objects.get(pk=self.post0.pk)
        post_text_value = getattr(post, 'text')
        post_group = getattr(post, 'group')

        self.assertNotEqual(post_text_value, form_data['text'])
        self.assertNotEqual(post_group, form_data['group'])

    def test_post_create_unauthorized_user(self):
        posts_count = Post.objects.count()

        form_data = {
            'text': 'Тестпост_изм',
            'group': self.group0.pk,
        }

        self.client.post(
            reverse('posts:create_post'),
            data=form_data,
            follow=True
        )

        self.assertEqual(Post.objects.count(), posts_count)

    def test_add_comment_form_makes_new_record(self):
        comments_count_before = (Comment.objects.filter
                                 (post=self.post0.pk).count())
        comment_form_data = {
            'text': 'Тестовый комментарий',
        }
        self.authorized_user.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post0.pk}),
            data=comment_form_data,
            follow=True
        )
        comments_count_after = Comment.objects.filter(post=self.post0).count()
        # проверка того, что количество комментариев увеличилось на 1
        self.assertEqual(comments_count_after, comments_count_before + 1)
        response = self.authorized_user.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post0.pk}))
        comment = response.context['comments'][0]
        # проверка того, что текст добавленного комментария соответствует
        # отправленному в форме
        self.assertEqual(comment.text, comment_form_data['text'])
