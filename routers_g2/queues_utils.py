"""
Several utility methods for app
"""

import collections
from io import StringIO
from datetime import datetime

# required to generate export file in memory
from django.http import HttpResponse
from django.utils import timezone
from django.db.models.signals import post_save
import routeros_api

from limiters_global.models import Global_Limiters, Global_Last_Queues
from .models import Limiter_rt, Last_queue_types, Last_queues, Queue_types, Queues
from .apps import RoutersConfig

PH_1000 = 'g2-queues-1000'
PH_750 = 'g2-queues-750'
PH_500 = 'g2-queues-500'
PH_300 = 'g2-queues-300'
PH_200 = 'g2-queues-200'
PH_100 = 'g2-queues-100'
PH_LAST = 'g2-queues-last'
FW_ADDRESS_LIST = 'NoFastTrack'

def huma(raw):
    """ Used to humanize the numbers """
    hum_g = 'G'.join(raw.rsplit('000000000'))
    hum_m = 'M'.join(hum_g.rsplit('000000'))
    hum = 'K'.join(hum_m.rsplit('000'))
    return hum

def rt_init(instance, api):
    """ Add limiter router record to table """
    rt_idnt = api.get_resource('/system/identity')
    for i in rt_idnt.get():
        rt_identity = i['name']
    instance.identity = rt_identity
    rt_db_save(instance, 's')
    # add to global limiters db
    new_rt = Global_Limiters(
        ip = instance.ip,
        identity = rt_identity,
        source_g = RoutersConfig.verbose_name
    )
    new_rt.save()
    # add router's queue types to table
    list_qt = api.get_resource('/queue/type')
    list_qts = sorted(list_qt.get(), key=lambda k: k['name'])
    for i in list_qts:
        qt = Queue_types(
            name = i['name'],
            kind = i['kind'],
            limiter_rt = instance
        )
        qt.save()
    # add router's simple queues to table
    list_q = api.get_resource('/queue/simple')
    list_qs = list_q.get()
    for i in list_qs :
        if i['disabled'] == 'true':
            dis = 'yes'
        else: dis = 'no'
        if 'total-queue' in i:
            v_total_queue = i['total-queue']
        else: v_total_queue = 'default-small'
        q = Queues(
            name = i['name'],
            target = i['target'],
            max_limit = huma(i['max-limit']),
            burst_limit = huma(i['burst-limit']),
            burst_threshold = huma(i['burst-threshold']),
            burst_time = i['burst-time'],
            limit_at = huma(i['limit-at']),
            priority = i['priority'],
            bucket_size = i['bucket-size'],
            queue = i['queue'],
            parent = i['parent'],
            disabled = dis,
            total_queue = v_total_queue,
            limiter_rt = instance
        )
        q.save()
    return list_qts, list_qs

def rt_conn(rt):
    """ Connect to router's API """
    try:
        connection = routeros_api.RouterOsApiPool(
            rt.ip,
            username=rt.username,
            password=rt.password,
            plaintext_login=True
            )
        api = connection.get_api()
    except Exception:
        rt_db_save(rt, 'f')
        return False, 0, 0
    return True, connection, api

def rt_disconn(rt, connection, new_status):
    """ Disconnect router's API """
    rt_db_save(rt, new_status)
    connection.disconnect()

def data_init(list_qts, list_qs):
    """ Initialize Last_queue_types and Last_queues when adding the first router """
    lq_number = 0
    for i in list_qts:
        lqt = Last_queue_types(
            name = i['name'],
            kind = i['kind'],
        )
        lqt.save()
    all_queue_obj = []
    all_queue_obj_g = []
    for i in list_qs :
        if i['disabled'] == 'true':
            dis = 'yes'
        else: dis = 'no'
        if 'total-queue' in i:
            v_total_queue = i['total-queue']
        else: v_total_queue = 'default-small'
        y_qs_qt_total = Last_queue_types.objects.get(name=v_total_queue)
        y_qs_qt = Last_queue_types.objects.get(name=i['queue'].split('/', 1)[0])
        lq = Last_queues(
            name = i['name'],
            target = i['target'],
            max_limit = huma(i['max-limit']),
            burst_limit = huma(i['burst-limit']),
            burst_threshold = huma(i['burst-threshold']),
            burst_time = i['burst-time'],
            limit_at = huma(i['limit-at']),
            priority = i['priority'],
            bucket_size = i['bucket-size'],
            queue = y_qs_qt,
            parent = i['parent'],
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
    # used bulk_create() to avoid triggering signals
    Last_queues.objects.bulk_create(all_queue_obj)
    # add to global queues db
    Global_Last_Queues.objects.bulk_create(all_queue_obj_g)

def q_add(instance, api, move_to):
    """ Used to add new queues """
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

def q_mod(instance, api, move_to, previous):
    """ Used to modify existing queues """
    list_queues = api.get_resource('/queue/simple')
    get_q = list_queues.get(name=previous.name)
    for j in get_q:
        qid = j['id']
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
    api.get_binary_resource('/').call(
        'queue/simple/move',
        { 'numbers': bq_name , 'destination': bq_dname }
        )

def global_up(instance, previous):
    """ Used to cupdate the global queues table after add/mod of simple queues """
    if instance.id is None:
        # add to global queues db
        Global_Last_Queues.objects.create(
            name = instance.name,
            target = instance.target,
            max_limit = instance.max_limit,
            disabled = instance.disabled,
            source_g = RoutersConfig.verbose_name
            )
    else:
        # update at global queues db
        Global_Last_Queues.objects.filter(name=previous.name).update(
            name = instance.name,
            target = instance.target,
            max_limit = instance.max_limit,
            disabled = instance.disabled,
            source_g = RoutersConfig.verbose_name
            )

def rt_refresh(rt_ip):
    """ Used to check if all related config in router are in sync """
    # This will effectivly delete the router (with all related field) then re-add it
    ipa = rt_ip
    rt_record = Limiter_rt.objects.get(ip=rt_ip)
    uname = rt_record.username
    upass = rt_record.password
    Limiter_rt.objects.filter(ip=ipa).delete()
    Limiter_rt.objects.create(ip=ipa, username=uname, password=upass)

def rt_fw_list_update(api):
    """ Used to create/update firewall address list used in tasttrack filter rule """
    notrack_new_list = []
    notrack_clean_list = []
    # Build list of subnets that SHOULD be in FW_ADDRESS_LIST if there are matching simple queues
    list_routes = api.get_resource('/ip/route')
    r1 = list_routes.get()
    for i in r1:
        if ('static' in i and 'active' in i) or 'connect' in i:
            notrack_new_list.append(i['dst-address'])
    for i in notrack_new_list:
        if not Last_queues.objects.filter(target__contains=i):
            notrack_clean_list.append(i)
    notrack_new_list = list(set(notrack_new_list) - set(notrack_clean_list))
    # Get current addresses in FW_ADDRESS_LIST list (if it exists)
    address_list = api.get_resource('/ip/firewall/address-list')
    fwlist = address_list.get()
    # Clean up old firewall list entries
    for i in fwlist:
        if i['list'] == FW_ADDRESS_LIST:
            address_list.remove(id=i['id'])
    # Add new firewall list entries
    for i in notrack_new_list:
        address_list.add(list=FW_ADDRESS_LIST, address=i)

def qt_compare( rt ):
    """ Used to compare queue types """
    lqt = Last_queue_types.objects.values_list('name', 'kind').all()
    qt = Queue_types.objects.values_list('name', 'kind').filter(limiter_rt = rt)
    return bool(collections.Counter(lqt) == collections.Counter(qt))

def q_compare(rt):
    """ Used to compare simple queues """
    lq = Last_queues.objects.values_list(
        'name',
        'burst_threshold',
        'limit_at',
        'parent',
        'priority',
        'target',
        'burst_limit',
        'burst_time',
        'max_limit',
        'bucket_size'
        ).all()
    q = Queues.objects.values_list(
        'name',
        'burst_threshold',
        'limit_at',
        'parent',
        'priority',
        'target',
        'burst_limit',
        'burst_time',
        'max_limit',
        'bucket_size'
        ).filter(limiter_rt = rt)
    # Note: 'queue' and 'total_queue' were removed from list of
    # keys-to-be-compared because it uses different types in each table
    return bool(collections.Counter(lq) == collections.Counter(q))

def calc_order(max_lim):
    """ Used to calculate to which group should the simple queue be moved """
    if max_lim == '0/0':
        download_limit_s = '0'
    else:
        download_limit_s = max_lim.split('/')[1]
        download_limit_s = download_limit_s[:-1]
    download_limit = int(download_limit_s)
    if download_limit > 1000:
        return PH_1000
    if download_limit > 750:
        return PH_750
    if download_limit > 500:
        return PH_500
    if download_limit > 300:
        return PH_300
    if download_limit > 200:
        return PH_200
    if download_limit > 100:
        return PH_100
    return PH_LAST

def lqdb_order(q_name, ph_name):
    """ Used to move simple queue to correct order """
    mod_q =  Last_queues.objects.get(name=q_name)
    ph_num = Last_queues.objects.get(name=ph_name).number
    mod_q_num = mod_q.number
    if ph_num < mod_q_num:
        lq_subset = Last_queues.objects.filter(number__gte=ph_num).exclude(number__gte=mod_q_num)
        for i in lq_subset:
            # used update() to avoid triggering signals
            Last_queues.objects.filter(name=i.name).update(number=i.number + 1)
        mod_q_num = ph_num
    else:
        lq_subset = Last_queues.objects.filter(number__lt=ph_num).exclude(number__lte=mod_q_num)
        for i in lq_subset:
            # used update() to avoid triggering signals
            Last_queues.objects.filter(name=i.name).update(number=i.number - 1)
        mod_q_num = ph_num - 1
    Last_queues.objects.filter(name=q_name).update(number=mod_q_num)

def q_gen_export():
    """ Used to generate export script of simple queues from DB """
    simple_queues_ex =StringIO('')
    simple_queues_ex.write('/queue simple\n')
    dt_now = datetime.now()
    filename = (
        RoutersConfig.verbose_name + \
        '-s_queues_export-' + \
        dt_now.strftime("%Y-%m-%d-%H_%M_%S") + \
        '.rsc'
    )
    lq = Last_queues.objects.all()
    for i in lq:
        c_queue = i.queue.name + '/' + i.queue.name
        c_total_queue = i.total_queue.name
        simple_queue = 'add name=' + i.name + ' target=' + \
            i.target + ' max-limit=' + i.max_limit + \
            ' burst-limit=' + i.burst_limit + \
            ' burst-threshold=' + i.burst_threshold + \
            ' burst-time=' + i.burst_time + \
            ' limit-at=' + i.limit_at + \
            ' priority=' + i.priority + \
            ' bucket-size=' + i.bucket_size + \
            ' queue=' + c_queue + ' parent=' + \
            i.parent + ' disabled=' + i.disabled + \
            ' total-queue=' + c_total_queue + '\n'
        simple_queues_ex.write(simple_queue)
    response = HttpResponse(simple_queues_ex.getvalue(), content_type='text/plain')
    response['Content-Disposition'] = 'attachment; filename= "%s"' % filename
    simple_queues_ex.close()
    return response

def rt_db_save(rt, new_status):
    """ Update and save limiter db entry """
    from .signals import rt_add
    rt.status = new_status
    rt.last_updated = timezone.now()
    # prevent triggering post_save signal!
    post_save.disconnect(rt_add, sender=Limiter_rt)
    rt.save()
    # Re-enable signal when adding queues to Last_queues
    post_save.connect(rt_add, sender=Limiter_rt)
