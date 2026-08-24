"""
WSGI config for unsdg project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "unsdg.settings")

application = get_wsgi_application()

# Parse the CSVs while the worker is booting rather than during the first
# request, so nobody waits for it.
from information.analytics import get_dataset  # noqa: E402

get_dataset()
