# -*- coding: utf-8 -*-
from django import forms
from django.utils.translation import gettext as _


class CommaSeparatedChoiceField(forms.MultipleChoiceField):
    """
    Several choices edited as a list and stored as one comma-separated string,
    in the order of the choices.
    """

    def prepare_value(self, value):
        if isinstance(value, str):
            return value.split(",") if value else []
        return value

    def clean(self, value):
        selected = set(super().clean(value))
        return ",".join(key for key, label in self.choices if key in selected)

    def has_changed(self, initial, data):
        return super().has_changed(self.prepare_value(initial), data)


class NapStartMaxTimeField(forms.TimeField):
    def validate(self, value):
        from core.models import Sleep

        if value < Sleep.settings.nap_start_min:
            raise forms.ValidationError(
                _(
                    "Nap start max. value %(max)s must be greater than nap start min. value %(min)s."
                ),
                code="invalid_nap_start_max",
                params={"max": value, "min": Sleep.settings.nap_start_min},
            )


class NapStartMinTimeField(forms.TimeField):
    def validate(self, value):
        from core.models import Sleep

        if value > Sleep.settings.nap_start_max:
            raise forms.ValidationError(
                _(
                    "Nap start min. value %(min)s must be less than nap start max. value %(max)s."
                ),
                code="invalid_nap_start_min",
                params={"min": value, "max": Sleep.settings.nap_start_max},
            )
