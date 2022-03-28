from typing import no_type_check

from django.db import models

from django_watcher.decorators import watched

from . import watchers
from .managers import SpyableManager, StubQuerySet, SubSpyableManager  # type: ignore


class WatcherModel(models.Model):
    text = models.CharField(max_length=100)

    objects = models.Manager.from_queryset(StubQuerySet)()

    @no_type_check
    def __eq__(self, __o: object) -> bool:
        if type(self) == type(__o) and self.id is None and __o.id is None:  # noqa
            return self.text == __o.text
        return super().__eq__(__o)

    def __hash__(self):  # noqa
        return super().__hash__()

    class Meta:
        app_label = 'tests'
        abstract = True


# region Models
@watched(watchers.StubCreateWatcher)
class CreateModel(WatcherModel):
    pass


@watched(watchers.StubDeleteWatcher)
class DeleteModel(WatcherModel):
    pass


@watched(watchers.StubSaveWatcher)
class SaveModel(WatcherModel):
    pass


@watched(watchers.StubUpdateWatcher)
class UpdateModel(WatcherModel):
    pass


@watched(watchers.StubSaveDeleteWatcher)
class SaveDeleteModel(WatcherModel):
    pass


# endregion


# region testImportWatcher
@watched('tests.StubCreateWatcher')
class CasualStringWatcherModel(WatcherModel):
    pass


@watched('tests.StubDeleteWatcher')
class CasualStringWatcherModel2(WatcherModel):
    pass


@watched('tests.watchers.StubCreateWatcher')
class StringWatcherModel(WatcherModel):
    pass


@watched('tests.watchers.StubDeleteWatcher')
class StringWatcherModel2(WatcherModel):
    pass


# endregion


# region testCustomQueryTools


@watched(watchers.StubSaveDeleteWatcher, ['objects', 'other_objects'])
class CustomManagerModel(WatcherModel):
    objects = SpyableManager()
    other_objects = SubSpyableManager()


@watched(watchers.StubSaveDeleteWatcher2)
class CustomManagerModel2(WatcherModel):
    objects = SpyableManager()


@watched(watchers.DeleteWatcher)
class RelationDeleteModel(WatcherModel):
    pass


@watched(watchers.DeleteWatcher2)
class RelationDeleteModel2(WatcherModel):
    delete_model = models.ForeignKey(RelationDeleteModel, on_delete=models.DO_NOTHING)
