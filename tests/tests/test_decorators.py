from unittest.mock import MagicMock, call, patch

from django.test import TestCase

from django_watcher.mixins import _QUERY_SET, MetaParams
from tests.models import (
    CasualStringWatcherModel,
    CasualStringWatcherModel2,
    CustomManagerModel,
    CustomManagerModel2,
    StringWatcherModel,
    StringWatcherModel2,
)
from tests.watchers import (
    StubCreateWatcher,
    StubDeleteWatcher,
    StubSaveDeleteWatcher,
    StubSaveDeleteWatcher2,
)

from .helpers import CopyingMock


class ImportWatcherTests(TestCase):
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


class CustomAndSubManagerTests(TestCase):
    def setUp(self) -> None:
        CustomManagerModel.objects.bulk_create(
            [
                CustomManagerModel(text='text1'),
                CustomManagerModel(text='text2'),
                CustomManagerModel(text='text3'),
                CustomManagerModel(text='text4'),
                CustomManagerModel(text='text5'),
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

    def test_create_hooks_order(self):
        qs = CustomManagerModel.objects.get_queryset()
        self.mock.UNWATCHED_create.side_effect = qs.UNWATCHED_create
        setattr(qs, 'UNWATCHED_create', self.mock.UNWATCHED_create)
        with patch.object(CustomManagerModel.objects, 'get_queryset', lambda: qs):
            instance = CustomManagerModel.objects.create('fake_param', text='fake')

        self.mock.assert_has_calls(
            [
                call.pre_save(
                    [CustomManagerModel(text='fake')],
                    {'source': _QUERY_SET, 'operation_params': {'text': 'fake'}},
                ),
                call.pre_create(
                    [CustomManagerModel(text='fake')],
                    {'source': _QUERY_SET, 'operation_params': {'text': 'fake'}},
                ),
                call.UNWATCHED_create(text='fake'),
                call.post_create(
                    CustomManagerModel.objects.filter(pk=instance.pk),
                    {'source': _QUERY_SET, 'operation_params': {'text': 'fake'}},
                ),
                call.post_save(
                    CustomManagerModel.objects.filter(pk=instance.pk),
                    {'source': _QUERY_SET, 'operation_params': {'text': 'fake'}},
                ),
            ]
        )
        self.assertEqual(len(self.mock.mock_calls), 5)
        self.assertEqual(6, CustomManagerModel.objects.count())

    @patch('tests.managers.watched')
    def test_update_hooks_order(self, mocked_watched):
        instance = CustomManagerModel.objects.first()
        qs = CustomManagerModel.objects.filter(pk=instance.pk)
        self.mock.UNWATCHED_update.side_effect = qs.UNWATCHED_update
        setattr(qs, 'UNWATCHED_update', self.mock.UNWATCHED_update)
        with patch.object(CustomManagerModel.objects, 'filter', lambda **_: qs):
            CustomManagerModel.objects.filter(pk='fake').update('fake_param', text='new_text')

        qs = CustomManagerModel.other_objects.filter(pk=instance.pk)
        self.mock.UNWATCHED_update_2.side_effect = qs.UNWATCHED_update
        setattr(qs, 'UNWATCHED_update', self.mock.UNWATCHED_update_2)
        with patch.object(CustomManagerModel.other_objects, 'filter', lambda **_: qs):
            CustomManagerModel.other_objects.filter(pk='fake').update(
                'fake_param_2', text='new_new_text'
            )

        self.mock.assert_has_calls(
            [
                call.pre_save(
                    CustomManagerModel.objects.filter(pk=instance.pk),
                    {'source': _QUERY_SET, 'operation_params': {'text': 'new_text'}},
                ),
                call.pre_update(
                    CustomManagerModel.objects.filter(pk=instance.pk),
                    {'source': _QUERY_SET, 'operation_params': {'text': 'new_text'}},
                ),
                call.UNWATCHED_update('fake_param', text='new_text'),
                call.post_update(
                    CustomManagerModel.objects.filter(pk=instance.pk),
                    {'source': _QUERY_SET, 'operation_params': {'text': 'new_text'}},
                ),
                call.post_save(
                    CustomManagerModel.objects.filter(pk=instance.pk),
                    {'source': _QUERY_SET, 'operation_params': {'text': 'new_text'}},
                ),
                call.pre_save(
                    CustomManagerModel.other_objects.filter(pk=instance.pk),
                    {'source': _QUERY_SET, 'operation_params': {'text': 'new_new_text'}},
                ),
                call.pre_update(
                    CustomManagerModel.other_objects.filter(pk=instance.pk),
                    {'source': _QUERY_SET, 'operation_params': {'text': 'new_new_text'}},
                ),
                call.UNWATCHED_update_2('fake_param_2', text='new_new_text'),
                call.post_update(
                    CustomManagerModel.other_objects.filter(pk=instance.pk),
                    {'source': _QUERY_SET, 'operation_params': {'text': 'new_new_text'}},
                ),
                call.post_save(
                    CustomManagerModel.other_objects.filter(pk=instance.pk),
                    {'source': _QUERY_SET, 'operation_params': {'text': 'new_new_text'}},
                ),
            ]
        )
        self.assertEqual(len(self.mock.mock_calls), 10)
        mocked_watched.assert_has_calls([call('fake_param'), call('fake_param_2')])

        instance.refresh_from_db()
        self.assertEqual('new_new_text', instance.text)

    @patch('tests.managers.watched')
    def test_delete_hooks_order(self, mocked_watched):

        meta_params: MetaParams = {'source': _QUERY_SET, 'operation_params': {}}

        instance = CustomManagerModel.objects.first()
        qs = CustomManagerModel.objects.filter(pk=instance.pk)
        self.mock.UNWATCHED_delete.side_effect = qs.UNWATCHED_delete
        setattr(qs, 'UNWATCHED_delete', self.mock.UNWATCHED_delete)
        with patch.object(CustomManagerModel.objects, 'filter', lambda **_: qs):
            CustomManagerModel.objects.filter(pk='fake').delete('fake_param')

        instance_2 = CustomManagerModel.other_objects.first()
        qs = CustomManagerModel.other_objects.filter(pk=instance_2.pk)
        self.mock.UNWATCHED_delete_2.side_effect = qs.UNWATCHED_delete
        setattr(qs, 'UNWATCHED_delete', self.mock.UNWATCHED_delete_2)
        with patch.object(CustomManagerModel.other_objects, 'filter', lambda **_: qs):
            CustomManagerModel.other_objects.filter(pk='fake').delete('fake_param_2')

        self.mock.assert_has_calls(
            [
                call.pre_delete(CustomManagerModel.objects.filter(pk=instance.pk), meta_params),
                call.UNWATCHED_delete('fake_param'),
                call.post_delete([instance], meta_params),
                call.pre_delete(
                    CustomManagerModel.other_objects.filter(pk=instance_2.pk), meta_params
                ),
                call.UNWATCHED_delete_2('fake_param_2'),
                call.post_delete([instance_2], meta_params),
            ]
        )
        mocked_watched.assert_has_calls([call('fake_param'), call('fake_param_2')])
        self.assertEqual(len(self.mock.mock_calls), 6)
        self.assertEqual(3, CustomManagerModel.objects.count())


class SameCustomManagerOnDifferentClassesTests(TestCase):
    def setUp(self) -> None:
        CustomManagerModel.objects.bulk_create(
            [
                CustomManagerModel(text='text1'),
                CustomManagerModel(text='text2'),
                CustomManagerModel(text='text3'),
                CustomManagerModel(text='text4'),
                CustomManagerModel(text='text5'),
            ]
        )
        CustomManagerModel2.objects.bulk_create(
            [
                CustomManagerModel(text='text6'),
                CustomManagerModel(text='text7'),
                CustomManagerModel(text='text8'),
                CustomManagerModel(text='text9'),
                CustomManagerModel(text='text0'),
            ]
        )

        self.mock: MagicMock = CopyingMock()
        self.mock2: MagicMock = CopyingMock()
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
        StubSaveDeleteWatcher2.set_hooks(
            ('pre_create', self.mock2.pre_create),
            ('post_create', self.mock2.post_create),
            ('pre_update', self.mock2.pre_update),
            ('post_update', self.mock2.post_update),
            ('pre_save', self.mock2.pre_save),
            ('post_save', self.mock2.post_save),
            ('pre_delete', self.mock2.pre_delete),
            ('post_delete', self.mock2.post_delete),
        )

    def test_create_hooks_order(self):
        qs = CustomManagerModel.objects.get_queryset()
        self.mock.UNWATCHED_create.side_effect = qs.UNWATCHED_create
        setattr(qs, 'UNWATCHED_create', self.mock.UNWATCHED_create)
        with patch.object(CustomManagerModel.objects, 'get_queryset', lambda: qs):
            instance = CustomManagerModel.objects.create('fake_param', text='fake')

        qs = CustomManagerModel2.objects.get_queryset()
        self.mock2.UNWATCHED_create.side_effect = qs.UNWATCHED_create
        setattr(qs, 'UNWATCHED_create', self.mock2.UNWATCHED_create)
        with patch.object(CustomManagerModel2.objects, 'get_queryset', lambda: qs):
            instance2 = CustomManagerModel2.objects.create('fake_param_2', text='fake_2')

        self.mock.assert_has_calls(
            [
                call.pre_save(
                    [CustomManagerModel(text='fake')],
                    {'source': _QUERY_SET, 'operation_params': {'text': 'fake'}},
                ),
                call.pre_create(
                    [CustomManagerModel(text='fake')],
                    {'source': _QUERY_SET, 'operation_params': {'text': 'fake'}},
                ),
                call.UNWATCHED_create(text='fake'),
                call.post_create(
                    CustomManagerModel.objects.filter(pk=instance.pk),
                    {'source': _QUERY_SET, 'operation_params': {'text': 'fake'}},
                ),
                call.post_save(
                    CustomManagerModel.objects.filter(pk=instance.pk),
                    {'source': _QUERY_SET, 'operation_params': {'text': 'fake'}},
                ),
            ]
        )
        self.assertEqual(len(self.mock.mock_calls), 5)
        self.assertEqual(6, CustomManagerModel.objects.count())

        self.mock2.assert_has_calls(
            [
                call.pre_save(
                    [CustomManagerModel2(text='fake_2')],
                    {'source': _QUERY_SET, 'operation_params': {'text': 'fake_2'}},
                ),
                call.pre_create(
                    [CustomManagerModel2(text='fake_2')],
                    {'source': _QUERY_SET, 'operation_params': {'text': 'fake_2'}},
                ),
                call.UNWATCHED_create(text='fake_2'),
                call.post_create(
                    CustomManagerModel2.objects.filter(pk=instance2.pk),
                    {'source': _QUERY_SET, 'operation_params': {'text': 'fake_2'}},
                ),
                call.post_save(
                    CustomManagerModel2.objects.filter(pk=instance2.pk),
                    {'source': _QUERY_SET, 'operation_params': {'text': 'fake_2'}},
                ),
            ]
        )
        self.assertEqual(len(self.mock2.mock_calls), 5)
        self.assertEqual(6, CustomManagerModel2.objects.count())

    @patch('tests.managers.watched')
    def test_update_hooks_order(self, mocked_watched):
        instance = CustomManagerModel.objects.first()
        qs = CustomManagerModel.objects.filter(pk=instance.pk)
        self.mock.UNWATCHED_update.side_effect = qs.UNWATCHED_update
        setattr(qs, 'UNWATCHED_update', self.mock.UNWATCHED_update)
        with patch.object(CustomManagerModel.objects, 'filter', lambda **_: qs):
            CustomManagerModel.objects.filter(pk='fake').update('fake_param', text='new_text')

        instance2 = CustomManagerModel2.objects.first()
        qs = CustomManagerModel2.objects.filter(pk=instance2.pk)
        self.mock2.UNWATCHED_update.side_effect = qs.UNWATCHED_update
        setattr(qs, 'UNWATCHED_update', self.mock2.UNWATCHED_update)
        with patch.object(CustomManagerModel2.objects, 'filter', lambda **_: qs):
            CustomManagerModel2.objects.filter(pk='fake').update('fake_param_2', text='other_text')

        self.mock.assert_has_calls(
            [
                call.pre_save(
                    CustomManagerModel.objects.filter(pk=instance.pk),
                    {'source': _QUERY_SET, 'operation_params': {'text': 'new_text'}},
                ),
                call.pre_update(
                    CustomManagerModel.objects.filter(pk=instance.pk),
                    {'source': _QUERY_SET, 'operation_params': {'text': 'new_text'}},
                ),
                call.UNWATCHED_update('fake_param', text='new_text'),
                call.post_update(
                    CustomManagerModel.objects.filter(pk=instance.pk),
                    {'source': _QUERY_SET, 'operation_params': {'text': 'new_text'}},
                ),
                call.post_save(
                    CustomManagerModel.objects.filter(pk=instance.pk),
                    {'source': _QUERY_SET, 'operation_params': {'text': 'new_text'}},
                ),
            ]
        )
        self.mock2.assert_has_calls(
            [
                call.pre_save(
                    CustomManagerModel2.objects.filter(pk=instance.pk),
                    {'source': _QUERY_SET, 'operation_params': {'text': 'other_text'}},
                ),
                call.pre_update(
                    CustomManagerModel2.objects.filter(pk=instance.pk),
                    {'source': _QUERY_SET, 'operation_params': {'text': 'other_text'}},
                ),
                call.UNWATCHED_update('fake_param_2', text='other_text'),
                call.post_update(
                    CustomManagerModel2.objects.filter(pk=instance.pk),
                    {'source': _QUERY_SET, 'operation_params': {'text': 'other_text'}},
                ),
                call.post_save(
                    CustomManagerModel2.objects.filter(pk=instance.pk),
                    {'source': _QUERY_SET, 'operation_params': {'text': 'other_text'}},
                ),
            ]
        )
        self.assertEqual(len(self.mock.mock_calls), 5)
        mocked_watched.assert_has_calls([call('fake_param'), call('fake_param_2')])

        instance.refresh_from_db()
        instance2.refresh_from_db()
        self.assertEqual('new_text', instance.text)
        self.assertEqual('other_text', instance2.text)

    @patch('tests.managers.watched')
    def test_delete_hooks_order(self, mocked_watched):
        instance = CustomManagerModel.objects.first()
        qs = CustomManagerModel.objects.filter(pk=instance.pk)
        self.mock.UNWATCHED_delete.side_effect = qs.UNWATCHED_delete
        setattr(qs, 'UNWATCHED_delete', self.mock.UNWATCHED_delete)
        with patch.object(CustomManagerModel.objects, 'filter', lambda **_: qs):
            CustomManagerModel.objects.filter(pk='fake').delete('fake_param')

        instance_2 = CustomManagerModel2.objects.first()
        qs = CustomManagerModel2.objects.filter(pk=instance_2.pk)
        self.mock2.UNWATCHED_delete.side_effect = qs.UNWATCHED_delete
        setattr(qs, 'UNWATCHED_delete', self.mock2.UNWATCHED_delete)
        with patch.object(CustomManagerModel2.objects, 'filter', lambda **_: qs):
            CustomManagerModel2.objects.filter(pk='fake').delete('fake_param_2')

        meta_params: MetaParams = {'source': _QUERY_SET, 'operation_params': {}}

        self.mock.assert_has_calls(
            [
                call.pre_delete(CustomManagerModel.objects.filter(pk=instance.pk), meta_params),
                call.UNWATCHED_delete('fake_param'),
                call.post_delete([instance], meta_params),
            ]
        )

        self.mock2.assert_has_calls(
            [
                call.pre_delete(CustomManagerModel2.objects.filter(pk=instance.pk), meta_params),
                call.UNWATCHED_delete('fake_param_2'),
                call.post_delete([instance_2], meta_params),
            ]
        )
        mocked_watched.assert_has_calls([call('fake_param'), call('fake_param_2')])
        self.assertEqual(len(self.mock.mock_calls), 3)
        self.assertEqual(4, CustomManagerModel.objects.count())
        self.assertEqual(len(self.mock2.mock_calls), 3)
        self.assertEqual(4, CustomManagerModel2.objects.count())
