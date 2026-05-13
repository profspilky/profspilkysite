/* Quill rich-text widget for Django admin.
 * Depends on quill.min.js (loaded before this file via Widget.Media).
 */
(function () {
    'use strict';

    function getCsrfToken() {
        const match = document.cookie
            .split(';')
            .map(function (c) { return c.trim(); })
            .find(function (c) { return c.startsWith('csrftoken='); });
        return match ? match.slice('csrftoken='.length) : '';
    }

    function setOverlay(wrapper, visible) {
        const overlay = wrapper.querySelector('.quill-upload-overlay');
        if (overlay) {
            overlay.classList.toggle('quill-upload-overlay--active', visible);
        }
    }

    function buildOverlay() {
        const el = document.createElement('div');
        el.className = 'quill-upload-overlay';
        el.innerHTML =
            '<div class="quill-upload-spinner"></div>' +
            '<span>Завантаження зображення\u2026</span>';
        return el;
    }

    function initQuill(wrapper) {
        if (wrapper._quillInit) return;
        wrapper._quillInit = true;

        const uploadUrl = wrapper.dataset.uploadUrl;
        const editorEl = wrapper.querySelector('.quill-editor');
        const textarea = wrapper.querySelector('.quill-textarea');

        if (!editorEl || !textarea) return;

        wrapper.appendChild(buildOverlay());

        var quill = new Quill(editorEl, {
            theme: 'snow',
            placeholder: 'Введіть текст статті\u2026',
            modules: {
                toolbar: {
                    container: [
                        [{ header: [2, 3, 4, false] }],
                        ['bold', 'italic', 'underline', 'strike'],
                        [{ list: 'ordered' }, { list: 'bullet' }],
                        ['blockquote', 'link', 'image'],
                        [{ align: [] }],
                        ['clean'],
                    ],
                    handlers: {
                        image: function () {
                            var self = this;
                            var input = document.createElement('input');
                            input.type = 'file';
                            input.accept = 'image/jpeg,image/png,image/webp,image/gif';
                            input.click();

                            input.addEventListener('change', function () {
                                var file = input.files[0];
                                if (!file) return;

                                setOverlay(wrapper, true);

                                var formData = new FormData();
                                formData.append('image', file);

                                fetch(uploadUrl, {
                                    method: 'POST',
                                    body: formData,
                                    headers: { 'X-CSRFToken': getCsrfToken() },
                                })
                                    .then(function (resp) {
                                        if (!resp.ok) {
                                            return resp.json().then(function (data) {
                                                throw new Error(
                                                    data.error || 'HTTP ' + resp.status
                                                );
                                            });
                                        }
                                        return resp.json();
                                    })
                                    .then(function (data) {
                                        if (data.url) {
                                            var range = quill.getSelection(true);
                                            quill.insertEmbed(
                                                range.index,
                                                'image',
                                                data.url,
                                                Quill.sources.USER
                                            );
                                            quill.setSelection(
                                                range.index + 1,
                                                Quill.sources.SILENT
                                            );
                                        }
                                    })
                                    .catch(function (err) {
                                        alert('Помилка завантаження: ' + err.message);
                                    })
                                    .finally(function () {
                                        setOverlay(wrapper, false);
                                    });
                            });
                        },
                    },
                },
            },
        });

        if (textarea.value.trim()) {
            quill.root.innerHTML = textarea.value;
        }

        function syncToTextarea() {
            var html = quill.root.innerHTML;
            textarea.value = html === '<p><br></p>' ? '' : html;
        }

        quill.on('text-change', syncToTextarea);

        var form = wrapper.closest('form');
        if (form) {
            form.addEventListener('submit', syncToTextarea);
        }
    }

    function initAll() {
        document.querySelectorAll('.quill-wrapper').forEach(initQuill);
    }

    function ready(fn) {
        if (typeof Quill === 'undefined') {
            var attempts = 0;
            var poll = setInterval(function () {
                attempts++;
                if (typeof Quill !== 'undefined') {
                    clearInterval(poll);
                    fn();
                } else if (attempts > 50) {
                    clearInterval(poll);
                    console.error('Quill.js failed to load within 5 s');
                }
            }, 100);
        } else if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', fn);
        } else {
            fn();
        }
    }

    ready(initAll);
})();
