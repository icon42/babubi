# -*- coding: utf-8 -*-
import importlib

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from babubi import roles

migration = importlib.import_module(
    "babubi.migrations.0039_settings_read_all_write_all"
)


def fresh(user):
    """The user again, without the permission caches of this instance."""
    return get_user_model().objects.get(pk=user.pk)


class RoleBackendTestCase(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="carer")

    def flags(self, **values):
        for name, value in values.items():
            setattr(self.user.settings, name, value)
        self.user.settings.save()
        self.user = fresh(self.user)

    def test_nothing_by_default(self):
        self.assertFalse(self.user.has_perm("core.view_feeding"))
        self.assertFalse(self.user.has_perm("core.view_child"))

    def test_read_all_reads_every_kind_and_the_children(self):
        self.flags(read_all=True)
        for t in roles.ENTRY_TYPES:
            self.assertTrue(self.user.has_perm(f"core.view_{t}"), t)
            self.assertFalse(self.user.has_perm(f"core.add_{t}"), t)
        self.assertTrue(self.user.has_perm("core.view_child"))
        self.assertTrue(self.user.has_perm("core.view_tag"))
        self.assertTrue(self.user.has_perm("core.view_timer"))
        self.assertFalse(self.user.has_perm("core.add_timer"))
        self.assertFalse(self.user.has_perm("core.change_child"))

    def test_write_all_writes_every_kind(self):
        self.flags(read_all=True, write_all=True)
        for t in roles.ENTRY_TYPES:
            for action in ("view", "add", "change", "delete"):
                self.assertTrue(self.user.has_perm(f"core.{action}_{t}"), t)
        self.assertTrue(self.user.has_perm("core.delete_timer"))
        self.assertTrue(self.user.has_perm("core.add_tag"))
        self.assertTrue(self.user.has_perm("core.change_child"))
        # Not an administrator: no users, no settings.
        self.assertFalse(self.user.has_perm("auth.add_user"))
        self.assertFalse(self.user.is_superuser)

    def test_derived_from_stored_kinds(self):
        roles.grant(self.user, {"medication"}, {"medication"})
        user = fresh(self.user)
        self.assertTrue(user.has_perm("core.delete_medication"))
        self.assertTrue(user.has_perm("core.change_tag"))
        # Medication is not timed: no timers.
        self.assertFalse(user.has_perm("core.view_timer"))
        roles.grant(user, {"medication", "sleep"}, {"medication"})
        user = fresh(user)
        self.assertTrue(user.has_perm("core.view_timer"))
        self.assertFalse(user.has_perm("core.add_timer"))

    def test_group_permissions_count_too(self):
        group = Group.objects.create(name="family")
        group.permissions.add(Permission.objects.get(codename="add_feeding"))
        self.user.groups.add(group)
        user = fresh(self.user)
        self.assertEqual(roles.stored(user), (set(), {"feeding"}))
        self.assertTrue(user.has_perm("core.add_timer"))

    def test_inactive_user_gets_nothing(self):
        self.flags(read_all=True, write_all=True)
        self.user.is_active = False
        self.user.save()
        self.assertFalse(fresh(self.user).has_perm("core.view_feeding"))

    def test_grant_replaces_the_matrix_only(self):
        extra = Permission.objects.get(codename="view_child")
        self.user.user_permissions.add(extra)
        roles.grant(self.user, {"sleep", "feeding"}, {"sleep"})
        roles.grant(self.user, {"feeding"}, set())
        codenames = set(self.user.user_permissions.values_list("codename", flat=True))
        self.assertEqual(codenames, {"view_child", "view_feeding"})

    def test_effective(self):
        roles.grant(self.user, {"sleep"}, {"sleep"})
        self.flags(read_all=True)
        reads, writes, read_all, write_all = roles.effective(self.user)
        self.assertEqual(reads, set(roles.ENTRY_TYPES))
        self.assertEqual(writes, {"sleep"})
        self.assertTrue(read_all)
        self.assertFalse(write_all)


class GroupsToMatrixMigrationTestCase(TestCase):
    """The data migration from the read-only and caregiver groups."""

    def test_members_keep_an_equivalent_access(self):
        from django.apps import apps
        from django.conf import settings

        read_only = Group.objects.get(name=settings.BABUBI["READ_ONLY_GROUP_NAME"])
        caregiver = Group.objects.create(name=migration.CAREGIVER_GROUP)
        caregiver.permissions.add(
            *Permission.objects.filter(codename__in=["view_feeding", "add_feeding"])
        )
        reader = get_user_model().objects.create_user(username="reader")
        reader.groups.add(read_only)
        carer = get_user_model().objects.create_user(username="carer")
        carer.groups.add(caregiver)
        migration.groups_to_matrix(apps, None)
        self.assertTrue(fresh(reader).settings.read_all)
        self.assertTrue(fresh(carer).has_perm("core.add_feeding"))
        self.assertFalse(Group.objects.filter(name=migration.CAREGIVER_GROUP).exists())


class RolesAPITestCase(APITestCase):
    fixtures = ["tests.json"]

    def as_user(self, **flags):
        user = get_user_model().objects.create_user(username="api-carer")
        for name, value in flags.items():
            setattr(user.settings, name, value)
        user.settings.save()
        token, _ = Token.objects.get_or_create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")
        return user

    def test_read_all_reads_but_does_not_write(self):
        self.as_user(read_all=True)
        for name in ("feeding", "bmi", "child", "timer", "tag"):
            with self.subTest(name=name):
                endpoint = reverse(f"api:{name}-list")
                self.assertEqual(self.client.get(endpoint).status_code, 200)
                self.assertEqual(
                    self.client.post(endpoint, {}, format="json").status_code, 403
                )

    def test_write_all_writes_and_deletes_but_no_users(self):
        self.as_user(read_all=True, write_all=True)
        endpoint = reverse("api:note-list")
        response = self.client.post(
            endpoint, {"child": 1, "note": "A note"}, format="json"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            self.client.delete(f"{endpoint}{response.data['id']}/").status_code, 204
        )
        self.assertEqual(self.client.get("/users/").status_code, 302)

    def test_user_list_names_the_access(self):
        admin = get_user_model().objects.create_user(
            username="boss", password="s", is_staff=True, is_superuser=True
        )
        self.as_user(read_all=True)
        self.client.credentials()
        self.client.force_login(admin)
        page = self.client.get("/users/")
        self.assertContains(page, "Read only")
        self.assertContains(page, "Administrator")
