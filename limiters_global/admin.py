"""
Register models of limiter_global
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import GlobalLimiters, GlobalLastQueues

class LimiterAdmin(admin.ModelAdmin):
    """ Limiter Routers' table reg """
    list_display = ("ip", "identity", 'source_g')
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
        return super().changeform_view(
            request, object_id,
            extra_context=extra_context
            )
admin.site.register(GlobalLimiters, LimiterAdmin)

class QueueAdmin(admin.ModelAdmin):
    """ Simple queue table reg """
    list_display = ("c_name", "target", "max_limit", "c_disabled", 'source_g')
    search_fields = ['name', 'target', "max_limit", "disabled", 'source_g']
    readonly_fields = ('name', 'target', "max_limit", "disabled", 'source_g')
    list_per_page = 15
    @admin.display(description='Name')
    def c_name(self,obj):
        """ Applying color codes to 'name' based on 'disabled' """
        if obj.disabled == 'yes':
            name_color = 'ffb66e;font-style: oblique;'
        else:
            name_color = 'currentColor'
        return format_html(
            '<span style="color: #{};">{}</span>',
            name_color,
            obj.name,
        )
    @admin.display(description='Disabled')
    def c_disabled(self,obj):
        """ Applying color codes to 'disabled' """
        if obj.disabled == 'yes':
            dis_color = 'ffb66e;font-style: oblique;'
        else:
            dis_color = 'currentColor'
        return format_html(
            '<span style="color: #{};">{}</span>',
            dis_color,
            obj.disabled,
        )
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
        return super().changeform_view(
            request, object_id,
            extra_context=extra_context
            )
admin.site.register(GlobalLastQueues, QueueAdmin)
