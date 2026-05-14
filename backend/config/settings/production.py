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
    config("FRONTEND_URL", default="https://analytics-platform.vercel.app"),
    "http://localhost:3000",
]
CORS_ALLOW_CREDENTIALS = True

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

LOGIN_REDIRECT_URL = config("FRONTEND_URL", default="https://analytics-platform.vercel.app") + "/auth-callback"
SOCIAL_AUTH_LOGIN_REDIRECT_URL = LOGIN_REDIRECT_URL
SOCIAL_AUTH_LOGIN_ERROR_URL = config("FRONTEND_URL", default="https://analytics-platform.vercel.app") + "/login"

# Email
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.gmail.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="noreply@analytics-platform.com")
