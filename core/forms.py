# -*- coding: utf-8 -*-
from django import forms
from django.forms import widgets
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from taggit.forms import TagField, TagWidgetMixin

from babubi.widgets import DateInput, DateTimeInput, TimeInput
from core import models
from core.models import Timer
from core.presets import PresetsMixin
from core.suggestions import SHORT, SuggestionsMixin, plain
from core.widgets import TagsEditor, ChildRadioSelect, PillRadioSelect


def set_initial_values(kwargs, form_type):
    """
    Sets initial value for add forms based on provided kwargs.

    :param kwargs: Keyword arguments.
    :param form_type: Class of the type of form being initialized.
    :return: Keyword arguments with updated "initial" values.
    """

    # Never update initial values for existing instance (e.g. edit operation).
    if kwargs.get("instance", None):
        kwargs.pop("child", None)
        kwargs.pop("timer", None)
        return kwargs

    # Add the "initial" kwarg if it does not already exist.
    if not kwargs.get("initial"):
        kwargs.update(initial={})

    # Set Child based on `child` kwarg or single Chile database.
    child_slug = kwargs.get("child", None)
    if child_slug:
        kwargs["initial"].update(
            {
                "child": models.Child.objects.filter(slug=child_slug).first(),
            }
        )
    elif models.Child.count() == 1:
        kwargs["initial"].update({"child": models.Child.objects.first()})

    # Set start and end time based on Timer from `timer` kwarg.
    timer_id = kwargs.get("timer", None)
    if timer_id:
        try:
            timer = models.Timer.objects.get(id=timer_id)
            kwargs["initial"].update(
                {"timer": timer, "start": timer.start, "end": timezone.now()}
            )
        except (Timer.DoesNotExist, ValueError, TypeError, OverflowError):
            pass

    # Set type and method values for Feeding instance based on last feed.
    if form_type == FeedingForm and "child" in kwargs["initial"]:
        last_feeding = (
            models.Feeding.objects.filter(child=kwargs["initial"]["child"])
            .order_by("end")
            .last()
        )
        if last_feeding:
            last_method = last_feeding.method
            last_feed_args = {"type": last_feeding.type}
            if last_method not in ["left breast", "right breast"]:
                last_feed_args["method"] = last_method
            kwargs["initial"].update(last_feed_args)

    # Set default "nap" value for Sleep instances.
    if form_type == SleepForm and "nap" not in kwargs["initial"]:
        try:
            start = timezone.localtime(kwargs["initial"]["start"]).time()
        except KeyError:
            start = timezone.localtime().time()
        nap = (
            models.Sleep.settings.nap_start_min
            <= start
            <= models.Sleep.settings.nap_start_max
        )
        kwargs["initial"].update({"nap": nap})

    # Remove custom kwargs, so they do not interfere with `super` calls.
    for key in ["child", "timer"]:
        try:
            kwargs.pop(key)
        except KeyError:
            pass

    return kwargs


class CoreModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", getattr(self, "user", None))
        # Set `timer_id` so the Timer can be consumed only after a successful save.
        self.timer_id = kwargs.get("timer", None)
        kwargs = set_initial_values(kwargs, type(self))
        super(CoreModelForm, self).__init__(*args, **kwargs)
        self.add_timer_field()
        self.hide_single_child()

    def hide_single_child(self):
        """
        With one child there is nothing to choose: the child field, already
        set, goes along hidden instead of as a lone pressed button.
        """
        field = self.fields.get("child")
        if field is None or models.Child.count() != 1:
            return
        if self.initial.get("child") is None:
            return
        field.widget = forms.HiddenInput()

    def add_timer_field(self):
        """
        Add a read-only field with the name of the Timer being stopped.

        The form is usually opened from a Timer, so showing which Timer the
        entry belongs to makes it possible to identify the timer after the
        fact. The Timer is only a source of initial values, so the field is
        disabled and not used when the form is saved.
        """
        if not self.timer_id:
            return

        try:
            timer = models.Timer.objects.filter(id=self.timer_id).first()
        except (ValueError, TypeError, OverflowError):
            return

        if not timer:
            return

        self.fields["timer"] = forms.CharField(
            label=_("Timer"),
            required=False,
            disabled=True,
        )
        self.initial["timer"] = timer.title_with_child
        self.fields = self.move_after(self.fields, "timer", "child")

        if hasattr(self, "fieldsets"):
            self.fieldsets = [
                {
                    **fieldset,
                    "fields": self.move_after(fieldset["fields"], "timer", "child"),
                }
                for fieldset in self.fieldsets
            ]

    @staticmethod
    def move_after(fields, item, anchor):
        """Return the fields with `item` placed directly after `anchor`."""
        if item == anchor or anchor not in fields:
            return fields

        if isinstance(fields, dict):
            if item not in fields:
                return fields

            items = list(fields.items())
            entry = items.pop([key for key, _ in items].index(item))
            items.insert([key for key, _ in items].index(anchor) + 1, entry)
            return dict(items)

        fields = list(fields)
        if item in fields:
            fields.remove(item)
        fields.insert(fields.index(anchor) + 1, item)
        return fields

    def clean(self):
        cleaned_data = super().clean()
        if self.timer_id is not None:
            try:
                timer = models.Timer.objects.get(pk=self.timer_id)
            except (Timer.DoesNotExist, ValueError, TypeError, OverflowError):
                raise forms.ValidationError(_("This timer does not exist."))
            if self.user is None or not timer.can_be_consumed_by(self.user):
                raise PermissionDenied(
                    _("You do not have permission to consume timers.")
                )
        return cleaned_data

    @transaction.atomic
    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            timer = None
            if self.timer_id is not None:
                # Lock until the entry and its tags have been saved successfully.
                timer = (
                    models.Timer.objects.select_for_update()
                    .filter(pk=self.timer_id)
                    .first()
                )
                if timer is None:
                    raise forms.ValidationError(_("This timer no longer exists."))
                # The timer may have changed owner since validation.
                if self.user is None or not timer.can_be_consumed_by(self.user):
                    raise PermissionDenied(
                        _("You do not have permission to consume timers.")
                    )
            instance.save()
            self.save_m2m()
            if timer is not None:
                timer.stop()
        return instance

    @property
    def hydrated_fielsets(self):
        # for some reason self.fields returns defintions and not bound fields
        # so until i figure out a better way we can just create a dict here
        # https://github.com/django/django/blob/main/django/forms/forms.py#L52

        bound_field_dict = {}
        for field in self:
            bound_field_dict[field.name] = field

        hydrated_fieldsets = []

        for fieldset in self.fieldsets:
            hyrdrated_fieldset = {
                "layout": fieldset.get("layout", "default"),
                "layout_attrs": fieldset.get("layout_attrs", {}),
                "fields": [],
            }
            for field_name in fieldset["fields"]:
                hyrdrated_fieldset["fields"].append(bound_field_dict[field_name])

            hydrated_fieldsets.append(hyrdrated_fieldset)

        return hydrated_fieldsets


class HiddenTagWidget(TagWidgetMixin, forms.HiddenInput):
    """Hidden tag input that still renders tag names instead of object reprs."""


class TaggableModelForm(forms.ModelForm):
    tags = TagField(
        label=_("Tags"),
        widget=TagsEditor,
        required=False,
        strip=True,
        help_text=_(
            "Click on the tags to add (+) or remove (-) tags or use the text editor to create new tags."
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.user is None or not self.user.has_perm("core.change_tag"):
            # Without `change_tag` the field stays in the form (the layout and
            # the preserved value depend on it) but is only a carrier for the
            # current tag names, which `clean_tags` accepts unchanged.
            self.fields["tags"].widget = HiddenTagWidget()
            self.fields["tags"].help_text = None

    def clean_tags(self):
        current = list(self.instance.tags.names()) if self.instance.pk else []
        if self.add_prefix("tags") not in self.data:
            return current
        tags = self.cleaned_data["tags"]
        models.Tag.check_assignment_permissions(self.user, tags, current)
        return tags


class BMIForm(SuggestionsMixin, CoreModelForm, TaggableModelForm):
    suggestions = {"notes": ("notes", SHORT)}

    fieldsets = [
        {
            "fields": ["child", "bmi", "date"],
            "layout": "required",
        },
        {"fields": ["notes", "tags"], "layout": "advanced"},
    ]

    class Meta:
        model = models.BMI
        fields = ["child", "bmi", "date", "notes", "tags"]
        widgets = {
            "child": ChildRadioSelect,
            "date": DateInput(),
            "notes": forms.Textarea(attrs={"rows": 5}),
        }


class BottleFeedingForm(
    PresetsMixin, SuggestionsMixin, CoreModelForm, TaggableModelForm
):
    suggestions = {"amount": "amount", "notes": ("notes", SHORT)}
    # Bottles given the same way at least twice.
    presets = {
        "fields": ["type", "amount"],
        "dated_by": "start",
        "minimum": 2,
        "filter": {"method": "bottle"},
    }

    fieldsets = [
        {"fields": ["child", "type", "start", "amount"], "layout": "required"},
        {"fields": ["notes", "tags"], "layout": "advanced"},
    ]

    def clean(self):
        cleaned_data = super().clean()
        if "start" in cleaned_data:
            self.instance.end = cleaned_data["start"]
        return cleaned_data

    def save(self, commit=True):
        self.instance.method = "bottle"
        self.instance.end = self.instance.start
        return super().save(commit=commit)

    class Meta:
        model = models.Feeding
        fields = ["child", "start", "type", "amount", "notes", "tags"]
        widgets = {
            "child": ChildRadioSelect,
            "start": DateTimeInput(),
            "type": PillRadioSelect(),
            "notes": forms.Textarea(attrs={"rows": 5}),
        }


class ChildForm(forms.ModelForm):
    # Kept in Babubi's own dashboard.ChildProfile, not on the Child model.
    sex = forms.ChoiceField(
        required=False,
        choices=[
            ("", _("Not specified")),
            ("boy", _("Boy")),
            ("girl", _("Girl")),
        ],
        label=_("Sex"),
        help_text=_("Picks the WHO growth standards; none when not specified."),
    )

    class Meta:
        model = models.Child
        fields = ["first_name", "last_name", "birth_date", "birth_time"]
        if settings.BABUBI["ALLOW_UPLOADS"]:
            fields.append("picture")
        widgets = {
            "birth_date": DateInput(),
            "birth_time": TimeInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            from core.growth import sex_of

            self.fields["sex"].initial = sex_of(self.instance)

    def save(self, commit=True):
        from core.growth import set_sex

        child = super().save(commit=commit)
        if commit:
            set_sex(child, self.cleaned_data.get("sex", ""))
        return child


class ChildDeleteForm(forms.ModelForm):
    confirm_name = forms.CharField(max_length=511)

    class Meta:
        model = models.Child
        fields = []

    def clean_confirm_name(self):
        confirm_name = self.cleaned_data["confirm_name"]
        if confirm_name != str(self.instance):
            raise forms.ValidationError(
                _("Name does not match child name."), code="confirm_mismatch"
            )
        return confirm_name

    def save(self, commit=True):
        instance = self.instance
        self.instance.delete()
        return instance


class DiaperChangeForm(SuggestionsMixin, CoreModelForm, TaggableModelForm):
    suggestions = {"amount": "amount", "notes": ("notes", SHORT)}

    fieldsets = [
        {"fields": ["child", "time"], "layout": "required"},
        {
            "fields": ["wet", "solid"],
            "layout": "choices",
            "layout_attrs": {"label": "Contents"},
        },
        {"fields": ["color", "amount"]},
        {"layout": "advanced", "fields": ["notes", "tags"]},
    ]

    class Meta:
        model = models.DiaperChange
        fields = ["child", "time", "wet", "solid", "color", "amount", "notes", "tags"]
        widgets = {
            "child": ChildRadioSelect(),
            "color": PillRadioSelect(),
            "time": DateTimeInput(),
            "notes": forms.Textarea(attrs={"rows": 5}),
        }


class FeedingForm(PresetsMixin, SuggestionsMixin, CoreModelForm, TaggableModelForm):
    suggestions = {"amount": "amount", "notes": ("notes", SHORT)}
    # Feedings given the same way at least twice.
    presets = {
        "fields": ["type", "method", "amount"],
        "dated_by": "start",
        "minimum": 2,
    }

    fieldsets = [
        {"fields": ["child", "start", "end", "type", "method"], "layout": "required"},
        {"fields": ["amount"]},
        {"fields": ["notes", "tags"], "layout": "advanced"},
    ]

    class Meta:
        model = models.Feeding
        fields = ["child", "start", "end", "type", "method", "amount", "notes", "tags"]
        widgets = {
            "child": ChildRadioSelect,
            "start": DateTimeInput(),
            "end": DateTimeInput(),
            "type": PillRadioSelect(),
            "method": PillRadioSelect(),
            "notes": forms.Textarea(attrs={"rows": 5}),
        }


class HeadCircumferenceForm(SuggestionsMixin, CoreModelForm, TaggableModelForm):
    suggestions = {"notes": ("notes", SHORT)}

    fieldsets = [
        {
            "fields": ["child", "head_circumference", "date"],
            "layout": "required",
        },
        {"fields": ["notes", "tags"], "layout": "advanced"},
    ]

    class Meta:
        model = models.HeadCircumference
        fields = ["child", "head_circumference", "date", "notes", "tags"]
        widgets = {
            "child": ChildRadioSelect,
            "date": DateInput(),
            "notes": forms.Textarea(attrs={"rows": 5}),
        }


class HeightForm(SuggestionsMixin, CoreModelForm, TaggableModelForm):
    suggestions = {"notes": ("notes", SHORT)}

    fieldsets = [
        {
            "fields": ["child", "height", "date"],
            "layout": "required",
        },
        {"fields": ["notes", "tags"], "layout": "advanced"},
    ]

    class Meta:
        model = models.Height
        fields = ["child", "height", "date", "notes", "tags"]
        widgets = {
            "child": ChildRadioSelect,
            "date": DateInput(),
            "notes": forms.Textarea(attrs={"rows": 5}),
        }


def interval_hours(interval):
    """A dose interval, stored as a duration, as the hours the form takes."""
    return interval.total_seconds() / 3600


class MedicationForm(PresetsMixin, SuggestionsMixin, CoreModelForm, TaggableModelForm):
    suggestions = {
        "name": "name",
        "notes": ("notes", SHORT),
        "dosage": "dosage",
        "next_dose_interval": ("next_dose_interval", {"to_form": interval_hours}),
    }
    # A treatment: a medication given with an interval to the next dose.
    presets = {
        "fields": ["name", "dosage", "dosage_unit", "next_dose_interval"],
        "dated_by": "time",
        "filter": {"next_dose_interval__isnull": False},
        "to_form": {"next_dose_interval": interval_hours},
    }

    next_dose_interval = forms.DecimalField(
        label=_("Time Until Next Dosage"),
        required=False,
        min_value=0,
        initial=0,
        help_text=_("Optional: Hours until next dose can be given"),
    )

    fieldsets = [
        {
            "fields": [
                "child",
                "time",
                "next_dose_interval",
                "name",
                "dosage",
                "dosage_unit",
            ],
            "layout": "required",
        },
        {"fields": ["notes", "tags"], "layout": "advanced"},
    ]

    class Meta:
        model = models.Medication
        fields = [
            "child",
            "name",
            "dosage",
            "dosage_unit",
            "time",
            "next_dose_interval",
            "notes",
            "tags",
        ]
        widgets = {
            "child": ChildRadioSelect,
            "dosage_unit": PillRadioSelect(),
            "time": DateTimeInput(),
            "notes": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Convert existing timedelta to hours for display
        if self.instance and self.instance.next_dose_interval:
            self.initial["next_dose_interval"] = plain(
                interval_hours(self.instance.next_dose_interval)
            )
        # A whole dose reads 1, not 1.0.
        if self.instance and self.instance.dosage is not None:
            self.initial["dosage"] = plain(self.instance.dosage)

    def preset_label(self, row):
        """E.g. "Dalsy · 5 ml · every 8 h"."""
        dose = " ".join(
            str(part)
            for part in (plain(row["dosage"]), row["dosage_unit"])
            if part not in (None, "")
        )
        every = _("every %(hours)s h") % {
            "hours": plain(interval_hours(row["next_dose_interval"]))
        }
        return " · ".join(part for part in (row["name"], dose, every) if part)

    def clean_next_dose_interval(self):
        hours = self.cleaned_data.get("next_dose_interval")
        if hours is not None and hours > 0:
            return timezone.timedelta(hours=float(hours))
        return None


class PumpingForm(SuggestionsMixin, CoreModelForm, TaggableModelForm):
    suggestions = {"amount": "amount", "notes": ("notes", SHORT)}

    fieldsets = [
        {"fields": ["child", "start", "end"], "layout": "required"},
        {"fields": ["amount"]},
        {"fields": ["notes", "tags"], "layout": "advanced"},
    ]

    class Meta:
        model = models.Pumping
        fields = ["child", "start", "end", "amount", "notes", "tags"]
        widgets = {
            "child": ChildRadioSelect,
            "start": DateTimeInput(),
            "end": DateTimeInput(),
            "notes": forms.Textarea(attrs={"rows": 5}),
        }


class NoteForm(SuggestionsMixin, CoreModelForm, TaggableModelForm):
    suggestions = {"note": ("note", SHORT)}

    class Meta:
        model = models.Note
        fields = ["child", "note", "time", "tags"]
        if settings.BABUBI["ALLOW_UPLOADS"]:
            fields.insert(2, "image")
        widgets = {
            "child": ChildRadioSelect,
            "time": DateTimeInput(),
        }


class SleepForm(SuggestionsMixin, CoreModelForm, TaggableModelForm):
    suggestions = {"notes": ("notes", SHORT)}

    fieldsets = [
        {
            "fields": ["child", "start", "end", "nap"],
            "layout": "required",
        },
        {"fields": ["notes", "tags"], "layout": "advanced"},
    ]

    class Meta:
        model = models.Sleep
        fields = ["child", "start", "end", "nap", "notes", "tags"]
        widgets = {
            "child": ChildRadioSelect,
            "start": DateTimeInput(),
            "end": DateTimeInput(),
            "notes": forms.Textarea(attrs={"rows": 5}),
        }


class TagAdminForm(CoreModelForm):
    fieldsets = [
        {
            "fields": ["name", "color"],
            "layout": "required",
        }
    ]

    class Meta:
        model = models.Tag
        fields = ["name", "color"]
        readonly_fields = ["slug"]
        widgets = {
            "color": widgets.TextInput(
                attrs={"type": "color", "class": "form-control-color"}
            )
        }


class TemperatureForm(SuggestionsMixin, CoreModelForm, TaggableModelForm):
    suggestions = {"notes": ("notes", SHORT)}

    fieldsets = [
        {
            "fields": ["child", "temperature", "time"],
            "layout": "required",
        },
        {"fields": ["notes", "tags"], "layout": "advanced"},
    ]

    class Meta:
        model = models.Temperature
        fields = ["child", "temperature", "time", "notes", "tags"]
        widgets = {
            "child": ChildRadioSelect,
            "time": DateTimeInput(),
            "notes": forms.Textarea(attrs={"rows": 5}),
        }


class TimerForm(CoreModelForm):
    # What it times, kept in Babubi's dashboard.TimerProfile; it can also be
    # set or changed from the timer's page while it runs.
    kind = forms.ChoiceField(
        required=False,
        choices=[
            ("", _("Not specified")),
            ("feeding", _("Feeding")),
            ("pumping", _("Pumping")),
            ("sleep", _("Sleep")),
            ("tummytime", _("Tummy Time")),
        ],
        label=_("Type"),
        widget=PillRadioSelect,
    )

    class Meta:
        model = models.Timer
        fields = ["child", "name", "start"]
        widgets = {
            "child": ChildRadioSelect,
            "start": DateTimeInput(),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super(TimerForm, self).__init__(*args, **kwargs)
        from core.timer_kinds import allowed, kind_of

        current = kind_of(self.instance) if self.instance.pk else ""
        if current:
            self.fields["kind"].initial = current
        # Only the kinds the user may add, plus the one the timer already has.
        kinds = ("", current) + allowed(self.user)
        self.fields["kind"].choices = [
            choice for choice in self.fields["kind"].choices if choice[0] in kinds
        ]

    def save(self, commit=True):
        from core.timer_kinds import set_kind

        instance = super(TimerForm, self).save(commit=False)
        if instance.user_id is None:
            instance.user = self.user
            instance.save()
        else:
            # Editing a timer does not change its owner, including an owner
            # changed by someone else while the form was open.
            instance.save(update_fields=self._meta.fields)
        set_kind(instance, self.cleaned_data.get("kind", ""))
        return instance


class TummyTimeForm(SuggestionsMixin, CoreModelForm, TaggableModelForm):
    suggestions = {"notes": ("notes", SHORT)}

    fieldsets = [
        {"fields": ["child", "start", "end"], "layout": "required"},
        {"fields": ["milestone"]},
        {"fields": ["notes", "tags"], "layout": "advanced"},
    ]

    class Meta:
        model = models.TummyTime
        fields = ["child", "start", "end", "milestone", "notes", "tags"]
        widgets = {
            "child": ChildRadioSelect,
            "start": DateTimeInput(),
            "end": DateTimeInput(),
            "notes": forms.Textarea(attrs={"rows": 5}),
        }


class WeightForm(SuggestionsMixin, CoreModelForm, TaggableModelForm):
    suggestions = {"notes": ("notes", SHORT)}

    fieldsets = [
        {
            "fields": ["child", "weight", "date"],
            "layout": "required",
        },
        {"fields": ["notes", "tags"], "layout": "advanced"},
    ]

    class Meta:
        model = models.Weight
        fields = ["child", "weight", "date", "notes", "tags"]
        widgets = {
            "child": ChildRadioSelect,
            "date": DateInput(),
            "notes": forms.Textarea(attrs={"rows": 5}),
        }
