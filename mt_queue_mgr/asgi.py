"""
ASGI config for mt_queue_mgr project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

from os import environ

from django.core.asgi import get_asgi_application

environ.setdefault('DJANGO_SETTINGS_MODULE', 'mt_queue_mgr.settings')

application = get_asgi_application()
