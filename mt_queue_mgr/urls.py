"""
URL configuration for mt_queue_mgr project.
"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('logs/', include('log_viewer.urls')),
    path('', admin.site.urls),
]
