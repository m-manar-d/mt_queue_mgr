"""
Register models of limiter_global
"""

from django.contrib import admin
from .models import Global_Limiters, Global_Last_Queues

class limiterAdmin(admin.ModelAdmin):
    """ Limiter Routers' table reg """
    list_display = ('ip', 'identity', 'source_g')
    search_fields = ['ip', 'identity', 'source_g']
    readonly_fields = ('ip', 'identity', 'source_g')
    list_per_page = 15
    def get_actions(self, request):
        """ This is used to remove the delete action """
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions
    def has_add_permission(self, request, obj=None):
        """ This is used to disallow adding elements from this app """
        return False
    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        """ This is used to remove some action buttons"""
        extra_context = extra_context or {}
        extra_context['show_save_and_continue'] = False
        extra_context['show_save'] = False
        extra_context['show_delete'] = False
        return super(limiterAdmin, self).changeform_view(
            request, object_id,
            extra_context=extra_context
            )
admin.site.register(Global_Limiters, limiterAdmin)

class queueAdmin(admin.ModelAdmin):
    """ Simple queue table reg """
    list_display = ("name", "target", "max_limit", "disabled", 'source_g')
    search_fields = ['name', 'target', "max_limit", "disabled", 'source_g']
    readonly_fields = ('name', 'target', "max_limit", "disabled", 'source_g')
    list_per_page = 15
    def get_actions(self, request):
        """ This is used to remove the delete action """
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions
    def has_add_permission(self, request, obj=None):
        """ This is used to disallow adding elements from this app """
        return False
    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        """ This is used to remove some action buttons"""
        extra_context = extra_context or {}
        extra_context['show_save_and_continue'] = False
        extra_context['show_save'] = False
        extra_context['show_delete'] = False
        return super(queueAdmin, self).changeform_view(
            request, object_id,
            extra_context=extra_context
            )
admin.site.register(Global_Last_Queues, queueAdmin)
