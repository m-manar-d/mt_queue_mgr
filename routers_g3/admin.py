from django.contrib import admin, messages
# messages needed for the message customization method

from django.utils.translation import ngettext
# ngettext needed for message output handling
from .models import Limiter_rt, Last_queues #, Last_queue_types
from .queues_utils import rt_refresh, q_gen_export, rt_fw_list_update
from django.urls import path

class limiterAdmin(admin.ModelAdmin):
  change_list_template = "routers_g3/limiteradmin_gen_export.html"
  list_display = ("ip", "identity", "status", 'last_updated')
  exclude = ('identity','status','last_updated')
  save_as = True
  actions = ['r_refresh', 'r_fw_list_update']
  def r_refresh(self, request, queryset):
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
    refreshed = 0
    for x in queryset:
      ipa = x.ip
      rt_fw_list_update(ipa)
      refreshed += 1
    self.message_user(request, ngettext(
      '%d NoFastTrack Firewall address_list was updated in selected router.',
      '%d NoFastTrack Firewall address_list was updated in selected routers.',
      refreshed,
    ) % refreshed, messages.SUCCESS)
  r_fw_list_update.short_description = "Update NoFastTrack Firewall address_list of selected routers"
  def gen_export(self, request):
    return q_gen_export()
  def get_urls(self):
    urls = super().get_urls()
    my_urls = [path('gen_export/', self.gen_export),]
    return my_urls + urls
admin.site.register(Limiter_rt, limiterAdmin)

class queueAdmin(admin.ModelAdmin):
  list_display = ("name", "target", "max_limit", "disabled", "number")
  search_fields = ['name', 'target']
  readonly_fields = ('parent','number')
  list_per_page = 15
  save_as = True
admin.site.register(Last_queues, queueAdmin)
