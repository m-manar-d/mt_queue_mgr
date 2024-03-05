from django.apps import AppConfig

class RoutersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'routers'
    
    def ready(self):
        import routers.signals
