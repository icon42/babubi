# -*- coding: utf-8 -*-
"""
Quick picks under a form field: the values most often entered in it before,
as small buttons that fill the field when clicked (babubi.js). A value shows
once it has been used at least twice; the most frequent come first.
"""
from django.db.models import Count
from django.db.models.functions import Length

LIMIT = 5
MINIMUM = 2

# For free text such as notes: only short values make useful picks, about
# five words of eight characters.
SHORT = {"max_length": 40}


def frequent(
    model, field, to_form=None, limit=LIMIT, minimum=MINIMUM, max_length=None
):
    """
    The values of a model field used at least `minimum` times, most frequent
    first.
    :param to_form: turns a stored value into the form field's (e.g. a
        duration into hours); by default the value itself.
    :param max_length: leaves out text values longer than this.
    """
    rows = model.objects.exclude(**{field + "__isnull": True}).exclude(
        **{field: ""} if _is_text(model, field) else {}
    )
    if max_length:
        rows = rows.annotate(length=Length(field)).filter(length__lte=max_length)
    rows = (
        rows.values(field)
        .annotate(uses=Count("pk"))
        .filter(uses__gte=minimum)
        .order_by("-uses", field)[:limit]
    )
    values = [row[field] for row in rows]
    return [to_form(value) for value in values] if to_form else values


def _is_text(model, field):
    kind = model._meta.get_field(field).get_internal_type()
    return kind in ("CharField", "TextField")


class SuggestionsMixin:
    """
    A form that offers quick picks for some of its fields: `suggestions` maps
    a form field to the model field its values come from, or to a tuple of the
    model field and a dict of further arguments for frequent().
    """

    suggestions = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # The picks show stored values, so they need the permission to view
        # the model, not only to add to it.
        meta = self._meta.model._meta
        user = getattr(self, "user", None)
        if user is None or not user.has_perm(
            "{}.view_{}".format(meta.app_label, meta.model_name)
        ):
            return
        for name, source in self.suggestions.items():
            if name not in self.fields:
                continue
            field, options = source if isinstance(source, tuple) else (source, {})
            widget = self.fields[name].widget
            self.fields[name].suggestions = [
                widget.format_value(plain(value))
                for value in frequent(self._meta.model, field, **options)
            ]


def plain(value):
    """A whole float as an integer, so 180.0 reads 180."""
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value
