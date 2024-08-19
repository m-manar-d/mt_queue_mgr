"""
Register routers_g2
"""

from django.apps import AppConfig

class RoutersConfig(AppConfig):
    """ Register routers_g2 """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'routers_g2'
    verbose_name = "G2-Antalya Limiters"
    def ready(self):
        import routers_g2.signals
