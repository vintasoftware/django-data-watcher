from django_watcher.mixins import DeleteWatcherMixin


class WatchInspector:
    @classmethod
    def assert_hook(cls, hook, asserption, *args, **kwargs):
        cls_hook = getattr(cls, hook)
        asserption_func = getattr(cls_hook, asserption)
        asserption_func(*args, **kwargs)


class StubDeleteWatcher(WatchInspector, DeleteWatcherMixin):
    pass
