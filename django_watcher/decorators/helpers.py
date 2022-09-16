from typing import Callable, List

from typing_extensions import Literal

from django_watcher.abstract_watcher import T


def get_watched_functions(cls: type, operation_names: List[str]) -> List[Callable]:
    """
    get_watched_functions returns the model methods to be watched

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


def unwatched_create(self, **kwargs) -> T:
    """
    unwatched_create is a function to be injected on the watched Manager
    the usual save will call models create which trigger the hooks twice
    this function will replace the Manager create in order to call the UNWATCHED_save

    :param kwargs: The params passed to the function to create the model
    :returns: The model
    """
    instance = self.model(**kwargs)
    instance.UNWATCHED_save(force_insert=True)
    return instance


def generate_settable(
    cls: type, for_type: Literal['model', 'queryset', 'manager']
) -> Callable[[str], None]:
    """
    _generate_settable is a function to return a function to be early called on the
    replacement of the unwatched operation for the watched operation on the modified class.
    The goal is to

    :param cls: The class
    :param for_type: A string with the type of class that this settable will be generated for
    :returns: A function which proper replaces the unwatched operation, called by the operation name
    """

    def settable(operation: str):
        def call_watched_operation(self, *args, **kwargs):

            if for_type == 'model':
                return self.watched_operation(operation, self, *args, **kwargs)

            if for_type == 'queryset':
                return self.model.watched_operation(operation, self, *args, **kwargs)

            return getattr(self.get_queryset(), operation)(*args, **kwargs)

        call_watched_operation.__name__ = operation
        call_watched_operation.__doc__ = getattr(cls(), f'UNWATCHED_{operation}').__doc__

        setattr(cls, operation, call_watched_operation)

    return settable
