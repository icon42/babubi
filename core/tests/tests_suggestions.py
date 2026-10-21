# -*- coding: utf-8 -*-
import datetime

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
        form = MedicationForm()
        self.assertEqual(form.fields["name"].suggestions, ["Vitamina D"])
        self.assertEqual(form.fields["next_dose_interval"].suggestions, ["24"])
        self.assertEqual(form.fields["dosage"].suggestions, ["1"])
        self.assertEqual(FeedingForm().fields["amount"].suggestions, [])

    def test_notes_offer_only_short_values(self):
        short, long = "Ha vomitat una mica", "Ha fet una presa molt llarga i ha dormit bé"
        for note in (short, short, long, long):
            models.Note.objects.create(child=self.child, note=note, time=timezone.now())
        self.assertEqual(NoteForm().fields["note"].suggestions, [short])
        # Each form counts only its own table's notes.
        self.assertEqual(SleepForm().fields["notes"].suggestions, [])
