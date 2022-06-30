from unittest.mock import MagicMock, Mock

from django.db.models import QuerySet
from django.test.testcases import TestCase

from faker import Faker

from django_watcher.abstract_watcher import AbstractWatcher
from tests.models import CreateModel, DeleteModel, SaveModel, UpdateModel
from tests.watchers import StubCreateWatcher, StubDeleteWatcher, StubSaveWatcher, StubUpdateWatcher

from .helpers import CopyingMock


class TestAbstractWatcher(TestCase):
    def setUp(self) -> None:
        class MyWatcher(AbstractWatcher):
            pass

        watched_operation = MagicMock()
        setattr(MyWatcher, '_watched_operation', classmethod(watched_operation))

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


class TestRunOperationsWithIgnoreHooks(TestCase):
    def setUp(self) -> None:
        self.mock: MagicMock = CopyingMock()

    def test_create_instance(self):
        StubCreateWatcher.set_hooks(
            ('pre_create', self.mock.pre_create), ('post_create', self.mock.post_create)
        )

        instance = CreateModel(text='text')
        instance.save(_ignore_hooks=True)

        StubCreateWatcher.assert_hook('pre_create', 'assert_not_called')
        StubCreateWatcher.assert_hook('post_create', 'assert_not_called')
        self.assertEqual(1, CreateModel.objects.count())

    def test_create_query(self):
        StubCreateWatcher.set_hooks(
            ('pre_create', self.mock.pre_create), ('post_create', self.mock.post_create)
        )

        CreateModel.objects.create(text='text', _ignore_hooks=True)

        StubCreateWatcher.assert_hook('pre_create', 'assert_not_called')
        StubCreateWatcher.assert_hook('post_create', 'assert_not_called')
        self.assertEqual(1, CreateModel.objects.count())

    def test_delete_instance(self):
        StubDeleteWatcher.set_hooks(
            ('pre_delete', self.mock.pre_delete), ('post_delete', self.mock.post_delete)
        )

        instance = DeleteModel(text='text')
        instance.save()

        self.assertEqual(1, DeleteModel.objects.count())
        instance.delete(_ignore_hooks=True)

        StubDeleteWatcher.assert_hook('pre_delete', 'assert_not_called')
        StubDeleteWatcher.assert_hook('post_delete', 'assert_not_called')
        self.assertEqual(0, DeleteModel.objects.count())

    def test_delete_query(self):
        StubDeleteWatcher.set_hooks(
            ('pre_delete', self.mock.pre_delete), ('post_delete', self.mock.post_delete)
        )

        instance = DeleteModel(text='text')
        instance.save()

        self.assertEqual(1, DeleteModel.objects.count())
        DeleteModel.objects.filter(pk=instance.pk).delete(_ignore_hooks=True)

        StubDeleteWatcher.assert_hook('pre_delete', 'assert_not_called')
        StubDeleteWatcher.assert_hook('post_delete', 'assert_not_called')
        self.assertEqual(0, DeleteModel.objects.count())

    def test_update_intance(self):
        StubUpdateWatcher.set_hooks(
            ('pre_update', self.mock.pre_update), ('post_update', self.mock.post_update)
        )

        instance = UpdateModel(text='text')
        instance.save()

        instance.text = 'new_text'
        instance.save(_ignore_hooks=True)

        StubUpdateWatcher.assert_hook('pre_update', 'assert_not_called')
        StubUpdateWatcher.assert_hook('post_update', 'assert_not_called')
        self.assertEqual(1, UpdateModel.objects.count())

    def test_update_query(self):
        StubUpdateWatcher.set_hooks(
            ('pre_update', self.mock.pre_update), ('post_update', self.mock.post_update)
        )

        instance = UpdateModel(text='text')
        instance.save()

        UpdateModel.objects.filter(pk=instance.pk).update(text='new_text', _ignore_hooks=True)

        StubUpdateWatcher.assert_hook('pre_update', 'assert_not_called')
        StubUpdateWatcher.assert_hook('post_update', 'assert_not_called')
        self.assertEqual(1, UpdateModel.objects.count())

    def test_save_instance(self):
        StubSaveWatcher.set_hooks(
            ('pre_create', self.mock.pre_create),
            ('post_create', self.mock.post_create),
            ('pre_update', self.mock.pre_update),
            ('post_update', self.mock.post_update),
            ('pre_save', self.mock.pre_save),
            ('post_save', self.mock.post_save),
        )

        instance = SaveModel(text='text')
        instance.save(_ignore_hooks=True)

        instance.text = 'new_text'
        instance.save(_ignore_hooks=True)

        StubSaveWatcher.assert_hook('pre_create', 'assert_not_called')
        StubSaveWatcher.assert_hook('post_create', 'assert_not_called')
        StubSaveWatcher.assert_hook('pre_update', 'assert_not_called')
        StubSaveWatcher.assert_hook('post_update', 'assert_not_called')
        StubSaveWatcher.assert_hook('pre_save', 'assert_not_called')
        StubSaveWatcher.assert_hook('post_save', 'assert_not_called')
        self.assertEqual(1, SaveModel.objects.count())

    def test_save_query(self):
        StubSaveWatcher.set_hooks(
            ('pre_create', self.mock.pre_create),
            ('post_create', self.mock.post_create),
            ('pre_update', self.mock.pre_update),
            ('post_update', self.mock.post_update),
            ('pre_save', self.mock.pre_save),
            ('post_save', self.mock.post_save),
        )

        instance = SaveModel.objects.create(text='text', _ignore_hooks=True)
        SaveModel.objects.filter(pk=instance.pk).update(text='new_text', _ignore_hooks=True)

        StubSaveWatcher.assert_hook('pre_create', 'assert_not_called')
        StubSaveWatcher.assert_hook('post_create', 'assert_not_called')
        StubSaveWatcher.assert_hook('pre_update', 'assert_not_called')
        StubSaveWatcher.assert_hook('post_update', 'assert_not_called')
        StubSaveWatcher.assert_hook('pre_save', 'assert_not_called')
        StubSaveWatcher.assert_hook('post_save', 'assert_not_called')
        self.assertEqual(1, SaveModel.objects.count())
