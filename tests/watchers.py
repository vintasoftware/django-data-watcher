from typing import Callable, Tuple

from django_watcher.mixins import (
    CreateWatcherMixin,
    DeleteWatcherMixin,
    SaveWatcherMixin,
    UpdateWatcherMixin,
)


class WatchInspector:

    overriden_hooks = []

    @classmethod
    def assert_hook(cls, hook, asserption, *args, **kwargs):
        cls_hook = getattr(cls, hook)
        asserption_func = getattr(cls_hook, asserption)
        asserption_func(*args, **kwargs)

    @classmethod
    def set_hooks(cls, *args: Tuple[str, Callable]) -> None:
        for hook_name, hook in args:
            setattr(cls, hook_name, hook)
            cls.overriden_hooks.append(hook_name)

    @classmethod
    def is_overriden(cls, method_name: str):
        return (
            True
            if method_name in cls.overriden_hooks
            else super().is_overriden(method_name)  # noqa
        )


class StubDeleteWatcher(WatchInspector, DeleteWatcherMixin):
    pass


class StubCreateWatcher(WatchInspector, CreateWatcherMixin):
    pass


class StubSaveWatcher(WatchInspector, SaveWatcherMixin):
    pass


class StubUpdateWatcher(WatchInspector, UpdateWatcherMixin):
    pass


class StubSaveDeleteWatcher(WatchInspector, SaveWatcherMixin, DeleteWatcherMixin):
    pass
