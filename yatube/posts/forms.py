from django import forms

from .models import Comment, Post


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ('text', 'group', 'image')
        labels = {
            'text': 'Текст',
            'group': 'Сообщество',
            'image': 'Картинка',
        }
        help_texts = {
            'text': 'Введите текст поста',
            'group': 'Укажите сообщество',
            'image': 'Добавьте картинку',
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('text',)
        labels = {
            'text': 'Текст',
        }
        help_texts = {
            'text': 'Введите текст комментария',
        }
