"""
Registering models and actions of this group
"""

import threading
import logging

from django.contrib import admin, messages
from django.urls import path
from django.utils.translation import ngettext
from django.utils.html import format_html
from django.forms import Form, FileField, ValidationError
from django.shortcuts import redirect

from core.limiter import Limiter
from core.core_utils import rt_refresh, rt_db_save, batch_add, rt_fw_list_update, q_gen_rt_export
from core.core_utils import q_save_pre_s, q_gen_export, global_up, calc_order, q_save_dup_check

logger = logging.getLogger('mt_queue_mgr')

def file_validate(value):
    """ Validate uploaded file """
    if value.content_type != 'text/csv':
        logger.error("Selected file: %s was not a CSV file!", value.name)
        raise ValidationError('Error message')

class UploadFileForm(Form):
    """ File upload custome class"""
    file = FileField(validators=[file_validate])

class LimiterAdminT(admin.ModelAdmin):
    """ Limiter Routers' table reg """
    list_display = ("ip", "identity", 'c_status', 'last_updated')
    exclude = ('identity','status','last_updated')
    save_as = True
    actions = ['r_refresh', 'r_fw_list_update']
    @admin.display(description='Status')
    def c_status(self,obj):
        """ Applying color codes to 'Status' """
        if obj.status == 'o':
            status_color = '23d823'
            status_text = 'On-line'
        if obj.status == 's':
            status_color = 'ff9e00'
            status_text = 'Syncing...'
        if obj.status == 'f':
            status_color = 'ff0000'
            status_text = 'Off-line !!'
        return format_html(
            '<span style="color: #{};">{}</span>',
            status_color,
            status_text,
        )
    def r_refresh(self, request, queryset):
        """ Used to check router's queue tables """
        refreshed = 0
        all_selected = False
        first_rt = True
        if set(queryset) == set(self.limiter_rt_db.objects.all()):
            all_selected = True
        for i in queryset:
            ipa = i.ip
            tid = threading.Thread(target=rt_refresh, args=(ipa,self.limiter_rt_db,))
            tid.start()
            # this is required because if all routers where deleted and several started adding \n
            # first data it cause wrong entries in LastQueues db
            if all_selected and first_rt:
                tid.join()
                first_rt = False
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
            con_rt = Limiter(i.ip, i.username, i.password)
            if con_rt.connected is False:
                self.message_user(
                    request,
                    "Limiter: " + i.ip + " is not responding, status changed to 'f'",
                    messages.ERROR
                    )
                rt_db_save(i, 'f')
                continue
            rt_fw_list_update(con_rt, self.last_queues_db)
            rt_db_save(i, 'o')
            fwl_updated += 1
        self.message_user(request, ngettext(
            '%d Firewall address_list was updated in selected router.',
            '%d Firewall address_list was updated in selected routers.',
            fwl_updated,
        ) % fwl_updated, messages.SUCCESS)
    r_fw_list_update.short_description = "Update Firewall address_list of selected routers"
    def gen_export(self, request):
        """ Used to generate simple queues .rsc file """
        res = q_gen_export(self.source_name, self.last_queues_db)
        logger.info(
            "Simple Queues export file of %s was generated successfully.",
            self.source_name
            )
        return res
    def gen_rt_export(self, request):
        """ Used to generate Limiter Router's .csv file """
        res = q_gen_rt_export(self.source_name, self.limiter_rt_db)
        logger.info(
            "Limiter routers' export file of %s was generated successfully.",
            self.source_name
            )
        return res
    def limiters_import(self, request):
        """ Used to uploaded .csv file for Limiters import """
        rt_added = [False, 0]
        to_same_page = redirect(request.META['HTTP_REFERER'])
        if request.method == "POST":
            form = UploadFileForm(request.POST, request.FILES)
            if form.is_valid():
                rt_added = batch_add(request.FILES["file"], self.limiter_rt_db)
            else:
                self.message_user(
                    request,
                    'No file selected or wrong file type! Please check logs for more details',
                    messages.WARNING
                    )
                return to_same_page
        if rt_added[0]:
            self.message_user(
                request, ngettext(
                    '%d Limiter added successfully, check log for more details.',
                    '%d Limiters added successfully, check log for more details.',
                    rt_added[1]
                ) % rt_added[1],
                messages.SUCCESS
                )
        else:
            self.message_user(
                request,
                'No Limiters added, check log for more details.',
                messages.WARNING
                )
        return to_same_page
    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('gen_export/', self.gen_export),
            path('limiters_import/', self.limiters_import),
            path('gen_rt_export/', self.gen_rt_export),
            ]
        return my_urls + urls
    class Meta:
        abstract = True

class QueueAdminT(admin.ModelAdmin):
    """ Simple queues table reg """
    list_display = ("c_name", "target", "max_limit", "c_disabled", "number")
    search_fields = ['name', 'target']
    readonly_fields = ('parent','number')
    list_per_page = 15
    save_as = True
    rt_modified = False
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
    def save_model(self, request, obj, form, change):
        """ pre_save actions after adding/modifying a simple queue entry """
        rt_list = []
        threads = []
        move_to = calc_order(obj.max_limit, self.source_name)
        self.rt_modified = False
        if obj.id is None:
            previous = None
            # first, check if name exists in global queues table
            if not q_save_dup_check(obj.name):
                messages.set_level(request, messages.ERROR)
                messages.error(
                    request,
                    "A queue with the same name already exists in Global table!"
                    )
                logger.error(
                    "A queue with the same name: %s already exists in Global table!",
                    obj.name
                    )
                return
        else:
            previous = self.last_queues_db.objects.get(id=obj.id)
            # first, check if name exists in global queues table
            if obj.name != previous.name and not q_save_dup_check(obj.name):
                messages.set_level(request, messages.ERROR)
                messages.error(
                    request,
                    "A queue with the same name already exists in Global table!"
                    )
                logger.error(
                    "A queue with the same name: %s already exists in Global table!",
                    obj.name
                    )
                return
        for i in self.limiter_rt_db.objects.filter(status ='o'):
            rt_list.append(i.ip)
            tid = threading.Thread(
                target=q_save_pre_s,
                args=(i,move_to,previous,obj,self,)
                )
            threads.append(tid)
            tid.start()
        for i in threads:
            i.join()
        # update at global queues db if change was applied to at least one limiter
        if self.rt_modified:
            global_up(obj, previous, self.source_v_name)
            super().save_model(request, obj, form, change)
        else:
            for j in self.limiter_rt_db.objects.filter(status ='s'):
                for i in rt_list:
                    if j.ip == i:
                        rt_db_save(j,'o')
            messages.set_level(request, messages.ERROR)
            messages.error(request, 'Errors encountered, changes not saved!')
    class Meta:
        abstract = True
