from importlib import import_module
from typing import TYPE_CHECKING, Callable, Dict, List, Set, Tuple, Type, TypeVar, Union

from django_watcher.abstract_watcher import AbstractWatcher
from django_watcher.mixins import (
    CreateWatcherMixin,
    DeleteWatcherMixin,
    SaveWatcherMixin,
    UpdateWatcherMixin,
)

from .model import set_watched_model
from .querytools import set_watched_manager


if TYPE_CHECKING:
    from .model import WatchedModel  # noqa: F401

    from django.db import models  # noqa: F401


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


T = TypeVar('T', bound='models.Model')


def watched(
    watcher: Union[str, Type[AbstractWatcher]],
    watched_managers: List[str] = None,
) -> Callable[[Type[T]], Type[T]]:
    """
    watched decorator, with this you can decorate a model to set a watcher class on it

    :param watcher: The watcher to observe model's data operations, it can be
    the watcher class, or a string with the path to it.
    :param watched_managers: Optional a list of managers' attributes to have their data operations
    watched, if not described it will use 'objects' as default
    """

    def decorator(cls: Type[T]) -> Type[T]:
        watcher_cls = _import_watcher(watcher) if isinstance(watcher, str) else watcher
        model_operations, objects_operations = _get_watched_operations(watcher_cls)
        model = set_watched_model(cls, model_operations)
        setattr(model, '_watcher', watcher_cls)

        if not watched_managers:
            set_watched_manager(model, 'objects', objects_operations)
        else:
            for manager_attr in watched_managers:
                set_watched_manager(model, manager_attr, objects_operations)

        return model

    return decorator
