# -*- coding: utf-8 -*-
from django.apps import AppConfig
from django.conf import settings
from django.db.models.signals import post_migrate


def _permissions(codenames):
    from django.contrib.auth.models import Permission

    permissions = []
    for codename in codenames:
        try:
            permissions.append(
                Permission.objects.get(
                    content_type__app_label="core", codename=codename
                )
            )
        except Permission.DoesNotExist:
            continue
    return permissions


def _add_group_permissions(group_name, permissions):
    from django.contrib.auth.models import Group

    if not permissions:
        return
    try:
        group = Group.objects.get(name=group_name)
    except Group.DoesNotExist:
        return
    group.permissions.add(*permissions)


def add_read_only_group_permissions(sender, **kwargs):
    from django.apps import apps

    _add_group_permissions(
        settings.BABUBI["READ_ONLY_GROUP_NAME"],
        _permissions(f"view_{model}" for model in apps.all_models["core"]),
    )


class CoreConfig(AppConfig):
    name = "core"

    def ready(self):
        # The read only group receiver deliberately has no `sender` filter.
        # `post_migrate` is emitted once per application, in `INSTALLED_APPS`
        # order, and both of the things this receiver depends on are only in
        # place part way through that sequence:
        #
        # - `core`'s permissions are created by `django.contrib.auth`, whose
        #   receiver is connected after this one (`django.contrib.auth` is
        #   listed after `core` in `INSTALLED_APPS`), so on `core`'s own signal
        #   they do not exist yet.
        # - the read-only group itself is created on `babubi`'s signal.
        #
        # Restricted to `sender=self` the receiver therefore ran exactly once,
        # too early, and a freshly migrated database ended up with an empty
        # read-only group. Running on every application's signal converges to
        # the complete set instead, and `Permission.objects.add()` makes the
        # repeats idempotent.
        post_migrate.connect(
            add_read_only_group_permissions,
            dispatch_uid="core.add_read_only_group_permissions",
        )
