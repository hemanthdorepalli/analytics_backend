from .base import *
from decouple import config

DEBUG = False

ALLOWED_HOSTS = [
    ".onrender.com",
    ".vercel.app",
    "localhost",
    "127.0.0.1",
]

SIMPLE_JWT["AUTH_COOKIE_SECURE"] = True
SIMPLE_JWT["AUTH_COOKIE_SAMESITE"] = "None"

CORS_ALLOWED_ORIGINS = [
    "https://analytics-frontend-one.vercel.app",
    "http://localhost:3000",
]
CORS_ALLOW_CREDENTIALS = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

LOGIN_REDIRECT_URL = "https://analytics-frontend-one.vercel.app/auth-callback"
SOCIAL_AUTH_LOGIN_REDIRECT_URL = "https://analytics-frontend-one.vercel.app/auth-callback"
SOCIAL_AUTH_LOGIN_ERROR_URL = "https://analytics-frontend-one.vercel.app/login"

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="noreply@analytics-platform.com")

import os
_redis = os.environ.get("REDIS_URL", "")
if _redis.startswith("rediss://"):
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": _redis,
            "OPTIONS": {"ssl_cert_reqs": None},
        }
    }
    CELERY_BROKER_URL = _redis
    CELERY_BROKER_USE_SSL = {"ssl_cert_reqs": None}
    CELERY_REDIS_BACKEND_USE_SSL = {"ssl_cert_reqs": None}
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [{"address": _redis, "ssl": True}],
            },
        }
    }

# Social auth — don't try to set first_name/last_name (we use full_name)
SOCIAL_AUTH_USER_FIELDS = ["email", "full_name"]
SOCIAL_AUTH_GOOGLE_OAUTH2_USER_FIELDS = ["email"]

# Fix AuthStateMissing — use database sessions
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = "None"
SESSION_COOKIE_AGE = 86400

# Social auth pipeline — remove user_details step that sets first_name
SOCIAL_AUTH_PIPELINE = (
    "social_core.pipeline.social_auth.social_details",
    "social_core.pipeline.social_auth.social_uid",
    "social_core.pipeline.social_auth.auth_allowed",
    "social_core.pipeline.social_auth.social_user",
    "social_core.pipeline.user.get_username",
    "social_core.pipeline.user.create_user",
    "app.authentication.services.save_google_profile",
    "social_core.pipeline.social_auth.associate_user",
    "social_core.pipeline.social_auth.load_extra_data",
)
