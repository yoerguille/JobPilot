import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=False)
SECRET_KEY = os.environ.get("JOBPILOT_SECRET_KEY", "django-insecure-jobpilot-local-development")
DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]

INSTALLED_APPS = ["django.contrib.staticfiles", "offers"]
MIDDLEWARE = ["django.middleware.csrf.CsrfViewMiddleware"]
ROOT_URLCONF = "jobpilot.urls"
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates", "APP_DIRS": True}]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LANGUAGE_CODE = "es"
TIME_ZONE = "Europe/Madrid"
USE_TZ = True

GREENHOUSE_BOARDS = {
    "typeform": "Typeform",
    "grafanalabs": "Grafana Labs",
    "elastic": "Elastic",
}
GREENHOUSE_TIMEOUT = 5
LEVER_BOARDS = {
    "prima": ("Prima", "eu"),
    "lodgify": ("Lodgify", "global"),
}
LEVER_TIMEOUT = 5

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_CV_MODEL = os.environ.get("JOBPILOT_OPENAI_MODEL", "gpt-5-mini")

STATIC_URL = "/static/"
