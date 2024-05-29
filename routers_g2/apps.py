from django.apps import AppConfig

class RoutersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'routers_g2'
    verbose_name = "G2-Group Name"
    
    def ready(self):
        import routers_g2.signals
