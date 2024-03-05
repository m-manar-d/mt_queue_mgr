from django.contrib import admin, messages
# messages needed for the message customization method

from django.utils.translation import ngettext
# ngettext needed for message output handling
from .models import Limiter_rt, Last_queue_types, Last_queues
from .signals import rt_refresh

class limiterAdmin(admin.ModelAdmin):
  list_display = ("ip", "identity", "status", 'last_updated')
  exclude = ('identity','status','last_updated')
  actions = ['r_refresh']
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

admin.site.register(Limiter_rt, limiterAdmin)

class queueAdmin(admin.ModelAdmin):
  list_display = ("name", "target", "max_limit", "disabled")
  search_fields = ['name', 'target']
  list_per_page = 15
  save_as = True
admin.site.register(Last_queues, queueAdmin)
