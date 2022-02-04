from typing import no_type_check

from django.db import models

from django_watcher.decorators import watched

from . import watchers


class StubQuerySet(models.QuerySet):
    @no_type_check
    def __eq__(self, __o: object) -> bool:
        return (
            (
                self.model == __o.model
                and self.query.chain().__str__() == __o.query.chain().__str__()
                and self._db == __o._db
                and self._hints == __o._hints
            )
            if isinstance(__o, models.QuerySet)
            else super().__eq__(__o)
        )


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
