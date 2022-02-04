from django.test import TestCase

from .models import (
    CasualStringWatcherModel,
    CasualStringWatcherModel2,
    StringWatcherModel,
    StringWatcherModel2,
)
from .watchers import StubCreateWatcher, StubDeleteWatcher


class TestImportWatcher(TestCase):
    def test_complete_path_import(self):
        model = StringWatcherModel()
        model2 = StringWatcherModel2()

        self.assertEqual(getattr(model, '_watcher'), StubCreateWatcher)
        self.assertEqual(getattr(model2, '_watcher'), StubDeleteWatcher)

    def test_casual_path_import(self):
        model = CasualStringWatcherModel()
        model2 = CasualStringWatcherModel2()

        self.assertEqual(getattr(model, '_watcher'), StubCreateWatcher)
        self.assertEqual(getattr(model2, '_watcher'), StubDeleteWatcher)
