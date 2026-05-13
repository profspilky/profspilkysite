"""Admin forms for the news app."""
from __future__ import annotations

from django import forms

from .models import Article
from .widgets import QuillBodyWidget


class ArticleAdminForm(forms.ModelForm):
    """ModelForm for Article with a Quill rich-text editor on the body field."""

    body = forms.CharField(
        widget=QuillBodyWidget(),
        required=False,
        label="Повний текст",
    )

    class Meta:
        model = Article
        fields = "__all__"
