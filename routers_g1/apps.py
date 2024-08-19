"""
Register routers_g1
"""

from django.apps import AppConfig

class RoutersConfig(AppConfig):
    """ Register routers_g1 """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'routers_g1'
    verbose_name = "G1-Istanbul Limiters"
    def ready(self):
        import routers_g1.signals
