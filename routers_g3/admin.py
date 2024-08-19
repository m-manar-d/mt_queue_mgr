"""
Registering models of this group
"""

from django import forms
from django.contrib import admin, messages
from django.urls import path
from django.utils.translation import ngettext
from routeros_api import exceptions as RosExcep

from .models import Limiter_rt, Last_queues
from .queues_utils import rt_refresh, rt_conn, rt_disconn, rt_db_save, rt_fw_list_update
from .queues_utils import q_add, q_gen_export, q_mod, calc_order, global_up

class Limiter_rtForm(forms.ModelForm):
    """ Hide routers passwords"""
    class Meta:
        model = Limiter_rt
        exclude = ('identity','status','last_updated')
        widgets = {
            'password': forms.PasswordInput(attrs={'size': 25})
        }

class limiterAdmin(admin.ModelAdmin):
    """ Limiter Routers' table reg """
    change_list_template = "routers_g3/limiteradmin_gen_export.html"
    list_display = ("ip", "identity", "status", 'last_updated')
    exclude = ('identity','status','last_updated')
    save_as = True
    actions = ['r_refresh', 'r_fw_list_update']
    form = Limiter_rtForm
    def r_refresh(self, request, queryset):
        """ Used to check router's queue tables """
        refreshed = 0
        for x in queryset:
            ipa = x.ip
            rt_refresh(ipa)
            refreshed += 1
        self.message_user(request, ngettext(
            '%d Router was refreshed, check STATUS for the result.',
            '%d Routers were refreshed, check STATUS for the results.',
            refreshed,
        ) % refreshed, messages.SUCCESS)
    r_refresh.short_description = "Refresh Quee Types and Queues of selected routers"
    r_refresh.allowed_permissions = ('change',)
    def r_fw_list_update(self, request, queryset):
        """ Used to update router's firewall address list """
        fwl_updated = 0
        for i in queryset:
            if i.status != 'o':
                continue
            conn = rt_conn(i)
            if conn[0] is False:
                self.message_user(
                    request,
                    "Limiter: " + i.ip + " is not responding, status changed to 'f'",
                    messages.ERROR
                    )
                continue
            connection = conn[1]
            api = conn[2]
            rt_fw_list_update(api)
            rt_disconn(i,connection,'o')
            fwl_updated += 1
        self.message_user(request, ngettext(
            '%d Firewall address_list was updated in selected router.',
            '%d Firewall address_list was updated in selected routers.',
            fwl_updated,
        ) % fwl_updated, messages.SUCCESS)
    r_fw_list_update.short_description = "Update Firewall address_list of selected routers"
    def gen_export(self, request):
        """ Used to generate simple queues .rsc file """
        res = q_gen_export()
        self.message_user(request, 'Export file generated successfully.', messages.SUCCESS)
        return res
    def get_urls(self):
        urls = super().get_urls()
        my_urls = [path('gen_export/', self.gen_export),]
        return my_urls + urls
admin.site.register(Limiter_rt, limiterAdmin)

class queueAdmin(admin.ModelAdmin):
    """ Simple queues table reg """
    list_display = ("name", "target", "max_limit", "disabled", "number")
    search_fields = ['name', 'target']
    readonly_fields = ('parent','number')
    list_per_page = 15
    save_as = True
    def save_model(self, request, obj, form, change):
        """ pre_save actions after adding/modifying a simple queue entry """
        rt_list = []
        rt_modified = False
        move_to = calc_order(obj.max_limit)
        for i in Limiter_rt.objects.filter(status ='o'):
            rt_list.append(i.ip)
            conn = rt_conn(i)
            if conn[0] is False:
                self.message_user(
                    request,
                    "Limiter: " + i.ip + " is not responding, status changed to 'f'",
                    messages.ERROR
                    )
                continue
            connection = conn[1]
            api = conn[2]
            # if created:
            if obj.id is None:
                previous = None
                try:
                    q_add(obj, api, move_to)
                    # refresh entries in firewall address_list:
                    rt_fw_list_update(api)
                except RosExcep.RouterOsApiCommunicationError as error:
                    self.message_user(
                        request,
                        "Limiter: " + i.ip + " " + error.original_message.decode('ascii'),
                        messages.ERROR
                        )
                    rt_disconn(i,connection,'s')
                    continue
                rt_disconn(i,connection,'o')
                rt_modified = True
            else:
                # if not created but modified
                previous = Last_queues.objects.get(id=obj.id)
                try:
                    q_mod(obj, api, move_to, previous)
                    # refresh entries in firewall address_list:
                    rt_fw_list_update(api)
                except RosExcep.RouterOsApiCommunicationError as error:
                    self.message_user(
                        request,
                        "Limiter: " + i.ip + " " + error.original_message.decode('ascii'),
                        messages.ERROR
                        )
                    rt_disconn(i,connection,'s')
                    continue
                except UnboundLocalError:
                    try:
                        q_add(obj, api, move_to)
                    except Exception:
                        self.message_user(
                            request,
                            "Limiter: " + i.ip + \
                                " A simple queue with the same name was not found!" + \
                                    " Attempt to add it failed!",
                            messages.ERROR
                            )
                        rt_disconn(i,connection,'s')
                        continue
                    self.message_user(
                        request,
                        "Limiter: " + i.ip + " A simple queue with the same name was not found," + \
                            " but added successfully!",
                        messages.WARNING
                        )
                    rt_disconn(i,connection,'o')
                    rt_modified = True
                    continue
                # update limiter's record and save
                rt_disconn(i,connection,'o')
                rt_modified = True
        # update at global queues db if change was applied to at least one limiter
        if rt_modified:
            global_up(obj, previous)
            super().save_model(request, obj, form, change)
        else:
            for j in Limiter_rt.objects.filter(status ='s'):
                for i in rt_list:
                    if j.ip == i:
                        rt_db_save(j,'o')
            messages.set_level(request, messages.ERROR)
            messages.error(request, 'Errors encountered, changes not saved!')
admin.site.register(Last_queues, queueAdmin)
