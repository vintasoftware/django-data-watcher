from typing import Any, Dict, List, Tuple, Type, Union

from django.db import models

from .abstract_watcher import AbstractWatcher, T, TargetType


class DeleteWatcherMixin(AbstractWatcher):
    @classmethod
    def pre_delete(cls, target: models.QuerySet) -> None:
        pass

    @classmethod
    def post_delete(cls, instances: List[T]) -> None:
        pass

    @classmethod
    def _watched_delete(cls, target: TargetType, **kwargs: Any) -> Tuple[int, Dict[str, int]]:
        cls.pre_delete(cls.to_queryset(target))
        instances = list(cls.to_queryset(target)) if cls.is_overriden('pos_delete') else []
        res = target.UNWATCHED_delete(**kwargs)
        cls.post_delete(instances)
        return res

    @classmethod
    def _delete(cls, target: TargetType, *args: Any, **kwargs: Any) -> Tuple[int, Dict[str, int]]:
        return cls._run_inside_transaction(cls._watched_delete, target, *args, **kwargs)


class CreateWatcherMixin(AbstractWatcher):
    @classmethod
    def pre_create(cls, target: List[T]) -> None:
        pass

    @classmethod
    def post_create(cls, target: models.QuerySet) -> None:
        pass

    @classmethod
    def _watched_create(cls, target: models.QuerySet, **kwargs) -> T:
        if cls.is_overriden('pre_create'):
            instance = target.model(**kwargs)
            cls.pre_create([instance])
        instance = target.UNWATCHED_create(**kwargs)
        if cls.is_overriden('post_create'):
            cls.post_create(cls.to_queryset(instance))
        return instance

    @classmethod
    def _create(cls, target: models.QuerySet, **kwargs) -> T:
        return cls._run_inside_transaction(cls._watched_create, target, **kwargs)

    @classmethod
    def _watched_save(cls, target: T, **kwargs) -> None:
        cls.pre_create([target])
        target.UNWATCHED_save(**kwargs)
        if cls.is_overriden('post_create'):
            cls.post_create(cls.to_queryset(target))

    @classmethod
    def _save(cls, target: T, **kwargs) -> None:
        create = not target.pk
        if create:
            cls._run_inside_transaction(cls._watched_save, target, **kwargs)
        else:
            target.UNWATCHED_save(**kwargs)


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
    def pre_update(cls, target: models.QuerySet) -> None:
        pass

    @classmethod
    def post_update(cls, target: models.QuerySet) -> None:
        pass

    @classmethod
    def _watched_update(cls, target: models.QuerySet, **kwargs) -> int:
        cls.pre_update(target)
        result = target.UNWATCHED_update(**kwargs)
        cls.post_update(target)
        return result

    @classmethod
    def _update(cls, target: models.QuerySet, **kwargs) -> int:
        return cls._run_inside_transaction(cls._watched_update, target, **kwargs)

    @classmethod
    def _watched_save(cls, target: T, **kwargs) -> None:
        if cls.is_overriden('pre_update'):
            cls.pre_update(cls.to_queryset(target))
        target.UNWATCHED_save(**kwargs)
        if cls.is_overriden('post_update'):
            cls.post_update(cls.to_queryset(target))

    @classmethod
    def _save(cls, target: T, **kwargs) -> None:
        update = bool(target.pk)
        if update:
            cls._run_inside_transaction(cls._watched_save, target, **kwargs)
        else:
            target.UNWATCHED_save(**kwargs)


class SaveWatcherMixin(UpdateWatcherMixin, CreateWatcherMixin):
    @classmethod
    def pre_save(cls, target: Union[List[T], models.QuerySet]) -> None:
        pass

    @classmethod
    def post_save(cls, target: models.QuerySet) -> None:
        pass

    @classmethod
    def _watched_save(cls, target: Type[T], **kwargs) -> None:
        create = not target.pk
        if create:
            cls.pre_save([target])
            cls.pre_create([target])
        else:
            qs = cls.to_queryset(target)
            cls.pre_save(qs)
            cls.pre_update(qs)

        target.UNWATCHED_save(**kwargs)

        qs = cls.to_queryset(target)
        if create:
            cls.post_create(qs)
        else:
            cls.post_update(qs)

        cls.post_save(qs)

    @classmethod
    def _save(cls, target: Type[T], **kwargs) -> None:
        cls._run_inside_transaction(cls._watched_save, target, **kwargs)

    @classmethod
    def _watched_create(cls, target: models.QuerySet, **kwargs) -> T:
        cls.pre_save([target.model(**kwargs)])
        instance = super()._watched_create(target, **kwargs)
        cls.post_save(cls.to_queryset(instance))
        return instance

    @classmethod
    def _watched_update(cls, target: models.QuerySet, **kwargs) -> int:
        cls.pre_save(target)
        res = super()._watched_update(target, **kwargs)
        cls.post_save(target)
        return res
