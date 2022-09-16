from typing import TYPE_CHECKING, Any, Dict, List, Tuple, TypeVar, Union, cast

from django.db import models

from typing_extensions import TypedDict

from .abstract_watcher import AbstractWatcher


class _MetaParams(TypedDict):
    source: str
    operation_params: dict


class MetaParams(_MetaParams, total=False):
    instance_ref: models.Model


_INSTANCE = 'instance'
_QUERY_SET = 'query_set'

if TYPE_CHECKING:

    class WatchedDeleteModel(models.Model):
        def UNWATCHED_delete(self, **kwargs) -> Tuple[int, Dict[str, int]]:  # nopep8
            pass

    class WatchedSaveModel(models.Model):
        def UNWATCHED_save(self, **kwargs) -> None:  # nopep8
            pass

    S = TypeVar('S', bound=WatchedSaveModel)
    D = TypeVar('D', bound=WatchedDeleteModel)

    class WatchedCreateQuerySet(models.QuerySet):
        def UNWATCHED_create(self, *args: Any, **kwargs: Any) -> S:  # nopep8
            pass

    class WatchedDeleteQuerySet(models.QuerySet):
        def UNWATCHED_delete(self, *args, **kwargs) -> Tuple[int, Dict[str, int]]:  # nopep8
            pass

    class WatchedUpdateQuerySet(models.QuerySet):
        def UNWATCHED_update(self, **kwargs: Any) -> int:  # nopep8
            pass

    class WatchedSaveQuerySet(WatchedCreateQuerySet, WatchedUpdateQuerySet):
        ...

    TargetDelete = Union['D', 'WatchedDeleteQuerySet']


class CreateWatcherMixin(AbstractWatcher):
    """
    CreateWatcherMixin is a DataWatcher for create operations
    Implement the methods you need choosing one or more of the following

    @classmethod
    def pre_create(cls, target: List[Model], meta_params: MetaParams) -> None
        ...

    @classmethod
    def post_create(cls, target: models.QuerySet, meta_params: MetaParams) -> None
        ...
    """

    @classmethod
    def pre_create(cls, target: List['S'], meta_params: MetaParams) -> None:
        pass

    @classmethod
    def post_create(cls, target: models.QuerySet, meta_params: MetaParams) -> None:
        pass

    @classmethod
    def _watched_create(cls, target: 'WatchedCreateQuerySet', *_, **kwargs) -> 'S':
        meta_params: MetaParams = {'source': _QUERY_SET, 'operation_params': kwargs}

        if cls.is_overriden('pre_create'):
            instance = target.model(**kwargs)
            cls.pre_create([instance], meta_params)
        instance = target.UNWATCHED_create(**kwargs)
        if cls.is_overriden('post_create'):
            cls.post_create(cls.to_queryset(instance), meta_params)
        return instance

    @classmethod
    def _create(cls, target: 'WatchedCreateQuerySet', *args, **kwargs) -> 'S':
        return cls._run_inside_transaction(cls._watched_create, target, *args, **kwargs)

    @classmethod
    def _watched_save(cls, target: 'S', **kwargs) -> None:
        meta_params: MetaParams = {
            'source': _INSTANCE,
            'operation_params': kwargs,
            'instance_ref': target,
        }

        cls.pre_create([target], meta_params)
        target.UNWATCHED_save(**kwargs)
        if cls.is_overriden('post_create'):
            cls.post_create(cls.to_queryset(target), meta_params)

    @classmethod
    def _save(cls, target: 'S', **kwargs) -> None:
        create = not target.pk
        if create:
            cls._run_inside_transaction(cls._watched_save, target, **kwargs)
        else:
            target.UNWATCHED_save(**kwargs)


class DeleteWatcherMixin(AbstractWatcher):
    """
    DeleteWatcherMixin is a DataWatcher for delete operations
    Implement the methods you need choosing one or more of the following

    @classmethod
    def pre_delete(cls, target: models.QuerySet) -> None
        ...

    @classmethod
    def post_delete(cls, undeleted_instances: List[Model]) -> None
        ...
    """

    @classmethod
    def pre_delete(cls, target: models.QuerySet, meta_params: MetaParams) -> None:
        pass

    @classmethod
    def post_delete(cls, undeleted_instances: List['D'], meta_params: MetaParams) -> None:
        pass

    @classmethod
    def _watched_delete(
        cls, target: 'TargetDelete', *args: Any, **kwargs: Any
    ) -> Tuple[int, Dict[str, int]]:
        meta_params: MetaParams = (
            {
                'source': _QUERY_SET,
                'operation_params': kwargs,
            }
            if cls.is_queryset(target)
            else {
                'source': _INSTANCE,
                'operation_params': kwargs,
                'instance_ref': cast('WatchedDeleteModel', target),
            }
        )

        cls.pre_delete(cls.to_queryset(target), meta_params)
        instances = list(cls.to_queryset(target)) if cls.is_overriden('post_delete') else []
        res = target.UNWATCHED_delete(*args, **kwargs)
        cls.post_delete(instances, meta_params)
        return res

    @classmethod
    def _delete(
        cls, target: 'TargetDelete', *args: Any, **kwargs: Any
    ) -> Tuple[int, Dict[str, int]]:
        return cls._run_inside_transaction(cls._watched_delete, target, *args, **kwargs)


class UpdateWatcherMixin(AbstractWatcher):
    """
    UpdateWatcherMixin is a DataWatcher for update operations
    Implement the methods you need, choosing one or more of the following

    @classmethod
    def pre_update(cls, target: models.QuerySet, meta_params: MetaParams) -> None
        ...

    @classmethod
    def post_update(cls, target: models.QuerySet, meta_params: MetaParams) -> None
        ...
    """

    @classmethod
    def pre_update(cls, target: models.QuerySet, meta_params: MetaParams) -> None:
        pass

    @classmethod
    def post_update(cls, target: models.QuerySet, meta_params: MetaParams) -> None:
        pass

    @classmethod
    def _watched_update(cls, target: 'WatchedUpdateQuerySet', *args, **kwargs) -> int:
        meta_params: MetaParams = {'source': _QUERY_SET, 'operation_params': kwargs}

        cls.pre_update(target, meta_params)
        result = target.UNWATCHED_update(*args, **kwargs)
        cls.post_update(target, meta_params)
        return result

    @classmethod
    def _update(cls, target: 'WatchedUpdateQuerySet', *update_args, **kwargs) -> int:
        return cls._run_inside_transaction(cls._watched_update, target, *update_args, **kwargs)

    @classmethod
    def _watched_save(cls, target: 'S', **kwargs) -> None:
        meta_params: MetaParams = {
            'source': _INSTANCE,
            'operation_params': kwargs,
            'instance_ref': target,
        }

        if cls.is_overriden('pre_update'):
            cls.pre_update(cls.to_queryset(target), meta_params)
        target.UNWATCHED_save(**kwargs)
        if cls.is_overriden('post_update'):
            cls.post_update(cls.to_queryset(target), meta_params)

    @classmethod
    def _save(cls, target: 'S', **kwargs) -> None:
        update = bool(target.pk)
        if update:
            cls._run_inside_transaction(cls._watched_save, target, **kwargs)
        else:
            target.UNWATCHED_save(**kwargs)


class SaveWatcherMixin(CreateWatcherMixin, UpdateWatcherMixin):
    """
    SaveWatcherMixin is a DataWatcher for create and update operations.
    Check hooks order for creation and update operation in the docs:
    https://django-data-watcher.readthedocs.io/en/latest/guide/usage.html#savewatchermixin

    Implement the methods you need choosing one or more of the following

    @classmethod
    def pre_create(cls, target: List[Model], meta_params: MetaParams) -> None
        ...

    @classmethod
    def post_create(cls, target: models.QuerySet, meta_params: MetaParams) -> None
        ...

    @classmethod
    def pre_update(cls, target: models.QuerySet, meta_params: MetaParams) -> None
        ...

    @classmethod
    def post_update(cls, target: models.QuerySet, meta_params: MetaParams) -> None
        ...

    @classmethod
    def pre_save(cls, target: Union[List[Model], models.QuerySet], meta_params: MetaParams) -> None
        ...

    @classmethod
    def post_save(cls, target: models.QuerySet, meta_params: MetaParams) -> None
        ...
    """

    @classmethod
    def pre_save(cls, target: Union[List['S'], models.QuerySet], meta_params: MetaParams) -> None:
        pass

    @classmethod
    def post_save(cls, target: models.QuerySet, meta_params: MetaParams) -> None:
        pass

    @classmethod
    def _watched_save(cls, target: 'S', **kwargs) -> None:
        create = not target.pk

        meta_params: MetaParams = {
            'source': _INSTANCE,
            'operation_params': kwargs,
            'instance_ref': target,
        }

        if create:
            cls.pre_save([target], meta_params)
            cls.pre_create([target], meta_params)
        else:
            qs = cls.to_queryset(target)
            cls.pre_save(qs, meta_params)
            cls.pre_update(qs, meta_params)

        target.UNWATCHED_save(**kwargs)

        qs = cls.to_queryset(target)
        if create:
            cls.post_create(qs, meta_params)
        else:
            cls.post_update(qs, meta_params)

        cls.post_save(qs, meta_params)

    @classmethod
    def _save(cls, target: 'S', **kwargs) -> None:
        cls._run_inside_transaction(cls._watched_save, target, **kwargs)

    @classmethod
    def _watched_create(cls, target: 'WatchedCreateQuerySet', *_, **kwargs) -> 'S':
        meta_params: MetaParams = {'source': _QUERY_SET, 'operation_params': kwargs}

        cls.pre_save([target.model(**kwargs)], meta_params)
        instance: 'WatchedSaveModel' = super()._watched_create(target, **kwargs)
        cls.post_save(cls.to_queryset(instance), meta_params)
        return instance  # type: ignore

    @classmethod
    def _watched_update(cls, target: 'WatchedUpdateQuerySet', *args, **kwargs) -> int:
        meta_params: MetaParams = {'source': _QUERY_SET, 'operation_params': kwargs}

        cls.pre_save(target, meta_params)
        res = super()._watched_update(target, *args, **kwargs)
        cls.post_save(target, meta_params)
        return res
