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

    def pre_create(self, target: List[Model], meta_params: MetaParams) -> None
        ...

    def post_create(self, target: models.QuerySet, meta_params: MetaParams) -> None
        ...
    """

    def pre_create(self, target: List['S'], meta_params: MetaParams, **hooks_params) -> None:
        pass

    def post_create(self, target: models.QuerySet, meta_params: MetaParams, **hooks_params) -> None:
        pass

    def _watched_create(self, target: 'WatchedCreateQuerySet', *_, hooks_params, **kwargs) -> 'S':
        meta_params: MetaParams = {'source': _QUERY_SET, 'operation_params': kwargs}

        if self.is_overriden('pre_create'):
            instance = target.model(**kwargs)
            self.pre_create([instance], meta_params, **hooks_params)
        instance = target.UNWATCHED_create(**kwargs)
        if self.is_overriden('post_create'):
            self.post_create(self.to_queryset(instance), meta_params, **hooks_params)
        return instance

    def _create(self, target: 'WatchedCreateQuerySet', *args, **kwargs) -> 'S':
        return self._run_inside_transaction(self._watched_create, target, *args, **kwargs)

    def _watched_save(self, target: 'S', *_, hooks_params, **kwargs) -> None:
        meta_params: MetaParams = {
            'source': _INSTANCE,
            'operation_params': kwargs,
            'instance_ref': target,
        }

        self.pre_create([target], meta_params, **hooks_params)
        target.UNWATCHED_save(**kwargs)
        if self.is_overriden('post_create'):
            self.post_create(self.to_queryset(target), meta_params, **hooks_params)

    def _save(self, target: 'S', **kwargs) -> None:
        create = not target.pk
        if create:
            self._run_inside_transaction(self._watched_save, target, **kwargs)
        else:
            target.UNWATCHED_save(**kwargs)


class DeleteWatcherMixin(AbstractWatcher):
    """
    DeleteWatcherMixin is a DataWatcher for delete operations
    Implement the methods you need choosing one or more of the following

    def pre_delete(self, target: models.QuerySet) -> None
        ...

    def post_delete(self, undeleted_instances: List[Model]) -> None
        ...
    """

    def pre_delete(self, target: models.QuerySet, meta_params: MetaParams, **hooks_params) -> None:
        pass

    def post_delete(
        self, undeleted_instances: List['D'], meta_params: MetaParams, **hooks_params
    ) -> None:
        pass

    def _watched_delete(
        self, target: 'TargetDelete', *args: Any, hooks_params, **kwargs: Any
    ) -> Tuple[int, Dict[str, int]]:
        meta_params: MetaParams = (
            {
                'source': _QUERY_SET,
                'operation_params': kwargs,
            }
            if self.is_queryset(target)
            else {
                'source': _INSTANCE,
                'operation_params': kwargs,
                'instance_ref': cast('WatchedDeleteModel', target),
            }
        )

        self.pre_delete(self.to_queryset(target), meta_params, **hooks_params)
        instances = list(self.to_queryset(target)) if self.is_overriden('post_delete') else []
        res = target.UNWATCHED_delete(*args, **kwargs)
        self.post_delete(instances, meta_params, **hooks_params)
        return res

    def _delete(
        self, target: 'TargetDelete', *args: Any, **kwargs: Any
    ) -> Tuple[int, Dict[str, int]]:
        return self._run_inside_transaction(self._watched_delete, target, *args, **kwargs)


class UpdateWatcherMixin(AbstractWatcher):
    """
    UpdateWatcherMixin is a DataWatcher for update operations
    Implement the methods you need, choosing one or more of the following

    def pre_update(self, target: models.QuerySet, meta_params: MetaParams) -> None
        ...

    def post_update(self, target: models.QuerySet, meta_params: MetaParams) -> None
        ...
    """

    def pre_update(self, target: models.QuerySet, meta_params: MetaParams, **hooks_params) -> None:
        pass

    def post_update(self, target: models.QuerySet, meta_params: MetaParams, **hooks_params) -> None:
        pass

    def _watched_update(
        self, target: 'WatchedUpdateQuerySet', *args, hooks_params, **kwargs
    ) -> int:
        meta_params: MetaParams = {'source': _QUERY_SET, 'operation_params': kwargs}

        self.pre_update(target, meta_params, **hooks_params)
        result = target.UNWATCHED_update(*args, **kwargs)
        self.post_update(target, meta_params, **hooks_params)
        return result

    def _update(self, target: 'WatchedUpdateQuerySet', *update_args, **kwargs) -> int:
        return self._run_inside_transaction(self._watched_update, target, *update_args, **kwargs)

    def _watched_save(self, target: 'S', *_, hooks_params, **kwargs) -> None:
        meta_params: MetaParams = {
            'source': _INSTANCE,
            'operation_params': kwargs,
            'instance_ref': target,
        }

        if self.is_overriden('pre_update'):
            self.pre_update(self.to_queryset(target), meta_params, **hooks_params)
        target.UNWATCHED_save(**kwargs)
        if self.is_overriden('post_update'):
            self.post_update(self.to_queryset(target), meta_params, **hooks_params)

    def _save(self, target: 'S', **kwargs) -> None:
        update = bool(target.pk)
        if update:
            self._run_inside_transaction(self._watched_save, target, **kwargs)
        else:
            target.UNWATCHED_save(**kwargs)


class SaveWatcherMixin(CreateWatcherMixin, UpdateWatcherMixin):
    """
    SaveWatcherMixin is a DataWatcher for create and update operations.
    Check hooks order for creation and update operation in the docs:
    https://django-data-watcher.readthedocs.io/en/latest/guide/usage.html#savewatchermixin

    Implement the methods you need choosing one or more of the following

    def pre_create(self, target: List[Model], meta_params: MetaParams) -> None
        ...

    def post_create(self, target: models.QuerySet, meta_params: MetaParams) -> None
        ...

    def pre_update(self, target: models.QuerySet, meta_params: MetaParams) -> None
        ...

    def post_update(self, target: models.QuerySet, meta_params: MetaParams) -> None
        ...

    def pre_save(self, target: Union[List[Model], models.QuerySet], meta_params: MetaParams) -> None
        ...

    def post_save(self, target: models.QuerySet, meta_params: MetaParams) -> None
        ...
    """

    def pre_save(
        self, target: Union[List['S'], models.QuerySet], meta_params: MetaParams, **hooks_params
    ) -> None:
        pass

    def post_save(self, target: models.QuerySet, meta_params: MetaParams, **hooks_params) -> None:
        pass

    def _watched_save(self, target: 'S', *_, hooks_params, **kwargs) -> None:
        create = not target.pk

        meta_params: MetaParams = {
            'source': _INSTANCE,
            'operation_params': kwargs,
            'instance_ref': target,
        }

        if create:
            self.pre_save([target], meta_params, **hooks_params)
            self.pre_create([target], meta_params, **hooks_params)
        else:
            qs = self.to_queryset(target)
            self.pre_save(qs, meta_params, **hooks_params)
            self.pre_update(qs, meta_params, **hooks_params)

        target.UNWATCHED_save(**kwargs)

        qs = self.to_queryset(target)
        if create:
            self.post_create(qs, meta_params, **hooks_params)
        else:
            self.post_update(qs, meta_params, **hooks_params)

        self.post_save(qs, meta_params, **hooks_params)

    def _save(self, target: 'S', **kwargs) -> None:
        self._run_inside_transaction(self._watched_save, target, **kwargs)

    def _watched_create(self, target: 'WatchedCreateQuerySet', *_, hooks_params, **kwargs) -> 'S':
        meta_params: MetaParams = {'source': _QUERY_SET, 'operation_params': kwargs}

        self.pre_save([target.model(**kwargs)], meta_params, **hooks_params)
        instance: 'WatchedSaveModel' = super()._watched_create(
            target, hooks_params=hooks_params, **kwargs
        )
        self.post_save(self.to_queryset(instance), meta_params, **hooks_params)
        return instance  # type: ignore

    def _watched_update(
        self, target: 'WatchedUpdateQuerySet', *args, hooks_params, **kwargs
    ) -> int:
        meta_params: MetaParams = {'source': _QUERY_SET, 'operation_params': kwargs}

        self.pre_save(target, meta_params, **hooks_params)
        res = super()._watched_update(target, *args, hooks_params=hooks_params, **kwargs)
        self.post_save(target, meta_params, **hooks_params)
        return res
