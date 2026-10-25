# -*- coding: utf-8 -*-
"""
What a child dashboard can show and how each user arranges it: the one list
of cards and of quick actions, the default arrangement, and the operations
of the dashboard's edit mode. A user's arrangement of a child's dashboard is
a DashboardLayout.
"""

from dataclasses import dataclass

from django.urls import resolve, reverse
from django.utils.translation import gettext_lazy as _

COLUMNS = 3


@dataclass(frozen=True)
class Card:
    key: str
    label: str
    # The card's inclusion tag in dashboard/templatetags/cards.py, and the
    # template it renders.
    tag: str
    template: str
    # The core model the user must be able to view, or None.
    model: str = None
    # For a report card, the report it shows.
    report: "Report" = None
    # Whether a layout that has not placed it yet keeps it among the hidden.
    default_hidden: bool = False
    # Whether the card has settings of its own in edit mode (a form in its
    # body), which a collapsed card on a narrow screen must unfold to reach.
    editable: bool = False


@dataclass(frozen=True)
class Report:
    key: str
    label: str
    # The report's view, under the reports namespace.
    url: str
    # The activity whose colour the card takes.
    activity: str
    # The graph's height in the card, in pixels.
    height: int = 280
    # The colour of the series to paint in the activity's colour, when it is
    # not the only or the first one.
    series_color: str = None
    # For a WHO percentile report, the sex it is for.
    sex: str = None

    def view(self, request=None, child=None):
        """
        The report's own view, to build its graph or read its permissions; set
        up for a child when there is one.
        """
        match = resolve(reverse(self.url, args=[child.slug if child else "-"]))
        view = match.func.view_class(**match.func.view_initkwargs)
        if child:
            view.setup(request, **match.kwargs)
            view.object = child
        return view


@dataclass(frozen=True)
class Action:
    key: str
    label: str
    # The core model it is about, which also names its colour and icon.
    model: str
    # The model's list view, opened for the dashboard's child; None for the
    # quick timer, which is a POST. Every fixed action has an "add:" twin
    # that opens the add form, and the quick timer a "list:" one (action()).
    url: str = None
    default: bool = False
    # For a child's shortcut, the child whose dashboard it opens.
    child: object = None
    # For a timer of a kind, the activity it times (core.timer_kinds).
    timer_kind: str = None
    # Whether it adds an entry (the add form) rather than opening the list.
    add: bool = False

    @property
    def activity(self):
        if self.timer_kind:
            return self.timer_kind
        return {"headcircumference": "head-circumference"}.get(self.model, self.model)

    @property
    def starts_timer(self):
        """Whether it starts a timer (the quick timer, of a kind or not)."""
        return self.url is None and self.child is None

    @property
    def rank(self):
        """The order of an activity's variants: timer, add form, list."""
        return 0 if self.starts_timer else 1 if self.add else 2


def _card(key, label, model):
    return Card(key, label, "card_" + key, "cards/{}.html".format(key), model)


# In their default order: the quick actions first, then the order the
# dashboard had before it could be arranged.
CARDS = [
    Card(
        "quick_actions",
        _("Quick Actions"),
        "card_quick_actions",
        "cards/quick_actions.html",
        editable=True,
    ),
    _card("timer_list", _("Timers"), "timer"),
    _card("feeding_last", _("Last Feeding"), "feeding"),
    _card("notes_recent", _("Recent Notes"), "note"),
    _card("diaperchange_last", _("Last Diaper Change"), "diaperchange"),
    _card("pumping_last", _("Last Pumping"), "pumping"),
    _card("pumping_recent", _("Recent Pumpings"), "pumping"),
    _card("sleep_last", _("Last Sleep"), "sleep"),
    _card("medication_last", _("Last Medication"), "medication"),
    _card("feeding_last_method", _("Last Feeding Method"), "feeding"),
    _card("feeding_recent", _("Recent Feedings"), "feeding"),
    _card("statistics", _("Statistics"), None),
    _card("sleep_recent", _("Recent Sleep"), "sleep"),
    _card("sleep_naps_day", _("Today's Naps"), "sleep"),
    _card("tummytime_day", _("Today's Tummy Time"), "tummytime"),
    _card("diaperchange_types", _("Diaper Changes"), "diaperchange"),
    _card("breastfeeding", _("Breastfeeding"), "feeding"),
    # Needs the child's sex, which only its settings give: hidden until then.
    Card(
        "percentiles",
        _("Percentiles"),
        "card_percentiles",
        "cards/percentiles.html",
        default_hidden=True,
        editable=True,
    ),
]
CARDS_BY_KEY = {card.key: card for card in CARDS}

# The reports of reports/templates/reports/report_list.html a report card can
# show; the key goes after "report:" in the card's key.
REPORTS = [
    Report(key, label, "reports:report-{}-child".format(key), activity, *extra)
    for key, label, activity, *extra in [
        ("bmi-change", _("Body Mass Index (BMI)"), "bmi"),
        ("diaperchange-amounts", _("Diaper Change Amounts"), "diaperchange"),
        ("diaperchange-types", _("Diaper Change Types"), "diaperchange"),
        ("diaperchange-intervals", _("Diaper Intervals"), "diaperchange"),
        ("diaperchange-lifetimes", _("Diaper Lifetimes"), "diaperchange"),
        ("feeding-amounts", _("Feeding Amounts"), "feeding"),
        ("feeding-duration", _("Feeding Durations (Average)"), "feeding"),
        ("feeding-intervals", _("Feeding Intervals"), "feeding"),
        ("feeding-pattern", _("Feeding Pattern"), "feeding"),
        (
            "head-circumference-change",
            _("Head Circumference"),
            "head-circumference",
        ),
        ("height-change", _("Height"), "height"),
        ("medication-frequency", _("Medication Frequency"), "medication"),
        ("medication-intervals", _("Medication Intervals"), "medication"),
        ("pumping-amounts", _("Pumping Amounts"), "pumping"),
        # A day per column and the hours down: it needs the height, and its
        # first series is the awake time between sleeps.
        ("sleep-pattern", _("Sleep Pattern"), "sleep", 460, "rgb(35, 110, 150)"),
        ("sleep-totals", _("Sleep Totals"), "sleep"),
        ("temperature-change", _("Temperature"), "temperature"),
        ("tummy-time-duration", _("Tummy Time Durations (Sum)"), "tummytime"),
        ("weight-change", _("Weight"), "weight"),
    ]
] + [
    # The WHO percentile curves, the child's measurements over them.
    Report(
        "{}-change-{}".format(measure, sex),
        label,
        "reports:report-{}-change-child-{}".format(measure, sex),
        measure,
        sex=sex,
    )
    for measure, sex, label in [
        (
            "head-circumference",
            "boy",
            _("WHO Head Circumference Percentiles for Boys in cm"),
        ),
        (
            "head-circumference",
            "girl",
            _("WHO Head Circumference Percentiles for Girls in cm"),
        ),
        ("height", "boy", _("WHO Height Percentiles for Boys in cm")),
        ("height", "girl", _("WHO Height Percentiles for Girls in cm")),
        ("weight", "boy", _("WHO Weight Percentiles for Boys in kg")),
        ("weight", "girl", _("WHO Weight Percentiles for Girls in kg")),
    ]
]
REPORTS_BY_KEY = {report.key: report for report in REPORTS}
REPORT_PREFIX = "report:"


def card(key):
    """The card a key names, a fixed one or a report card, or None."""
    if key in CARDS_BY_KEY:
        return CARDS_BY_KEY[key]
    if key.startswith(REPORT_PREFIX):
        report = REPORTS_BY_KEY.get(key[len(REPORT_PREFIX) :])
        if report:
            return Card(
                key, report.label, "card_report", "cards/report.html", None, report
            )
    return None


ACTIONS = [
    Action(
        "diaperchange",
        _("Diaper Change"),
        "diaperchange",
        "core:diaperchange-list",
        True,
    ),
    Action("feeding", _("Feeding"), "feeding", "core:feeding-list", True),
    Action("sleep", _("Sleep"), "sleep", "core:sleep-list", True),
    Action("timer", _("Timer"), "timer", default=True),
    Action("tummytime", _("Tummy Time"), "tummytime", "core:tummytime-list"),
    Action("pumping", _("Pumping"), "pumping", "core:pumping-list"),
    Action("medication", _("Medication"), "medication", "core:medication-list"),
    Action("temperature", _("Temperature"), "temperature", "core:temperature-list"),
    Action("note", _("Note"), "note", "core:note-list"),
    Action("weight", _("Weight"), "weight", "core:weight-list"),
    Action("height", _("Height"), "height", "core:height-list"),
    Action(
        "headcircumference",
        _("Head Circumference"),
        "headcircumference",
        "core:head-circumference-list",
    ),
    Action("bmi", _("BMI"), "bmi", "core:bmi-list"),
]
ACTIONS_BY_KEY = {action.key: action for action in ACTIONS}
CHILD_PREFIX = "child:"
TIMER_PREFIX = "timer:"
ADD_PREFIX = "add:"
LIST_PREFIX = "list:"


def action(key):
    """
    The quick action a key names: a fixed one (its list, or the quick timer),
    the add form of one ("add:<key>"), the timer list ("list:timer"), a timer
    of a kind ("timer:<kind>") or a shortcut to a child's dashboard
    ("child:<slug>"); None if there is no such action.
    """
    if key in ACTIONS_BY_KEY:
        return ACTIONS_BY_KEY[key]
    # The add and list views are named after the activity (core/urls.py).
    if key.startswith(ADD_PREFIX):
        fixed = ACTIONS_BY_KEY.get(key[len(ADD_PREFIX) :])
        if fixed:
            url = "core:{}-add".format(fixed.activity)
            return Action(key, fixed.label, fixed.model, url, add=True)
    if key.startswith(LIST_PREFIX):
        fixed = ACTIONS_BY_KEY.get(key[len(LIST_PREFIX) :])
        if fixed and not fixed.url:
            url = "core:{}-list".format(fixed.activity)
            return Action(key, _("Timers"), fixed.model, url)
    if key.startswith(TIMER_PREFIX):
        from core.timer_kinds import KINDS

        kind = key[len(TIMER_PREFIX) :]
        if kind in KINDS:
            # Named after the activity; the card marks it as a timer.
            return Action(key, ACTIONS_BY_KEY[kind].label, "timer", timer_kind=kind)
    if key.startswith(CHILD_PREFIX):
        from core.models import Child

        child = Child.objects.filter(slug=key[len(CHILD_PREFIX) :]).first()
        if child:
            return Action(key, child.first_name, "child", child=child)
    return None


def _default_column(index):
    """Deals the default order out to the columns, left to right."""
    return index % COLUMNS


DEFAULT_COLUMN = {card.key: _default_column(i) for i, card in enumerate(CARDS)}


def default_columns():
    columns = [[] for _ in range(COLUMNS)]
    for fixed in CARDS:
        if not fixed.default_hidden:
            columns[DEFAULT_COLUMN[fixed.key]].append(fixed.key)
    return columns


def default_hidden():
    return [fixed.key for fixed in CARDS if fixed.default_hidden]


def default_actions():
    return [action.key for action in ACTIONS if action.default]


def card_allowed(user, card):
    if card.report:
        return user.has_perms(card.report.view().permission_required)
    return card.model is None or user.has_perm("core.view_" + card.model)


def action_allowed(user, action):
    if action.child:
        return user.has_perm("core.view_child")
    # A timer of a kind also needs the activity it times.
    if action.timer_kind and not user.has_perm("core.add_" + action.timer_kind):
        return False
    if action.url and not action.add:
        return user.has_perm("core.view_" + action.model)
    return user.has_perm("core.add_" + action.model)


def action_url(action, child):
    if action.child:
        return reverse("core:child", args=[action.child.slug])
    if action.add:
        # The add form, for the child (it takes the slug).
        return "{}?child={}".format(reverse(action.url), child.slug)
    # The list, filtered to the child (its filter form takes the pk).
    return "{}?child={}".format(reverse(action.url), child.pk)


def arrangement(layout):
    """
    A layout's cards and actions, cleaned up: keys no longer known are
    dropped, each key appears once, and keys the layout has never seen
    (cards and actions added since it was saved) take their default place.
    :param layout: a DashboardLayout, saved or not.
    :returns: (columns, hidden, actions, hidden_actions, order), lists of
        keys; `order` is the cards' order on narrow screens, every shown card
        once, interleaved from the columns where the layout has not set it.
    """
    seen = set()

    def known(keys, is_known):
        kept = []
        for key in keys:
            if is_known(key) and key not in seen:
                seen.add(key)
                kept.append(key)
        return kept

    columns = [known(column, card) for column in layout.columns[:COLUMNS]]
    columns += [[] for _ in range(COLUMNS - len(columns))]
    hidden = known(layout.hidden, card)
    for fixed in CARDS:
        if fixed.key not in seen:
            if fixed.default_hidden:
                hidden.append(fixed.key)
            else:
                columns[DEFAULT_COLUMN[fixed.key]].append(fixed.key)
    order = narrow_order(layout.order, columns)

    seen.clear()
    actions = known(layout.actions, action)
    hidden_actions = known(layout.hidden_actions, action)
    for fixed in ACTIONS:
        if fixed.key not in seen:
            (actions if fixed.default else hidden_actions).append(fixed.key)
    # A timer of each kind, the add form of each list and every child as a
    # shortcut: one the layout has not placed yet waits among the hidden
    # actions.
    from core.models import Child
    from core.timer_kinds import KINDS

    for kind in KINDS:
        if TIMER_PREFIX + kind not in seen:
            hidden_actions.append(TIMER_PREFIX + kind)
    for fixed in ACTIONS:
        if ADD_PREFIX + fixed.key not in seen:
            hidden_actions.append(ADD_PREFIX + fixed.key)
        if not fixed.url and LIST_PREFIX + fixed.key not in seen:
            hidden_actions.append(LIST_PREFIX + fixed.key)

    for slug in Child.objects.order_by("last_name", "first_name").values_list(
        "slug", flat=True
    ):
        if CHILD_PREFIX + slug not in seen:
            hidden_actions.append(CHILD_PREFIX + slug)
    return columns, hidden, actions, hidden_actions, order


def interleaved(columns):
    """
    The cards in the order narrow screens show them unless arranged there:
    the first of each column, then the second of each, and so on.
    :returns: a dict of key → position.
    """
    order = {}
    depth = max((len(column) for column in columns), default=0)
    for row in range(depth):
        for column in columns:
            if row < len(column):
                order[column[row]] = len(order)
    return order


def narrow_order(order, columns):
    """
    The order of the shown cards on narrow screens: `order` as saved, less
    the keys no longer shown, then the shown cards it does not place yet
    (added since it was arranged) as the columns interleave them. An empty
    `order`, never arranged, gives the interleaving itself.
    """
    ideal = interleaved(columns)
    kept = []
    for key in order:
        if key in ideal and key not in kept:
            kept.append(key)
    kept += [key for key in sorted(ideal, key=ideal.get) if key not in kept]
    return kept


def _move_within(keys, key, step):
    i = keys.index(key)
    j = i + step
    if 0 <= j < len(keys):
        keys[i], keys[j] = keys[j], keys[i]


def _rearranged(old, new):
    """
    `old` with the keys `new` lists moved into that order among themselves;
    the others (cards the user editing cannot see) keep their slots.
    :param new: a subset of `old`, each key once.
    """
    moved = iter(new)
    return [next(moved) if key in new else key for key in old]


def configure(layout, key, data):
    """
    Saves a card's settings from its edit-mode form, without saving the
    layout. Only the percentiles card has any: the measures to show, at most
    all three (the sex is the child's own, in its profile).
    :param data: the submitted form, a QueryDict.
    :returns: True if the settings were valid.
    """
    from core import growth

    if key != "percentiles":
        return False
    measures = [m for m in growth.MEASURES if m in data.getlist("measures")]
    options = dict(layout.options or {})
    options[key] = {"measures": measures}
    layout.options = options
    return True


def apply(layout, kind, key, op, keys=None):
    """
    Applies one edit-mode operation to a layout, without saving it.
    :param kind: "card" or "action".
    :param op: up, down, left, right (cards only), hide or show; for report
        cards also add (to the dashboard) and remove (from the hidden ones).
        For cards also the whole arrangement dragged on the page: "columns"
        with `keys` the three columns, or "order" with `keys` the order on
        narrow screens; both list the shown cards the user sees, which take
        that order among themselves while the others keep their places.
    :returns: True if the operation was understood.
    """
    columns, hidden, actions, hidden_actions, order = arrangement(layout)
    # The narrow-screen order follows the columns until arranged on its own.
    arranged_narrow = bool(layout.order)
    shown = {k for column in columns for k in column}

    def listed(submitted):
        """The submitted keys if they are shown cards, each once, else None."""
        if not isinstance(submitted, list) or len(set(submitted)) != len(submitted):
            return None
        return submitted if shown.issuperset(submitted) else None

    if kind == "card" and op == "order":
        new = listed(keys)
        if new is None:
            return False
        order = _rearranged(order, new)
        arranged_narrow = True
    elif kind == "card" and op == "columns":
        if not isinstance(keys, list) or len(keys) != COLUMNS:
            return False
        new = [listed(column) for column in keys]
        flat = [k for column in new if column is not None for k in column]
        if None in new or listed(flat) is None:
            return False
        # The cards the user cannot see stay in their column, at their row.
        for c, column in enumerate(columns):
            for row, k in enumerate(column):
                if k not in flat:
                    new[c].insert(min(row, len(new[c])), k)
        columns = new
    elif kind == "card" and card(key):
        where = next((c for c in columns if key in c), None)
        is_report = card(key).report is not None
        if op == "hide" and where is not None:
            where.remove(key)
            hidden.append(key)
            order.remove(key)
        elif op == "show" and key in hidden:
            hidden.remove(key)
            columns[DEFAULT_COLUMN.get(key, 0)].append(key)
            order.append(key)
        elif op == "add" and is_report and where is None:
            if key in hidden:
                hidden.remove(key)
            columns[0].append(key)
            order.append(key)
        elif op == "remove" and is_report and key in hidden:
            hidden.remove(key)
        elif op in ("up", "down") and where is not None:
            _move_within(where, key, -1 if op == "up" else 1)
        elif op in ("left", "right") and where is not None:
            target = columns.index(where) + (-1 if op == "left" else 1)
            if not 0 <= target < COLUMNS:
                return False
            # The card keeps its height on the page as far as it can.
            row = where.index(key)
            where.remove(key)
            columns[target].insert(min(row, len(columns[target])), key)
        else:
            return False
    elif kind == "action" and action(key):
        if op == "hide" and key in actions:
            actions.remove(key)
            hidden_actions.append(key)
        elif op == "show" and key in hidden_actions:
            hidden_actions.remove(key)
            actions.append(key)
        elif op in ("up", "down") and key in actions:
            _move_within(actions, key, -1 if op == "up" else 1)
        else:
            return False
    else:
        return False
    layout.columns = columns
    layout.hidden = hidden
    layout.actions = actions
    layout.hidden_actions = hidden_actions
    layout.order = order if arranged_narrow else []
    return True


def reset(layout):
    layout.columns = default_columns()
    layout.hidden = default_hidden()
    layout.order = []
    layout.actions = default_actions()
    layout.hidden_actions = [a.key for a in ACTIONS if not a.default]
