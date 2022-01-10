from django.db import models

from django_watcher.decorators import watched

from . import watchers


class WatcherModel(models.Model):
    text = models.CharField(max_length=100)

    def __eq__(self, __o: object) -> bool:
        if type(self) == type(__o) and self.id is None and __o.id is None:  # noqa
            return self.text == __o.text
        return super().__eq__(__o)

    class Meta:
        app_label = 'tests'
        abstract = True


@watched(watchers.StubCreateWatcher, ['create'])
class CreateModel(WatcherModel):
    pass


@watched(watchers.StubDeleteWatcher, ['delete'])
class DeleteModel(WatcherModel):
    pass


@watched(watchers.StubSaveWatcher, ['save'])
class SaveModel(WatcherModel):
    pass


@watched(watchers.StubUpdateWatcher, ['update'])
class UpdateModel(WatcherModel):
    pass
