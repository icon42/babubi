# -*- coding: utf-8 -*-
"""
Recent entries to repeat, above a form (babubi/form_presets.html): the
combinations of some fields entered before, most recent first, each a button
that fills those fields at once without submitting the form (babubi.js).

A form opened for one child (from its dashboard, or with a single child)
offers that child's entries; otherwise everyone's.
"""

import json

from django.db.models import Count, Max

from core.suggestions import plain

LIMIT = 5


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
        for row in recent(
            self._meta.model,
            self.presets["fields"],
            self.presets["dated_by"],
            minimum=self.presets.get("minimum", 1),
            child=self.initial.get("child"),
            **self.presets.get("filter", {}),
        ):
            values = {}
            for name, value in row.items():
                if value is not None:
                    value = plain(to_form.get(name, lambda v: v)(value))
                values[self[name].html_name] = "" if value is None else value
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
