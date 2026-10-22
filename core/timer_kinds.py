# -*- coding: utf-8 -*-
"""
The activity a timer times, kept in Babubi's dashboard.TimerProfile rather
than on upstream's Timer model: "feeding", "pumping", "sleep", "tummytime",
or "" when not set.
"""

from django.core.exceptions import ObjectDoesNotExist

KINDS = ("feeding", "pumping", "sleep", "tummytime")


def allowed(user):
    """
    The kinds the user may start or set: those whose activity they may add.
    A user who does not track feedings gets no feeding timers anywhere.
    """
    return tuple(kind for kind in KINDS if user.has_perm("core.add_" + kind))


def kind_of(timer):
    try:
        return timer.profile.kind
    except ObjectDoesNotExist:
        return ""


def kind_label(timer):
    """The name of a timer's kind, translated, or "" when not set."""
    from dashboard.models import TimerProfile

    return dict(TimerProfile.KINDS).get(kind_of(timer), "")


def set_kind(timer, kind):
    """Sets a timer's kind; an unknown one clears it. Returns the kind set."""
    from dashboard.models import TimerProfile

    kind = kind if kind in KINDS else ""
    TimerProfile.objects.update_or_create(timer=timer, defaults={"kind": kind})
    return kind
