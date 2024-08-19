"""
Main DB-edit signals actions methods
"""

from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete

from limiters_global.models import Global_Limiters, Global_Last_Queues
from .models import Limiter_rt, Last_queue_types, Last_queues, Queue_types, Queues
from .apps import RoutersConfig
from .queues_utils import rt_init, rt_conn, rt_disconn, rt_fw_list_update, data_init
from .queues_utils import lqdb_order, calc_order, qt_compare, q_compare

#   ", weak=False" added to all receivers [pre_save did not work when "DEBUG = False"]
#   because i was using same function names for pre_save and post_save of the same sender
@receiver(post_save, sender=Limiter_rt, weak=False)
def rt_add(instance, created, **kwargs):
    """ post_save actions after adding a limiter router to table """
    if not created:
        return
    conn = rt_conn(instance)
    if conn[0] is False:
        return
    connection = conn[1]
    api = conn[2]
    rt_data = rt_init(instance, api)
    list_qts = rt_data[0]
    list_qs = rt_data[1]
    # if this is the first router in this group:
    if not Limiter_rt.objects.exclude(ip=instance.ip).all():
        data_init(list_qts, list_qs)
        instance.status = 'o'
    else:
        # if not the first router int table, then check if data is synchronized:
        if qt_compare(instance) and q_compare(instance):
            instance.status = 'o'
    # refresh entries in firewall address_list:
    rt_fw_list_update(api)
    # update limiter's record and save
    rt_disconn(instance, connection, instance.status)

@receiver(post_delete, sender=Limiter_rt, weak=False)
def rt_delete(instance , **kwargs):
    """ post_delete actions after deleting a limiter router from table """
    # remove from global limiters db
    Global_Limiters.objects.filter(ip=instance.ip).delete()
    # if the deleted router was the last entry in routers table:
    if not Limiter_rt.objects.all():
        # prevent triggering delete signal when clearing Last_queues by this function
        post_delete.disconnect(q_rem, sender=Last_queues)
        if Last_queues.objects.all():
            Last_queues.objects.all().delete()
        if Last_queue_types.objects.all():
            Last_queue_types.objects.all().delete()
        if Queues.objects.all():
            Queues.objects.all().delete()
        if Queue_types.objects.all():
            Queue_types.objects.all().delete()
        # Re-enable signal when adding queues to Last_queues
        post_delete.connect(q_rem, sender=Last_queues)
        # remove all from global queues db
        Global_Last_Queues.objects.filter(source_g=RoutersConfig.verbose_name).delete()

@receiver(post_save, sender=Last_queues, weak=False)
def q_addmod_post_s(instance, **kwargs):
    """ post_save actions after adding/modifying a simple queue entry """
    move_to = calc_order(instance.max_limit)
    lqdb_order(instance.name,move_to)

@receiver(post_delete, sender=Last_queues, weak=False)
def q_rem(instance, **kwargs):
    """ post_delete actions after deleting simple queue entry """
    # delete from global queues db
    Global_Last_Queues.objects.filter(name=instance.name).delete()
    for i in Limiter_rt.objects.all():
        if i.status != 'o':
            continue
        conn = rt_conn(i)
        if conn[0] is False:
            continue
        connection = conn[1]
        api = conn[2]
        list_queues = api.get_resource('/queue/simple')
        get_q = list_queues.get(name=instance.name)
        for j in get_q:
            qid = j['id']
        list_queues.remove(id=qid)
        # refresh entries in firewall address_list:
        rt_fw_list_update(api)
        # update limiter's record and save
        rt_disconn(i,connection,'o')
