# pylint: disable=too-many-lines

from copy import deepcopy
from unittest.mock import MagicMock, call, patch

from django.test.testcases import TestCase

from .models import CreateModel, DeleteModel, SaveDeleteModel, SaveModel, UpdateModel
from .watchers import (
    StubCreateWatcher,
    StubDeleteWatcher,
    StubSaveDeleteWatcher,
    StubSaveWatcher,
    StubUpdateWatcher,
)


class CopyingMock(MagicMock):
    def __call__(self, *args, **kwargs):
        args = deepcopy(args)
        kwargs = deepcopy(kwargs)
        return super().__call__(*args, **kwargs)


class CreateMixinTests(TestCase):
    def setUp(self) -> None:
        CreateModel.objects.bulk_create(
            [
                CreateModel(text='text1'),
                CreateModel(text='text2'),
                CreateModel(text='text3'),
                CreateModel(text='text4'),
                CreateModel(text='text5'),
            ]
        )

        self.mock: MagicMock = CopyingMock()
        StubCreateWatcher.set_hooks(
            ('pre_create', self.mock.pre_create), ('post_create', self.mock.post_create)
        )

    def test_hooks_with_instance(self):
        instance = CreateModel(text='text')
        instance.save()

        StubCreateWatcher.assert_hook(
            'pre_create', 'assert_called_once_with', [CreateModel(text='text')]
        )
        StubCreateWatcher.assert_hook(
            'post_create', 'assert_called_once_with', CreateModel.objects.filter(pk=instance.pk)
        )
        self.assertEqual(6, CreateModel.objects.count())

    def test_hooks_with_objects(self):
        instance = CreateModel.objects.create(text='text')

        StubCreateWatcher.assert_hook(
            'pre_create', 'assert_called_once_with', [CreateModel(text='text')]
        )
        StubCreateWatcher.assert_hook(
            'post_create', 'assert_called_once_with', CreateModel.objects.filter(pk=instance.pk)
        )
        self.assertEqual(6, CreateModel.objects.count())

    def test_hooks_order_with_instance(self):
        instance = CreateModel(text='text')
        self.mock.UNWATCHED_save.side_effect = instance.UNWATCHED_save  # noqa
        with patch.object(instance, 'UNWATCHED_save', self.mock.UNWATCHED_save):
            instance.save()

        self.mock.assert_has_calls(
            [
                call.pre_create([CreateModel(text='text')]),
                call.UNWATCHED_save(),
                call.post_create(CreateModel.objects.filter(pk=instance.pk)),
            ]
        )
        self.assertEqual(len(self.mock.mock_calls), 3)
        self.assertEqual(6, CreateModel.objects.count())

    def test_hooks_order_with_objects(self):
        qs = CreateModel.objects.get_queryset()
        self.mock.UNWATCHED_create.side_effect = qs.UNWATCHED_create
        setattr(qs, 'UNWATCHED_create', self.mock.UNWATCHED_create)
        with patch.object(CreateModel.objects, 'get_queryset', lambda: qs):
            instance = CreateModel.objects.create(text='text')

        self.mock.assert_has_calls(
            [
                call.pre_create([CreateModel(text='text')]),
                call.UNWATCHED_create(text='text'),
                call.post_create(CreateModel.objects.filter(pk=instance.pk)),
            ]
        )
        self.assertEqual(len(self.mock.mock_calls), 3)
        self.assertEqual(6, CreateModel.objects.count())

    def test_exception_on_post_create_dont_save(self):
        self.mock.post_create.side_effect = Exception

        with self.assertRaises(Exception):
            CreateModel.objects.create(text='fake')
            CreateModel(text='fake').save()

        self.assertEqual(CreateModel.objects.count(), 5)

    def test_exception_on_pre_create_dont_save(self):
        self.mock.pre_create.side_effect = Exception

        with self.assertRaises(Exception):
            CreateModel.objects.create(text='fake')
            CreateModel(text='fake').save()

        self.assertEqual(CreateModel.objects.count(), 5)

    def test_dont_call_hooks_on_update_with_instance(self):
        instance = CreateModel.objects.first()
        instance.text = 'new_text'
        instance.save()

        StubCreateWatcher.assert_hook('pre_create', 'assert_not_called')
        StubCreateWatcher.assert_hook('post_create', 'assert_not_called')

        instance.refresh_from_db()
        self.assertEqual('new_text', instance.text)

    def test_dont_call_hooks_on_update_with_objects(self):
        instance = CreateModel.objects.first()
        CreateModel.objects.filter(pk=instance.pk).update(text='new_text')

        StubCreateWatcher.assert_hook('pre_create', 'assert_not_called')
        StubCreateWatcher.assert_hook('post_create', 'assert_not_called')

        instance.refresh_from_db()
        self.assertEqual('new_text', instance.text)


class DeleteMixinTests(TestCase):
    def setUp(self) -> None:
        DeleteModel.objects.bulk_create(
            [
                CreateModel(text='text1'),
                CreateModel(text='text2'),
                CreateModel(text='text3'),
                CreateModel(text='text4'),
                CreateModel(text='text5'),
            ]
        )

        self.mock: MagicMock = CopyingMock()
        StubDeleteWatcher.set_hooks(
            ('pre_delete', self.mock.pre_delete), ('post_delete', self.mock.post_delete)
        )

    def test_hooks_with_instance(self):
        instance = DeleteModel.objects.first()
        pk = instance.pk
        instance_copy = deepcopy(instance)
        instance.delete()

        StubDeleteWatcher.assert_hook(
            'pre_delete', 'assert_called_once_with', DeleteModel.objects.filter(pk=pk)
        )
        StubDeleteWatcher.assert_hook('post_delete', 'assert_called_once_with', [instance_copy])
        self.assertEqual(4, DeleteModel.objects.count())

    def test_hooks_with_objects(self):
        instance = DeleteModel.objects.first()
        DeleteModel.objects.filter(pk=instance.pk).delete()

        StubDeleteWatcher.assert_hook(
            'pre_delete', 'assert_called_once_with', DeleteModel.objects.filter(pk=instance.pk)
        )
        StubDeleteWatcher.assert_hook('post_delete', 'assert_called_once_with', [instance])
        self.assertEqual(4, DeleteModel.objects.count())

    def test_hooks_with_multiple_objects(self):
        instances = list(DeleteModel.objects.all())
        DeleteModel.objects.all().delete()

        StubDeleteWatcher.assert_hook(
            'pre_delete', 'assert_called_once_with', DeleteModel.objects.all()
        )
        StubDeleteWatcher.assert_hook('post_delete', 'assert_called_once_with', instances)
        self.assertEqual(0, DeleteModel.objects.count())

    def test_hooks_order_with_instance(self):
        instance = DeleteModel.objects.first()
        instance_copy = deepcopy(instance)
        self.mock.UNWATCHED_delete.side_effect = instance.UNWATCHED_delete
        with patch.object(instance, 'UNWATCHED_delete', self.mock.UNWATCHED_delete):
            instance.delete()

        self.mock.assert_has_calls(
            [
                call.pre_delete(DeleteModel.objects.filter(pk=instance_copy.pk)),
                call.UNWATCHED_delete(),
                call.post_delete([instance_copy]),
            ]
        )
        self.assertEqual(len(self.mock.mock_calls), 3)
        self.assertEqual(4, DeleteModel.objects.count())

    def test_hooks_order_with_objects(self):
        qs = DeleteModel.objects.all()
        instance = qs.first()
        qs = qs.filter(pk=instance.pk)
        self.mock.UNWATCHED_delete.side_effect = qs.UNWATCHED_delete
        setattr(qs, 'UNWATCHED_delete', self.mock.UNWATCHED_delete)
        with patch.object(DeleteModel.objects, 'filter', lambda **_: qs):
            DeleteModel.objects.filter(pk='fake').delete()

        self.mock.assert_has_calls(
            [
                call.pre_delete(DeleteModel.objects.filter(pk=instance.pk)),
                call.UNWATCHED_delete(),
                call.post_delete([instance]),
            ]
        )
        self.assertEqual(len(self.mock.mock_calls), 3)
        self.assertEqual(4, DeleteModel.objects.count())

    # def test_hooks_order_with_multiple_objects(self):
    #     qs = DeleteModel.objects.all()
    #     instances = list(qs)
    #     pks = qs.values_list('id', flat=True)
    #     qs = qs.filter(pk__in=pks)
    #     self.mock.UNWATCHED_delete.side_effect = qs.UNWATCHED_delete
    #     setattr(qs, 'UNWATCHED_delete', self.mock.UNWATCHED_delete)
    #     with patch.object(DeleteModel.objects, 'filter', lambda **_: qs):
    #         DeleteModel.objects.filter(pk="fake").delete()

    #     import pdb

    #     pdb.set_trace()
    #     self.mock.assert_has_calls(
    #         [
    #             call.pre_delete(DeleteModel.objects.filter(pk__in=pks)),
    #             call.UNWATCHED_delete(),
    #             call.post_delete(instances),
    #         ]
    #     )
    #     self.assertEqual(len(self.mock.mock_calls), 3)
    #     self.assertEqual(0, DeleteModel.objects.count())

    def test_exception_on_post_delete_dont_delete(self):
        self.mock.post_delete.side_effect = Exception

        with self.assertRaises(Exception):
            instance = DeleteModel.objects.first()
            instance.delete()
            DeleteModel.objects.all().delete()

        self.assertEqual(DeleteModel.objects.count(), 5)

    def test_exception_on_pre_delete_dont_delete(self):
        self.mock.pre_delete.side_effect = Exception

        with self.assertRaises(Exception):
            instance = DeleteModel.objects.first()
            instance.delete()
            DeleteModel.objects.all().delete()

        self.assertEqual(DeleteModel.objects.count(), 5)


class UpdateMixinTests(TestCase):
    def setUp(self) -> None:
        UpdateModel.objects.bulk_create(
            [
                UpdateModel(text='text1'),
                UpdateModel(text='text2'),
                UpdateModel(text='text3'),
                UpdateModel(text='text4'),
                UpdateModel(text='text5'),
            ]
        )
        self.mock: MagicMock = CopyingMock()
        StubUpdateWatcher.set_hooks(
            ('pre_update', self.mock.pre_update), ('post_update', self.mock.post_update)
        )

    def test_hooks_with_instance(self):
        updated = UpdateModel.objects.first()
        updated.text = 'new_text'
        updated.save()

        StubUpdateWatcher.assert_hook(
            'pre_update', 'assert_called_once_with', UpdateModel.objects.filter(pk=updated.pk)
        )
        StubUpdateWatcher.assert_hook(
            'post_update', 'assert_called_once_with', UpdateModel.objects.filter(pk=updated.pk)
        )
        updated.refresh_from_db()
        self.assertEqual('new_text', updated.text)

    def test_hooks_with_objects(self):
        first = UpdateModel.objects.first()
        UpdateModel.objects.filter(pk=first.pk).update(text='fake')

        StubUpdateWatcher.assert_hook(
            'pre_update', 'assert_called_once_with', UpdateModel.objects.filter(pk=first.pk)
        )
        StubUpdateWatcher.assert_hook(
            'post_update', 'assert_called_once_with', UpdateModel.objects.filter(pk=first.pk)
        )
        first.refresh_from_db()
        self.assertEqual('fake', first.text)

    def test_hooks_with_multiple_objects(self):
        UpdateModel.objects.update(text='fake')

        StubUpdateWatcher.assert_hook(
            'pre_update', 'assert_called_once_with', UpdateModel.objects.all()
        )
        StubUpdateWatcher.assert_hook(
            'post_update', 'assert_called_once_with', UpdateModel.objects.all()
        )
        self.assertEqual(5, UpdateModel.objects.filter(text='fake').count())

    def test_hooks_order_with_instance(self):
        instance = UpdateModel.objects.first()
        self.mock.UNWATCHED_save.side_effect = instance.UNWATCHED_save  # noqa
        with patch.object(instance, 'UNWATCHED_save', self.mock.UNWATCHED_save):
            instance.text = 'new_text'
            instance.save()

        self.mock.assert_has_calls(
            [
                call.pre_update(UpdateModel.objects.filter(pk=instance.pk)),
                call.UNWATCHED_save(),
                call.post_update(UpdateModel.objects.filter(pk=instance.pk)),
            ]
        )
        self.assertEqual(len(self.mock.mock_calls), 3)
        instance.refresh_from_db()
        self.assertEqual('new_text', instance.text)

    def test_hooks_order_with_objects(self):
        instance = UpdateModel.objects.first()
        qs = UpdateModel.objects.filter(pk=instance.pk)
        self.mock.UNWATCHED_update.side_effect = qs.UNWATCHED_update
        setattr(qs, 'UNWATCHED_update', self.mock.UNWATCHED_update)
        with patch.object(UpdateModel.objects, 'filter', lambda **_: qs):
            UpdateModel.objects.filter(pk='fake').update(text='new_text')

        self.mock.assert_has_calls(
            [
                call.pre_update(UpdateModel.objects.filter(pk=instance.pk)),
                call.UNWATCHED_update(text='new_text'),
                call.post_update(UpdateModel.objects.filter(pk=instance.pk)),
            ]
        )
        self.assertEqual(len(self.mock.mock_calls), 3)

        instance.refresh_from_db()
        self.assertEqual('new_text', instance.text)

    def test_hooks_order_with_multiples_objects(self):
        pks = UpdateModel.objects.all().values_list('pk', flat=True)
        qs = UpdateModel.objects.filter(pk__in=pks)
        self.mock.UNWATCHED_update.side_effect = qs.UNWATCHED_update
        setattr(qs, 'UNWATCHED_update', self.mock.UNWATCHED_update)
        with patch.object(UpdateModel.objects, 'filter', lambda **_: qs):
            UpdateModel.objects.filter(pk='fake').update(text='new_text')

        self.mock.assert_has_calls(
            [
                call.pre_update(UpdateModel.objects.filter(pk__in=pks)),
                call.UNWATCHED_update(text='new_text'),
                call.post_update(UpdateModel.objects.filter(pk__in=pks)),
            ]
        )
        self.assertEqual(len(self.mock.mock_calls), 3)
        self.assertEqual(5, UpdateModel.objects.filter(text='new_text').count())

    def test_dont_call_hooks_on_create_with_instance(self):
        instance = UpdateModel(text='text')
        instance.save()

        StubUpdateWatcher.assert_hook('pre_update', 'assert_not_called')
        StubUpdateWatcher.assert_hook('post_update', 'assert_not_called')
        self.assertEqual(6, UpdateModel.objects.count())

    def test_dont_call_hooks_on_create_with_objects(self):
        UpdateModel.objects.create(text='text')

        StubUpdateWatcher.assert_hook('pre_update', 'assert_not_called')
        StubUpdateWatcher.assert_hook('post_update', 'assert_not_called')
        self.assertEqual(6, UpdateModel.objects.count())

    def test_exception_on_post_update_dont_save(self):
        self.mock.post_update.side_effect = Exception

        with self.assertRaises(Exception):
            UpdateModel.objects.all().update(text='new_text')
            instance = UpdateModel.objects.first()
            instance.text = 'new_text'
            instance.save()

        self.assertEqual(0, UpdateModel.objects.filter(text='new_text').count())

    def test_exception_on_pre_update_dont_save(self):
        self.mock.pre_update.side_effect = Exception

        with self.assertRaises(Exception):
            UpdateModel.objects.all().update(text='new_text')
            instance = UpdateModel.objects.first()
            instance.text = 'new_text'
            instance.save()

        self.assertEqual(0, UpdateModel.objects.filter(text='new_text').count())


class SaveMixinTests(TestCase):
    def setUp(self) -> None:
        SaveModel.objects.bulk_create(
            [
                SaveModel(text='text1'),
                SaveModel(text='text2'),
                SaveModel(text='text3'),
                SaveModel(text='text4'),
                SaveModel(text='text5'),
            ]
        )

        self.mock: MagicMock = CopyingMock()
        StubSaveWatcher.set_hooks(
            ('pre_create', self.mock.pre_create),
            ('post_create', self.mock.post_create),
            ('pre_update', self.mock.pre_update),
            ('post_update', self.mock.post_update),
            ('pre_save', self.mock.pre_save),
            ('post_save', self.mock.post_save),
        )

    def test_create_hooks_with_instance(self):
        instance = SaveModel(text='text')
        instance.save()

        StubSaveWatcher.assert_hook('pre_save', 'assert_called_once_with', [SaveModel(text='text')])
        StubSaveWatcher.assert_hook(
            'pre_create', 'assert_called_once_with', [SaveModel(text='text')]
        )
        StubSaveWatcher.assert_hook(
            'post_create', 'assert_called_once_with', SaveModel.objects.filter(pk=instance.pk)
        )
        StubSaveWatcher.assert_hook(
            'post_save', 'assert_called_once_with', SaveModel.objects.filter(pk=instance.pk)
        )
        self.assertEqual(6, SaveModel.objects.count())

    def test_update_hooks_with_instance(self):
        instance = SaveModel.objects.first()
        instance.text = 'new_text'
        instance.save()

        StubSaveWatcher.assert_hook(
            'pre_save', 'assert_called_once_with', SaveModel.objects.filter(pk=instance.pk)
        )
        StubSaveWatcher.assert_hook(
            'pre_update', 'assert_called_once_with', SaveModel.objects.filter(pk=instance.pk)
        )
        StubSaveWatcher.assert_hook(
            'post_update', 'assert_called_once_with', SaveModel.objects.filter(pk=instance.pk)
        )
        StubSaveWatcher.assert_hook(
            'post_save', 'assert_called_once_with', SaveModel.objects.filter(pk=instance.pk)
        )
        instance.refresh_from_db()
        self.assertEqual('new_text', instance.text)

    def test_create_hooks_with_objects(self):
        instance = SaveModel.objects.create(text='text')

        StubSaveWatcher.assert_hook('pre_save', 'assert_called_once_with', [SaveModel(text='text')])
        StubSaveWatcher.assert_hook(
            'pre_create', 'assert_called_once_with', [SaveModel(text='text')]
        )
        StubSaveWatcher.assert_hook(
            'post_create', 'assert_called_once_with', SaveModel.objects.filter(pk=instance.pk)
        )
        StubSaveWatcher.assert_hook(
            'post_save', 'assert_called_once_with', SaveModel.objects.filter(pk=instance.pk)
        )
        self.assertEqual(6, SaveModel.objects.count())

    def test_update_hooks_with_objects(self):
        first = SaveModel.objects.first()
        SaveModel.objects.filter(pk=first.pk).update(text='new_text')

        StubSaveWatcher.assert_hook(
            'pre_save', 'assert_called_once_with', SaveModel.objects.filter(pk=first.pk)
        )
        StubSaveWatcher.assert_hook(
            'pre_update', 'assert_called_once_with', SaveModel.objects.filter(pk=first.pk)
        )
        StubSaveWatcher.assert_hook(
            'post_update', 'assert_called_once_with', SaveModel.objects.filter(pk=first.pk)
        )
        StubSaveWatcher.assert_hook(
            'post_save', 'assert_called_once_with', SaveModel.objects.filter(pk=first.pk)
        )
        first.refresh_from_db()
        self.assertEqual('new_text', first.text)

    def test_update_hooks_with_multiple_objects(self):
        SaveModel.objects.update(text='new_text')

        StubSaveWatcher.assert_hook('pre_save', 'assert_called_once_with', SaveModel.objects.all())
        StubSaveWatcher.assert_hook(
            'pre_update', 'assert_called_once_with', SaveModel.objects.all()
        )
        StubSaveWatcher.assert_hook(
            'post_update', 'assert_called_once_with', SaveModel.objects.all()
        )
        StubSaveWatcher.assert_hook('post_save', 'assert_called_once_with', SaveModel.objects.all())
        self.assertEqual(5, SaveModel.objects.filter(text='new_text').count())

    def test_create_hooks_order_with_instance(self):
        instance = SaveModel(text='text')
        self.mock.UNWATCHED_save.side_effect = instance.UNWATCHED_save  # noqa
        with patch.object(instance, 'UNWATCHED_save', self.mock.UNWATCHED_save):
            instance.save()

        self.mock.assert_has_calls(
            [
                call.pre_save([SaveModel(text='text')]),
                call.pre_create([SaveModel(text='text')]),
                call.UNWATCHED_save(),
                call.post_create(SaveModel.objects.filter(pk=instance.pk)),
                call.post_save(SaveModel.objects.filter(pk=instance.pk)),
            ]
        )
        self.assertEqual(len(self.mock.mock_calls), 5)
        self.assertEqual(6, SaveModel.objects.count())

    def test_update_hooks_order_with_instance(self):
        instance = SaveModel.objects.first()
        self.mock.UNWATCHED_save.side_effect = instance.UNWATCHED_save  # noqa
        with patch.object(instance, 'UNWATCHED_save', self.mock.UNWATCHED_save):
            instance.text = 'new_text'
            instance.save()

        self.mock.assert_has_calls(
            [
                call.pre_save(SaveModel.objects.filter(pk=instance.pk)),
                call.pre_update(SaveModel.objects.filter(pk=instance.pk)),
                call.UNWATCHED_save(),
                call.post_update(SaveModel.objects.filter(pk=instance.pk)),
                call.post_save(SaveModel.objects.filter(pk=instance.pk)),
            ]
        )
        self.assertEqual(len(self.mock.mock_calls), 5)
        instance.refresh_from_db()
        self.assertEqual('new_text', instance.text)

    def test_create_hooks_order_with_objects(self):
        qs = SaveModel.objects.get_queryset()
        self.mock.UNWATCHED_create.side_effect = qs.UNWATCHED_create
        setattr(qs, 'UNWATCHED_create', self.mock.UNWATCHED_create)
        with patch.object(SaveModel.objects, 'get_queryset', lambda: qs):
            instance = SaveModel.objects.create(text='text')

        self.mock.assert_has_calls(
            [
                call.pre_save([SaveModel(text='text')]),
                call.pre_create([SaveModel(text='text')]),
                call.UNWATCHED_create(text='text'),
                call.post_create(SaveModel.objects.filter(pk=instance.pk)),
                call.post_save(SaveModel.objects.filter(pk=instance.pk)),
            ]
        )
        self.assertEqual(len(self.mock.mock_calls), 5)
        self.assertEqual(6, SaveModel.objects.count())

    def test_update_hooks_order_with_objects(self):
        instance = SaveModel.objects.first()
        qs = SaveModel.objects.filter(pk=instance.pk)
        self.mock.UNWATCHED_update.side_effect = qs.UNWATCHED_update
        setattr(qs, 'UNWATCHED_update', self.mock.UNWATCHED_update)
        with patch.object(SaveModel.objects, 'filter', lambda **_: qs):
            SaveModel.objects.filter(pk='fake').update(text='new_text')

        self.mock.assert_has_calls(
            [
                call.pre_save(SaveModel.objects.filter(pk=instance.pk)),
                call.pre_update(SaveModel.objects.filter(pk=instance.pk)),
                call.UNWATCHED_update(text='new_text'),
                call.post_update(SaveModel.objects.filter(pk=instance.pk)),
                call.post_save(SaveModel.objects.filter(pk=instance.pk)),
            ]
        )
        self.assertEqual(len(self.mock.mock_calls), 5)

        instance.refresh_from_db()
        self.assertEqual('new_text', instance.text)

    def test_update_hooks_order_with_multiples_objects(self):
        pks = SaveModel.objects.all().values_list('pk', flat=True)
        qs = SaveModel.objects.filter(pk__in=pks)
        self.mock.UNWATCHED_update.side_effect = qs.UNWATCHED_update
        setattr(qs, 'UNWATCHED_update', self.mock.UNWATCHED_update)
        with patch.object(SaveModel.objects, 'filter', lambda **_: qs):
            SaveModel.objects.filter(pk='fake').update(text='new_text')

        self.mock.assert_has_calls(
            [
                call.pre_save(SaveModel.objects.filter(pk__in=pks)),
                call.pre_update(SaveModel.objects.filter(pk__in=pks)),
                call.UNWATCHED_update(text='new_text'),
                call.post_update(SaveModel.objects.filter(pk__in=pks)),
                call.post_save(SaveModel.objects.filter(pk__in=pks)),
            ]
        )
        self.assertEqual(len(self.mock.mock_calls), 5)
        self.assertEqual(5, SaveModel.objects.filter(text='new_text').count())

    def test_exception_on_pre_create_dont_save(self):
        self.mock.pre_create.side_effect = Exception

        with self.assertRaises(Exception):
            SaveModel.objects.create(text='fake')
            SaveModel(text='fake').save()

        self.assertEqual(SaveModel.objects.count(), 5)

    def test_exception_on_post_create_dont_save(self):
        self.mock.post_create.side_effect = Exception

        with self.assertRaises(Exception):
            SaveModel.objects.create(text='fake')
            SaveModel(text='fake').save()

        self.assertEqual(SaveModel.objects.count(), 5)

    def test_exception_on_pre_update_dont_save(self):
        self.mock.pre_update.side_effect = Exception

        with self.assertRaises(Exception):
            SaveModel.objects.all().update(text='new_text')
            instance = SaveModel.objects.first()
            instance.text = 'new_text'
            instance.save()

        self.assertEqual(0, SaveModel.objects.filter(text='new_text').count())

    def test_exception_on_post_update_dont_save(self):
        self.mock.post_update.side_effect = Exception

        with self.assertRaises(Exception):
            SaveModel.objects.all().update(text='new_text')
            instance = SaveModel.objects.first()
            instance.text = 'new_text'
            instance.save()

        self.assertEqual(0, SaveModel.objects.filter(text='new_text').count())

    def test_exception_on_pre_save_dont_save(self):
        self.mock.pre_save.side_effect = Exception

        with self.assertRaises(Exception):
            SaveModel.objects.all().update(text='new_text')
            instance = SaveModel.objects.first()
            instance.text = 'new_text'
            instance.save()

        self.assertEqual(0, SaveModel.objects.filter(text='new_text').count())

    def test_exception_on_post_save_dont_save(self):
        self.mock.post_save.side_effect = Exception

        with self.assertRaises(Exception):
            SaveModel.objects.all().update(text='new_text')
            instance = SaveModel.objects.first()
            instance.text = 'new_text'
            instance.save()

        self.assertEqual(0, SaveModel.objects.filter(text='new_text').count())


class AllMixinsTests(TestCase):  # noqa
    def setUp(self) -> None:
        SaveDeleteModel.objects.bulk_create(
            [
                SaveDeleteModel(text='text1'),
                SaveDeleteModel(text='text2'),
                SaveDeleteModel(text='text3'),
                SaveDeleteModel(text='text4'),
                SaveDeleteModel(text='text5'),
            ]
        )

        self.mock: MagicMock = CopyingMock()
        StubSaveDeleteWatcher.set_hooks(
            ('pre_create', self.mock.pre_create),
            ('post_create', self.mock.post_create),
            ('pre_update', self.mock.pre_update),
            ('post_update', self.mock.post_update),
            ('pre_save', self.mock.pre_save),
            ('post_save', self.mock.post_save),
            ('pre_delete', self.mock.pre_delete),
            ('post_delete', self.mock.post_delete),
        )

    def test_create_hooks_with_instance(self):
        instance = SaveDeleteModel(text='text')
        instance.save()

        StubSaveDeleteWatcher.assert_hook(
            'pre_save', 'assert_called_once_with', [SaveDeleteModel(text='text')]
        )
        StubSaveDeleteWatcher.assert_hook(
            'pre_create', 'assert_called_once_with', [SaveDeleteModel(text='text')]
        )
        StubSaveDeleteWatcher.assert_hook(
            'post_create', 'assert_called_once_with', SaveDeleteModel.objects.filter(pk=instance.pk)
        )
        StubSaveDeleteWatcher.assert_hook(
            'post_save', 'assert_called_once_with', SaveDeleteModel.objects.filter(pk=instance.pk)
        )
        self.assertEqual(6, SaveDeleteModel.objects.count())

    def test_update_hooks_with_instance(self):
        instance = SaveDeleteModel.objects.first()
        instance.text = 'new_text'
        instance.save()

        StubSaveDeleteWatcher.assert_hook(
            'pre_save', 'assert_called_once_with', SaveDeleteModel.objects.filter(pk=instance.pk)
        )
        StubSaveDeleteWatcher.assert_hook(
            'pre_update', 'assert_called_once_with', SaveDeleteModel.objects.filter(pk=instance.pk)
        )
        StubSaveDeleteWatcher.assert_hook(
            'post_update', 'assert_called_once_with', SaveDeleteModel.objects.filter(pk=instance.pk)
        )
        StubSaveDeleteWatcher.assert_hook(
            'post_save', 'assert_called_once_with', SaveDeleteModel.objects.filter(pk=instance.pk)
        )
        instance.refresh_from_db()
        self.assertEqual('new_text', instance.text)

    def test_delete_hooks_with_instance(self):
        instance = SaveDeleteModel.objects.first()
        pk = instance.pk
        instance_copy = deepcopy(instance)
        instance.delete()

        StubSaveDeleteWatcher.assert_hook(
            'pre_delete', 'assert_called_once_with', SaveDeleteModel.objects.filter(pk=pk)
        )
        StubSaveDeleteWatcher.assert_hook('post_delete', 'assert_called_once_with', [instance_copy])
        self.assertEqual(4, SaveDeleteModel.objects.count())

    def test_create_hooks_with_objects(self):
        instance = SaveDeleteModel.objects.create(text='text')

        StubSaveDeleteWatcher.assert_hook(
            'pre_save', 'assert_called_once_with', [SaveDeleteModel(text='text')]
        )
        StubSaveDeleteWatcher.assert_hook(
            'pre_create', 'assert_called_once_with', [SaveDeleteModel(text='text')]
        )
        StubSaveDeleteWatcher.assert_hook(
            'post_create', 'assert_called_once_with', SaveDeleteModel.objects.filter(pk=instance.pk)
        )
        StubSaveDeleteWatcher.assert_hook(
            'post_save', 'assert_called_once_with', SaveDeleteModel.objects.filter(pk=instance.pk)
        )
        self.assertEqual(6, SaveDeleteModel.objects.count())

    def test_delete_hooks_with_objects(self):
        instance = SaveDeleteModel.objects.first()
        SaveDeleteModel.objects.filter(pk=instance.pk).delete()

        StubSaveDeleteWatcher.assert_hook(
            'pre_delete', 'assert_called_once_with', SaveDeleteModel.objects.filter(pk=instance.pk)
        )
        StubSaveDeleteWatcher.assert_hook('post_delete', 'assert_called_once_with', [instance])
        self.assertEqual(4, SaveDeleteModel.objects.count())

    def test_delete_hooks_with_multiple_objects(self):
        instances = list(SaveDeleteModel.objects.all())
        SaveDeleteModel.objects.all().delete()

        StubSaveDeleteWatcher.assert_hook(
            'pre_delete', 'assert_called_once_with', SaveDeleteModel.objects.all()
        )
        StubSaveDeleteWatcher.assert_hook('post_delete', 'assert_called_once_with', instances)
        self.assertEqual(0, SaveDeleteModel.objects.count())

    def test_update_hooks_with_objects(self):
        first = SaveDeleteModel.objects.first()
        SaveDeleteModel.objects.filter(pk=first.pk).update(text='new_text')

        StubSaveDeleteWatcher.assert_hook(
            'pre_save', 'assert_called_once_with', SaveDeleteModel.objects.filter(pk=first.pk)
        )
        StubSaveDeleteWatcher.assert_hook(
            'pre_update', 'assert_called_once_with', SaveDeleteModel.objects.filter(pk=first.pk)
        )
        StubSaveDeleteWatcher.assert_hook(
            'post_update', 'assert_called_once_with', SaveDeleteModel.objects.filter(pk=first.pk)
        )
        StubSaveDeleteWatcher.assert_hook(
            'post_save', 'assert_called_once_with', SaveDeleteModel.objects.filter(pk=first.pk)
        )
        first.refresh_from_db()
        self.assertEqual('new_text', first.text)

    def test_update_hooks_with_multiple_objects(self):
        SaveDeleteModel.objects.update(text='new_text')

        StubSaveDeleteWatcher.assert_hook(
            'pre_save', 'assert_called_once_with', SaveDeleteModel.objects.all()
        )
        StubSaveDeleteWatcher.assert_hook(
            'pre_update', 'assert_called_once_with', SaveDeleteModel.objects.all()
        )
        StubSaveDeleteWatcher.assert_hook(
            'post_update', 'assert_called_once_with', SaveDeleteModel.objects.all()
        )
        StubSaveDeleteWatcher.assert_hook(
            'post_save', 'assert_called_once_with', SaveDeleteModel.objects.all()
        )
        self.assertEqual(5, SaveDeleteModel.objects.filter(text='new_text').count())

    def test_create_hooks_order_with_instance(self):
        instance = SaveDeleteModel(text='text')
        self.mock.UNWATCHED_save.side_effect = instance.UNWATCHED_save  # noqa
        with patch.object(instance, 'UNWATCHED_save', self.mock.UNWATCHED_save):
            instance.save()

        self.mock.assert_has_calls(
            [
                call.pre_save([SaveDeleteModel(text='text')]),
                call.pre_create([SaveDeleteModel(text='text')]),
                call.UNWATCHED_save(),
                call.post_create(SaveDeleteModel.objects.filter(pk=instance.pk)),
                call.post_save(SaveDeleteModel.objects.filter(pk=instance.pk)),
            ]
        )
        self.assertEqual(len(self.mock.mock_calls), 5)
        self.assertEqual(6, SaveDeleteModel.objects.count())

    def test_delete_hooks_order_with_instance(self):
        instance = SaveDeleteModel.objects.first()
        instance_copy = deepcopy(instance)
        self.mock.UNWATCHED_delete.side_effect = instance.UNWATCHED_delete
        with patch.object(instance, 'UNWATCHED_delete', self.mock.UNWATCHED_delete):
            instance.delete()

        self.mock.assert_has_calls(
            [
                call.pre_delete(SaveDeleteModel.objects.filter(pk=instance_copy.pk)),
                call.UNWATCHED_delete(),
                call.post_delete([instance_copy]),
            ]
        )
        self.assertEqual(len(self.mock.mock_calls), 3)
        self.assertEqual(4, SaveDeleteModel.objects.count())

    def test_update_hooks_order_with_instance(self):
        instance = SaveDeleteModel.objects.first()
        self.mock.UNWATCHED_save.side_effect = instance.UNWATCHED_save  # noqa
        with patch.object(instance, 'UNWATCHED_save', self.mock.UNWATCHED_save):
            instance.text = 'new_text'
            instance.save()

        self.mock.assert_has_calls(
            [
                call.pre_save(SaveDeleteModel.objects.filter(pk=instance.pk)),
                call.pre_update(SaveDeleteModel.objects.filter(pk=instance.pk)),
                call.UNWATCHED_save(),
                call.post_update(SaveDeleteModel.objects.filter(pk=instance.pk)),
                call.post_save(SaveDeleteModel.objects.filter(pk=instance.pk)),
            ]
        )
        self.assertEqual(len(self.mock.mock_calls), 5)
        instance.refresh_from_db()
        self.assertEqual('new_text', instance.text)

    def test_create_hooks_order_with_objects(self):
        qs = SaveDeleteModel.objects.get_queryset()
        self.mock.UNWATCHED_create.side_effect = qs.UNWATCHED_create
        setattr(qs, 'UNWATCHED_create', self.mock.UNWATCHED_create)
        with patch.object(SaveDeleteModel.objects, 'get_queryset', lambda: qs):
            instance = SaveDeleteModel.objects.create(text='text')

        self.mock.assert_has_calls(
            [
                call.pre_save([SaveDeleteModel(text='text')]),
                call.pre_create([SaveDeleteModel(text='text')]),
                call.UNWATCHED_create(text='text'),
                call.post_create(SaveDeleteModel.objects.filter(pk=instance.pk)),
                call.post_save(SaveDeleteModel.objects.filter(pk=instance.pk)),
            ]
        )
        self.assertEqual(len(self.mock.mock_calls), 5)
        self.assertEqual(6, SaveDeleteModel.objects.count())

    def test_delete_hooks_order_with_objects(self):
        qs = SaveDeleteModel.objects.all()
        instance = qs.first()
        qs = qs.filter(pk=instance.pk)
        self.mock.UNWATCHED_delete.side_effect = qs.UNWATCHED_delete
        setattr(qs, 'UNWATCHED_delete', self.mock.UNWATCHED_delete)
        with patch.object(SaveDeleteModel.objects, 'filter', lambda **_: qs):
            SaveDeleteModel.objects.filter(pk='fake').delete()

        self.mock.assert_has_calls(
            [
                call.pre_delete(SaveDeleteModel.objects.filter(pk=instance.pk)),
                call.UNWATCHED_delete(),
                call.post_delete([instance]),
            ]
        )
        self.assertEqual(len(self.mock.mock_calls), 3)
        self.assertEqual(4, SaveDeleteModel.objects.count())

    # def test_delete_hooks_order_with_multiple_objects(self):
    #     qs = SaveDeleteModel.objects.all()
    #     instances = list(qs)
    #     pks = qs.values_list('id', flat=True)
    #     qs = qs.filter(pk__in=pks)
    #     self.mock.UNWATCHED_delete.side_effect = qs.UNWATCHED_delete
    #     setattr(qs, 'UNWATCHED_delete', self.mock.UNWATCHED_delete)
    #     with patch.object(SaveDeleteModel.objects, 'filter', lambda **_: qs):
    #         SaveDeleteModel.objects.filter(pk="fake").delete()

    #     # import pdb

    #     # pdb.set_trace()
    #     self.mock.assert_has_calls(
    #         [
    #             call.pre_delete(SaveDeleteModel.objects.filter(pk__in=pks)),
    #             call.UNWATCHED_delete(),
    #             call.post_delete(instances),
    #         ]
    #     )
    #     self.assertEqual(len(self.mock.mock_calls), 3)
    #     self.assertEqual(0, SaveDeleteModel.objects.count())

    def test_update_hooks_order_with_objects(self):
        instance = SaveDeleteModel.objects.first()
        qs = SaveDeleteModel.objects.filter(pk=instance.pk)
        self.mock.UNWATCHED_update.side_effect = qs.UNWATCHED_update
        setattr(qs, 'UNWATCHED_update', self.mock.UNWATCHED_update)
        with patch.object(SaveDeleteModel.objects, 'filter', lambda **_: qs):
            SaveDeleteModel.objects.filter(pk='fake').update(text='new_text')

        self.mock.assert_has_calls(
            [
                call.pre_save(SaveDeleteModel.objects.filter(pk=instance.pk)),
                call.pre_update(SaveDeleteModel.objects.filter(pk=instance.pk)),
                call.UNWATCHED_update(text='new_text'),
                call.post_update(SaveDeleteModel.objects.filter(pk=instance.pk)),
                call.post_save(SaveDeleteModel.objects.filter(pk=instance.pk)),
            ]
        )
        self.assertEqual(len(self.mock.mock_calls), 5)

        instance.refresh_from_db()
        self.assertEqual('new_text', instance.text)

    def test_update_hooks_order_with_multiples_objects(self):
        pks = SaveDeleteModel.objects.all().values_list('pk', flat=True)
        qs = SaveDeleteModel.objects.filter(pk__in=pks)
        self.mock.UNWATCHED_update.side_effect = qs.UNWATCHED_update
        setattr(qs, 'UNWATCHED_update', self.mock.UNWATCHED_update)
        with patch.object(SaveDeleteModel.objects, 'filter', lambda **_: qs):
            SaveDeleteModel.objects.filter(pk='fake').update(text='new_text')

        self.mock.assert_has_calls(
            [
                call.pre_save(SaveDeleteModel.objects.filter(pk__in=pks)),
                call.pre_update(SaveDeleteModel.objects.filter(pk__in=pks)),
                call.UNWATCHED_update(text='new_text'),
                call.post_update(SaveDeleteModel.objects.filter(pk__in=pks)),
                call.post_save(SaveDeleteModel.objects.filter(pk__in=pks)),
            ]
        )
        self.assertEqual(len(self.mock.mock_calls), 5)
        self.assertEqual(5, SaveDeleteModel.objects.filter(text='new_text').count())

    def test_exception_on_pre_create_dont_save(self):
        self.mock.pre_create.side_effect = Exception

        with self.assertRaises(Exception):
            SaveDeleteModel.objects.create(text='fake')
            SaveDeleteModel(text='fake').save()

        self.assertEqual(SaveDeleteModel.objects.count(), 5)

    def test_exception_on_post_create_dont_save(self):
        self.mock.post_create.side_effect = Exception

        with self.assertRaises(Exception):
            SaveDeleteModel.objects.create(text='fake')
            SaveDeleteModel(text='fake').save()

        self.assertEqual(SaveDeleteModel.objects.count(), 5)

    def test_exception_on_pre_update_dont_save(self):
        self.mock.pre_update.side_effect = Exception

        with self.assertRaises(Exception):
            SaveDeleteModel.objects.all().update(text='new_text')
            instance = SaveDeleteModel.objects.first()
            instance.text = 'new_text'
            instance.save()

        self.assertEqual(0, SaveDeleteModel.objects.filter(text='new_text').count())

    def test_exception_on_post_update_dont_save(self):
        self.mock.post_update.side_effect = Exception

        with self.assertRaises(Exception):
            SaveDeleteModel.objects.all().update(text='new_text')
            instance = SaveDeleteModel.objects.first()
            instance.text = 'new_text'
            instance.save()

        self.assertEqual(0, SaveDeleteModel.objects.filter(text='new_text').count())

    def test_exception_on_pre_save_dont_save(self):
        self.mock.pre_save.side_effect = Exception

        with self.assertRaises(Exception):
            SaveDeleteModel.objects.all().update(text='new_text')
            instance = SaveDeleteModel.objects.first()
            instance.text = 'new_text'
            instance.save()

        self.assertEqual(0, SaveDeleteModel.objects.filter(text='new_text').count())

    def test_exception_on_post_save_dont_save(self):
        self.mock.post_save.side_effect = Exception

        with self.assertRaises(Exception):
            SaveDeleteModel.objects.all().update(text='new_text')
            instance = SaveDeleteModel.objects.first()
            instance.text = 'new_text'
            instance.save()

        self.assertEqual(0, SaveDeleteModel.objects.filter(text='new_text').count())

    def test_exception_on_pre_delete_dont_delete(self):
        self.mock.pre_delete.side_effect = Exception

        with self.assertRaises(Exception):
            instance = SaveDeleteModel.objects.first()
            instance.delete()
            SaveDeleteModel.objects.all().delete()

        self.assertEqual(SaveDeleteModel.objects.count(), 5)

    def test_exception_on_post_delete_dont_delete(self):
        self.mock.post_delete.side_effect = Exception

        with self.assertRaises(Exception):
            instance = SaveDeleteModel.objects.first()
            instance.delete()
            SaveDeleteModel.objects.all().delete()

        self.assertEqual(SaveDeleteModel.objects.count(), 5)
