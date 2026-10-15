#!/bin/sh
# Start-up of the Babubi image: prepare /config, bring the database up to
# date and hand over to gunicorn.
set -eu

mkdir -p /config/data /config/media

# A SECRET_KEY from the environment wins; otherwise one is generated on the
# first start and kept in the volume, so sessions survive a new container.
if [ -z "${SECRET_KEY:-}" ]; then
    if [ ! -s /config/.secretkey ]; then
        echo "No secret key found, generating one in /config/.secretkey"
        (umask 077 && python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key(), end="")' >/config/.secretkey)
    fi
    SECRET_KEY="$(cat /config/.secretkey)"
    export SECRET_KEY
fi

python manage.py migrate_from_babybuddy
python manage.py migrate --noinput
python manage.py createcachetable

exec gunicorn babubi.wsgi:application \
    --bind 0.0.0.0:8000 \
    --worker-class gthread \
    --workers "${GUNICORN_WORKERS:-2}" \
    --threads "${GUNICORN_THREADS:-4}" \
    --timeout 30 \
    --worker-tmp-dir /dev/shm \
    --access-logfile - \
    --error-logfile -
