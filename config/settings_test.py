"""
Settings for pytest.

By default the backend test suite runs on in-memory SQLite, so unit tests and
contract tests work without Docker/PostgreSQL. To run the PostgreSQL-specific
integration tests, set TEST_USE_CONFIGURED_DB=1 before invoking pytest; in that
case Django creates and uses test_<POSTGRES_DB> from the configured .env.
"""
import os

from .settings import *  # noqa: F401,F403

if os.getenv('TEST_USE_CONFIGURED_DB', '').lower() not in {'1', 'true', 'yes', 'on'}:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
        }
    }

# Never send real emails while testing: the email helper skips sending when
# credentials are empty.
MAIL_USERNAME = ''
MAIL_PASSWORD = ''
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
