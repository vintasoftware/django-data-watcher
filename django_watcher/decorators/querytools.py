from typing import TYPE_CHECKING, List, Type, no_type_check

from .helpers import generate_settable, get_watched_functions, unwatched_create
from .queryset import get_qs_cls


if TYPE_CHECKING:
    from django.db import models


@no_type_check
def _clone_queryset_in_new_cls(
    queryset: 'models.QuerySet', queryset_cls: type
) -> 'models.QuerySet':
    # pylint: disable=protected-access
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


def _get_manager_cls(manager: 'models.Manager') -> Type['models.Manager']:
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

    return type(manager_name, (manager_cls,), {})  # type: ignore


def _get_watched_manager_cls(manager: 'models.Manager', watched_operations: List[str]) -> type:
    manager_cls = _get_manager_cls(manager)
    qs = manager.get_queryset()
    qs_cls = get_qs_cls(qs, watched_operations)

    watched_operations_copy = watched_operations.copy()

    if 'delete' in watched_operations_copy:
        watched_operations_copy.remove('delete')

    for func in get_watched_functions(manager_cls, watched_operations_copy):
        setattr(
            manager_cls,
            f'UNWATCHED_{func.__name__}',
            func if func.__name__ != 'create' else unwatched_create,
        )

    new_qs_instance = _clone_queryset_in_new_cls(qs, qs_cls)
    setattr(manager_cls, 'get_queryset', lambda self: new_qs_instance)

    settable = generate_settable(manager_cls, 'manager')
    for operation in watched_operations_copy:
        settable(operation)
    return manager_cls


def set_watched_manager(model: type, manager_attr: str, watched_operations: List[str]) -> None:
    manager = getattr(model, manager_attr)
    manager_cls = _get_watched_manager_cls(manager, watched_operations)
    manager = manager_cls()

    if manager_attr == 'objects':
        setattr(manager, 'use_for_related_fields', True)

    setattr(model, manager_attr, manager)
