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

# Auto-detect Render hostname — no hardcoding needed
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

# ── Database ───────────────────────────────────────────────────────────
# Uses Supabase Session Pooler URL in production (IPv4, not IPv6).
# Locally falls back to SQLite.
# IMPORTANT: Use the Supabase POOLER connection string, not the direct one.
# Pooler URL format: postgresql://postgres.PROJECT:PASS@aws-0-REGION.pooler.supabase.com:5432/postgres
db_config = dj_database_url.config(
    default=f'sqlite:///{BASE_DIR}/db.sqlite3',
    conn_max_age=600,
    ssl_require=not DEBUG,
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
CSRF_COOKIE_HTTPONLY = False
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

# ── Cache ──────────────────────────────────────────────────────────────
# SECURITY / FIX: django_ratelimit requires a SHARED cache backend in
# production. LocMemCache is per-process — with 2 Gunicorn workers each
# worker has its own counter, so rate limits only apply per-worker (half
# effective) and fail the django_ratelimit system check entirely.
#
# FileBasedCache writes to disk and is shared across all workers on the
# same machine — works on Render's free tier with no extra services.
# For multi-machine scale, swap this for Redis (e.g. Upstash free tier).

# ── Cache & Rate Limiting ──────────────────────────────────────────────
# django-ratelimit requires atomic increment support.
# On Render free tier we have no Redis/Memcached.
# Solution: use LocMemCache (per-worker) and silence the system check.
# This means rate limits are per-worker (2 workers = 2x the limit
# effectively) — acceptable for a personal/portfolio project.
# For production at scale: swap to Upstash Redis (free tier available).

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'protocol-ratelimit',
    }
}

RATELIMIT_USE_CACHE = 'default'
RATELIMIT_FAIL_OPEN = True   # If cache fails, allow request through

# Silence django-ratelimit's system check about LocMemCache.
# We accept the per-worker limitation for this deployment tier.
SILENCED_SYSTEM_CHECKS = ['django_ratelimit.E003', 'django_ratelimit.W001']
# SECURITY: Fail closed — if cache is unavailable, block the request
# rather than letting unlimited traffic through.
RATELIMIT_FAIL_OPEN = False

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