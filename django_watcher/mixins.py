from typing import Any, Dict, List, Tuple, TypeVar, Union

from django.db import models

from typing_extensions import TypedDict

from .abstract_watcher import AbstractWatcher


class _MetaParams(TypedDict):
    source: str
    operation_params: dict


class MetaParams(_MetaParams, total=False):
    unsaved_instance: models.Model


_INSTANCE = 'instance'
_QUERY_SET = 'query_set'


class WatchedDeleteModel(models.Model):
    def UNWATCHED_delete(self, **kwargs) -> Tuple[int, Dict[str, int]]:  # noqa
        pass


class WatchedSaveModel(models.Model):
    def UNWATCHED_save(self, **kwargs) -> None:  # noqa
        pass


S = TypeVar('S', bound=WatchedSaveModel)
D = TypeVar('D', bound=WatchedDeleteModel)


class WatchedCreateQuerySet(models.QuerySet):
    def UNWATCHED_create(self, *args: Any, **kwargs: Any) -> S:  # noqa
        pass


class WatchedDeleteQuerySet(models.QuerySet):
    def UNWATCHED_delete(self) -> Tuple[int, Dict[str, int]]:  # noqa
        ...


class WatchedUpdateQuerySet(models.QuerySet):
    def UNWATCHED_update(self, **kwargs: Any) -> int:  # noqa
        pass


class WatchedSaveQuerySet(WatchedCreateQuerySet, WatchedUpdateQuerySet):
    ...


TargetDelete = Union[D, WatchedDeleteModel]


class CreateWatcherMixin(AbstractWatcher):
    @classmethod
    def pre_create(cls, target: List[S], meta_params: MetaParams) -> None:
        pass

    @classmethod
    def post_create(cls, target: models.QuerySet, meta_params: MetaParams) -> None:
        pass

    @classmethod
    def _watched_create(cls, target: WatchedCreateQuerySet, *_, **kwargs) -> S:
        if cls.is_overriden('pre_create'):
            instance = target.model(**kwargs)
            cls.pre_create([instance], {'source': _QUERY_SET, 'operation_params': kwargs})
        instance = target.UNWATCHED_create(**kwargs)
        if cls.is_overriden('post_create'):
            cls.post_create(
                cls.to_queryset(instance), {'source': _QUERY_SET, 'operation_params': kwargs}
            )
        return instance

    @classmethod
    def _create(cls, target: WatchedCreateQuerySet, *args, **kwargs) -> S:
        return cls._run_inside_transaction(cls._watched_create, target, *args, **kwargs)

    @classmethod
    def _watched_save(cls, target: S, **kwargs) -> None:
        cls.pre_create([target], {'source': _INSTANCE, 'operation_params': kwargs})
        target.UNWATCHED_save(**kwargs)
        if cls.is_overriden('post_create'):
            cls.post_create(
                cls.to_queryset(target), {'source': _INSTANCE, 'operation_params': kwargs}
            )

    @classmethod
    def _save(cls, target: S, **kwargs) -> None:
        create = not target.pk
        if create:
            cls._run_inside_transaction(cls._watched_save, target, **kwargs)
        else:
            target.UNWATCHED_save(**kwargs)


class DeleteWatcherMixin(AbstractWatcher):
    @classmethod
    def pre_delete(cls, target: models.QuerySet) -> None:
        pass

    @classmethod
    def post_delete(cls, undeleted_instances: List[D]) -> None:
        pass

    @classmethod
    def _watched_delete(
        cls, target: TargetDelete, *args: Any, **kwargs: Any
    ) -> Tuple[int, Dict[str, int]]:
        cls.pre_delete(cls.to_queryset(target))
        instances = list(cls.to_queryset(target)) if cls.is_overriden('post_delete') else []
        res = target.UNWATCHED_delete(*args, **kwargs)
        cls.post_delete(instances)
        return res

    @classmethod
    def _delete(cls, target: TargetDelete, *args: Any, **kwargs: Any) -> Tuple[int, Dict[str, int]]:
        return cls._run_inside_transaction(cls._watched_delete, target, *args, **kwargs)


class UpdateWatcherMixin(AbstractWatcher):
    """
    UpdateWatcherMixin is DataWatcher for update operations
    Implement the methods you need choosing one or more of the followings

    @classmethod
    def pre_update(cls, target: models.QuerySet) -> None:
        ...

    @classmethod
    def post_update(cls, target: models.QuerySet) -> None:
        ...
    """

    @classmethod
    def pre_update(cls, target: models.QuerySet, meta_params: MetaParams) -> None:
        pass

    @classmethod
    def post_update(cls, target: models.QuerySet, meta_params: MetaParams) -> None:
        pass

    @classmethod
    def _watched_update(cls, target: WatchedUpdateQuerySet, *args, **kwargs) -> int:
        cls.pre_update(target, {'source': _QUERY_SET, 'operation_params': kwargs})
        result = target.UNWATCHED_update(*args, **kwargs)
        cls.post_update(target, {'source': _QUERY_SET, 'operation_params': kwargs})
        return result

    @classmethod
    def _update(cls, target: WatchedUpdateQuerySet, *update_args, **kwargs) -> int:
        return cls._run_inside_transaction(cls._watched_update, target, *update_args, **kwargs)

    @classmethod
    def _watched_save(cls, target: S, **kwargs) -> None:
        if cls.is_overriden('pre_update'):
            cls.pre_update(
                cls.to_queryset(target),
                {'source': _INSTANCE, 'operation_params': kwargs, 'unsaved_instance': target},
            )
        target.UNWATCHED_save(**kwargs)
        if cls.is_overriden('post_update'):
            cls.post_update(
                cls.to_queryset(target), {'source': _INSTANCE, 'operation_params': kwargs}
            )

    @classmethod
    def _save(cls, target: S, **kwargs) -> None:
        update = bool(target.pk)
        if update:
            cls._run_inside_transaction(cls._watched_save, target, **kwargs)
        else:
            target.UNWATCHED_save(**kwargs)


class SaveWatcherMixin(CreateWatcherMixin, UpdateWatcherMixin):
    @classmethod
    def pre_save(cls, target: Union[List[S], models.QuerySet], meta_params: MetaParams) -> None:
        pass

    @classmethod
    def post_save(cls, target: models.QuerySet, meta_params: MetaParams) -> None:
        pass

    @classmethod
    def _watched_save(cls, target: S, **kwargs) -> None:
        create = not target.pk
        if create:
            cls.pre_save([target], {'source': _INSTANCE, 'operation_params': kwargs})
            cls.pre_create([target], {'source': _INSTANCE, 'operation_params': kwargs})
        else:
            qs = cls.to_queryset(target)
            cls.pre_save(
                qs, {'source': _INSTANCE, 'operation_params': kwargs, 'unsaved_instance': target}
            )
            cls.pre_update(
                qs, {'source': _INSTANCE, 'operation_params': kwargs, 'unsaved_instance': target}
            )

        target.UNWATCHED_save(**kwargs)

        qs = cls.to_queryset(target)
        if create:
            cls.post_create(qs, {'source': _INSTANCE, 'operation_params': kwargs})
        else:
            cls.post_update(qs, {'source': _INSTANCE, 'operation_params': kwargs})

        cls.post_save(qs, {'source': _INSTANCE, 'operation_params': kwargs})

    @classmethod
    def _save(cls, target: S, **kwargs) -> None:
        cls._run_inside_transaction(cls._watched_save, target, **kwargs)

    @classmethod
    def _watched_create(cls, target: WatchedCreateQuerySet, *_, **kwargs) -> S:
        cls.pre_save([target.model(**kwargs)], {'source': _QUERY_SET, 'operation_params': kwargs})
        instance: WatchedSaveModel = super()._watched_create(target, **kwargs)
        cls.post_save(cls.to_queryset(instance), {'source': _QUERY_SET, 'operation_params': kwargs})
        return instance  # type: ignore

    @classmethod
    def _watched_update(cls, target: WatchedUpdateQuerySet, *args, **kwargs) -> int:
        cls.pre_save(target, {'source': _QUERY_SET, 'operation_params': kwargs})
        res = super()._watched_update(target, *args, **kwargs)
        cls.post_save(target, {'source': _QUERY_SET, 'operation_params': kwargs})
        return res
