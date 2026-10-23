# -*- coding: utf-8 -*-
from django import template
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from core.timer_kinds import allowed, kind_of

register = template.Library()

ADD_URLS = {
    "feeding": "core:feeding-add",
    "pumping": "core:pumping-add",
    "sleep": "core:sleep-add",
    "tummytime": "core:tummytime-add",
}

# The finish button of the timer page: whole sentences, so each language
# can put the activity's article and gender right.
FINISH_LABELS = {
    "feeding": _("Finish and create a feeding"),
    "pumping": _("Finish and create a pumping"),
    "sleep": _("Finish and create a sleep"),
    "tummytime": _("Finish and create a tummy time"),
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
    :returns: a list of dicts with the kind, its label, the sentence of the
        button that finishes it and the finishing url, for the kinds the user
        may add.
    """
    from dashboard.models import TimerProfile

    labels = dict(TimerProfile.KINDS)
    current = kind_of(timer)
    options = []
    for kind in sorted(allowed(context["request"].user), key=lambda k: k != current):
        url = "{}?timer={}".format(reverse(ADD_URLS[kind]), timer.id)
        if timer.child:
            url += "&child={}".format(timer.child.slug)
        options.append(
            {
                "kind": kind,
                "label": labels[kind],
                "finish": FINISH_LABELS[kind],
                "url": url,
            }
        )
    return options


@register.simple_tag(takes_context=True)
def timer_kind_choices(context):
    """
    The kinds the user may start a timer as: a list of (kind, label).
    """
    from dashboard.models import TimerProfile

    kinds = allowed(context["request"].user)
    return [(kind, label) for kind, label in TimerProfile.KINDS if kind in kinds]
