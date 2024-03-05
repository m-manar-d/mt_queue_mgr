import routeros_api
import collections
from django.utils import timezone
from routers.models import Limiter_rt, Last_queue_types, Last_queues, Queue_types, Queues 

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver, Signal
# required for triggering action after adding/deleting db records

def huma(raw):
    # used to humanize the numbers
    humG = 'G'.join(raw.rsplit('000000000'))
    humM = 'M'.join(humG.rsplit('000000'))
    hum = 'K'.join(humM.rsplit('000'))
    return(hum)

@receiver(post_save, sender=Limiter_rt)
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
    list_qs = sorted(list_q.get(), key=lambda k: k['target'])
    for y in list_qs :
        if y['disabled'] == 'true': dis = 'yes'
        else: dis = 'no'
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
            limiter_rt = instance
        )
        q.save()
    if not Limiter_rt.objects.exclude(ip=instance.ip).all():
        # prevent triggering save signal when adding queues to Last_queues by this function
        post_save.disconnect(q_addmod, sender=Last_queues)
        for x in list_qts:
            lqt = Last_queue_types(
                name = x['name'],
                kind = x['kind'],
            )
            lqt.save()
        for y in list_qs :
            if y['disabled'] == 'true': dis = 'yes'
            else: dis = 'no'
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
            )
            lq.save()
        instance.status = 'o'
        instance.last_updated = timezone.now()
        instance.save()
        connection.disconnect()
        # Re-enable signal when adding queues to Last_queues
        post_save.connect(q_addmod, sender=Last_queues)
    else:
        if qt_compare(instance) == 1:
            print('Synchronizing Queue Types tables faild')
        else:
            if q_compare(instance) == 1:
                print('Synchronizing Queues tables faild')
            else:
                instance.status = 'o'
                instance.last_updated = timezone.now()
                instance.save()
                connection.disconnect()
    # return values:
    # 1 = connection failed

@receiver(post_delete, sender=Limiter_rt)
def clean_if_last_rt(sender , instance , **kwargs):
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

def qt_compare( rt ):
    lqt = Last_queue_types.objects.values_list('name', 'kind').all()
    qt = Queue_types.objects.values_list('name', 'kind').filter(limiter_rt = rt)
    if collections.Counter(lqt) == collections.Counter(qt): return(0)
    else: return(1)

def q_compare(rt):
    lq = Last_queues.objects.values_list('name', 'burst_threshold', 'limit_at', 'parent', 'priority', 'target', 'burst_limit', 'burst_time', 'max_limit', 'bucket_size').all()
    q = Queues.objects.values_list('name', 'burst_threshold', 'limit_at', 'parent', 'priority', 'target', 'burst_limit', 'burst_time', 'max_limit', 'bucket_size').filter(limiter_rt = rt)
    # 'queue' is removed from the list of keys to be compared because it uses different types in each table
    if collections.Counter(lq) == collections.Counter(q): return(0)
    else: return(1)

def rt_refresh(rt_ip):
    ipa = rt_ip
    rt_record = Limiter_rt.objects.get(ip=rt_ip)
    uname = rt_record.username
    upass = rt_record.password
    Limiter_rt.objects.filter(ip=ipa).delete()
    Limiter_rt.objects.create(ip=ipa, username=uname, password=upass)

@receiver(post_save, sender=Last_queues)
def q_addmod(sender, instance, created, **kwargs):
    if created:
        # no need to check that queue with same name does not exist, since field is set to "unique"
        # add a routine to chack and warn if queue with same target exist
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
            )
            x.last_updated = timezone.now()
            x.save()
            connection.disconnect()
    else:
        # routine if a queue was not created but modified
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
            get_q = list_queues.get(name=instance.name)
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
            )
            x.last_updated = timezone.now()
            x.save()
            connection.disconnect()

@receiver(post_delete, sender=Last_queues)
def q_rem(sender, instance, **kwargs):
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

