release: python manage.py migrate --noinput
web: gunicorn unsdg.wsgi:application --bind 0.0.0.0:$PORT --workers ${WEB_CONCURRENCY:-3} --threads 2 --preload --access-logfile -
