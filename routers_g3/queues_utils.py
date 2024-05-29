from routers_g3.models import Limiter_rt, Last_queue_types, Last_queues, Queue_types, Queues
import routeros_api
import collections
# v2 added:
# (required to generate export file in memory)
from io import StringIO
from django.http import HttpResponse
from datetime import datetime
from routers_g3.apps import RoutersConfig


# v2 added:
ph_1000 = 'g3-queues-1000'
ph_750 = 'g3-queues-750'
ph_500 = 'g3-queues-500'
ph_300 = 'g3-queues-300'
ph_200 = 'g3-queues-200'
ph_100 = 'g3-queues-100'
ph_last = 'g3-queues-last'
FW_address_list = 'NoFastTrack'

def huma(raw):
    # used to humanize the numbers
    humG = 'G'.join(raw.rsplit('000000000'))
    humM = 'M'.join(humG.rsplit('000000'))
    hum = 'K'.join(humM.rsplit('000'))
    return(hum)

def qt_compare( rt ):
    lqt = Last_queue_types.objects.values_list('name', 'kind').all()
    qt = Queue_types.objects.values_list('name', 'kind').filter(limiter_rt = rt)
    # v2 edited
    if collections.Counter(lqt) == collections.Counter(qt): return(True)
    else: return(False)

def q_compare(rt):
    lq = Last_queues.objects.values_list('name', 'burst_threshold', 'limit_at', 'parent', 'priority', 'target', 'burst_limit', 'burst_time', 'max_limit', 'bucket_size').all()
    q = Queues.objects.values_list('name', 'burst_threshold', 'limit_at', 'parent', 'priority', 'target', 'burst_limit', 'burst_time', 'max_limit', 'bucket_size').filter(limiter_rt = rt)
    # v2 edited the note:
    # 'queue' and 'total_queue' is removed from the list of keys to be compared because it uses different types in each table
    if collections.Counter(lq) == collections.Counter(q): return(True)
    else: return(False)

def rt_refresh(rt_ip):
    ipa = rt_ip
    rt_record = Limiter_rt.objects.get(ip=rt_ip)
    uname = rt_record.username
    upass = rt_record.password
    Limiter_rt.objects.filter(ip=ipa).delete()
    Limiter_rt.objects.create(ip=ipa, username=uname, password=upass)

# v2 added:
def rt_fw_list_update(rt_ip):
    rt_record = Limiter_rt.objects.get(ip=rt_ip)
    uname = rt_record.username
    upass = rt_record.password
    try:
        connection = routeros_api.RouterOsApiPool(rt_ip, username=uname, password=upass ,plaintext_login=True)
        api = connection.get_api()
    except:
        rt_record.status = 'f'
        rt_record.save()
        connection.disconnect()
    notrack_new_list = []
    notrack_old_list = []
    notrack_clean_list = []
    # Build list of subnets that SHOULD be in FW_address_list if there are matching simple queues
    list_routes1 = api.get_resource('/ip/route')
    r1 = list_routes1.get()
    for x in r1:
        if 'static' in x and 'active' in x:
            notrack_new_list.append(x['dst-address'])
        if 'connect' in x:
            notrack_new_list.append(x['dst-address'])
    # Get current addresses in FW_address_list list (if it exists)
    address_list1 = api.get_resource('/ip/firewall/address-list')
    l1 = address_list1.get()
    for y in l1:
        if  y['list'] == FW_address_list: notrack_old_list.append(y['address'])
    # Generate lists of addresses to be added/cleaned from FW_address_list list
    # Check old entries with no matching routes
    for i in notrack_old_list:
        cleanit = True
        for j in notrack_new_list:
            if i == j: cleanit = False
        if cleanit: notrack_clean_list.append(i)
    # Check old entries with no matching queue targets, add them to cleanlist if not already there
    for i in notrack_old_list:
        if not Last_queues.objects.filter(target__contains=i):
            if i not in notrack_clean_list: notrack_clean_list.append(i)
    # Update old list to reflect the remaining contents
    updated_old_list = list(set(notrack_old_list) - set(notrack_clean_list))
    # Remove entries that will remain in OLD list from new list
    updated_new_list = list(set(notrack_new_list) - set(updated_old_list))
    # Check new entries with no queue target match
    rem_list = []
    for i in notrack_new_list:
        if not Last_queues.objects.filter(target__contains=i):rem_list.append(i)
    for i in rem_list: updated_new_list.remove(i)
    # apply to router then close connection
    for i in notrack_clean_list:
        for y in l1:
            if y['list'] == FW_address_list and y['address'] == i:
                address_list1.remove(id=y['id'])
    for i in updated_new_list:
        address_list1.add(list=FW_address_list, address=i)
    connection.disconnect()

# v2 added:
def lqdb_order(q_name, ph_name):
    mod_q =  Last_queues.objects.get(name=q_name)
    ph_num = Last_queues.objects.get(name=ph_name).number
    mod_q_num = mod_q.number
    if ph_num < mod_q_num:
        lq_subset = Last_queues.objects.filter(number__gte=ph_num).exclude(number__gte=mod_q_num)
        for y in lq_subset:
            # used update() to avoid triggering signals.
            Last_queues.objects.filter(name=y.name).update(number=y.number + 1)
        mod_q_num = ph_num
    else:
        lq_subset = Last_queues.objects.filter(number__lt=ph_num).exclude(number__lte=mod_q_num)
        for y in lq_subset:
            # used update() to avoid triggering signals.
            Last_queues.objects.filter(name=y.name).update(number=y.number - 1)
        mod_q_num = ph_num - 1
    Last_queues.objects.filter(name=q_name).update(number=mod_q_num)

# v2 added:
def q_gen_export():
    simple_queues_ex =StringIO('')
    simple_queues_ex.write('/queue simple\n')
    dt_now = datetime.now()
    filename = RoutersConfig.verbose_name + '-s_queues_export-' + dt_now.strftime("%Y-%m-%d-%H_%M_%S") + '.rsc'
    lq = Last_queues.objects.all()
    for y in lq:
        c_queue = y.queue.name + '/' + y.queue.name
        c_total_queue = y.total_queue.name
        simple_queue = 'add name="' + y.name + '" target=' + y.target + ' max-limit=' + y.max_limit + \
            ' burst-limit=' + y.burst_limit + ' burst-threshold=' + y.burst_threshold + \
            ' burst-time=' + y.burst_time + ' limit-at=' + y.limit_at + ' priority=' + y.priority + \
            ' bucket-size=' + y.bucket_size + ' queue=' + c_queue + ' parent=' + y.parent + \
            ' disabled=' + y.disabled + ' total-queue=' + c_total_queue + '\n'
        simple_queues_ex.write(simple_queue)
    response = HttpResponse(simple_queues_ex.getvalue(), content_type='text/plain')
    response['Content-Disposition'] = 'attachment; filename= "%s"' % filename
    simple_queues_ex.close()
    return response

# v2 added
def calc_order(max_lim):
    move_to = ph_last
    if max_lim == '0/0': download_limit_s = '0'
    else: 
        download_limit_s = max_lim.split('/')[1]
        download_limit_s = download_limit_s[:-1]
    download_limit = int(download_limit_s)
    if download_limit > 1000: move_to = ph_1000 
    else:
        if download_limit > 750: move_to = ph_750
        else:
            if download_limit > 500: move_to = ph_500
            else:
                if download_limit > 300: move_to = ph_300
                else:
                    if download_limit > 200: move_to = ph_200
                    else:
                        if download_limit > 100: move_to = ph_100
    return(move_to)
