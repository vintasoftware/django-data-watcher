from django.test.testcases import TestCase

from tests.models import RelationDeleteModel, RelationDeleteModel2


class RelationTests(TestCase):
    def setUp(self):
        self.relation_delete_model = RelationDeleteModel.objects.create(text='text')

        RelationDeleteModel2.objects.bulk_create(
            [
                RelationDeleteModel2(text='text1', delete_model=self.relation_delete_model),
                RelationDeleteModel2(text='text2', delete_model=self.relation_delete_model),
                RelationDeleteModel2(text='text3', delete_model=self.relation_delete_model),
                RelationDeleteModel2(text='text4', delete_model=self.relation_delete_model),
                RelationDeleteModel2(text='text5', delete_model=self.relation_delete_model),
            ]
        )

    def test_dont_delete_with_sub_hook_exception(self):
        with self.assertRaises(Exception):
            self.relation_delete_model.delete()

        self.assertEqual(1, RelationDeleteModel.objects.count())
        self.assertEqual(5, RelationDeleteModel2.objects.count())
