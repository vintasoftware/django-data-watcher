# pylint: disable=protected-access
from importlib import import_module
from typing import Any, Callable, Dict, List, Set, Tuple, Type, Union, no_type_check

from django.db import models

from .abstract_watcher import AbstractWatcher, T, TargetType
from .mixins import CreateWatcherMixin, DeleteWatcherMixin, SaveWatcherMixin, UpdateWatcherMixin


class _Manager(type):
    pass


class _QuerySet(type):
    pass


def _get_watched_functions(cls: type, operation_names: List[str]) -> List[Callable]:
    """
    _get_watched_functions returns the model methods to be watched

    :param cls: The model's class to be watched
    :param operation_names: List of the methods names
    """
    operation_names_copy = operation_names.copy()
    watched_functions = []
    for func_name in operation_names:
        func = getattr(cls, func_name, None)
        if callable(func):
            watched_functions.append(func)
            operation_names_copy.remove(func.__name__)
    if operation_names_copy:
        plural = 's' if len(operation_names_copy) > 1 else ''
        extra = ', '.join(operation_names_copy)
        raise TypeError(f'type object {cls} has no callable{plural} {extra}')

    return watched_functions


def _import_watcher(casual_path: str) -> Type[AbstractWatcher]:
    """
    _import_watcher will return a watcher from a path

    :param casual_path: The watcher's casual or full path
    :returns: The watcher
    """
    splited_path = casual_path.split('.')
    if len(splited_path) < 2:
        raise ValueError('Watcher casual path is expected to have at least base_module.Watcher')
    watcher_name = splited_path.pop(-1)
    if len(splited_path) < 2:
        module_name = f'{splited_path[0]}.watchers'
    else:
        module_name = splited_path.pop(0) if len(splited_path) == 1 else '.'.join(splited_path)
    module = import_module(module_name)
    return getattr(module, watcher_name)


def _unwatched_create(self, **kwargs: Any) -> T:
    """
    _unwatched_create is a function to be injected on the watched Manager
    the usual save will call models create which trigger the hooks twice
    this function will replace the Manager create in order to call the UNWATCHED_save

    :param kwargs: The params passed to the function to create the model
    :returns: The model
    """
    instance = self.model(**kwargs)
    instance.UNWATCHED_save(force_insert=True)
    return instance


@no_type_check
def _clone_queryset_in_new_cls(queryset: models.QuerySet, queryset_cls: type) -> models.QuerySet:
    """
    _clone_queryset_in_new_cls is a function to get old queryset instance and transform it to a new
    instance from a diferent class (with new methods)

    :param queryset: The old queryset instance
    :param queryset_cls: The new queryset class
    :returns: The instance of the new cls with filters, prefetches, etc from older instance
    """
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


def _generate_settable_for_manager(manager_cls: _Manager) -> Callable[[str], None]:
    """
    _generate_settable_for_manager is a function to return a function to be early called on the
    replacement of the unwatched operation for the watched operation on the madified class.

    :param manager_cls: The manager class
    :returns: A function which proper replaces the unwatched operation, called by the operation name
    """

    def settable(operation: str):
        def call_watched_operation(self: models.Manager, *args, **kwargs):
            return getattr(self.get_queryset(), operation)(*args, **kwargs)

        call_watched_operation.__name__ = operation
        call_watched_operation.__doc__ = getattr(manager_cls(), f'UNWATCHED_{operation}').__doc__

        setattr(manager_cls, operation, call_watched_operation)

    return settable


def _generate_settable_for_qs(qs_cls: _QuerySet) -> Callable[[str], None]:
    """
    _generate_settable_for_qs is a function to return a function to be early called on the
    replacement of the unwatched operation for the watched operation on the madified class.

    :param qs_cls: The queryset class
    :returns: A function which proper replaces the unwatched operation, called by the operation name
    """

    def settable(operation: str):
        def call_watched_operation(self: models.QuerySet, *args, **kwargs):
            return self.model.watched_operation(operation, self, *args, **kwargs)

        call_watched_operation.__name__ = operation
        call_watched_operation.__doc__ = getattr(qs_cls(), f'UNWATCHED_{operation}').__doc__

        setattr(qs_cls, operation, call_watched_operation)

    return settable


def _generate_settable_for_model(model_cls: Type[models.Model]) -> Callable[[str], None]:
    """
    _generate_settable_for_model is a function to return a function to be early called on the
    replacement of the unwatched operation for the watched operation on the madified class.

    :param model_cls: The model class
    :returns: A function which proper replaces the unwatched operation, called by the operation name
    """

    def settable(operation: str):
        def call_watched_operation(self: models.Model, *args, **kwargs):
            return self.watched_operation(operation, self, *args, **kwargs)  # type: ignore

        call_watched_operation.__name__ = operation
        call_watched_operation.__doc__ = getattr(model_cls, f'UNWATCHED_{operation}').__doc__

        setattr(model_cls, operation, call_watched_operation)

    return settable


def _get_manager_cls(manager: models.Manager) -> Type[models.Manager]:
    """
    _get_manager_cls returns a the manager class to be modified.
    If the manager instance is a base django manager it will create a new type in memory and
    returns it, so different modifications on the manager wouldn't interfer with each other

    :param manager: The model class
    :returns: The manager class
    """
    manager_cls = manager.__class__

    manager_name = (
        f'{manager.get_queryset().model.__name__}Manager'
        if 'django.db.models.manager.Manager' in str(manager_cls)
        else manager_cls.__name__
    )

    return type.__new__(_Manager, manager_name, (manager_cls,), {})  # type: ignore


def _get_qs_cls(qs: models.QuerySet, watched_operations: List[str]) -> Type[models.QuerySet]:
    qs_cls = qs.__class__

    qs_name = (
        f'{qs.model.__name__}QuerySet'
        if 'django.db.models.query.QuerySet' in str(qs_cls)
        else qs_cls.__name__
    )

    new_qs_cls = type.__new__(_QuerySet, qs_name, (qs_cls,), {})

    for func in _get_watched_functions(new_qs_cls, watched_operations):
        setattr(
            new_qs_cls,
            f'UNWATCHED_{func.__name__}',
            func if func.__name__ != 'create' else _unwatched_create,
        )

    settable = _generate_settable_for_qs(new_qs_cls)
    for operation in watched_operations:
        settable(operation)

    return new_qs_cls  # type: ignore


def _get_watched_manager_cls(manager: models.Manager, watched_operations: List[str]) -> type:
    manager_cls = _get_manager_cls(manager)
    qs = manager.get_queryset()
    qs_cls = _get_qs_cls(qs, watched_operations)

    watched_operations_copy = watched_operations.copy()

    if 'delete' in watched_operations_copy:
        watched_operations_copy.remove('delete')

    for func in _get_watched_functions(manager_cls, watched_operations_copy):
        setattr(
            manager_cls,
            f'UNWATCHED_{func.__name__}',
            func if func.__name__ != 'create' else _unwatched_create,
        )

    new_qs_instance = _clone_queryset_in_new_cls(qs, qs_cls)
    setattr(manager_cls, 'get_queryset', lambda self: new_qs_instance)

    settable = _generate_settable_for_manager(manager_cls)  # type: ignore
    for operation in watched_operations_copy:
        settable(operation)
    return manager_cls


def _set_watched_manager(model: type, manager_attr: str, watched_operations: List[str]) -> None:
    manager = getattr(model, manager_attr)
    manager_cls = _get_watched_manager_cls(manager, watched_operations)
    manager = manager_cls()

    if manager_attr == 'objects':
        setattr(manager, 'use_for_related_fields', True)

    setattr(model, manager_attr, manager)


def _watched_operation(cls, operation: str, target: TargetType, *args: Any, **kwargs: Any) -> Any:
    """
    _watched_operation is a function to be injected on the Model as classmethod.
    It will call the watcher to manage the operations

    :param cls: The model's class
    :param operation: The operation name
    :param target: List of instances or Queryset, both with all affected ocurrences of the model
    :param args: Any *args passed to the operation when called
    :param kwargs: Any **kwargs passed to the operation when called
    """
    return cls._watcher.run(operation, target, *args, **kwargs)


def _set_watched_model(cls: type, watched_operations: List[str]) -> type:
    watched_operations = watched_operations.copy()

    setattr(cls, 'watched_operation', classmethod(_watched_operation))

    for func in _get_watched_functions(cls, watched_operations):
        setattr(cls, f'UNWATCHED_{func.__name__}', func)

    settable = _generate_settable_for_model(cls)
    for operation in watched_operations:
        settable(operation)

    return cls


_map_operations_by_watcher: Dict[Type[AbstractWatcher], Tuple[str, Tuple[str, ...]]] = {
    SaveWatcherMixin: ('save', ('create', 'update')),
    UpdateWatcherMixin: ('save', ('update',)),
    CreateWatcherMixin: ('save', ('create',)),
    DeleteWatcherMixin: ('delete', ('delete',)),
}


def _get_watched_operations(
    watcher: Type[AbstractWatcher],
) -> Tuple[List[str], List[str]]:
    model_operations: Set[str] = set()
    objects_operations: Set[str] = set()
    for k, v in _map_operations_by_watcher.items():
        if issubclass(watcher, k):
            m_operation, o_operations = v
            model_operations.add(m_operation)
            for operation in o_operations:
                objects_operations.add(operation)

    return list(model_operations), list(objects_operations)


def watched(
    watcher: Union[str, Type[AbstractWatcher]],
    watched_managers: List[str] = None,
) -> Callable:
    """
    watched decorator, with this you can decorate a model to set a watcher class on it

    :param watcher: The watcher to observe model's data operations, it can be
    the watcher class, or a string with the path to it.
    :param watched_managers: Optional a list of managers' attributes to have their data operations
    watched, if not described it will use 'objects' as default
    """

    def decorator(cls: type) -> type:
        watcher_cls = _import_watcher(watcher) if isinstance(watcher, str) else watcher
        model_operations, objects_operations = _get_watched_operations(watcher_cls)
        model = _set_watched_model(cls, model_operations)
        setattr(model, '_watcher', watcher_cls)

        if not watched_managers:
            _set_watched_manager(model, 'objects', objects_operations)
        else:
            for manager_attr in watched_managers:
                _set_watched_manager(model, manager_attr, objects_operations)

        return model

    return decorator
