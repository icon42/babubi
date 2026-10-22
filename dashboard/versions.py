# -*- coding: utf-8 -*-
"""
A version for each child's data, so an open dashboard can ask cheaply
whether anything changed (dashboard.js) before fetching its cards again.

Saving or deleting anything that belongs to a child bumps that child's
counter; a timer with no child, or a child's own record, bumps a shared one,
since every dashboard shows it. The counters live in the cache, so reading a
version costs one lookup by key and no query on the activity tables.
"""

from django.core.cache import cache

TIMEOUT = None  # Kept until the cache is cleared; a lost counter restarts at 1.


def _key(name):
    return "dashboard-version:{}".format(name)


def _bump(name):
    key = _key(name)
    try:
        cache.incr(key)
    except ValueError:
        cache.set(key, 1, TIMEOUT)


def bump(child_id):
    """Marks a child's data as changed; None, every child's."""
    _bump(child_id if child_id is not None else "all")


def version(child):
    """The version of a child's dashboard data, a short string."""
    values = cache.get_many([_key(child.pk), _key("all")])
    return "{}.{}".format(values.get(_key(child.pk), 0), values.get(_key("all"), 0))


def on_change(sender, instance, **kwargs):
    """post_save and post_delete receiver for the models dashboards show."""
    from core.models import Child

    if isinstance(instance, Child):
        bump(None)
    elif hasattr(instance, "timer_id"):  # a TimerProfile: its timer's child
        bump(instance.timer.child_id if instance.timer_id else None)
    else:
        bump(getattr(instance, "child_id", None))
