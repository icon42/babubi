# -*- coding: utf-8 -*-
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.utils import timezone

from core.models import Child
from babubi.templatetags import babubi


class TemplateTagsTestCase(TestCase):
    def test_child_count(self):
        self.assertEqual(babubi.get_child_count(), 0)
        Child.objects.create(
            first_name="Test", last_name="Child", birth_date=timezone.localdate()
        )
        self.assertEqual(babubi.get_child_count(), 1)
        Child.objects.create(
            first_name="Test", last_name="Child 2", birth_date=timezone.localdate()
        )
        self.assertEqual(babubi.get_child_count(), 2)

    def test_user_is_read_only(self):
        user = get_user_model().objects.create_user(
            username="readonly", password="readonly", is_superuser=False, is_staff=False
        )
        self.assertFalse(babubi.user_is_read_only(user))

        group = Group.objects.get(name=settings.BABUBI["READ_ONLY_GROUP_NAME"])
        user.groups.add(group)
        self.assertTrue(babubi.user_is_read_only(user))

    def test_user_is_caregiver(self):
        user = get_user_model().objects.create_user(
            username="caregiver",
            password="caregiver",
            is_superuser=False,
            is_staff=False,
        )
        self.assertFalse(babubi.user_is_caregiver(user))

        group = Group.objects.get(name=settings.BABUBI["CAREGIVER_GROUP_NAME"])
        user.groups.add(group)
        self.assertTrue(babubi.user_is_caregiver(user))
        self.assertFalse(babubi.user_is_read_only(user))
