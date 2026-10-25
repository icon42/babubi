# -*- coding: utf-8 -*-
from django import template
from django.utils.safestring import mark_safe

from core import growth
from core.models import Child
from dashboard import layout
from dashboard.layout_views import ACTIVE_CHILD
from dashboard.models import DashboardLayout
from dashboard.templatetags import cards

register = template.Library()


@register.simple_tag(takes_context=True)
def dashboard_layout(context, child):
    """
    The user's arrangement of the child dashboard, limited to what the user
    may see: three columns of cards, each card with its position on narrow
    screens, plus the hidden cards and the quick actions.
    """
    user = context["request"].user
    columns, hidden, actions, hidden_actions, order = layout.arrangement(
        DashboardLayout.of(user, child)
    )

    sex = growth.sex_of(child)

    def visible(card):
        # A WHO report card only for a child of its sex.
        report_sex = card.report.sex if card.report else None
        return layout.card_allowed(user, card) and report_sex in (None, sex)

    def cards_of(keys):
        return [layout.card(key) for key in keys if visible(layout.card(key))]

    def actions_of(keys):
        # A shortcut to the child of this dashboard would lead nowhere.
        found = [layout.action(key) for key in keys]
        return [
            a
            for a in found
            if a and a.child != child and layout.action_allowed(user, a)
        ]

    columns = [cards_of(column) for column in columns]
    hidden = cards_of(hidden)
    shown = {card.key for card in shown_cards(columns)}
    # The narrow-screen positions, among the cards this user sees.
    order = {key: i for i, key in enumerate(k for k in order if k in shown)}
    return {
        "columns": [
            [{"card": card, "order": order[card.key]} for card in column]
            for column in columns
        ],
        "hidden": hidden,
        "has_reports": any(card.report for card in hidden + shown_cards(columns)),
        # The reports the user may add as a card and has not on the page yet.
        "reports": [
            card.report
            for card in cards_of(layout.REPORT_PREFIX + r.key for r in layout.REPORTS)
            if card.key not in shown
        ],
        "actions": actions_of(actions),
        "hidden_actions": actions_of(hidden_actions),
    }


def shown_cards(columns):
    return [card for column in columns for card in column]


@register.simple_tag(takes_context=True)
def dashboard_card(context, card, child):
    """Renders one card of the registry, as its own inclusion tag would."""
    # The in-place refresh (dashboard.js) leaves graph cards as drawn: no
    # need to build them again.
    if card.report and context["request"].GET.get("refresh"):
        return ""
    function = getattr(cards, card.tag, None) or globals()[card.tag]
    if card.report:
        values = function(context, child, card.report)
    else:
        values = function(context, child)
    new_context = context.new(values)
    csrf_token = context.get("csrf_token")
    if csrf_token is not None:
        new_context["csrf_token"] = csrf_token
    card_template = context.template.engine.get_template(card.template)
    return mark_safe(card_template.render(new_context))


@register.inclusion_tag("cards/quick_actions.html", takes_context=True)
def card_quick_actions(context, child):
    """
    Buttons that add an entry for the child, in the order the user chose; in
    edit mode, every action the user may take, to arrange and hide.
    """
    arranged = dashboard_layout(context, child)
    edit = bool(context["request"].GET.get("edit"))
    return {
        "type": "activities",
        "child": child,
        "edit": edit,
        "actions": [
            {
                "action": action,
                "url": (action.url or action.child)
                and layout.action_url(action, child),
            }
            for action in arranged["actions"]
        ],
        "hidden_actions": arranged["hidden_actions"],
        "empty": not arranged["actions"] and not edit,
        "hide_empty": True,
    }


def card_report(context, child, report):
    """A report's graph, built by the report's own view."""
    view = report.view(context["request"], child)
    values = view.get_context_data(object=child)
    return {
        "type": report.activity,
        "report": report,
        "child": child,
        "html": values.get("html"),
        "js": values.get("js"),
    }


def card_percentiles(context, child):
    """
    The child's latest weight, height and head circumference as WHO
    percentiles, for the sex and measures chosen in the card's settings; in
    edit mode, the settings form.
    """
    user = context["request"].user
    options = (DashboardLayout.of(user, child).options or {}).get("percentiles", {})
    sex = growth.sex_of(child)
    chosen = options.get("measures", list(growth.MEASURES))
    allowed = [
        key
        for key, measure in growth.MEASURES.items()
        if user.has_perm("core.view_" + measure.model._meta.model_name)
    ]
    rows = []
    if sex:
        for key in chosen:
            if key in allowed:
                latest = growth.latest(child, key, sex)
                rows.append(latest or {"measure": growth.MEASURES[key]})
    return {
        "type": "measurements",
        "child": child,
        "edit": bool(context["request"].GET.get("edit")),
        "sex": sex,
        "rows": rows,
        "measures": [growth.MEASURES[key] for key in allowed],
        "chosen": chosen,
    }


@register.simple_tag(takes_context=True)
def active_child(context):
    """
    The child whose dashboard the user opened last, or the first child.
    :returns: a dict with the child (or None without children) and the others.
    """
    request = context.get("request")
    if request is None or not request.user.is_authenticated:
        return {"child": None, "others": []}
    children = list(Child.objects.order_by("last_name", "first_name", "id"))
    slug = request.session.get(ACTIVE_CHILD)
    child = next((c for c in children if c.slug == slug), None)
    if child is None and children:
        child = children[0]
    return {"child": child, "others": [c for c in children if c != child]}


@register.simple_tag
def dashboard_version(child):
    """The version of the child's data the page was rendered with."""
    from dashboard import versions

    return versions.version(child)


@register.simple_tag
def dashboard_time_words():
    """
    The words dashboard.js writes "… ago" times with, in the page's language:
    the singular and plural of an hour and a minute, and the "ago" phrase.
    """
    from django.utils.translation import gettext, ngettext

    def forms(singular, plural, name):
        return [ngettext(singular, plural, n) % {name: "%(n)s"} for n in (1, 2)]

    return {
        "hour": forms("%(hours)s hour", "%(hours)s hours", "hours"),
        "minute": forms("%(minutes)s minute", "%(minutes)s minutes", "minutes"),
        "ago": gettext("%(time_ago)s ago"),
    }
