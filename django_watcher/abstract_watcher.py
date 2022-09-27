import inspect
from typing import Any, Callable, TypeVar, Union, cast

from django.db import models, transaction


T = TypeVar('T', bound=models.Model)
TargetType = Union[T, models.QuerySet]


class AbstractWatcher:
    class Meta:
        abstract = True

    def is_queryset(self, target: TargetType) -> bool:
        return isinstance(target, models.QuerySet)

    def to_queryset(self, target: TargetType) -> models.QuerySet:
        if not self.is_queryset(target):
            target = cast(models.Model, target)
            target = target.__class__.objects.filter(pk=target.pk)

        return target

    @transaction.atomic
    def _run_inside_transaction(
        self, func: Callable, target: TargetType, *args: Any, **kwargs: Any
    ) -> Any:
        hooks_params = {}
        keys = list(kwargs.keys())
        for k in keys:
            if k.startswith('hooks__') and len(k) > 7:
                hooks_params[k[7:]] = kwargs.pop(k)
        return func(target, *args, hooks_params=hooks_params, **kwargs)

    def run(
        self, operation: str, target: TargetType, *args: Any, _ignore_hooks=False, **kwargs: Any
    ):
        if _ignore_hooks:
            return getattr(target, f'UNWATCHED_{operation}')(*args, **kwargs)
        return getattr(self, f'_{operation}')(target, *args, **kwargs)

    def is_overriden(self, method_name: str) -> bool:
        cls = type(self)
        classes = inspect.getmro(cls)[1:]
        return any(
            hasattr(klass, method_name)
            and not getattr(klass, method_name).__code__ is getattr(self, method_name).__code__
            for klass in classes
        )
