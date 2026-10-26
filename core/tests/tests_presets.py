# -*- coding: utf-8 -*-
import datetime
import json

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import Client as HttpClient
from django.test import TestCase
from django.utils import timezone

from core import models
from core.forms import BottleFeedingForm, FeedingForm, MedicationForm


class PresetsTestCase(TestCase):
    def setUp(self):
        self.child = models.Child.objects.create(
            first_name="Ada", last_name="X", birth_date=timezone.localdate()
        )
        self.user = get_user_model().objects.create_user(
            username="parent", password="secret", is_superuser=True
        )
        self.clock = timezone.now() - datetime.timedelta(days=30)

    def tick(self):
        """The next moment, so every entry is later than the one before."""
        self.clock += datetime.timedelta(hours=1)
        return self.clock

    def give(self, name, hours=8, child=None, **fields):
        return models.Medication.objects.create(
            child=child or self.child,
            name=name,
            time=self.tick(),
            next_dose_interval=datetime.timedelta(hours=hours) if hours else None,
            **fields,
        )

    def feed(self, type, method, amount=None, times=1):
        for _ in range(times):
            start = self.tick()
            models.Feeding.objects.create(
                child=self.child,
                start=start,
                end=start,
                type=type,
                method=method,
                amount=amount,
            )

    def buttons(self, form_class, **kwargs):
        return form_class(user=self.user, **kwargs).preset_buttons

    def labels(self, form_class, **kwargs):
        return [button["label"] for button in self.buttons(form_class, **kwargs)]

    def values(self, form_class, **kwargs):
        return {
            button["label"]: json.loads(button["values"])
            for button in self.buttons(form_class, **kwargs)
        }

    def test_a_treatment_is_the_medication_and_its_interval(self):
        # The same name with two doses is one treatment, with the usual dose.
        self.give("Dalsy", dosage=4, dosage_unit="ml")
        self.give("Dalsy", dosage=5, dosage_unit="ml")
        self.give("Dalsy", dosage=5, dosage_unit="ml")
        # The same name with another interval is another treatment.
        self.give("Dalsy", hours=6, dosage=5, dosage_unit="ml")
        # Once is enough; without an interval it is no treatment.
        self.give("Vitamin D", hours=24, dosage=1, dosage_unit="drops")
        self.give("Apiretal", hours=None, dosage=2.5, dosage_unit="ml")
        self.assertEqual(
            self.labels(MedicationForm),
            [
                "Dalsy · 5 ml · every 8 h",
                "Vitamin D · 1 drops · every 24 h",
                "Dalsy · 5 ml · every 6 h",
            ],
        )
        self.assertEqual(
            self.values(MedicationForm)["Dalsy · 5 ml · every 8 h"],
            {
                "name": "Dalsy",
                "next_dose_interval": "8",
                "dosage": "5",
                "dosage_unit": "ml",
                "notes": "",
                "tags": [],
            },
        )

    def test_the_usual_dose_is_the_most_frequent_recent_one(self):
        self.give("Dalsy", dosage=4)
        self.give("Dalsy", dosage=4)
        self.give("Dalsy", dosage=5)
        self.assertEqual(self.labels(MedicationForm), ["Dalsy · 4 · every 8 h"])
        # A tie goes to the most recent.
        self.give("Dalsy", dosage=5)
        self.assertEqual(self.labels(MedicationForm), ["Dalsy · 5 · every 8 h"])

    def test_feedings_by_type_and_method_with_the_usual_amount(self):
        self.feed("formula", "bottle", 150, times=2)
        self.feed("formula", "bottle", 120)
        self.feed("breast milk", "left breast")
        self.assertEqual(
            self.labels(FeedingForm),
            ["Formula · Bottle · 150", "Breast milk · Left breast"],
        )
        # No amount at the breast: the field is cleared.
        self.assertEqual(
            self.values(FeedingForm)["Breast milk · Left breast"],
            {
                "type": "breast milk",
                "method": "left breast",
                "amount": "",
                "notes": "",
                "tags": [],
            },
        )
        self.assertEqual(self.labels(BottleFeedingForm), ["Formula · 150"])

    def test_at_most_four_the_most_frequent_first(self):
        self.feed("breast milk", "left breast", times=3)
        self.feed("breast milk", "right breast", times=3)
        self.feed("formula", "bottle", 150)
        self.feed("solid food", "parent fed")
        self.feed("fortified breast milk", "bottle", 100)
        labels = self.labels(FeedingForm)
        self.assertEqual(len(labels), 4)
        # Three times each, the most recent first; then the one-offs, the
        # most recent first, so the oldest one-off is left out.
        self.assertEqual(
            labels,
            [
                "Breast milk · Right breast",
                "Breast milk · Left breast",
                "Fortified breast milk · Bottle · 100",
                "Solid food · Parent fed",
            ],
        )

    def test_only_the_child_of_the_form(self):
        other = models.Child.objects.create(
            first_name="Bo", last_name="X", birth_date=timezone.localdate()
        )
        self.give("Dalsy", child=other)
        self.give("Vitamin D")
        self.assertEqual(
            self.labels(MedicationForm, child=self.child.slug),
            ["Vitamin D · every 8 h"],
        )
        self.assertEqual(len(self.labels(MedicationForm)), 2)

    def test_not_when_editing_nor_without_the_permission_to_view(self):
        entry = self.give("Dalsy")
        self.assertEqual(self.buttons(MedicationForm, instance=entry), [])
        adder = get_user_model().objects.create_user(username="adder", password="s")
        adder.user_permissions.add(Permission.objects.get(codename="add_medication"))
        self.assertEqual(MedicationForm(user=adder).preset_buttons, [])

    def test_notes_and_tags_carried_when_the_occurrences_usually_agree(self):
        # Two out of three times with the same note and tag: the usual wins.
        for notes, tag in (
            ("After meals", "evening"),
            ("Once", "fever"),
            ("After meals", "evening"),
        ):
            entry = self.give("Dalsy", dosage=5, dosage_unit="ml", notes=notes)
            entry.tags.add(tag)
        # A split, one against one, is no habit.
        self.give("Vitamin D", hours=24, notes="With breakfast")
        self.give("Vitamin D", hours=24, notes="Forgot yesterday")
        values = {
            label.split(" ·")[0]: value
            for label, value in self.values(MedicationForm).items()
        }
        self.assertEqual(values["Dalsy"]["notes"], "After meals")
        self.assertEqual([t["name"] for t in values["Dalsy"]["tags"]], ["evening"])
        self.assertEqual(values["Vitamin D"]["notes"], "")
        self.assertEqual(values["Vitamin D"]["tags"], [])

    def test_the_form_page_offers_them(self):
        self.give("Dalsy", dosage=5, dosage_unit="ml")
        c = HttpClient()
        c.login(username="parent", password="secret")
        page = c.get("/medication/add/")
        self.assertContains(page, "Same as before")
        self.assertContains(page, "Dalsy · 5 ml · every 8 h")
        self.assertContains(page, "data-preset=")
        self.assertNotContains(c.get("/sleep/add/"), "Same as before")
