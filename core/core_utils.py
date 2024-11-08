"""
Several utility methods buy multiple apps
"""

import threading
import collections
import logging
import csv
from io import StringIO, TextIOWrapper
from datetime import datetime
from routeros_api import exceptions as RosExcep

# required to generate export file in memory
from django.http import HttpResponse
from django.utils import timezone
from django.conf import settings
from django.db.models.signals import post_delete

from core.limiter import Limiter
from limiters_global.models import GlobalLimiters, GlobalLastQueues

logger = logging.getLogger('mt_queue_mgr')
fw_add_list = settings.FW_ADDRESS_LIST

def huma(raw):
    """ Used to humanize the numbers """
    hum_g = 'G'.join(raw.rsplit('000000000'))
    hum_m = 'M'.join(hum_g.rsplit('000000'))
    hum = 'K'.join(hum_m.rsplit('000'))
    return hum

def rt_init(instance, con_rt, source_v_name, queue_types_db, queues_db):
    """ Add limiter router record to table """
    instance.identity = con_rt.identity
    rt_db_save(instance, 's')
    # add to global limiters db
    new_rt = GlobalLimiters(
        ip = instance.ip,
        identity = con_rt.identity,
        source_g = source_v_name
    )
    new_rt.save()
    # add router's queue types to table
    list_qts = sorted(con_rt.list_qts.get(), key=lambda k: k['name'])
    for i in list_qts:
        qt = queue_types_db(
            name = i['name'],
            kind = i['kind'],
            limiter_rt = instance
        )
        qt.save()
    # add router's simple queues to table
    list_qs = con_rt.list_queues.get()
    for i in list_qs :
        if i['disabled'] == 'true':
            dis = 'yes'
        else: dis = 'no'
        if 'total-queue' in i:
            v_total_queue = i['total-queue']
        else: v_total_queue = 'default-small'
        q = queues_db(
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

def rt_db_save(rt, new_status):
    """ Update and save limiter db entry """
    rt.status = new_status
    rt.last_updated = timezone.now()
    rt.save()
    logger.info("Limiter %s status has changed to %s", rt.ip, new_status)

def data_init(list_qts, list_qs, source_name, last_queue_types_db, last_queues_db):
    """ Initialize Last_queue_types and Last_queues when adding the first router """
    lq_number = 0
    for i in list_qts:
        lqt = last_queue_types_db(
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
        y_qs_qt_total = last_queue_types_db.objects.get(name=v_total_queue)
        y_qs_qt = last_queue_types_db.objects.get(name=i['queue'].split('/', 1)[0])
        lq = last_queues_db(
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
        queue_obj_g = GlobalLastQueues(
            name = lq.name,
            target = lq.target,
            max_limit = lq.max_limit,
            disabled = lq.disabled,
            source_g = source_name
        )
        all_queue_obj_g.append(queue_obj_g)
        lq_number += 1
    # used bulk_create() to avoid triggering signals
    last_queues_db.objects.bulk_create(all_queue_obj)
    # add to global queues db
    GlobalLastQueues.objects.bulk_create(all_queue_obj_g)

def rt_refresh(rt_ip, limiter_rt_db):
    """ Used to check if all related config in router are in sync """
    # This will effectivly delete the router (with all related field) then re-add it
    rt_record = limiter_rt_db.objects.get(ip=rt_ip)
    uname = rt_record.username
    upass = rt_record.password
    limiter_rt_db.objects.filter(ip=rt_ip).delete()
    limiter_rt_db.objects.create(ip=rt_ip, username=uname, password=upass)

def q_add(instance, con_rt, move_to):
    """ Used to add new queues """
    con_rt.list_queues.add(
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

def q_mod(instance, con_rt, move_to, previous):
    """ Used to modify existing queues """
    get_q = con_rt.list_queues.get(name=previous.name)
    for j in get_q:
        qid = j['id']
    con_rt.list_queues.set(id=qid,
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
    con_rt.bin_com.call(
        'queue/simple/move',
        { 'numbers': bq_name , 'destination': bq_dname }
        )

def q_save_dup_check(q_name):
    if GlobalLastQueues.objects.filter(name=q_name):
        return False
    return True

def q_save_pre_s(i, move_to, previous, instance, caller_func):
    """ pre_save actions after adding/modifying a simple queue entry """
    con_rt = Limiter(i.ip, i.username, i.password)
    if con_rt.connected is False:
        logger.error("Limiter: %s is not responding, status changed to 'f'", i.ip)
        rt_db_save(i, 'f')
        return
    # if created:
    if previous is None:
        try:
            q_add(instance, con_rt, move_to)
            # refresh entries in firewall address_list:
            rt_fw_list_update(con_rt, caller_func.last_queues_db)
        except RosExcep.RouterOsApiCommunicationError as error:
            logger.error("Limiter: %s %s", i.ip, error.original_message.decode('ascii'))
            rt_db_save(i, 's')
            return
        rt_db_save(i, 'o')
        caller_func.rt_modified = True
        return
    # if not created but modified
    try:
        q_mod(instance, con_rt, move_to, previous)
        # refresh entries in firewall address_list:
        rt_fw_list_update(con_rt, caller_func.last_queues_db)
    except RosExcep.RouterOsApiCommunicationError as error:
        logger.error("Limiter: %s %s", i.ip, error.original_message.decode('ascii'))
        rt_db_save(i, 's')
        return
    except UnboundLocalError:
        try:
            q_add(instance, con_rt, move_to)
        except Exception:
            logger.error("Limiter: %s Referenced queue missing! Attempt to add it failed!",
                            i.ip
                            )
            rt_db_save(i, 's')
            return
        logger.warning("Limiter: %s Referenced queue was missing but added successfully!",
                        i.ip
                        )
    rt_db_save(i, 'o')
    caller_func.rt_modified = True

def qt_compare(rt, last_queue_types_db, queue_types_db):
    """ Used to compare queue types """
    lqt = last_queue_types_db.objects.values_list('name', 'kind').all()
    qt = queue_types_db.objects.values_list('name', 'kind').filter(limiter_rt = rt)
    return bool(collections.Counter(lqt) == collections.Counter(qt))

def q_compare(rt, last_queues_db, queues_db):
    """ Used to compare simple queues """
    # All listed fields will be compared and if different values are encountered \n
    # for the same entry the router will be marked as 's'
    lq = last_queues_db.objects.values_list(
        'name',
        'burst_threshold',
        'target',
        'burst_limit',
        'max_limit'
        ).all()
    q = queues_db.objects.values_list(
        'name',
        'burst_threshold',
        'target',
        'burst_limit',
        'max_limit'
        ).filter(limiter_rt = rt)
    # Note: 'queue' and 'total_queue' were removed from list of \n
    # keys-to-be-compared because it uses different types in each table
    result = bool(collections.Counter(lq) == collections.Counter(q))
    if not result:
        logger.warning(
            "Checking Router: %s, but differences were encountered, Router has: %s but DB has: %s",
            rt.ip,
            collections.Counter(q) - collections.Counter(lq),
            collections.Counter(lq) - collections.Counter(q)
            )
    return result

def calc_order(max_lim, source_name):
    """ Used to calculate to which group should the simple queue be moved """
    if max_lim == '0/0':
        download_limit_s = '0'
    else:
        download_limit_s = max_lim.split('/')[1]
        download_limit_s = download_limit_s[:-1]
    download_limit = int(download_limit_s)
    bw_ranges = {
        range(1000, 10000): source_name + '-1000',
        range(751, 999): (source_name + '-750'),
        range(500, 749): (source_name + '-500'),
        range(300, 499): (source_name + '-300'),
        range(200, 299): (source_name + '-200'),
        range(100, 199): (source_name + '-100'),
        range(0, 99): (source_name + '-last'),
    }
    for key, sep_queue in bw_ranges.items():
        if download_limit in key:
            return sep_queue

def lqdb_order(q_name, ph_name, last_queues_db):
    """ Used to move simple queue to correct order """
    mod_q =  last_queues_db.objects.get(name=q_name)
    ph_num = last_queues_db.objects.get(name=ph_name).number
    mod_q_num = mod_q.number
    if ph_num < mod_q_num:
        lq_subset = last_queues_db.objects.filter(number__gte=ph_num).exclude(number__gte=mod_q_num)
        for i in lq_subset:
            # used update() to avoid triggering signals
            last_queues_db.objects.filter(name=i.name).update(number=i.number + 1)
        mod_q_num = ph_num
    else:
        lq_subset = last_queues_db.objects.filter(number__lt=ph_num).exclude(number__lt=mod_q_num)
        for i in lq_subset:
            # used update() to avoid triggering signals
            last_queues_db.objects.filter(name=i.name).update(number=i.number - 1)
        mod_q_num = ph_num - 1
    last_queues_db.objects.filter(name=q_name).update(number=mod_q_num)

def global_up(instance, previous, source_name):
    """ Used to cupdate the global queues table after add/mod of simple queues """
    if instance.id is None:
        # add to global queues db
        GlobalLastQueues.objects.create(
            name = instance.name,
            target = instance.target,
            max_limit = instance.max_limit,
            disabled = instance.disabled,
            source_g = source_name
            )
    else:
        # update at global queues db
        GlobalLastQueues.objects.filter(name=previous.name).update(
            name = instance.name,
            target = instance.target,
            max_limit = instance.max_limit,
            disabled = instance.disabled,
            source_g = source_name
            )

def rt_fw_list_update(con_rt, last_queues_db):
    """ Used to create/update firewall address list used in tasttrack filter rule """
    notrack_new_list = []
    notrack_clean_list = []
    # Build list of subnets that SHOULD be in FW_ADDRESS_LIST if there are matching simple queues
    r1 = con_rt.list_routes.get(static='true',inactive='false')
    r1 = r1 + con_rt.list_routes.get(connect='true')
    for i in r1:
        notrack_new_list.append(i['dst-address'])
    for i in notrack_new_list:
        if not last_queues_db.objects.filter(target__contains=i):
            notrack_clean_list.append(i)
    notrack_new_list = list(set(notrack_new_list) - set(notrack_clean_list))
    # Get current addresses in FW_ADDRESS_LIST list (if it exists)
    fwlist = con_rt.list_fw_add.get()
    # Clean up old firewall list entries
    for i in fwlist:
        if i['list'] == fw_add_list:
            con_rt.list_fw_add.remove(id=i['id'])
    # Add new firewall list entries
    for i in notrack_new_list:
        con_rt.list_fw_add.add(list=fw_add_list, address=i)

def q_gen_export(source_name, last_queues_db):
    """ Used to generate export script of simple queues from DB """
    simple_queues_ex =StringIO('')
    simple_queues_ex.write('/queue simple\n')
    dt_now = datetime.now()
    filename = (
        source_name + \
        '-s_queues_export-' + \
        dt_now.strftime("%Y-%m-%d-%H_%M_%S") + \
        '.rsc'
    )
    lq = last_queues_db.objects.all()
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
    response = HttpResponse(
        simple_queues_ex.getvalue(),
        headers={
            "content_type": "text/plain",
            "Content-Disposition": f'attachment; filename= {filename}',
            },
        )
    simple_queues_ex.close()
    return response

def q_gen_rt_export(source_name, limiter_rt_db):
    """ Used to generate export script of simple queues from DB """
    limiters_ex =StringIO('')
    dt_now = datetime.now()
    filename = (
        source_name + \
        '-limiters_export-' + \
        dt_now.strftime("%Y-%m-%d-%H_%M_%S") + \
        '.csv'
    )
    lrt = limiter_rt_db.objects.all()
    for i in lrt:
        rt_record = i.ip + "," + i.username + "," + i.password + "\n"
        limiters_ex.write(rt_record)
    response = HttpResponse(
        limiters_ex.getvalue(),
        headers={
            "content_type": "text/csv",
            "Content-Disposition": f'attachment; filename= {filename}',
            },
        )
    limiters_ex.close()
    return response

def batch_add(file, limiter_rt_db):
    """ Used to import Limiters from uploaded .csv file """
    is_empty = False
    rt_added = False
    counter = 0
    if not limiter_rt_db.objects.all():
        is_empty = True
    encoded_f = TextIOWrapper(file, encoding='ascii', errors='replace')
    imported_text = csv.reader(encoded_f)
    for i in imported_text:
        if limiter_rt_db.objects.filter(ip=i[0]):
            logger.warning("A limiter with IP %s already in table!", i[0])
            continue
        tid = threading.Thread(
            target=import_limiters,
            args=(limiter_rt_db, i[0], i[1], i[2],)
            )
        tid.start()
        if is_empty:
            tid.join()
            is_empty = False
        counter += 1
        logger.info("A limiter with IP %s is successfuly added!", i[0])
        if not rt_added:
            rt_added = True
    if rt_added:
        return True, counter
    return False, 0

def import_limiters(limiter_rt_db, rt_ip, rt_user, rt_pass):
    """ Threads used to import Limiters from uploaded .csv file """
    new_rt = limiter_rt_db(
        ip = rt_ip,
        username = rt_user,
        password = rt_pass,
        )
    new_rt.save()

# ==================================================================
# Functions used by signals:
# ==================================================================
def rt_add_post_s(instance, source_name):
    """ post_save actions after adding a limiter router to table """
    module = __import__(source_name)
    source_v_name = module.apps.RoutersConfig.verbose_name
    limiter_rt_db = module.models.LimiterRT
    queue_types_db = module.models.QueueTypes
    last_queue_types_db = module.models.LastQueueTypes
    queues_db = module.models.Queues
    last_queues_db = module.models.LastQueues
    con_rt = Limiter(instance.ip, instance.username, instance.password)
    if con_rt.connected is False:
        return
    rt_data = rt_init(instance, con_rt, source_v_name, queue_types_db, queues_db)
    list_qts = rt_data[0]
    list_qs = rt_data[1]
    # if this is the first router in this group:
    if not limiter_rt_db.objects.exclude(ip=instance.ip).all():
        data_init(list_qts, list_qs, source_v_name, last_queue_types_db, last_queues_db)
        instance.status = 'o'
    else:
        # if not the first, then check if data is synchronized:
        if qt_compare(
            instance, last_queue_types_db, queue_types_db)\
                and\
                    q_compare(instance, last_queues_db, queues_db):
            instance.status = 'o'
    # refresh entries in firewall address_list:
    if instance.status == 'o':
        rt_fw_list_update(con_rt, last_queues_db)
    # update limiter's record and save
    rt_db_save(instance, instance.status)

def rt_delete_post_d(instance, source_name):
    """ post_delete actions after deleting a limiter router from table """
    module = __import__(source_name)
    source_v_name = module.apps.RoutersConfig.verbose_name
    limiter_rt_db = module.models.LimiterRT
    queue_types_db = module.models.QueueTypes
    last_queue_types_db = module.models.LastQueueTypes
    queues_db = module.models.Queues
    last_queues_db = module.models.LastQueues
    q_rem_s = getattr(module.signals, 'q_rem')
    # remove from global limiters db
    GlobalLimiters.objects.filter(ip=instance.ip).delete()
    # if the deleted router was the last entry in routers table:
    if not limiter_rt_db.objects.all():
        # prevent triggering delete signal when clearing LastQueues by this function
        post_delete.disconnect(q_rem_s, sender=last_queues_db)
        if last_queues_db.objects.all():
            last_queues_db.objects.all().delete()
        if last_queue_types_db.objects.all():
            last_queue_types_db.objects.all().delete()
        if queues_db.objects.all():
            queues_db.objects.all().delete()
        if queue_types_db.objects.all():
            queue_types_db.objects.all().delete()
        # Re-enable signal when adding queues to LastQueues
        post_delete.connect(q_rem_s, sender=last_queues_db)
        # remove all from global queues db
        GlobalLastQueues.objects.filter(source_g=source_v_name).delete()

def q_rem_post_d(instance, source_name):
    """ post_delete actions after deleting simple queue entry """
    # delete from global queues db
    module = __import__(source_name)
    limiter_rt_db = module.models.LimiterRT
    last_queues_db = module.models.LastQueues
    GlobalLastQueues.objects.filter(name=instance.name).delete()
    for i in limiter_rt_db.objects.all():
        if i.status != 'o':
            continue
        con_rt = Limiter(i.ip, i.username, i.password)
        if con_rt.connected is False:
            rt_db_save(i, 'f')
            continue
        list_queues = con_rt.list_queues
        get_q = list_queues.get(name=instance.name)
        for j in get_q:
            qid = j['id']
        list_queues.remove(id=qid)
        # refresh entries in firewall address_list:
        rt_fw_list_update(con_rt, last_queues_db)
        # update limiter's record and save
        rt_db_save(i, 'o')

def q_addmod_post_s(instance, source_name):
    """ post_save actions after adding/modifying a simple queue entry """
    module = __import__(source_name)
    last_queues_db = module.models.LastQueues
    move_to = calc_order(instance.max_limit, source_name)
    lqdb_order(instance.name, move_to, last_queues_db)
