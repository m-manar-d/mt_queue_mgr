"""
Register routers_g3
"""

from django.apps import AppConfig

class RoutersConfig(AppConfig):
    """ Register routers_g3 """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'routers_g3'
    verbose_name = "G3-Group3 Limiters"
    def ready(self):
        import routers_g3.signals
