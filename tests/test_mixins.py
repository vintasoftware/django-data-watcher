from copy import deepcopy
from unittest.mock import MagicMock, call, patch

from django.test.testcases import TestCase

from .models import CreateModel, DeleteModel, UpdateModel
from .watchers import StubCreateWatcher, StubDeleteWatcher, StubUpdateWatcher


class CopyingMock(MagicMock):
    def __call__(self, *args, **kwargs):
        args = deepcopy(args)
        kwargs = deepcopy(kwargs)
        return super().__call__(*args, **kwargs)


class CreateMixinTest(TestCase):
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


class DeleteMixinTest(TestCase):
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


class UpdateMixinTest(TestCase):
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
