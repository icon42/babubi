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

    def give(self, name, hours=8, child=None, days_ago=0, **fields):
        return models.Medication.objects.create(
            child=child or self.child,
            name=name,
            time=timezone.now() - datetime.timedelta(days=days_ago),
            next_dose_interval=datetime.timedelta(hours=hours) if hours else None,
            **fields,
        )

    def feed(self, type, method, amount=None, times=1):
        for _ in range(times):
            models.Feeding.objects.create(
                child=self.child,
                start=timezone.now(),
                end=timezone.now(),
                type=type,
                method=method,
                amount=amount,
            )

    def buttons(self, form_class, **kwargs):
        return form_class(user=self.user, **kwargs).preset_buttons

    def test_treatments_most_recent_first(self):
        self.give("Vitamina D", hours=24, dosage=1, dosage_unit="drops", days_ago=3)
        self.give("Dalsy", hours=8, dosage=5, dosage_unit="ml")
        self.give("Dalsy", hours=8, dosage=5, dosage_unit="ml", days_ago=1)
        self.give("Apiretal", hours=None, dosage=2.5, dosage_unit="ml")
        buttons = self.buttons(MedicationForm)
        self.assertEqual(
            [button["label"] for button in buttons],
            ["Dalsy · 5 ml · every 8 h", "Vitamina D · 1 drops · every 24 h"],
        )
        self.assertEqual(
            json.loads(buttons[0]["values"]),
            {
                "name": "Dalsy",
                "dosage": 5,
                "dosage_unit": "ml",
                "next_dose_interval": 8,
            },
        )

    def test_feedings_given_the_same_way_twice(self):
        self.feed("formula", "bottle", 150, times=2)
        self.feed("breast milk", "left breast", times=2)
        self.feed("formula", "bottle", 120)
        buttons = self.buttons(FeedingForm)
        self.assertEqual(
            [button["label"] for button in buttons],
            ["Breast milk · Left breast", "Formula · Bottle · 150"],
        )
        # A missing amount clears the field.
        self.assertEqual(
            json.loads(buttons[0]["values"]),
            {"type": "breast milk", "method": "left breast", "amount": ""},
        )
        self.assertEqual(
            [button["label"] for button in self.buttons(BottleFeedingForm)],
            ["Formula · 150"],
        )

    def test_only_the_child_of_the_form(self):
        other = models.Child.objects.create(
            first_name="Bo", last_name="X", birth_date=timezone.localdate()
        )
        self.give("Dalsy", child=other)
        self.give("Vitamina D")
        labels = [
            button["label"]
            for button in self.buttons(MedicationForm, child=self.child.slug)
        ]
        self.assertEqual(labels, ["Vitamina D · every 8 h"])
        self.assertEqual(len(self.buttons(MedicationForm)), 2)

    def test_not_when_editing_nor_without_the_permission_to_view(self):
        entry = self.give("Dalsy")
        self.assertEqual(self.buttons(MedicationForm, instance=entry), [])
        adder = get_user_model().objects.create_user(username="adder", password="s")
        adder.user_permissions.add(Permission.objects.get(codename="add_medication"))
        self.assertEqual(MedicationForm(user=adder).preset_buttons, [])

    def test_the_form_page_offers_them(self):
        self.give("Dalsy", dosage=5, dosage_unit="ml")
        c = HttpClient()
        c.login(username="parent", password="secret")
        page = c.get("/medication/add/")
        self.assertContains(page, "Same as before")
        self.assertContains(page, "Dalsy · 5 ml · every 8 h")
        self.assertContains(page, "data-preset=")
        self.assertNotContains(c.get("/sleep/add/"), "Same as before")
