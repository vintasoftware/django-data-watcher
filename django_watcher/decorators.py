# pylint: disable=protected-access

from typing import Any, Callable, List, Type, Union

from django.db import models

from .abstract_watcher import AbstractWatcher, T, TargetType


class _Manager(type):
    pass


class _QuerySet(type):
    pass


def _get_watched_functions(cls: type, operation_names: List[str]) -> List[callable]:
    operation_names_copy = operation_names.copy()
    watched_functions = []
    for func in operation_names:
        func = getattr(cls, func, None)
        if callable(func):
            watched_functions.append(func)
            operation_names_copy.remove(func.__name__)
    if operation_names_copy:
        plural = 's' if len(operation_names_copy) > 1 else ''
        extra = ', '.join(operation_names_copy)
        raise TypeError(f'type object {cls} has no callable{plural} {extra}')

    return watched_functions


def _watched_operation(cls, operation: str, target: TargetType, *args: Any, **kwargs: Any) -> Any:
    return cls._watcher.run(operation, target, *args, **kwargs)


def _import_watcher(casual_path: str) -> AbstractWatcher:
    path = casual_path.split('.')
    if len(path) < 2:
        raise ValueError('Watcher casual path is expected to have at least base_module.Watcher')
    watcher_name = path.pop(-1)
    module_name = path.pop(0) if len(path) == 1 else '.'.join(path)
    module = __import__(module_name)
    return getattr(module.data_watcher, watcher_name)


def _unwatched_create(self, **kwargs: Any) -> T:
    instance = self.model(**kwargs)
    instance.UNWATCHED_save(force_insert=True)
    return instance


def _clone_queryset_in_new_cls(queryset: models.QuerySet, queryset_cls: type) -> models.QuerySet:
    c = queryset_cls(
        model=queryset.model,
        query=queryset.query.chain(),
        using=queryset._db,
        hints=queryset._hints,
    )
    c._sticky_filter = queryset._sticky_filter
    c._for_write = queryset._for_write
    c._prefetch_related_lookups = queryset._prefetch_related_lookups[:]
    c._known_related_objects = queryset._known_related_objects
    c._iterable_class = queryset._iterable_class
    c._fields = queryset._fields

    return c


def _generate_settable_for_qs(qs_cls: Type[models.QuerySet]) -> Callable:
    return lambda operation: setattr(
        qs_cls,
        operation,
        lambda self, *args, **kwargs: self.model.watched_operation(
            operation, self, *args, **kwargs
        ),
    )


def _generate_settable_for_model(model_cls: Type[models.Model]) -> Callable:
    return lambda operation: setattr(
        model_cls,
        operation,
        lambda self, *args, **kwargs: self.watched_operation(operation, self, *args, **kwargs),
    )


def _get_manager_cls(manager: models.Manager) -> Type[models.Manager]:
    manager_cls = manager.__class__

    manager_name = (
        f'{manager.get_queryset().model.__name__}Manager'
        if 'django.db.models.manager.Manager' in str(manager_cls)
        else manager_cls.__name__
    )

    return type.__new__(_Manager, manager_name, (manager_cls,), {})


def _get_qs_cls(qs: models.QuerySet) -> Type[models.QuerySet]:
    qs_cls = qs.__class__

    qs_name = (
        f'{qs.model.__name__}QuerySet'
        if 'django.db.models.query.QuerySet' in str(qs_cls)
        else qs_cls.__name__
    )

    return type.__new__(_QuerySet, qs_name, (qs_cls,), {})


def _get_watched_manager_cls(manager: models.Manager, watched_operations: List[str]) -> type:
    manager_cls = _get_manager_cls(manager)
    qs = manager.get_queryset()
    qs_cls = _get_qs_cls(qs)

    watched_operations = watched_operations.copy()
    if 'save' in watched_operations:
        watched_operations.remove('save')
        watched_operations.append('create')
        watched_operations.append('update')

    for func in _get_watched_functions(qs_cls, watched_operations):
        setattr(
            qs_cls,
            f'UNWATCHED_{func.__name__}',
            func if func.__name__ != 'create' else _unwatched_create,
        )

    settable = _generate_settable_for_qs(qs_cls)
    for operation in watched_operations:
        settable(operation)

    new_qs_instance = _clone_queryset_in_new_cls(qs, qs_cls)

    setattr(manager_cls, 'get_queryset', lambda self: new_qs_instance)
    return manager_cls


def _set_watched_manager(model: type, manager_attr: str, watched_operations: List[str]) -> None:
    manager = getattr(model, manager_attr)
    manager_cls = _get_watched_manager_cls(manager, watched_operations)

    setattr(model, manager_attr, manager_cls())


def _set_watched_model(
    cls: type, watcher: Union[str, AbstractWatcher], watched_operations: List[str]
) -> type:
    watched_operations = watched_operations.copy()
    if 'create' in watched_operations:
        watched_operations.remove('create')
        watched_operations.append('save')

    if 'update' in watched_operations:
        watched_operations.remove('update')
        if 'save' not in watched_operations:
            watched_operations.append('save')

    cls.watched_operation = classmethod(_watched_operation)
    cls._watcher = _import_watcher(watcher) if isinstance(watcher, str) else watcher

    for operation in _get_watched_functions(cls, watched_operations):
        setattr(cls, f'UNWATCHED_{operation.__name__}', operation)

    settable = _generate_settable_for_model(cls)
    for operation in watched_operations:
        settable(operation)

    return cls


def watched(
    watcher: Union[str, AbstractWatcher],
    watched_operations: List[str],
    watched_managers: List[str] = None,
) -> Callable:
    def decorator(cls: type) -> type:
        model = _set_watched_model(cls, watcher, watched_operations)

        if not watched_managers:
            _set_watched_manager(model, 'objects', watched_operations)
        else:
            for manager_attr in watched_managers:
                _set_watched_manager(model, manager_attr, watched_operations)

        return model

    return decorator
