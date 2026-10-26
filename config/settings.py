"""
Django settings for PlomApp backend.

Replicates the configuration of the original Flask application:
- Database resolution: DATABASE_URL | Postgres env vars | MySQL env vars | SQLite fallback
- JWT auth (HS256, identity stored as string "sub") compatible with the React frontend
- CORS wide open for /api/* like Flask-CORS resources={r"/api/*": {"origins": "*"}}
- SMTP (Zoho) email sending
- Uploaded evidence photos served from /static/uploads/evidence/<file>

IMPORTANT: This project intentionally does NOT use django.contrib.admin/auth
so the database schema stays 1:1 with the original Flask/SQLAlchemy schema
(same tables, same columns) and can point at the existing `plomapp` database
without conflicts. Authentication is 100% JWT, like the Flask version.
"""
import os
import sys
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env from project root (same behavior as Flask's load_dotenv())
load_dotenv(BASE_DIR / '.env')


def _env_bool(name, default=False):
    """Lee una variable de entorno booleana (1/true/yes/on)."""
    return os.getenv(name, str(default)).lower() in {'1', 'true', 'yes', 'on'}

# --------------------------------------------------------------------------- #
# Core
# --------------------------------------------------------------------------- #
SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
DEBUG = os.getenv('DEBUG', 'True').lower() in {'1', 'true', 'yes', 'on'}
ALLOWED_HOSTS = [h.strip() for h in os.getenv('ALLOWED_HOSTS', '*').split(',') if h.strip()]

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.staticfiles',
    'api',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware',
    'api.middleware.JSONErrorMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# --------------------------------------------------------------------------- #
# Database (same resolution logic as app/config/__init__.py in Flask)
# --------------------------------------------------------------------------- #
def _build_database():
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        url = database_url
        for prefix, replacement in (
            ('postgres://', 'postgresql://'),
            ('postgresql+psycopg2://', 'postgresql://'),
            ('postgresql+asyncpg://', 'postgresql://'),
            ('mysql+pymysql://', 'mysql://'),
        ):
            if url.startswith(prefix):
                url = url.replace(prefix, replacement, 1)
                break
        if url.startswith('postgresql://'):
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': (parsed.path or '/').lstrip('/') or 'plomapp',
                'USER': parsed.username or 'postgres',
                'PASSWORD': parsed.password or '',
                'HOST': parsed.hostname or 'localhost',
                'PORT': str(parsed.port or 5432),
                'CONN_MAX_AGE': 60,
            }
        if url.startswith('mysql://'):
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return {
                'ENGINE': 'django.db.backends.mysql',
                'NAME': (parsed.path or '/').lstrip('/') or 'plomapp',
                'USER': parsed.username or 'root',
                'PASSWORD': parsed.password or '',
                'HOST': parsed.hostname or 'localhost',
                'PORT': str(parsed.port or 3306),
            }
        if url.startswith('sqlite'):
            return {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': BASE_DIR / 'db.sqlite3',
            }

    db_engine = os.getenv('DB_ENGINE', 'mysql').lower()
    if db_engine in ('postgres', 'postgresql') or os.getenv('POSTGRES_DB'):
        return {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('POSTGRES_DB', 'plomapp'),
            'USER': os.getenv('POSTGRES_USER', 'postgres'),
            'PASSWORD': os.getenv('POSTGRES_PASSWORD', ''),
            'HOST': os.getenv('POSTGRES_HOST', 'localhost'),
            'PORT': os.getenv('POSTGRES_PORT', '5432'),
            'CONN_MAX_AGE': 60,
        }

    if db_engine == 'sqlite':
        return {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }

    return {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('MYSQL_DB', 'plomapp'),
        'USER': os.getenv('MYSQL_USER', 'root'),
        'PASSWORD': os.getenv('MYSQL_PASSWORD', 'password'),
        'HOST': os.getenv('MYSQL_HOST', 'localhost'),
        'PORT': os.getenv('MYSQL_PORT', '3306'),
        'OPTIONS': {'charset': 'utf8mb4'},
    }


DATABASES = {'default': _build_database()}

# Tests: run on in-memory SQLite by default so the suite works without a
# live PostgreSQL/MySQL. Set TEST_USE_CONFIGURED_DB=1 to test against the
# configured production database instead (Django will create test_<db>).
if 'test' in sys.argv and os.getenv(
    'TEST_USE_CONFIGURED_DB', ''
).lower() not in {'1', 'true', 'yes', 'on'}:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
        }
    }

# --------------------------------------------------------------------------- #
# Internationalization
# --------------------------------------------------------------------------- #
LANGUAGE_CODE = 'es-co'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = False  # Store naive UTC datetimes, like the Flask/SQLAlchemy version

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static'] if (BASE_DIR / 'static').exists() else []

MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

# --------------------------------------------------------------------------- #
# CORS (Flask-CORS allowed any origin on /api/*)
# --------------------------------------------------------------------------- #
CORS_ALLOW_ALL_ORIGINS = os.getenv('CORS_ALLOW_ALL_ORIGINS', 'True').lower() in {'1', 'true', 'yes', 'on'}
_cors_origins = os.getenv('CORS_ORIGINS', '')
CORS_ALLOWED_ORIGINS = [o.strip() for o in _cors_origins.split(',') if o.strip()]
if CORS_ALLOWED_ORIGINS and not CORS_ALLOW_ALL_ORIGINS:
    CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOW_CREDENTIALS = True

# --------------------------------------------------------------------------- #
# JWT (Flask-JWT-Extended compatible: HS256, "sub" = str(user_id))
# --------------------------------------------------------------------------- #
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
JWT_ALGORITHM = 'HS256'
JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=int(os.getenv('JWT_EXPIRATION_HOURS', '24')))

# --------------------------------------------------------------------------- #
# Email (SMTP - Zoho, same env vars as Flask)
# --------------------------------------------------------------------------- #
MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.zoho.com')
MAIL_PORT = int(os.getenv('MAIL_PORT', '465'))
MAIL_USE_SSL = os.getenv('MAIL_USE_SSL', 'True').lower() in {'1', 'true', 'yes', 'on'}
MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'False').lower() in {'1', 'true', 'yes', 'on'}
MAIL_USERNAME = os.getenv('MAIL_USERNAME')
MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
EMAIL_TIMEOUT = int(os.getenv('EMAIL_TIMEOUT', '12'))
DEFAULT_FROM_EMAIL = f"PlomApp <{MAIL_USERNAME}>" if MAIL_USERNAME else 'plomaap@zohomail.com'

# --------------------------------------------------------------------------- #
# App / integrations
# --------------------------------------------------------------------------- #
APP_NAME = os.getenv('APP_NAME', 'PlomApp')
APP_VERSION = os.getenv('APP_VERSION', '1.0.0')
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '')
GOOGLE_DEFAULT_PASSWORD = os.getenv('GOOGLE_DEFAULT_PASSWORD', 'GoogleAuth123!')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
VOYAGE_API_KEY = os.getenv('VOYAGE_API_KEY', '')
EMBEDDING_PROVIDER = os.getenv('EMBEDDING_PROVIDER', 'voyage')
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'voyage-3-lite')

# WebAuthn / Passkeys
WEBAUTHN_RP_ID = os.getenv('WEBAUTHN_RP_ID', 'localhost')
WEBAUTHN_RP_NAME = os.getenv('WEBAUTHN_RP_NAME', 'PlomApp')
WEBAUTHN_ORIGIN = os.getenv('WEBAUTHN_ORIGIN', 'android:apk-key-hash:plomaap')

# Uploaded evidence photos are served from /static/uploads/evidence/<file>
# (mirrors Flask's app/static/uploads/evidence directory)
UPLOADS_STATIC_DIR = BASE_DIR / 'static' / 'uploads' / 'evidence'

# --------------------------------------------------------------------------- #
# Endurecimiento para producción (todo desactivado por defecto)
# --------------------------------------------------------------------------- #
# En local el frontend React consume http://localhost:5000 por HTTP y con
# DEBUG=True, así que estas opciones van apagadas para no romper el desarrollo.
# En producción define en el .env: DEBUG=False, ALLOWED_HOSTS, CORS_ORIGINS,
# SECRET_KEY/JWT_SECRET_KEY fuertes y las variables SECURE_* que necesites.
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'

SECURE_SSL_REDIRECT = _env_bool('SECURE_SSL_REDIRECT', False)
SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '0'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = _env_bool('SECURE_HSTS_INCLUDE_SUBDOMAINS', False)
SECURE_HSTS_PRELOAD = _env_bool('SECURE_HSTS_PRELOAD', False)
SESSION_COOKIE_SECURE = _env_bool('SESSION_COOKIE_SECURE', False)
CSRF_COOKIE_SECURE = _env_bool('CSRF_COOKIE_SECURE', False)
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'

# Detrás de un proxy/balanceador que termina TLS (nginx, Caddy, Render...)
if _env_bool('USE_X_FORWARDED_PROTO', False):
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.getenv('CSRF_TRUSTED_ORIGINS', '').split(',') if o.strip()]

# Límites de subida (evitan agotar memoria/CPU con cuerpos gigantes)
DATA_UPLOAD_MAX_MEMORY_SIZE = int(os.getenv('DATA_UPLOAD_MAX_MEMORY_SIZE', str(10 * 1024 * 1024)))
FILE_UPLOAD_MAX_MEMORY_SIZE = int(os.getenv('FILE_UPLOAD_MAX_MEMORY_SIZE', str(10 * 1024 * 1024)))
DATA_UPLOAD_MAX_NUMBER_FIELDS = int(os.getenv('DATA_UPLOAD_MAX_NUMBER_FIELDS', '1000'))

# Impedir arrancar en producción con las claves de ejemplo del repositorio.
if not DEBUG:
    _weak_secrets = {
        'dev-secret-key-change-in-production',
        'your-secret-key-change-in-production',
        'jwt-secret-key-change-in-production',
        'your-jwt-secret-key-change-in-production',
    }
    if SECRET_KEY in _weak_secrets or JWT_SECRET_KEY in _weak_secrets:
        from django.core.exceptions import ImproperlyConfigured

        raise ImproperlyConfigured(
            'Con DEBUG=False debes definir SECRET_KEY y JWT_SECRET_KEY reales '
            '(no los valores de ejemplo) en el .env.'
        )
