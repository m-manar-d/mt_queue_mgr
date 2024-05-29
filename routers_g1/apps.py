from django.apps import AppConfig

class RoutersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'routers_g1'
    verbose_name = "G1-Group Name"
    
    def ready(self):
        import routers_g1.signals
