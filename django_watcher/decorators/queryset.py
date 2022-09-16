from typing import TYPE_CHECKING, List, Type

from .helpers import generate_settable, get_watched_functions, unwatched_create


if TYPE_CHECKING:
    from django.db import models  # noqa


def get_qs_cls(qs: 'models.QuerySet', watched_operations: List[str]) -> Type['models.QuerySet']:
    qs_cls = qs.__class__

    qs_name = (
        f'{qs.model.__name__}QuerySet'
        if 'django.db.models.query.QuerySet' in str(qs_cls)
        else qs_cls.__name__
    )

    new_qs_cls = type(qs_name, (qs_cls,), {})

    for func in get_watched_functions(new_qs_cls, watched_operations):
        setattr(
            new_qs_cls,
            f'UNWATCHED_{func.__name__}',
            func if func.__name__ != 'create' else unwatched_create,
        )

    settable = generate_settable(new_qs_cls, 'queryset')
    for operation in watched_operations:
        settable(operation)

    return new_qs_cls  # type: ignore
