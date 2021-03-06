from django.db import models
from django.contrib.auth.models import User


class Job(models.Model):
    name = models.CharField(unique=True, max_length=128)
    type = models.CharField(max_length=10, choices=(
        ('hourly', 'hourly'),
        ('daily', 'daily'),
        ('daily_9am', 'daily_9am'),
        ('daily_7pm', 'daily_7pm'),
        ('weekly', 'weekly'),
        ('monthly', 'monthly')
    ),
        default='hourly',
    )
    dashboard = models.ForeignKey('website.Dashboard')
    owner = models.ForeignKey(User)
    create_time = models.DateTimeField(auto_now_add=True, editable=False)
    last_run_time = models.DateTimeField(auto_now=True, editable=False)

    def __str__(self):
        return self.name

    def clean(self):
        return True  # TODO Validate database connection


class EmailUser(models.Model):

    class Meta:
        unique_together = ['user', 'job']
    job = models.ForeignKey(Job)
    user = models.ForeignKey(User)
