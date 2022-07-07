# pylint: disable=too-many-lines
from copy import deepcopy
from typing import List, Optional
from unittest.mock import MagicMock, call, patch

from django.db.models import QuerySet
from django.test.testcases import TestCase

from django_watcher.mixins import _INSTANCE, _QUERY_SET, MetaParams
from tests.models import CreateModel, DeleteModel, SaveDeleteModel, SaveModel, UpdateModel
from tests.watchers import (
    StubCreateWatcher,
    StubDeleteWatcher,
    StubSaveDeleteWatcher,
    StubSaveWatcher,
    StubUpdateWatcher,
)

from .helpers import CopyingMock


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

    def copy_instance(self, instance) -> CreateModel:
        return CreateModel(text=instance.text)

    def get_params(
        self, instance: CreateModel, source: str, operation_params: Optional[dict] = None
    ) -> List:

        operation_params = operation_params or {}

        meta_params_pre: MetaParams = {
            'source': source,
            'operation_params': operation_params,
        }
        meta_params_post: MetaParams = {
            'source': source,
            'operation_params': operation_params,
        }

        instance_copy = self.copy_instance(instance)

        if source == _INSTANCE:
            meta_params_pre['instance_ref'] = instance_copy
            meta_params_post['instance_ref'] = instance

        pre_params = [[instance_copy], meta_params_pre]
        post_params = [CreateModel.objects.filter(pk=instance.pk), meta_params_post]

        return [pre_params, post_params]

    def test_hooks_with_instance(self):
        instance = CreateModel(text='text')
        instance.save()

        pre_params, post_params = self.get_params(instance, _INSTANCE)

        StubCreateWatcher.assert_hook('pre_create', 'assert_called_once_with', *pre_params)
        StubCreateWatcher.assert_hook('post_create', 'assert_called_once_with', *post_params)
        self.assertEqual(6, CreateModel.objects.count())

    def test_hooks_with_objects(self):
        instance = CreateModel.objects.create(text='text')

        pre_params, post_params = self.get_params(
            instance, _QUERY_SET, operation_params={'text': 'text'}
        )

        StubCreateWatcher.assert_hook('pre_create', 'assert_called_once_with', *pre_params)
        StubCreateWatcher.assert_hook('post_create', 'assert_called_once_with', *post_params)
        self.assertEqual(6, CreateModel.objects.count())

    def test_hooks_order_with_instance(self):
        instance = CreateModel(text='text')
        self.mock.UNWATCHED_save.side_effect = instance.UNWATCHED_save  # noqa
        with patch.object(instance, 'UNWATCHED_save', self.mock.UNWATCHED_save):
            instance.save()

        pre_params, post_params = self.get_params(instance, _INSTANCE)

        self.mock.assert_has_calls(
            [
                call.pre_create(*pre_params),
                call.UNWATCHED_save(),
                call.post_create(*post_params),
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

        pre_params, post_params = self.get_params(
            instance, _QUERY_SET, operation_params={'text': 'text'}
        )

        self.mock.assert_has_calls(
            [
                call.pre_create(*pre_params),
                call.UNWATCHED_create(text='text'),
                call.post_create(*post_params),
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

    def get_params(
        self,
        instance: DeleteModel,
        source: str,
        queryset: QuerySet = None,
    ) -> List:

        instance_copy = self.copy_instance(instance)
        meta_params_pre: MetaParams = {
            'source': source,
            'operation_params': {},
        }
        meta_params_post: MetaParams = {
            'source': source,
            'operation_params': {},
        }
        if source == _INSTANCE:
            meta_params_pre['instance_ref'] = deepcopy(instance)
            meta_params_post['instance_ref'] = instance_copy

        if not queryset:
            queryset = DeleteModel.objects.filter(pk=instance.pk)

        pre_params = [DeleteModel.objects.filter(pk=instance.pk), meta_params_pre]
        post_params = [[deepcopy(instance)], meta_params_post]

        return [pre_params, post_params]

    def copy_instance(self, instance) -> DeleteModel:
        return DeleteModel(text=instance.text)

    def test_hooks_with_instance(self):
        instance = DeleteModel.objects.first()
        pre_params, post_params = self.get_params(instance, _INSTANCE)
        instance.delete()

        StubDeleteWatcher.assert_hook('pre_delete', 'assert_called_once_with', *pre_params)
        StubDeleteWatcher.assert_hook('post_delete', 'assert_called_once_with', *post_params)
        self.assertEqual(4, DeleteModel.objects.count())

    def test_hooks_with_objects(self):
        instance = DeleteModel.objects.first()
        DeleteModel.objects.filter(pk=instance.pk).delete()

        pre_params, post_params = self.get_params(instance, _QUERY_SET)

        StubDeleteWatcher.assert_hook('pre_delete', 'assert_called_once_with', *pre_params)
        StubDeleteWatcher.assert_hook('post_delete', 'assert_called_once_with', *post_params)
        self.assertEqual(4, DeleteModel.objects.count())

    def test_hooks_with_multiple_objects(self):
        instances = list(DeleteModel.objects.all())
        DeleteModel.objects.all().delete()

        meta_params: MetaParams = {'source': _QUERY_SET, 'operation_params': {}}

        StubDeleteWatcher.assert_hook(
            'pre_delete', 'assert_called_once_with', DeleteModel.objects.all(), meta_params
        )
        StubDeleteWatcher.assert_hook(
            'post_delete', 'assert_called_once_with', instances, meta_params
        )
        self.assertEqual(0, DeleteModel.objects.count())

    def test_hooks_order_with_instance(self):
        instance = DeleteModel.objects.first()
        pre_params, post_params = self.get_params(instance, _INSTANCE)
        self.mock.UNWATCHED_delete.side_effect = instance.UNWATCHED_delete
        with patch.object(instance, 'UNWATCHED_delete', self.mock.UNWATCHED_delete):
            instance.delete()

        self.mock.assert_has_calls(
            [
                call.pre_delete(*pre_params),
                call.UNWATCHED_delete(),
                call.post_delete(*post_params),
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

        pre_params, post_params = self.get_params(instance, _QUERY_SET)

        self.mock.assert_has_calls(
            [
                call.pre_delete(*pre_params),
                call.UNWATCHED_delete(),
                call.post_delete(*post_params),
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

    def copy_instance(self, instance: SaveModel) -> SaveModel:
        return SaveModel(text=instance.text)

    def get_params(
        self,
        instance: Optional[UpdateModel],
        source: str,
        operation_params: dict = None,
        queryset: QuerySet = None,
    ) -> List:
        if not operation_params:
            operation_params = {}
        meta_params: MetaParams = {
            'source': source,
            'operation_params': operation_params,
        }
        if instance and source == _INSTANCE:
            meta_params['instance_ref'] = instance

        if not queryset:
            queryset = (
                UpdateModel.objects.filter(pk=instance.pk)
                if instance
                else UpdateModel.objects.all()
            )

        return [queryset, meta_params]

    def test_hooks_with_instance(self):
        instance = UpdateModel.objects.first()
        instance.text = 'new_text'
        instance.save()

        params = self.get_params(instance, _INSTANCE)
        params.insert(0, 'assert_called_once_with')

        StubUpdateWatcher.assert_hook('pre_update', *params)
        StubUpdateWatcher.assert_hook('post_update', *params)
        self.assertEqual('new_text', instance.text)

    def test_hooks_with_objects(self):
        instance = UpdateModel.objects.first()
        UpdateModel.objects.filter(pk=instance.pk).update(text='fake')

        params = self.get_params(instance, _QUERY_SET, operation_params={'text': 'fake'})
        params.insert(0, 'assert_called_once_with')

        StubUpdateWatcher.assert_hook('pre_update', *params)
        StubUpdateWatcher.assert_hook('post_update', *params)
        instance.refresh_from_db()
        self.assertEqual('fake', instance.text)

    def test_hooks_with_multiple_objects(self):
        UpdateModel.objects.update(text='fake')

        params = self.get_params(None, _QUERY_SET, operation_params={'text': 'fake'})
        params.insert(0, 'assert_called_once_with')

        StubUpdateWatcher.assert_hook('pre_update', *params)
        StubUpdateWatcher.assert_hook('post_update', *params)
        self.assertEqual(5, UpdateModel.objects.filter(text='fake').count())

    def test_hooks_order_with_instance(self):
        instance = UpdateModel.objects.first()
        self.mock.UNWATCHED_save.side_effect = instance.UNWATCHED_save  # noqa
        with patch.object(instance, 'UNWATCHED_save', self.mock.UNWATCHED_save):
            instance.text = 'new_text'
            instance.save()

        params = self.get_params(instance, _INSTANCE)

        self.mock.assert_has_calls(
            [
                call.pre_update(*params),
                call.UNWATCHED_save(),
                call.post_update(*params),
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

        params = self.get_params(
            instance, _QUERY_SET, queryset=qs, operation_params={'text': 'new_text'}
        )

        self.mock.assert_has_calls(
            [
                call.pre_update(*params),
                call.UNWATCHED_update(text='new_text'),
                call.post_update(*params),
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

        params = self.get_params(
            None, _QUERY_SET, queryset=qs, operation_params={'text': 'new_text'}
        )

        self.mock.assert_has_calls(
            [
                call.pre_update(*params),
                call.UNWATCHED_update(text='new_text'),
                call.post_update(*params),
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

    def copy_instance(self, instance: SaveModel) -> SaveModel:
        return SaveModel(text=instance.text)

    def get_instance_params(self, instance: SaveModel, is_create=False) -> List:
        if not is_create:
            meta_params: MetaParams = {
                'source': _INSTANCE,
                'operation_params': {},
                'instance_ref': instance,
            }
            return [SaveModel.objects.filter(pk=instance.pk), meta_params]

        instance_copy = self.copy_instance(instance)
        meta_params_pre: MetaParams = {
            'source': _INSTANCE,
            'operation_params': {},
            'instance_ref': instance_copy,
        }

        meta_params_post: MetaParams = {
            'source': _INSTANCE,
            'operation_params': {},
            'instance_ref': instance,
        }
        pre_params = [[instance_copy], meta_params_pre]

        post_params = [SaveModel.objects.filter(pk=instance.pk), meta_params_post]

        return [pre_params, post_params]

    def get_objects_params(
        self,
        instance: Optional[SaveModel],
        operation_params: dict,
        is_create: bool = False,
        queryset: QuerySet = None,
    ) -> List:
        if not is_create:
            meta_params: MetaParams = {
                'source': _QUERY_SET,
                'operation_params': operation_params,
            }
            if not queryset:
                queryset = (
                    SaveModel.objects.filter(pk=instance.pk)
                    if instance
                    else SaveModel.objects.all()
                )
            return [queryset, meta_params]

        if not instance:
            raise TypeError("On create operations instance param can't be null")

        meta_params_pre: MetaParams = {
            'source': _QUERY_SET,
            'operation_params': operation_params,
        }

        meta_params_post: MetaParams = {
            'source': _QUERY_SET,
            'operation_params': operation_params,
        }

        pre_params = [[self.copy_instance(instance)], meta_params_pre]

        post_params = [SaveModel.objects.filter(pk=instance.pk), meta_params_post]

        return [pre_params, post_params]

    def test_create_hooks_with_instance(self):
        instance = SaveModel(text='text')
        instance.save()

        pre_params, post_params = self.get_instance_params(instance, is_create=True)
        pre_params.insert(0, 'assert_called_once_with')
        post_params.insert(0, 'assert_called_once_with')

        StubSaveWatcher.assert_hook('pre_save', *pre_params)
        StubSaveWatcher.assert_hook('pre_create', *pre_params)
        StubSaveWatcher.assert_hook('post_create', *post_params)
        StubSaveWatcher.assert_hook('post_save', *post_params)
        self.assertEqual(6, SaveModel.objects.count())

    def test_update_hooks_with_instance(self):
        instance = SaveModel.objects.first()
        instance.text = 'new_text'
        instance.save()

        params = self.get_instance_params(instance)
        params.insert(0, 'assert_called_once_with')

        StubSaveWatcher.assert_hook('pre_save', *params)
        StubSaveWatcher.assert_hook('pre_update', *params)
        StubSaveWatcher.assert_hook('post_update', *params)
        StubSaveWatcher.assert_hook('post_save', *params)
        self.assertEqual('new_text', instance.text)

    def test_create_hooks_with_objects(self):
        instance = SaveModel.objects.create(text='fake')

        pre_params, post_params = self.get_objects_params(
            instance, operation_params={'text': 'fake'}, is_create=True
        )
        pre_params.insert(0, 'assert_called_once_with')
        post_params.insert(0, 'assert_called_once_with')

        StubSaveWatcher.assert_hook('pre_save', *pre_params)
        StubSaveWatcher.assert_hook('pre_create', *pre_params)
        StubSaveWatcher.assert_hook('post_create', *post_params)
        StubSaveWatcher.assert_hook('post_save', *post_params)
        self.assertEqual(6, SaveModel.objects.count())

    def test_update_hooks_with_objects(self):
        instance = SaveModel.objects.first()
        SaveModel.objects.filter(pk=instance.pk).update(text='new_text')

        params = self.get_objects_params(instance, operation_params={'text': 'new_text'})
        params.insert(0, 'assert_called_once_with')

        StubSaveWatcher.assert_hook('pre_save', *params)
        StubSaveWatcher.assert_hook('pre_update', *params)
        StubSaveWatcher.assert_hook('post_update', *params)
        StubSaveWatcher.assert_hook('post_save', *params)
        instance.refresh_from_db()
        self.assertEqual('new_text', instance.text)

    def test_update_hooks_with_multiple_objects(self):
        SaveModel.objects.update(text='new_text')

        params = self.get_objects_params(None, operation_params={'text': 'new_text'})
        params.insert(0, 'assert_called_once_with')

        StubSaveWatcher.assert_hook('pre_save', *params)
        StubSaveWatcher.assert_hook('pre_update', *params)
        StubSaveWatcher.assert_hook('post_update', *params)
        StubSaveWatcher.assert_hook('post_save', *params)
        self.assertEqual(5, SaveModel.objects.filter(text='new_text').count())

    def test_create_hooks_order_with_instance(self):
        instance = SaveModel(text='text')
        self.mock.UNWATCHED_save.side_effect = instance.UNWATCHED_save  # noqa
        with patch.object(instance, 'UNWATCHED_save', self.mock.UNWATCHED_save):
            instance.save()

        pre_params, post_params = self.get_instance_params(instance, is_create=True)

        self.mock.assert_has_calls(
            [
                call.pre_save(*pre_params),
                call.pre_create(*pre_params),
                call.UNWATCHED_save(),
                call.post_create(*post_params),
                call.post_save(*post_params),
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

        params = self.get_instance_params(instance)

        self.mock.assert_has_calls(
            [
                call.pre_save(*params),
                call.pre_update(*params),
                call.UNWATCHED_save(),
                call.post_update(*params),
                call.post_save(*params),
            ]
        )
        self.assertEqual(len(self.mock.mock_calls), 5)
        self.assertEqual('new_text', instance.text)

    def test_create_hooks_order_with_objects(self):
        qs = SaveModel.objects.get_queryset()
        self.mock.UNWATCHED_create.side_effect = qs.UNWATCHED_create
        setattr(qs, 'UNWATCHED_create', self.mock.UNWATCHED_create)
        with patch.object(SaveModel.objects, 'get_queryset', lambda: qs):
            instance = SaveModel.objects.create(text='create_with_objects')

        pre_params, post_params = self.get_objects_params(
            instance, {'text': 'create_with_objects'}, is_create=True
        )

        self.mock.assert_has_calls(
            [
                call.pre_save(*pre_params),
                call.pre_create(*pre_params),
                call.UNWATCHED_create(text='create_with_objects'),
                call.post_create(*post_params),
                call.post_save(*post_params),
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

        params = self.get_objects_params(instance, operation_params={'text': 'new_text'})

        self.mock.assert_has_calls(
            [
                call.pre_save(*params),
                call.pre_update(*params),
                call.UNWATCHED_update(text='new_text'),
                call.post_update(*params),
                call.post_save(*params),
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

        params = self.get_objects_params(None, operation_params={'text': 'new_text'}, queryset=qs)

        self.mock.assert_has_calls(
            [
                call.pre_save(*params),
                call.pre_update(*params),
                call.UNWATCHED_update(text='new_text'),
                call.post_update(*params),
                call.post_save(*params),
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

    def copy_instance(self, instance: SaveDeleteModel) -> SaveDeleteModel:
        return SaveDeleteModel(text=instance.text)

    def get_instance_params(self, instance: SaveDeleteModel, is_create=False) -> List:
        if not is_create:
            meta_params: MetaParams = {
                'source': _INSTANCE,
                'operation_params': {},
                'instance_ref': instance,
            }
            return [SaveDeleteModel.objects.filter(pk=instance.pk), meta_params]

        instance_copy = self.copy_instance(instance)
        meta_params_pre: MetaParams = {
            'source': _INSTANCE,
            'operation_params': {},
            'instance_ref': instance_copy,
        }

        meta_params_post: MetaParams = {
            'source': _INSTANCE,
            'operation_params': {},
            'instance_ref': instance,
        }
        pre_params = [[instance_copy], meta_params_pre]

        post_params = [SaveDeleteModel.objects.filter(pk=instance.pk), meta_params_post]

        return [pre_params, post_params]

    def get_objects_params(
        self,
        instance: Optional[SaveDeleteModel],
        operation_params: dict,
        is_create: bool = False,
        queryset: QuerySet = None,
    ) -> List:
        if not is_create:
            meta_params: MetaParams = {
                'source': _QUERY_SET,
                'operation_params': operation_params,
            }
            if not queryset:
                queryset = (
                    SaveDeleteModel.objects.filter(pk=instance.pk)
                    if instance
                    else SaveDeleteModel.objects.all()
                )
            return [queryset, meta_params]

        if not instance:
            raise TypeError("On create operations instance param can't be null")

        meta_params_pre: MetaParams = {
            'source': _QUERY_SET,
            'operation_params': operation_params,
        }

        meta_params_post: MetaParams = {
            'source': _QUERY_SET,
            'operation_params': operation_params,
        }

        pre_params = [[self.copy_instance(instance)], meta_params_pre]

        post_params = [SaveDeleteModel.objects.filter(pk=instance.pk), meta_params_post]

        return [pre_params, post_params]

    def get_delete_params(
        self,
        instance: SaveDeleteModel,
        source: str,
        queryset: QuerySet = None,
    ) -> List:

        instance_copy = self.copy_instance(instance)
        meta_params_pre: MetaParams = {
            'source': source,
            'operation_params': {},
        }
        meta_params_post: MetaParams = {
            'source': source,
            'operation_params': {},
        }
        if source == _INSTANCE:
            meta_params_pre['instance_ref'] = deepcopy(instance)
            meta_params_post['instance_ref'] = instance_copy

        if not queryset:
            queryset = SaveDeleteModel.objects.filter(pk=instance.pk)

        pre_params = [SaveDeleteModel.objects.filter(pk=instance.pk), meta_params_pre]
        post_params = [[deepcopy(instance)], meta_params_post]

        return [pre_params, post_params]

    def test_create_hooks_with_instance(self):
        instance = SaveDeleteModel(text='text')
        instance.save()

        pre_params, post_params = self.get_instance_params(instance, is_create=True)
        pre_params.insert(0, 'assert_called_once_with')
        post_params.insert(0, 'assert_called_once_with')

        StubSaveDeleteWatcher.assert_hook('pre_save', *pre_params)
        StubSaveDeleteWatcher.assert_hook('pre_create', *pre_params)
        StubSaveDeleteWatcher.assert_hook('post_create', *post_params)
        StubSaveDeleteWatcher.assert_hook('post_save', *post_params)
        self.assertEqual(6, SaveDeleteModel.objects.count())

    def test_update_hooks_with_instance(self):
        instance = SaveDeleteModel.objects.first()
        instance.text = 'new_text'
        instance.save()

        params = self.get_instance_params(instance)
        params.insert(0, 'assert_called_once_with')

        StubSaveDeleteWatcher.assert_hook('pre_save', *params)
        StubSaveDeleteWatcher.assert_hook('pre_update', *params)
        StubSaveDeleteWatcher.assert_hook('post_update', *params)
        StubSaveDeleteWatcher.assert_hook('post_save', *params)
        instance.refresh_from_db()
        self.assertEqual('new_text', instance.text)

    def test_delete_hooks_with_instance(self):
        instance = SaveDeleteModel.objects.first()
        pre_params, post_params = self.get_delete_params(instance, _INSTANCE)
        instance.delete()

        StubSaveDeleteWatcher.assert_hook('pre_delete', 'assert_called_once_with', *pre_params)
        StubSaveDeleteWatcher.assert_hook('post_delete', 'assert_called_once_with', *post_params)
        self.assertEqual(4, SaveDeleteModel.objects.count())

    def test_create_hooks_with_objects(self):
        instance = SaveDeleteModel.objects.create(text='create_hooks_with_objects')

        pre_params, post_params = self.get_objects_params(
            instance, {'text': 'create_hooks_with_objects'}, is_create=True
        )
        pre_params.insert(0, 'assert_called_once_with')
        post_params.insert(0, 'assert_called_once_with')

        StubSaveDeleteWatcher.assert_hook('pre_save', *pre_params)
        StubSaveDeleteWatcher.assert_hook('pre_create', *pre_params)
        StubSaveDeleteWatcher.assert_hook('post_create', *post_params)
        StubSaveDeleteWatcher.assert_hook('post_save', *post_params)
        self.assertEqual(6, SaveDeleteModel.objects.count())

    def test_delete_hooks_with_objects(self):
        instance = SaveDeleteModel.objects.first()
        pre_params, post_params = self.get_delete_params(instance, _QUERY_SET)
        SaveDeleteModel.objects.filter(pk=instance.pk).delete()

        StubSaveDeleteWatcher.assert_hook('pre_delete', 'assert_called_once_with', *pre_params)
        StubSaveDeleteWatcher.assert_hook('post_delete', 'assert_called_once_with', *post_params)
        self.assertEqual(4, SaveDeleteModel.objects.count())

    def test_delete_hooks_with_multiple_objects(self):
        instances = list(SaveDeleteModel.objects.all())
        SaveDeleteModel.objects.all().delete()

        meta_params: MetaParams = {'source': _QUERY_SET, 'operation_params': {}}

        StubSaveDeleteWatcher.assert_hook(
            'pre_delete', 'assert_called_once_with', SaveDeleteModel.objects.all(), meta_params
        )
        StubSaveDeleteWatcher.assert_hook(
            'post_delete', 'assert_called_once_with', instances, meta_params
        )
        self.assertEqual(0, SaveDeleteModel.objects.count())

    def test_update_hooks_with_objects(self):
        instance = SaveDeleteModel.objects.first()
        SaveDeleteModel.objects.filter(pk=instance.pk).update(text='new_text')

        params = self.get_objects_params(instance, {'text': 'new_text'})
        params.insert(0, 'assert_called_once_with')

        StubSaveDeleteWatcher.assert_hook('pre_save', *params)
        StubSaveDeleteWatcher.assert_hook('pre_update', *params)
        StubSaveDeleteWatcher.assert_hook('post_update', *params)
        StubSaveDeleteWatcher.assert_hook('post_save', *params)
        instance.refresh_from_db()
        self.assertEqual('new_text', instance.text)

    def test_update_hooks_with_multiple_objects(self):
        SaveDeleteModel.objects.update(text='new_text')

        params = self.get_objects_params(None, {'text': 'new_text'})
        params.insert(0, 'assert_called_once_with')

        StubSaveDeleteWatcher.assert_hook('pre_save', *params)
        StubSaveDeleteWatcher.assert_hook('pre_update', *params)
        StubSaveDeleteWatcher.assert_hook('post_update', *params)
        StubSaveDeleteWatcher.assert_hook('post_save', *params)
        self.assertEqual(5, SaveDeleteModel.objects.filter(text='new_text').count())

    def test_create_hooks_order_with_instance(self):
        instance = SaveDeleteModel(text='text')
        self.mock.UNWATCHED_save.side_effect = instance.UNWATCHED_save  # noqa
        with patch.object(instance, 'UNWATCHED_save', self.mock.UNWATCHED_save):
            instance.save()

        pre_params, post_params = self.get_instance_params(instance, is_create=True)

        self.mock.assert_has_calls(
            [
                call.pre_save(*pre_params),
                call.pre_create(*pre_params),
                call.UNWATCHED_save(),
                call.post_create(*post_params),
                call.post_save(*post_params),
            ]
        )
        self.assertEqual(len(self.mock.mock_calls), 5)
        self.assertEqual(6, SaveDeleteModel.objects.count())

    def test_delete_hooks_order_with_instance(self):
        instance = SaveDeleteModel.objects.first()
        pre_params, post_params = self.get_delete_params(instance, _INSTANCE)
        self.mock.UNWATCHED_delete.side_effect = instance.UNWATCHED_delete
        with patch.object(instance, 'UNWATCHED_delete', self.mock.UNWATCHED_delete):
            instance.delete()

        self.mock.assert_has_calls(
            [call.pre_delete(*pre_params), call.UNWATCHED_delete(), call.post_delete(*post_params)]
        )
        self.assertEqual(len(self.mock.mock_calls), 3)
        self.assertEqual(4, SaveDeleteModel.objects.count())

    def test_update_hooks_order_with_instance(self):
        instance = SaveDeleteModel.objects.first()
        self.mock.UNWATCHED_save.side_effect = instance.UNWATCHED_save  # noqa
        with patch.object(instance, 'UNWATCHED_save', self.mock.UNWATCHED_save):
            instance.text = 'new_text'
            instance.save()

        params = self.get_instance_params(instance)

        self.mock.assert_has_calls(
            [
                call.pre_save(*params),
                call.pre_update(*params),
                call.UNWATCHED_save(),
                call.post_update(*params),
                call.post_save(*params),
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
            instance = SaveDeleteModel.objects.create(text='fake')

        pre_params, post_params = self.get_objects_params(
            instance, {'text': 'fake'}, is_create=True
        )

        self.mock.assert_has_calls(
            [
                call.pre_save(*pre_params),
                call.pre_create(*pre_params),
                call.UNWATCHED_create(text='fake'),
                call.post_create(*post_params),
                call.post_save(*post_params),
            ]
        )
        self.assertEqual(len(self.mock.mock_calls), 5)
        self.assertEqual(6, SaveDeleteModel.objects.count())

    def test_delete_hooks_order_with_objects(self):
        qs = SaveDeleteModel.objects.all()
        instance = qs.first()
        pre_params, post_params = self.get_delete_params(instance, _QUERY_SET)
        qs = qs.filter(pk=instance.pk)
        self.mock.UNWATCHED_delete.side_effect = qs.UNWATCHED_delete
        setattr(qs, 'UNWATCHED_delete', self.mock.UNWATCHED_delete)
        with patch.object(SaveDeleteModel.objects, 'filter', lambda **_: qs):
            SaveDeleteModel.objects.filter(pk='fake').delete()

        self.mock.assert_has_calls(
            [call.pre_delete(*pre_params), call.UNWATCHED_delete(), call.post_delete(*post_params)]
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

        params = self.get_objects_params(instance, {'text': 'new_text'}, queryset=qs)

        self.mock.assert_has_calls(
            [
                call.pre_save(*params),
                call.pre_update(*params),
                call.UNWATCHED_update(text='new_text'),
                call.post_update(*params),
                call.post_save(*params),
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
            SaveDeleteModel.objects.filter(pk='fake').update(text='new_text_new')

        params = self.get_objects_params(None, {'text': 'new_text_new'}, queryset=qs)

        self.mock.assert_has_calls(
            [
                call.pre_save(*params),
                call.pre_update(*params),
                call.UNWATCHED_update(text='new_text_new'),
                call.post_update(*params),
                call.post_save(*params),
            ]
        )
        self.assertEqual(len(self.mock.mock_calls), 5)
        self.assertEqual(5, SaveDeleteModel.objects.filter(text='new_text_new').count())

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
