from typing import TYPE_CHECKING, Any, List

from django_watcher.abstract_watcher import TargetType

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
    # pylint: disable=protected-access
    return cls._watcher.run(operation, target, *args, **kwargs)


def set_watched_model(cls: type, watched_operations: List[str]) -> type:
    watched_operations = watched_operations.copy()

    setattr(cls, 'watched_operation', classmethod(_watched_operation))

    for func in get_watched_functions(cls, watched_operations):
        setattr(cls, f'UNWATCHED_{func.__name__}', func)

    settable = generate_settable(cls, 'model')
    for operation in watched_operations:
        settable(operation)

    return cls
