from pathlib import Path

from .settings import *  # noqa: F401,F403


BASE_DIR = Path(__file__).resolve().parent.parent

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(BASE_DIR / "smoke_workflow.sqlite3"),
    }
}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
LOGGING_CONFIG = None
LOGGING = {}
ALLOWED_HOSTS = ["*"]
DEBUG = True
