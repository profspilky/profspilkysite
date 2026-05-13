"""Custom form widgets for the news editor."""
from __future__ import annotations

from django.forms import Widget
from django.utils.html import escape
from django.utils.safestring import mark_safe

_QUILL_CSS_CDN = "https://cdn.quilljs.com/1.3.7/quill.snow.css"
_QUILL_JS_CDN = "https://cdn.quilljs.com/1.3.7/quill.min.js"

_UPLOAD_URL = "/admin/news/article/upload-image/"


class QuillBodyWidget(Widget):
    """Quill.js rich-text widget that syncs to a hidden textarea.

    Image uploads go to Cloudinary via the admin upload-image endpoint.
    """

    def render(
        self,
        name: str,
        value: str | None,
        attrs: dict | None = None,
        renderer=None,
    ) -> str:
        final_attrs = self.build_attrs(attrs or {}, {"name": name})
        widget_id = final_attrs.get("id", f"id_{name}")
        value_str = value or ""
        escaped = escape(value_str)

        return mark_safe(
            f'<div class="quill-wrapper"'
            f' id="wrapper_{widget_id}"'
            f' data-upload-url="{_UPLOAD_URL}"'
            f' data-field-id="{widget_id}">'
            f'<div id="quill_{widget_id}" class="quill-editor"></div>'
            f'<textarea id="{widget_id}" name="{name}"'
            f' class="quill-textarea">{escaped}</textarea>'
            f"</div>"
        )

    class Media:
        css = {
            "all": [
                _QUILL_CSS_CDN,
                "admin/css/quill_widget.css",
            ]
        }
        js = [
            _QUILL_JS_CDN,
            "admin/js/quill_widget.js",
        ]
