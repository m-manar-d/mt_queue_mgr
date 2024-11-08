"""
Main DB-edit signals actions methods
"""

from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete

from core.core_utils import rt_add_post_s, rt_delete_post_d, q_rem_post_d, q_addmod_post_s
from .models import LimiterRT, LastQueues
from .apps import RoutersConfig

SOURCE_NAME = RoutersConfig.name

#   ", weak=False" added to all receivers [pre_save did not work when "DEBUG = False"]
#   because i was using same function names for pre_save and post_save of the same sender
@receiver(post_save, sender=LimiterRT, weak=False)
def rt_add(instance, created, **kwargs):
    """ post_save actions after adding a limiter router to table """
    if not created:
        return
    rt_add_post_s(instance, SOURCE_NAME)

@receiver(post_delete, sender=LimiterRT, weak=False)
def rt_delete(instance , **kwargs):
    """ post_delete actions after deleting a limiter router from table """
    rt_delete_post_d(instance, SOURCE_NAME)

@receiver(post_save, sender=LastQueues, weak=False)
def q_addmod(instance, **kwargs):
    """ post_save actions after adding/modifying a simple queue entry """
    q_addmod_post_s(instance, SOURCE_NAME)

@receiver(post_delete, sender=LastQueues, weak=False)
def q_rem(instance, **kwargs):
    """ post_delete actions after deleting simple queue entry """
    q_rem_post_d(instance, SOURCE_NAME)
