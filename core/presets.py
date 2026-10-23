# -*- coding: utf-8 -*-
"""
Recent entries to repeat, above a form (babubi/form_presets.html): the
combinations of some fields entered before, most recent first, each a button
that fills those fields at once without submitting the form (babubi.js).

A form opened for one child (from its dashboard, or with a single child)
offers that child's entries; otherwise everyone's.
"""

import json
from collections import Counter

from django.db.models import Count, Max

from core.suggestions import plain

LIMIT = 5

# How many of the latest occurrences of an entry are looked at for the notes
# and tags they usually have (carried()).
OCCURRENCES = 10


def recent(model, fields, dated_by, minimum=1, child=None, **filters):
    """
    The combinations of `fields` entered at least `minimum` times, most
    recent first.
    :param dated_by: the model field that dates an entry.
    :param child: a Child instance to limit the entries to, or None.
    :param filters: further lookups the entries must match.
    :returns: a list of dicts with the fields' stored values.
    """
    rows = model.objects.filter(**filters)
    if child is not None:
        rows = rows.filter(child=child)
    rows = (
        rows.values(*fields)
        .annotate(uses=Count("pk"), last=Max(dated_by))
        .filter(uses__gte=minimum)
        .order_by("-last")[:LIMIT]
    )
    return [{field: row[field] for field in fields} for row in rows]


def usual(values):
    """
    The value most of `values` have (more than half), or None: a one-off
    difference does not count, a split does. Ties go to the first, so pass
    the most recent first.
    """
    value, count = Counter(values).most_common(1)[0]
    return value if count * 2 > len(values) else None


def carried(model, row, dated_by, child=None, **filters):
    """
    The notes and tags the latest occurrences of an entry usually have, to
    pre-fill the form with: "" or [] when they have none or disagree.
    :param row: the entry's stored values by field, from recent().
    :returns: a dict with "notes" and "tags" (a list of dicts with name and
        color), for the fields the model has.
    """
    occurrences = model.objects.filter(**filters, **row)
    if child is not None:
        occurrences = occurrences.filter(child=child)
    occurrences = list(
        occurrences.order_by("-" + dated_by).prefetch_related("tags")[:OCCURRENCES]
    )
    found = {}
    fields = {f.name for f in model._meta.get_fields()}
    if "notes" in fields:
        found["notes"] = usual([o.notes or "" for o in occurrences]) or ""
    if "tags" in fields:
        names = (
            usual([tuple(sorted(t.name for t in o.tags.all())) for o in occurrences])
            or ()
        )
        tags = {t.name: t for o in occurrences for t in o.tags.all()}
        found["tags"] = [{"name": name, "color": tags[name].color} for name in names]
    return found


class PresetsMixin:
    """
    A form that offers recent entries to repeat: `presets` holds the model
    `fields` that make up an entry, the field that dates it (`dated_by`), how
    many times a combination must have been entered (`minimum`, 1 by
    default), a `filter` the entries must match and `to_form` converters from
    a stored value to the form field's. An edit form offers none.
    """

    presets = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.preset_buttons = []
        if not self.presets or self.instance.pk:
            return
        # Like the quick picks, they show stored values: viewing is needed.
        meta = self._meta.model._meta
        user = getattr(self, "user", None)
        if user is None or not user.has_perm(
            "{}.view_{}".format(meta.app_label, meta.model_name)
        ):
            return
        to_form = self.presets.get("to_form", {})
        scope = {
            "dated_by": self.presets["dated_by"],
            "child": self.initial.get("child"),
            **self.presets.get("filter", {}),
        }
        for row in recent(
            self._meta.model,
            self.presets["fields"],
            minimum=self.presets.get("minimum", 1),
            **scope,
        ):
            values = {}
            for name, value in row.items():
                if value is not None:
                    value = plain(to_form.get(name, lambda v: v)(value))
                values[self[name].html_name] = "" if value is None else value
            for name, value in carried(self._meta.model, row, **scope).items():
                if name in self.fields:
                    values[self[name].html_name] = value
            self.preset_buttons.append(
                {"label": self.preset_label(row), "values": json.dumps(values)}
            )

    def preset_label(self, row):
        """
        Name an entry: its values, choices by their label, joined by dots.
        :param row: the entry's stored values by field.
        """
        parts = []
        for name, value in row.items():
            if value in (None, ""):
                continue
            choices = dict(self._meta.model._meta.get_field(name).flatchoices)
            parts.append(str(choices.get(value, plain(value))))
        return " · ".join(parts)
