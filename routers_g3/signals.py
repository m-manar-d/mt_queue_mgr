from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.utils import timezone
import routeros_api
from routers_g3.models import Limiter_rt, Last_queue_types, Last_queues, Queue_types, Queues
from routers_g3.apps import RoutersConfig
from limiters_global.models import Global_Limiters, Global_Last_Queues
from .queues_utils import huma, qt_compare, q_compare, calc_order, lqdb_order, rt_fw_list_update


@receiver(post_save, sender=Limiter_rt, weak=False)
def rt_add(sender, instance, created, **kwargs):
    if not created: return
    ipa = instance.ip
    uname = instance.username
    upass = instance.password
    try:
        connection = routeros_api.RouterOsApiPool(ipa, username=uname, password=upass ,plaintext_login=True)
        api = connection.get_api()
    except:
        instance.status = 'f'
        instance.save()
        connection.disconnect()
        return
    rt_idnt = api.get_resource('/system/identity')
    for i in rt_idnt.get() : rt_identity = i['name']
    instance.identity = rt_identity
    instance.status = 's'
    instance.save()
    # v2 edited:
    list_qt = api.get_resource('/queue/type')
    list_qts = sorted(list_qt.get(), key=lambda k: k['name'])
    for x in list_qts:
        qt = Queue_types(
            name = x['name'],
            kind = x['kind'],
            limiter_rt = instance
        )
        qt.save()
    list_q = api.get_resource('/queue/simple')
    list_qs = list_q.get()
    for y in list_qs :
        if y['disabled'] == 'true': dis = 'yes'
        else: dis = 'no'
        if 'total-queue' in y: v_total_queue = y['total-queue']
        else: v_total_queue = 'default-small'
        q = Queues(
            name = y['name'],
            target = y['target'],
            max_limit = huma(y['max-limit']),
            burst_limit = huma(y['burst-limit']),
            burst_threshold = huma(y['burst-threshold']),
            burst_time = y['burst-time'],
            limit_at = huma(y['limit-at']),
            priority = y['priority'],
            bucket_size = y['bucket-size'],
            queue = y['queue'],
            parent = y['parent'],
            disabled = dis,
            total_queue = v_total_queue,
            limiter_rt = instance
        )
        q.save()
    if not Limiter_rt.objects.exclude(ip=instance.ip).all():
        lq_number = 0
        for x in list_qts:
            lqt = Last_queue_types(
                name = x['name'],
                kind = x['kind'],
            )
            lqt.save()
        # used bulk_create() to avoid triggering signals.
        all_queue_obj = []
        all_queue_obj_g = []
        for y in list_qs :
            if y['disabled'] == 'true': dis = 'yes'
            else: dis = 'no'
            if 'total-queue' in y: v_total_queue = y['total-queue']
            else: v_total_queue = 'default-small'
            y_qs_qt_total = Last_queue_types.objects.get(name=v_total_queue)
            y_qs_qt = Last_queue_types.objects.get(name=y['queue'].split('/', 1)[0])
            lq = Last_queues(
                name = y['name'],
                target = y['target'],
                max_limit = huma(y['max-limit']),
                burst_limit = huma(y['burst-limit']),
                burst_threshold = huma(y['burst-threshold']),
                burst_time = y['burst-time'],
                limit_at = huma(y['limit-at']),
                priority = y['priority'],
                bucket_size = y['bucket-size'],
                queue = y_qs_qt,
                parent = y['parent'],
                disabled = dis,
                total_queue = y_qs_qt_total,
                number = lq_number
            )
            all_queue_obj.append(lq)
            queue_obj_g = Global_Last_Queues(
                name = lq.name,
                target = lq.target,
                max_limit = lq.max_limit,
                disabled = lq.disabled,
                source_g = RoutersConfig.verbose_name
            )
            all_queue_obj_g.append(queue_obj_g)
            lq_number += 1
        Last_queues.objects.bulk_create(all_queue_obj)
        # add to global queues db
        Global_Last_Queues.objects.bulk_create(all_queue_obj_g)
        instance.status = 'o'
        instance.last_updated = timezone.now()
        instance.save()
        connection.disconnect()
    else:
        if qt_compare(instance) and q_compare(instance):
            instance.status = 'o'
            instance.last_updated = timezone.now()
            instance.save()
            connection.disconnect()
    rt_fw_list_update(ipa)
    # add to global limiters db
    new_rt = Global_Limiters(
        ip = instance.ip,
        identity = rt_identity,
        source_g = RoutersConfig.verbose_name
    )
    new_rt.save()

@receiver(post_delete, sender=Limiter_rt, weak=False)
def clean_if_last_rt(sender , instance , **kwargs):
    # remove from global limiters db
    Global_Limiters.objects.filter(ip=instance.ip).delete()
    if not Limiter_rt.objects.all():
        # prevent triggering delete signal when clearing Last_queues by this function
        # this is changed from post_save to post_delete
        post_delete.disconnect(q_rem, sender=Last_queues)
        if Last_queues.objects.all(): Last_queues.objects.all().delete()
        if Last_queue_types.objects.all(): Last_queue_types.objects.all().delete()
        if Queues.objects.all(): Queues.objects.all().delete()
        if Queue_types.objects.all(): Queue_types.objects.all().delete()
        # Re-enable signal when adding queues to Last_queues
        # this is changed from post_save to post_delete
        post_delete.connect(q_rem, sender=Last_queues)
        # remove all from global queues db
        Global_Last_Queues.objects.filter(source_g=RoutersConfig.verbose_name).delete()

@receiver(pre_save, sender=Last_queues, weak=False)
def q_addmod(sender, instance, **kwargs):
    move_to = calc_order(instance.max_limit)
    if instance.id is None:
        # update at global queues db
        Global_Last_Queues.objects.create(
                name = instance.name,
                target = instance.target,
                max_limit = instance.max_limit,
                disabled = instance.disabled,
                source_g = RoutersConfig.verbose_name
                )
        # no need to check that queue with same name does not exist, since field is set to "unique"
        # add a routine to check and warn if queue with same target exist
        for x in Limiter_rt.objects.all():
            try:
                connection = routeros_api.RouterOsApiPool(x.ip, username=x.username, password=x.password ,plaintext_login=True)
                api = connection.get_api()
            except:
                x.status = 'f'
                x.save()
                connection.disconnect()
                continue
            list_queues = api.get_resource('/queue/simple')
            list_queues.add(
                name=instance.name,
                burst_threshold=instance.burst_threshold,
                limit_at=instance.limit_at,
                parent=instance.parent,
                priority=instance.priority,
                target=instance.target,
                burst_limit=instance.burst_limit,
                burst_time=instance.burst_time,
                max_limit=instance.max_limit,
                queue=instance.queue.name + '/' + instance.queue.name,
                bucket_size=instance.bucket_size,
                disabled=instance.disabled,
                total_queue=instance.total_queue.name,
                place_before=move_to
            )
            x.last_updated = timezone.now()
            x.save()
            connection.disconnect()
    else:
        # routine if a queue was not created but modified
        previous = Last_queues.objects.get(id=instance.id)
        for x in Limiter_rt.objects.all():
            try:
                connection = routeros_api.RouterOsApiPool(x.ip, username=x.username, password=x.password ,plaintext_login=True)
                api = connection.get_api()
            except:
                x.status = 'f'
                x.save()
                connection.disconnect()
                continue
            list_queues = api.get_resource('/queue/simple')
            get_q = list_queues.get(name=previous.name)
            for y in get_q: qid = y['id']
            list_queues.set(id=qid,
                name=instance.name,
                burst_threshold=instance.burst_threshold,
                limit_at=instance.limit_at,
                parent=instance.parent,
                priority=instance.priority,
                target=instance.target,
                burst_limit=instance.burst_limit,
                burst_time=instance.burst_time,
                max_limit=instance.max_limit,
                queue=instance.queue.name + '/' + instance.queue.name,
                bucket_size=instance.bucket_size,
                disabled=instance.disabled,
                total_queue=instance.total_queue.name,
            )
            bq_name = bytes(instance.name, encoding="ascii")
            bq_dname = bytes(move_to, encoding="ascii")
            api.get_binary_resource('/').call('queue/simple/move',{ 'numbers': bq_name , 'destination': bq_dname })
            x.last_updated = timezone.now()
            x.save()
            connection.disconnect()
        # update at global queues db
        Global_Last_Queues.objects.filter(name=previous.name).update(
            name = instance.name,
            target = instance.target,
            max_limit = instance.max_limit,
            disabled = instance.disabled,
            source_g = RoutersConfig.verbose_name
            )

@receiver(post_save, sender=Last_queues, weak=False)
def q_addmod(sender, instance, **kwargs):
    move_to = calc_order(instance.max_limit)
    lqdb_order(instance.name,move_to)
    # refresh entries in firewall address_list:
    for x in Limiter_rt.objects.all(): rt_fw_list_update(x.ip)

@receiver(post_delete, sender=Last_queues, weak=False)
def q_rem(sender, instance, **kwargs):
    # delete from global queues db
    Global_Last_Queues.objects.filter(name=instance.name).delete()
    for x in Limiter_rt.objects.all():
        try:
            connection = routeros_api.RouterOsApiPool(x.ip, username=x.username, password=x.password ,plaintext_login=True)
            api = connection.get_api()
        except:
            x.status = 'f'
            x.save()
            continue
        list_queues = api.get_resource('/queue/simple')
        get_q = list_queues.get(name=instance.name)
        for y in get_q: qid = y['id']
        list_queues.remove(id=qid)
        x.last_updated = timezone.now()
        x.save()
        connection.disconnect()
        rt_fw_list_update(x.ip)
