# -*- coding: utf-8 -*-
"""
Entries to repeat, above a form (babubi/form_presets.html): the entries
made before, told apart by a few key fields and the most frequent first, each
a button that fills the form as that entry usually goes, without submitting
it (babubi.js).

A form opened for one child (from its dashboard, or with a single child)
offers that child's entries; otherwise everyone's.
"""

import json
from collections import Counter

from django import forms
from django.db.models import Count, Max

from core.suggestions import plain

# At most this many entries, so the list never grows without end.
LIMIT = 4

# How many of the latest occurrences of an entry are looked at for the
# values it usually has (typical()).
OCCURRENCES = 10


def frequent_entries(model, key, dated_by, child=None, **filters):
    """
    The entries told apart by their `key` fields, the most frequent first
    and, at the same frequency, the most recent; one occurrence is enough.
    :param dated_by: the model field that dates an entry.
    :param child: a Child instance to limit the entries to, or None.
    :param filters: further lookups the entries must match.
    :returns: a list of dicts with the key fields' stored values.
    """
    rows = model.objects.filter(**filters)
    if child is not None:
        rows = rows.filter(child=child)
    rows = (
        rows.values(*key)
        .annotate(uses=Count("pk"), last=Max(dated_by))
        .order_by("-uses", "-last")[:LIMIT]
    )
    return [{field: row[field] for field in key} for row in rows]


def commonest(values):
    """The most frequent of `values`; ties go to the first (the most recent)."""
    return Counter(values).most_common(1)[0][0]


def majority(values):
    """
    The value most of `values` have (more than half), or None: a one-off
    difference does not count, a split does. Ties go to the first, so pass
    the most recent first.
    """
    value, count = Counter(values).most_common(1)[0]
    return value if count * 2 > len(values) else None


def typical(model, row, usual, dated_by, child=None, **filters):
    """
    How the latest occurrences of an entry usually go, to pre-fill the form
    with: the `usual` fields by their most frequent value, the notes and tags
    only when most occurrences share them ("" or [] otherwise).
    :param row: the entry's key values, from frequent_entries().
    :param usual: the model fields filled with their most frequent value.
    :returns: a dict by field; "tags" is a list of dicts with name and color.
    """
    occurrences = model.objects.filter(**filters, **row)
    if child is not None:
        occurrences = occurrences.filter(child=child)
    occurrences = list(
        occurrences.order_by("-" + dated_by).prefetch_related("tags")[:OCCURRENCES]
    )
    found = {
        field: commonest([getattr(o, field) for o in occurrences]) for field in usual
    }
    fields = {f.name for f in model._meta.get_fields()}
    if "notes" in fields:
        found["notes"] = majority([o.notes or "" for o in occurrences]) or ""
    if "tags" in fields:
        names = (
            majority([tuple(sorted(t.name for t in o.tags.all())) for o in occurrences])
            or ()
        )
        tags = {t.name: t for o in occurrences for t in o.tags.all()}
        found["tags"] = [{"name": name, "color": tags[name].color} for name in names]
    return found


class PresetsMixin:
    """
    A form that offers entries to repeat: `presets` holds the model fields
    that tell an entry apart (`key`), those filled with the value the entry
    usually has (`usual`), the field that dates it (`dated_by`), a `filter`
    the entries must match and `to_form` converters from a stored value to
    the form field's. An edit form offers none.
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
        usual = self.presets.get("usual", ())
        for key in frequent_entries(self._meta.model, self.presets["key"], **scope):
            found = typical(self._meta.model, key, usual, **scope)
            row = {**key, **{name: found.pop(name) for name in usual}}
            values = {}
            for name, value in row.items():
                if value is not None:
                    value = plain(to_form.get(name, lambda v: v)(value))
                    # A number with decimals as the field shows it, with the
                    # language's separator (core/forms.py, DecimalInput).
                    if isinstance(
                        self.fields[name], (forms.FloatField, forms.DecimalField)
                    ):
                        value = self.fields[name].widget.format_value(value)
                values[self[name].html_name] = "" if value is None else value
            for name, value in found.items():
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
