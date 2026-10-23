# -*- coding: utf-8 -*-
"""
What a user may read and write, per kind of entry.

Babubi keeps Django's model permissions (view, add, change and delete per
model), which every view, template, report and API endpoint already checks,
and sets them per user from a matrix in the user form: one row per kind of
entry, a Read column (view) and a Write column (add, change and delete). The
"All" of each column is kept in the user's settings (`read_all`,
`write_all`), not as permissions, so a kind added later is covered too; the
permissions backend (babubi/permissions.py) grants it from there, together
with what follows from the matrix: children and tags to read for anyone who
reads something, tags and children to change for anyone who writes
something, and timers for the timed kinds.
"""

from django.apps import apps
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import Permission

# The kinds of entry, in the order of the menus: activities, then measurements.
ENTRY_TYPES = (
    "diaperchange",
    "feeding",
    "pumping",
    "sleep",
    "tummytime",
    "medication",
    "note",
    "temperature",
    "weight",
    "height",
    "headcircumference",
    "bmi",
)

# The kinds a timer can time: timers follow their permissions.
TIMED_TYPES = ("feeding", "pumping", "sleep", "tummytime")

# The icon classes that do not match the model name (icons/icons.scss).
ICONS = {"headcircumference": "head-circumference"}

READ_ACTIONS = ("view",)
WRITE_ACTIONS = ("add", "change", "delete")


def label(entry_type):
    """The translated name of a kind of entry."""
    return apps.get_model("core", entry_type)._meta.verbose_name


def icon(entry_type):
    """The icon class of a kind of entry."""
    return "icon-" + ICONS.get(entry_type, entry_type)


def perms(types, actions):
    """The "core.<action>_<type>" permissions of some kinds and actions."""
    return {f"core.{action}_{t}" for t in types for action in actions}


def derived(reads, writes):
    """
    The permissions that follow from reading or writing some kinds, which the
    matrix does not show.
    :param reads: the kinds the user reads.
    :param writes: the kinds the user writes.
    """
    found = set()
    if reads:
        found |= {"core.view_child", "core.view_tag"}
    if writes:
        found |= {"core.change_child", "core.add_tag", "core.change_tag"}
    if set(reads) & set(TIMED_TYPES):
        found |= perms(["timer"], READ_ACTIONS)
    if set(writes) & set(TIMED_TYPES):
        found |= perms(["timer"], WRITE_ACTIONS)
    return found


def stored(user):
    """
    The kinds a user reads and writes by their own and their groups'
    permissions, as two sets; a superuser gets every kind.
    """
    granted = ModelBackend().get_all_permissions(user)
    reads = {t for t in ENTRY_TYPES if f"core.view_{t}" in granted}
    writes = {t for t in ENTRY_TYPES if f"core.add_{t}" in granted}
    return reads, writes


def effective(user):
    """
    The kinds a user reads and writes once the "All" flags count, as two
    sets, plus the flags themselves: (reads, writes, read_all, write_all).
    """
    reads, writes = stored(user)
    read_all = write_all = False
    if not user.is_superuser:
        flags = getattr(user, "settings", None)
        read_all = bool(flags and flags.read_all)
        write_all = bool(flags and flags.write_all)
    if read_all or user.is_superuser:
        reads = set(ENTRY_TYPES)
    if write_all or user.is_superuser:
        writes = set(ENTRY_TYPES)
    return reads, writes, read_all, write_all


def grant(user, reads, writes):
    """
    Set the user's own permissions on the kinds of entry to exactly these:
    view for `reads`, add, change and delete for `writes`; other permissions
    the user may hold are left alone.
    """
    wanted = perms(reads, READ_ACTIONS) | perms(writes, WRITE_ACTIONS)
    matrix = perms(ENTRY_TYPES, READ_ACTIONS + WRITE_ACTIONS)
    rows = Permission.objects.filter(
        content_type__app_label="core",
        codename__in=[p.split(".", 1)[1] for p in matrix],
    )
    by_name = {f"core.{row.codename}": row for row in rows}
    user.user_permissions.remove(*[by_name[p] for p in matrix - wanted if p in by_name])
    user.user_permissions.add(*[by_name[p] for p in wanted if p in by_name])
