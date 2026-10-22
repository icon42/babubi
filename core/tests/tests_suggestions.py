# -*- coding: utf-8 -*-
import datetime

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase
from django.utils import timezone

from core import models
from core.forms import FeedingForm, MedicationForm, NoteForm, SleepForm
from core.suggestions import frequent


class SuggestionsTestCase(TestCase):
    def setUp(self):
        self.child = models.Child.objects.create(
            first_name="Ada", last_name="X", birth_date=timezone.localdate()
        )
        self.user = get_user_model().objects.create_user(
            username="parent", password="secret", is_superuser=True
        )

    def form(self, form_class, **kwargs):
        return form_class(user=self.user, **kwargs)

    def give(self, name, times, hours=8):
        for _ in range(times):
            models.Medication.objects.create(
                child=self.child,
                name=name,
                dosage=1,
                time=timezone.now(),
                next_dose_interval=datetime.timedelta(hours=hours),
            )

    def test_most_frequent_first_and_used_at_least_twice(self):
        self.give("Vitamina D", 4)
        self.give("Ibuprofèn", 2)
        self.give("Once", 1)
        self.assertEqual(
            frequent(models.Medication, "name"), ["Vitamina D", "Ibuprofèn"]
        )

    def test_form_fields_offer_them(self):
        self.give("Vitamina D", 3, hours=24)
        form = self.form(MedicationForm)
        self.assertEqual(form.fields["name"].suggestions, ["Vitamina D"])
        self.assertEqual(form.fields["next_dose_interval"].suggestions, ["24"])
        self.assertEqual(form.fields["dosage"].suggestions, ["1"])
        self.assertEqual(self.form(FeedingForm).fields["amount"].suggestions, [])

    def test_only_with_the_permission_to_view(self):
        self.give("Vitamina D", 3)
        adder = get_user_model().objects.create_user(username="adder", password="s")
        adder.user_permissions.add(Permission.objects.get(codename="add_medication"))
        form = MedicationForm(user=adder)
        self.assertFalse(hasattr(form.fields["name"], "suggestions"))
        self.assertFalse(hasattr(MedicationForm().fields["name"], "suggestions"))

    def test_notes_offer_only_short_values(self):
        short, long = (
            "Ha vomitat una mica",
            "Ha fet una presa molt llarga i ha dormit bé",
        )
        for note in (short, short, long, long):
            models.Note.objects.create(child=self.child, note=note, time=timezone.now())
        self.assertEqual(self.form(NoteForm).fields["note"].suggestions, [short])
        # Each form counts only its own table's notes.
        self.assertEqual(self.form(SleepForm).fields["notes"].suggestions, [])

    def test_whole_doses_read_without_decimals(self):
        self.give("Vitamina D", 1, hours=24)
        form = self.form(MedicationForm, instance=models.Medication.objects.get())
        self.assertEqual(form["dosage"].value(), 1)
        self.assertEqual(form["next_dose_interval"].value(), 24)
