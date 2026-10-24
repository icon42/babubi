# -*- coding: utf-8 -*-
from django.test import TestCase
from django.utils import timezone

from core import filters, models


class MedicationFilterTestCase(TestCase):
    def setUp(self):
        child = models.Child.objects.create(
            first_name="Ada", last_name="X", birth_date=timezone.localdate()
        )
        for name in ("Oftalmolosa Cusi", "Oftalmolosa Cusi", "Dalsy"):
            models.Medication.objects.create(
                child=child, name=name, time=timezone.now()
            )

    def found(self, name):
        return filters.MedicationFilter(
            {"name": name}, queryset=models.Medication.objects.all()
        ).qs.count()

    def test_a_part_of_the_name_in_any_case_finds_it(self):
        self.assertEqual(self.found("cusi"), 2)
        self.assertEqual(self.found("OFTALMOLOSA"), 2)
        self.assertEqual(self.found("Dalsy"), 1)
        self.assertEqual(self.found("Apiretal"), 0)
        self.assertEqual(self.found(""), 3)

    def test_the_field_keeps_its_name_and_label(self):
        field = filters.MedicationFilter(queryset=models.Medication.objects.none())
        self.assertEqual(field.form.fields["name"].label, "Medication Name")
