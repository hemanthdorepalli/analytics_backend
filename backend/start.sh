#!/bin/bash
set -e

# Run migrations
python manage.py migrate --noinput

# Start Celery worker in background
celery -A config.celery worker --loglevel=info --concurrency=1 &

# Start Celery Beat in background
celery -A config.celery beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler &

# Start Gunicorn in foreground (keeps container alive)
exec gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120
