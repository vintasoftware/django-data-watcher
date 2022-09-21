from typing import TYPE_CHECKING, Any, Callable, List, Type

from django_watcher.abstract_watcher import AbstractWatcher, TargetType

from .helpers import generate_settable, get_watched_functions


if TYPE_CHECKING:
    from typing_extensions import Protocol

    from typing import TypeVar

    from django.db import models

    M = TypeVar('M', bound=models.Model, covariant=True)

    class WatchedModel(Protocol[M]):
        @classmethod
        def watched_operation(  # pylint: disable=unused-argument
            cls, operation: str, target: TargetType, *args: Any, **kwargs: Any
        ) -> Any:
            ...


# pylint: disable=protected-access
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
    return cls._get_watcher().run(operation, target, *args, **kwargs)


def _generate_get_watcher(watcher_cls: Type[AbstractWatcher]) -> Callable[[Any], AbstractWatcher]:
    # pylint: disable=unused-argument
    def _get_watcher(cls):
        return watcher_cls()

    return _get_watcher


def set_watched_model(cls: type, watcher_cls: type, watched_operations: List[str]) -> type:
    watched_operations = watched_operations.copy()

    setattr(cls, 'watched_operation', classmethod(_watched_operation))
    setattr(cls, '_get_watcher', classmethod(_generate_get_watcher(watcher_cls)))

    for func in get_watched_functions(cls, watched_operations):
        setattr(cls, f'UNWATCHED_{func.__name__}', func)

    settable = generate_settable(cls, 'model')
    for operation in watched_operations:
        settable(operation)

    return cls
