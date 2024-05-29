from django.apps import AppConfig

class RoutersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'routers_g3'
    verbose_name = "G3-Group Name"
    
    def ready(self):
        import routers_g3.signals
