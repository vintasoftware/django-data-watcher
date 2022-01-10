from copy import deepcopy
from unittest.mock import MagicMock, patch

from django.test.testcases import TestCase

from .models import CreateModel
from .watchers import StubCreateWatcher


class CopyingMock(MagicMock):
    def __call__(self, *args, **kwargs):
        args = deepcopy(args)
        kwargs = deepcopy(kwargs)
        return super().__call__(*args, **kwargs)


class TestCreateMixin(TestCase):
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

    def test_hooks_with_objects(self):
        created = CreateModel.objects.create(text='fake')

        StubCreateWatcher.assert_hook(
            'pre_create', 'assert_called_once_with', [CreateModel(text='fake')]
        )
        StubCreateWatcher.assert_hook('post_create', 'assert_called_once')
        self.assertEqual(created, self.mock.post_create.call_args[0][0].get())

    def test_hooks_with_instance(self):
        created = CreateModel(text='fake')
        created.save()

        StubCreateWatcher.assert_hook(
            'pre_create', 'assert_called_once_with', [CreateModel(text='fake')]
        )
        StubCreateWatcher.assert_hook('post_create', 'assert_called_once')
        self.assertEqual(created, self.mock.post_create.call_args[0][0].get())

    def test_hooks_order_with_instance(self):
        instance = CreateModel(text='fake')
        self.mock.UNWATCHED_save.side_effect = instance.UNWATCHED_save  # noqa
        with patch.object(instance, 'UNWATCHED_save', self.mock.UNWATCHED_save):
            instance.save()

        calls = self.mock.mock_calls

        self.assertEqual(len(calls), 3)
        self.assertIn('call.pre_create', str(calls[0]))
        self.assertIn('call.UNWATCHED_save', str(calls[1]))
        self.assertIn('call.post_create', str(calls[2]))

    def test_hooks_order_with_objects(self):
        qs = CreateModel.objects.get_queryset()
        self.mock.UNWATCHED_create.side_effect = qs.UNWATCHED_create
        setattr(qs, 'UNWATCHED_create', self.mock.UNWATCHED_create)
        with patch.object(CreateModel.objects, 'get_queryset', lambda: qs):

            CreateModel.objects.create(text='fake')

        calls = self.mock.mock_calls

        self.assertEqual(len(calls), 3)
        self.assertIn('call.pre_create', str(calls[0]))
        self.assertIn('call.UNWATCHED_create', str(calls[1]))
        self.assertIn('call.post_create', str(calls[2]))

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
