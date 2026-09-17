#!/bin/sh
# Container entrypoint: prepare Django's own tables, then hand over to the
# command. The site's content needs no database, so this is quick and safe to
# repeat on every start.
set -e

python manage.py migrate --noinput

if [ "$1" = "gunicorn" ]; then
  shift
  exec gunicorn unsdg.wsgi:application \
    --bind "0.0.0.0:${PORT:-9011}" \
    --workers "${WEB_CONCURRENCY:-3}" \
    --preload \
    --threads "${GUNICORN_THREADS:-2}" \
    --timeout "${GUNICORN_TIMEOUT:-60}" \
    --access-logfile - \
    --error-logfile - \
    "$@"
fi

exec "$@"
