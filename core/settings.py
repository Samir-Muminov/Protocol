# core/settings.py
import os
from pathlib import Path
import environ
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Environment ────────────────────────────────────────────────────────
env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

SECRET_KEY    = env('SECRET_KEY')
DEBUG         = env('DEBUG')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['127.0.0.1', 'localhost'])

# Auto-add Render hostname so you never need to hardcode it
RENDER_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_HOSTNAME)

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'protocol_app',
    'django_ratelimit',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
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

# ── Database (Supabase in production, SQLite locally) ─────────────────
# SECURITY: DATABASE_URL from environment — never hardcoded
db_config = dj_database_url.config(
    default=f'sqlite:///{BASE_DIR}/db.sqlite3',
    conn_max_age=600,
    ssl_require=not DEBUG,   # Supabase requires SSL; SQLite ignores it
)
DATABASES = {'default': db_config}

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
STATIC_URL       = '/static/'
STATIC_ROOT      = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'protocol_app' / 'static']

# FIX: STATICFILES_STORAGE is deprecated in Django 6 — use STORAGES instead
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL           = '/login/'
LOGIN_REDIRECT_URL  = '/'
LOGOUT_REDIRECT_URL = '/login/'

# ── Session security ───────────────────────────────────────────────────
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE              = 28800
SESSION_COOKIE_HTTPONLY         = True
SESSION_COOKIE_SECURE           = not DEBUG
SESSION_COOKIE_SAMESITE         = 'Lax'

# ── CSRF ───────────────────────────────────────────────────────────────
CSRF_COOKIE_HTTPONLY = False   # JS needs to read it for AJAX
CSRF_COOKIE_SECURE   = not DEBUG
CSRF_COOKIE_SAMESITE = 'Lax'

# ── Security headers ───────────────────────────────────────────────────
X_FRAME_OPTIONS                = 'DENY'
SECURE_SSL_REDIRECT            = not DEBUG
SECURE_HSTS_SECONDS            = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD            = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF    = True
SECURE_BROWSER_XSS_FILTER      = True

# ── Rate limiting ──────────────────────────────────────────────────────
RATELIMIT_USE_CACHE = 'default'
RATELIMIT_FAIL_OPEN = False

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# ── Logging ────────────────────────────────────────────────────────────
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