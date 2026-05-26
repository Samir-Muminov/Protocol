# core/settings.py
# SECURITY: All secrets loaded from environment variables via django-environ
# Never hardcode SECRET_KEY, DATABASE_URL, or DEBUG in this file

import os
from pathlib import Path
import environ

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Environment variables ──────────────────────────────────────────────
# SECURITY: django-environ reads from .env file locally,
# and from real env vars in production (Render, Railway, etc.)
# ── Environment variables ──────────────────────────────────────────────
env = environ.Env(
    DEBUG=(bool, False),
)

# Read .env file if it exists
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')

# ГИБКИЙ ALLOWED_HOSTS:
# Если мы на Render, он возьмет адрес из переменной окружения,
# если нет — разрешит localhost
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['127.0.0.1', 'localhost'])

# Если мы в продакшене (Render), добавляем адрес сайта принудительно
if not DEBUG:
    ALLOWED_HOSTS.append('protocol-06sy.onrender.com')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'protocol_app',
    # SECURITY: rate limiting middleware
    'django_ratelimit',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # SECURITY: WhiteNoise serves static files securely in production
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'core.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'protocol_app' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.protocol_context.protocol_quote',
            ],
        },
    },
]

WSGI_APPLICATION = 'core.wsgi.application'

# ── Database ───────────────────────────────────────────────────────────
# SECURITY: DATABASE_URL from env — never hardcode credentials
# DATABASES = {
#     'default': env.db('DATABASE_URL', default=f'sqlite:///{BASE_DIR}/db.sqlite3')
# }

# ── Password validation ────────────────────────────────────────────────
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
     'OPTIONS': {'min_length': 8}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ── Localization ───────────────────────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE     = 'Asia/Tashkent'
USE_I18N      = True
USE_TZ        = True

# ── Static files ───────────────────────────────────────────────────────
STATIC_URL  = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'protocol_app' / 'static']
# SECURITY: WhiteNoise compressed static files
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL          = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL= '/login/'

# ── Session security ───────────────────────────────────────────────────
# SECURITY: Sessions expire on browser close, 8h max
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE              = 28800
SESSION_COOKIE_HTTPONLY         = True
# SECURITY: Set True in production (requires HTTPS)
SESSION_COOKIE_SECURE           = not DEBUG
SESSION_COOKIE_SAMESITE         = 'Lax'

# ── CSRF ───────────────────────────────────────────────────────────────
# SECURITY: CSRF cookie not accessible via JS
CSRF_COOKIE_HTTPONLY = False  # Must be False — JS reads it for AJAX
CSRF_COOKIE_SECURE   = not DEBUG
CSRF_COOKIE_SAMESITE = 'Lax'

# ── Security headers ───────────────────────────────────────────────────
# SECURITY: Prevent clickjacking
X_FRAME_OPTIONS = 'DENY'
# SECURITY: Force HTTPS in production
SECURE_SSL_REDIRECT              = not DEBUG
SECURE_HSTS_SECONDS              = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS   = not DEBUG
SECURE_HSTS_PRELOAD              = not DEBUG
# SECURITY: Prevent MIME-type sniffing
SECURE_CONTENT_TYPE_NOSNIFF      = True
# SECURITY: XSS protection header
SECURE_BROWSER_XSS_FILTER        = True

# ── Rate limiting defaults ─────────────────────────────────────────────
# SECURITY: Global defaults — overridden per-view as needed
RATELIMIT_USE_CACHE = 'default'
RATELIMIT_FAIL_OPEN = False  # Block if cache is down (safe default)

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# ── Logging ────────────────────────────────────────────────────────────
# SECURITY: Log security events without exposing secrets
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django.security': {
            'handlers': ['console'],
            'level': 'WARNING',
            'propagate': True,
        },
        'protocol_app': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
# /* PATH: Supabase — enforce SSL on database connection */
# SECURITY: Supabase rejects non-SSL connections in production
import dj_database_url

db_config = dj_database_url.config(
    default=env('DATABASE_URL', default=f'sqlite:///{BASE_DIR}/db.sqlite3'),
    conn_max_age=600,
)

# Add SSL requirement for Supabase (any non-SQLite connection)
if db_config.get('ENGINE') != 'django.db.backends.sqlite3':
    db_config.setdefault('OPTIONS', {})
    db_config['OPTIONS']['sslmode'] = 'require'

DATABASES = {'default': db_config}