"""
Group's model definitions
"""

from django.db import models

class GlobalLimiters(models.Model):
    """ The table to summarize all limiter routers """
    ip = models.CharField(max_length=50, unique=True)
    identity = models.CharField(max_length=64, default = '')
    source_g = models.CharField(max_length=50, verbose_name="Source Group")
    class Meta:
        verbose_name = "All Limiter Router"
    def __str__(self):
        return f"'{self.ip}' - Source: ' {self.source_g}"

class GlobalLastQueues(models.Model):
    """ The table to summarize all simple queues """
    name = models.CharField(
        max_length=96,
        unique=True,
        error_messages={'unique':"A simple queue with this name has already been registered."}
        )
    target = models.CharField(max_length=180)
    max_limit = models.CharField(max_length=24, default='1/1')
    disabled = models.CharField(max_length=3)
    source_g = models.CharField(max_length=50, verbose_name="Source Group")
    class Meta:
        verbose_name = "All Simple Queues"
        ordering = ["source_g"]
    def __str__(self):
        return f"'{self.name}' - Limit: '{self.max_limit}' - Source: ' {self.source_g}"
