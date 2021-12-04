import inspect
from typing import Any, Callable, Type, TypeVar, Union

from django.db import models, transaction


T = TypeVar('T', bound=models.Model)
TargetType = Union[Type[T], models.QuerySet]


class AbstractWatcher:
    class Meta:
        abstract = True

    @staticmethod
    def is_queryset(target: TargetType) -> bool:
        return isinstance(target, models.QuerySet)

    @classmethod
    def to_queryset(cls, target: TargetType) -> models.QuerySet:
        if not cls.is_queryset(target):
            target = target.__class__.objects.filter(pk=target.pk)

        return target

    @classmethod
    def _run_inside_transaction(
        cls, func: Callable, target: TargetType, *args: Any, **kwargs: Any
    ) -> Any:
        if transaction.get_connection().in_atomic_block:
            return func(target, *args, **kwargs)
        with transaction.atomic():
            return func(target, *args, **kwargs)

    @classmethod
    def run(cls, operation: str, target: TargetType, *args: Any, **kwargs: Any):
        return getattr(cls, f'_{operation}')(target, *args, **kwargs)

    @classmethod
    def is_overriden(cls, method_name: str) -> bool:
        classes = inspect.getmro(cls)[1:]
        return any(
            hasattr(klass, method_name)
            and not getattr(klass, method_name).__code__ is getattr(cls, method_name).__code__
            for klass in classes
        )
