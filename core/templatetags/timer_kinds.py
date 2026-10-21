# -*- coding: utf-8 -*-
from django import template
from django.urls import reverse

from core.timer_kinds import KINDS, kind_of

register = template.Library()

ADD_URLS = {
    "feeding": "core:feeding-add",
    "pumping": "core:pumping-add",
    "sleep": "core:sleep-add",
    "tummytime": "core:tummytime-add",
}


@register.filter
def timer_kind(timer):
    """What a timer times: "feeding", "pumping", "sleep", "tummytime" or ""."""
    return kind_of(timer)


@register.simple_tag(takes_context=True)
def timer_kinds(context, timer):
    """
    The kinds a timer can time, each with the form that finishes the timer as
    that activity; the timer's own kind, when set, comes first.
    :returns: a list of dicts with the kind, its label and the finishing url,
        for the kinds the user may add.
    """
    from dashboard.models import TimerProfile

    perms = context["perms"]
    labels = dict(TimerProfile.KINDS)
    current = kind_of(timer)
    options = []
    for kind in sorted(KINDS, key=lambda k: k != current):
        if not perms["core"]["add_" + kind]:
            continue
        url = "{}?timer={}".format(reverse(ADD_URLS[kind]), timer.id)
        if timer.child:
            url += "&child={}".format(timer.child.slug)
        options.append({"kind": kind, "label": labels[kind], "url": url})
    return options


@register.simple_tag
def timer_kind_choices():
    """The kinds a timer can be started as: a list of (kind, label)."""
    from dashboard.models import TimerProfile

    return TimerProfile.KINDS
