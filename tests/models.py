from django.db import models


# from django_watcher.decorators import watched

# from .watchers import DeleteWatcher


class WatcherModel(models.Model):
    class Meta:
        app_label = 'tests'
        abstract = True


# @watched(DeleteWatcher, ['delete'])
class DeleteModel(WatcherModel):
    text = models.CharField(max_length=100)
