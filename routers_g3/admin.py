"""
Registering models and actions of this group
"""

from django import forms
from django.contrib import admin

from core.core_admin import LimiterAdminT, QueueAdminT
from .models import LimiterRT, LastQueues
from .apps import RoutersConfig

class LimiterRtForm(forms.ModelForm):
    """ Hide routers passwords in input form"""
    class Meta:
        exclude = ('identity','status','last_updated')
        widgets = {
            'password': forms.PasswordInput(attrs={'size': 25})
        }

class LimiterAdmin(LimiterAdminT):
    """ Limiter Routers' table reg """
    form = LimiterRtForm
    limiter_rt_db = LimiterRT
    last_queues_db = LastQueues
    source_name = RoutersConfig.name
    change_list_template = source_name + "/limiteradmin_gen_export.html"
admin.site.register(LimiterRT, LimiterAdmin)

class QueueAdmin(QueueAdminT):
    """ Simple queues table reg """
    limiter_rt_db = LimiterRT
    last_queues_db = LastQueues
    source_name = RoutersConfig.name
    source_v_name = RoutersConfig.verbose_name
admin.site.register(LastQueues, QueueAdmin)
