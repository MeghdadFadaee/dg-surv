"""WSGI config for the survey service."""
import os

from django.core.wsgi import get_wsgi_application


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "survey_service.settings")

application = get_wsgi_application()
