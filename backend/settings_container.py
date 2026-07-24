from pathlib import Path
import os

from .settings import *


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(config("DATA_DIR", default=str(BASE_DIR / "data")))
DATA_DIR.mkdir(parents=True, exist_ok=True)

DEBUG = parse_env_flag(config("DEBUG", default="False"), default=False)

ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    default=(
        "localhost,127.0.0.1,host.docker.internal,testhub-backend,"
        "testhub-automation-service,testhub-document-service,testhub-asset-service,"
        "testhub-integration-service,testhub-report-service,"
        "testhub-deployment-service,testhub-frontend"
    ),
    cast=lambda value: [item.strip() for item in value.split(",") if item.strip()],
)

STATIC_ROOT = config("STATIC_ROOT", default=str(BASE_DIR / "static"))
MEDIA_ROOT = config("MEDIA_ROOT", default=str(BASE_DIR / "media"))

os.makedirs(STATIC_ROOT, exist_ok=True)
os.makedirs(MEDIA_ROOT, exist_ok=True)

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:31080,http://127.0.0.1:31080,http://host.docker.internal:31080",
    cast=lambda value: [item.strip() for item in value.split(",") if item.strip()],
)
CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default="http://localhost:31080,http://127.0.0.1:31080,http://host.docker.internal:31080",
    cast=lambda value: [item.strip() for item in value.split(",") if item.strip()],
)

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

SIMPLEUI_INDEX = config("SIMPLEUI_INDEX", default="/")
