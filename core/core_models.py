"""
Model templates
"""

from django.db import models
from django.utils import timezone

RT_STATUS_CHOICES = [
    ('f', 'offline'),
    ('o', 'online'),
    ('s', 'syncing'),
]

class LimiterRtT(models.Model):
    """ Limiter routers table template"""
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
    def __str__(self):
        return f"'{self.ip}' - status: '{self.status}'"
    class Meta:
        verbose_name = "Limiter Routers"
        abstract = True

class LastQueueTypesT(models.Model):
    """ Queue types final table """
    name = models.CharField(max_length=64, unique=True)
    kind = models.CharField(max_length = 50)
    def __str__(self):
        return f"'{self.name}' Type: '{self.kind}'"
    class Meta:
        verbose_name = "Queue Types"
        abstract = True

class QueuesMT(models.Model):
    """ Simple Queues tables main template """
    name = models.CharField(max_length=96)
    target = models.CharField(max_length=180)
    max_limit = models.CharField(max_length=24, default='1/1')
    burst_limit = models.CharField(max_length=24)
    burst_threshold = models.CharField(max_length=24)
    burst_time = models.CharField(max_length=24)
    limit_at = models.CharField(max_length=24)
    priority = models.CharField(max_length=24)
    bucket_size = models.CharField(max_length=24)
    queue = models.CharField(max_length=64)
    parent = models.CharField(max_length=24, default = 'none')
    disabled = models.CharField(
        max_length=3,
        choices=[('yes', 'yes'),
                ('no', 'no'),]
        )
    total_queue = models.CharField(max_length=24)
    class Meta:
        verbose_name = "Per Router Simple Queues"
        abstract = True

class LastQueuesT(QueuesMT):
    """ Simple queues final table """
    name = models.CharField(max_length=96, unique=True)
    number = models.IntegerField(default = 10000)
    def __str__(self):
        return f"'{self.name}' Limit: '{self.max_limit}'"
    class Meta:
        verbose_name = "Simple Queues"
        ordering = ["number"]
        abstract = True
