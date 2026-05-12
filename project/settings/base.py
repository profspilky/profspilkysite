"""Base settings shared across environments.

Loads configuration from environment variables (.env in development,
real env vars on Render in production). NEVER hardcode secrets here.
"""
from __future__ import annotations

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    EMAIL_USE_TLS=(bool, True),
    SECURE_SSL_REDIRECT=(bool, False),
)

env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(str(env_file))

SECRET_KEY = env("SECRET_KEY", default="insecure-development-key-change-me")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

INSTALLED_APPS = [
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",

    "rest_framework",
    "tinymce",
    "cloudinary",
    "cloudinary_storage",

    "apps.core",
    "apps.news",
    "apps.pages",
    "apps.accounts",
    "apps.gallery",
    "apps.documents",
]

UNFOLD = {
    "SITE_TITLE": "Адмінпанель ФПУ",
    "SITE_HEADER": "Федерація Профспілок України",
    "SITE_SYMBOL": "shield_person",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": True,
    "COLORS": {
        "font": {
            "subtle-light": "107 114 128",
            "subtle-dark": "156 163 175",
            "default-light": "75 85 99",
            "default-dark": "209 213 219",
            "important-light": "17 24 39",
            "important-dark": "243 244 246",
        },
        "primary": {
            "50": "240 249 255",
            "100": "224 242 254",
            "200": "186 230 253",
            "300": "125 211 252",
            "400": "56 189 248",
            "500": "14 165 233",
            "600": "2 132 199",
            "700": "3 105 161",
            "800": "7 89 133",
            "900": "12 74 110",
            "950": "8 47 73",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": "Контент",
                "separator": False,
                "collapsible": False,
                "items": [
                    {
                        "title": "Новини",
                        "icon": "newspaper",
                        "link": "/admin/news/article/",
                    },
                    {
                        "title": "Категорії новин",
                        "icon": "label",
                        "link": "/admin/news/category/",
                    },
                    {
                        "title": "Статичні сторінки",
                        "icon": "article",
                        "link": "/admin/pages/staticpage/",
                    },
                ],
            },
            {
                "title": "Медіа",
                "separator": True,
                "collapsible": False,
                "items": [
                    {
                        "title": "Альбоми",
                        "icon": "photo_library",
                        "link": "/admin/gallery/galleryalbum/",
                    },
                    {
                        "title": "Фотографії",
                        "icon": "image",
                        "link": "/admin/gallery/galleryphoto/",
                    },
                ],
            },
            {
                "title": "Документи",
                "separator": True,
                "collapsible": False,
                "items": [
                    {
                        "title": "Документи",
                        "icon": "description",
                        "link": "/admin/documents/document/",
                    },
                    {
                        "title": "Категорії документів",
                        "icon": "folder",
                        "link": "/admin/documents/documentcategory/",
                    },
                ],
            },
            {
                "title": "Організація",
                "separator": True,
                "collapsible": False,
                "items": [
                    {
                        "title": "Пріоритети",
                        "icon": "star",
                        "link": "/admin/core/priority/",
                    },
                    {
                        "title": "Команда",
                        "icon": "group",
                        "link": "/admin/core/teammember/",
                    },
                    {
                        "title": "Членські організації",
                        "icon": "account_balance",
                        "link": "/admin/core/memberorganization/",
                    },
                    {
                        "title": "Налаштування сайту",
                        "icon": "settings",
                        "link": "/admin/core/sitesettings/",
                    },
                ],
            },
            {
                "title": "Конструктор сторінок",
                "separator": True,
                "collapsible": False,
                "items": [
                    {
                        "title": "Блоки сторінок",
                        "icon": "widgets",
                        "link": "/admin/core/pagesection/",
                    },
                ],
            },
            {
                "title": "Доступ",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "Користувачі",
                        "icon": "person",
                        "link": "/admin/auth/user/",
                    },
                    {
                        "title": "Групи",
                        "icon": "groups",
                        "link": "/admin/auth/group/",
                    },
                ],
            },
        ],
    },
}

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",
                "django.template.context_processors.static",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.site_chrome",
            ],
        },
    },
]

WSGI_APPLICATION = "project.wsgi.application"

DATABASES = {
    "default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
}

# TCP keepalive prevents Render Free Postgres from dropping SSL connections
# during long bulk operations (loaddata / load_fixtures with large fixtures).
if DATABASES["default"].get("ENGINE", "").endswith("psycopg2"):
    DATABASES["default"].setdefault("OPTIONS", {}).update({
        "keepalives": 1,
        "keepalives_idle": 60,
        "keepalives_interval": 10,
        "keepalives_count": 5,
    })

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "uk"
TIME_ZONE = "Europe/Kyiv"
USE_I18N = True
USE_TZ = True

LANGUAGES = [
    ("uk", "Українська"),
    ("en", "English"),
]
LOCALE_PATHS = [BASE_DIR / "locale"]

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CLOUDINARY_STORAGE = {
    "CLOUD_NAME": env("CLOUDINARY_CLOUD_NAME", default=""),
    "API_KEY": env("CLOUDINARY_API_KEY", default=""),
    "API_SECRET": env("CLOUDINARY_API_SECRET", default=""),
}
DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"
MEDIA_URL = "/media/"

# ── Cache ──────────────────────────────────────────────────────────────────────
# REDIS_URL береться з env (Render надає при підключенні Redis-сервісу).
# Без Redis падаємо на LocMemCache (dev/тести/перший деплой без Redis).
_redis_url = env("REDIS_URL", default="")
if _redis_url:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": _redis_url,
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = env("EMAIL_USE_TLS")
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="webmaster@localhost")

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {"handlers": ["console"], "level": "INFO"},
}
