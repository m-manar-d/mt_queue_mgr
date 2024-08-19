"""
Group's model definitions
"""

from django.db import models
from django.utils import timezone

RT_STATUS_CHOICES = [
    ('f', 'offline'),
    ('o', 'online'),
    ('s', 'syncing'),
]

class Limiter_rt(models.Model):
    """ Limiter routers table """
    ip = models.CharField(max_length=50, unique=True)
    identity = models.CharField(max_length=64, default = '')
    username = models.CharField(max_length=50)
    password = models.CharField(max_length=50)
    status = models.CharField(
        max_length = 7,
        choices=RT_STATUS_CHOICES,
        default='f',
    )
    last_updated = models.DateTimeField(default = timezone.now)
    class Meta:
        verbose_name = "Limiter Router"
    def __str__(self):
        return f"'{self.ip}' - status: '{self.status}'"

class Last_queue_types(models.Model):
    """ Queue types final table """
    name = models.CharField(max_length=64, unique=True)
    kind = models.CharField(max_length = 50)
    class Meta:
        verbose_name = "Queue Type"
    def __str__(self):
        return f"'{self.name}' Type: '{self.kind}'"

class Queue_types(models.Model):
    """ Queue types per router table """
    name = models.CharField(max_length=64, unique=False)
    kind = models.CharField(max_length = 50)
    limiter_rt = models.ForeignKey(Limiter_rt, on_delete=models.CASCADE)
    class Meta:
        verbose_name = "Per Router Queue Type"
    def __str__(self):
        return f"'{self.name}' Type: '{self.kind}' Limiter: '{self.limiter_rt}'"

class Queues_T(models.Model):
    """ Simple queues table template """
    name = models.CharField(max_length=64)
    target = models.CharField(max_length=180)
    max_limit = models.CharField(max_length=24, default='1/1')
    burst_limit = models.CharField(max_length=24)
    burst_threshold = models.CharField(max_length=24)
    burst_time = models.CharField(max_length=24)
    limit_at = models.CharField(max_length=24)
    priority = models.CharField(max_length=24)
    bucket_size = models.CharField(max_length=24)
    queue = models.CharField(max_length=24)
    parent = models.CharField(max_length=24, default = 'none')
    disabled = models.CharField(
        max_length=3,
        choices=[('yes', 'yes'),
                ('no', 'no'),]
        )
    total_queue = models.CharField(max_length=24)
    class Meta:
        abstract = True

class Last_queues(Queues_T):
    """ Simple queues final table """
    name = models.CharField(max_length=64, unique=True)
    queue = models.ForeignKey(Last_queue_types, related_name='queue', on_delete=models.PROTECT)
    total_queue = models.ForeignKey(
        Last_queue_types,
        related_name='total_queue',
        on_delete=models.PROTECT
        )
    number = models.IntegerField(default = 10000)
    class Meta:
        verbose_name = "Simple Queue"
        ordering = ["number"]
    def __str__(self):
        return f"'{self.name}' Limit: '{self.max_limit}'"

class Queues(Queues_T):
    """ Simple queues per router table """
    limiter_rt = models.ForeignKey(Limiter_rt, on_delete=models.CASCADE)
    class Meta:
        verbose_name = "Per Router Simple Queue"
    def __str__(self):
        return f"'{self.name}' Limit: '{self.max_limit}' Limiter: '{self.limiter_rt}'"
