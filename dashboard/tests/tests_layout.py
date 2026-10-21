# -*- coding: utf-8 -*-
from django.test import TestCase
from django.utils import timezone

from core.models import Child


class ChildSexTestCase(TestCase):
    def test_child_form_saves_the_sex(self):
        from core.forms import ChildForm
        from core.growth import sex_of

        child = Child.objects.create(
            first_name="Ada", last_name="X", birth_date=timezone.localdate()
        )
        self.assertEqual(sex_of(child), "")
        data = {
            "first_name": "Ada",
            "last_name": "X",
            "birth_date": timezone.localdate().isoformat(),
            "sex": "girl",
        }
        form = ChildForm(data, instance=child)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        child.refresh_from_db()
        self.assertEqual(sex_of(child), "girl")
        self.assertEqual(ChildForm(instance=child).fields["sex"].initial, "girl")
