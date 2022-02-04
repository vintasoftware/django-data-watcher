# type: ignore[override]

from typing import Any, Dict, Tuple, no_type_check

from django.db.models import Manager, QuerySet

from django_watcher.decorators import watched


class StubQuerySet(QuerySet):
    @no_type_check
    def __eq__(self, __o: object) -> bool:
        return (
            (
                self.model == __o.model
                and self.query.chain().__str__() == __o.query.chain().__str__()
                and self._db == __o._db
                and self._hints == __o._hints
            )
            if isinstance(__o, QuerySet)
            else super().__eq__(__o)
        )


class SpyableQuerySet(StubQuerySet):
    # pylint: disable=arguments-differ
    def update(self, new_param: str, **kwargs: Any) -> int:
        watched(new_param)
        return super().update(**kwargs)

    def create(self, new_param, *args: Any, **kwargs: Any):
        watched(new_param)
        return super().create(*args, **kwargs)

    def delete(self, new_param) -> Tuple[int, Dict[str, int]]:
        watched(new_param)
        return super().delete()


class SpyableManager(Manager.from_queryset(SpyableQuerySet)):
    pass


class SubSpyableManager(SpyableManager):
    pass
