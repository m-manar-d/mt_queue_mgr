"""
Group's model definitions
"""

from django.db import models
from core.core_models import LimiterRtT, LastQueueTypesT, QueuesMT, LastQueuesT

class LimiterRT(LimiterRtT):
    """ Limiter routers' table """

class QueueTypes(LastQueueTypesT):
    """ Queue types per router table """
    name = models.CharField(max_length=64, unique=False)
    limiter_rt = models.ForeignKey(LimiterRT, on_delete=models.CASCADE)
    def __str__(self):
        return f"'{self.name}' Type: '{self.kind}' Limiter: '{self.limiter_rt}'"
    class Meta:
        verbose_name = "Per-Router Queue Types table"

class LastQueueTypes(LastQueueTypesT):
    """ Queue types final table """

class Queues(QueuesMT):
    """ Simple queues per router table """
    limiter_rt = models.ForeignKey(
        LimiterRT,
        on_delete=models.CASCADE)
    def __str__(self):
        return f"'{self.name}' Limit: '{self.max_limit}' Limiter: '{self.limiter_rt}'"

class LastQueues(LastQueuesT):
    """ Simple queues final table """
    queue = models.ForeignKey(
        LastQueueTypes,
        related_name='queue',
        on_delete=models.PROTECT
        )
    total_queue = models.ForeignKey(
        LastQueueTypes,
        related_name='total_queue',
        on_delete=models.PROTECT
        )
