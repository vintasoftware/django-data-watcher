from unittest.mock import MagicMock, Mock

from django.db.models import QuerySet
from django.test.testcases import TestCase

from faker import Faker

from django_watcher.abstract_watcher import AbstractWatcher
from tests.models import DeleteModel


class TestAbstractWatcher(TestCase):
    def setUp(self) -> None:
        class MyWatcher(AbstractWatcher):
            pass

        watched_operation = MagicMock()
        MyWatcher._watched_operation = classmethod(watched_operation)  # noqa

        self.Watcher = MyWatcher
        self.operation = watched_operation
        self.fake = Faker()

    def test_run_without_additional_params(self):
        target = Mock()
        self.Watcher.run('watched_operation', target)
        self.operation.assert_called_once_with(self.Watcher, target)

    def test_run_with_additional_params(self):
        target = Mock()
        args = self.fake.pylist()
        kwargs = self.fake.pydict()
        self.Watcher.run('watched_operation', target, *args, **kwargs)
        self.operation.assert_called_once_with(self.Watcher, target, *args, **kwargs)

    def test_is_overriden(self):
        self.assertFalse(self.Watcher.is_overriden('run'))
        self.assertFalse(self.Watcher.is_overriden('to_queryset'))

        self.Watcher.run = classmethod(lambda operation, target, *args, **kwargs: None)
        self.Watcher.to_queryset = classmethod(lambda target: None)

        self.assertTrue(self.Watcher.is_overriden('run'))
        self.assertTrue(self.Watcher.is_overriden('to_queryset'))

    def test_is_queryset(self):
        self.assertTrue(self.Watcher.is_queryset(DeleteModel.objects.all()))
        self.assertFalse(self.Watcher.is_queryset(DeleteModel.objects.create(text='hello')))

    def test_to_queryset(self):
        qs = DeleteModel.objects.all()
        result_qs = self.Watcher.to_queryset(qs)

        model = DeleteModel.objects.create(text='hello')
        model_qs = self.Watcher.to_queryset(model)

        self.assertIsInstance(qs, QuerySet)
        self.assertIsInstance(model_qs, QuerySet)

        self.assertIs(qs, result_qs)
        self.assertEqual(model, model_qs.first())
