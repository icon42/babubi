# -*- coding: utf-8 -*-
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordChangeForm, UserCreationForm
from django.utils.translation import gettext_lazy as _

from babubi import roles

from .models import Settings
from .widgets import DateTimeInput


class BabubiUserForm(forms.ModelForm):
    """
    A user with explicit roles: an administrator (superuser) or a matrix of
    what they read and write per kind of entry (babubi/roles.py), with an
    "All" per column kept in their settings so later kinds are covered too.
    """

    access_expires = forms.DateTimeField(
        required=False,
        label=_("Access expires"),
        help_text=_(
            "Optional. After this time the user can no longer sign in or use "
            "the API."
        ),
        widget=DateTimeInput(),
    )
    read_all = forms.BooleanField(required=False, label=_("All"))
    write_all = forms.BooleanField(required=False, label=_("All"))

    class Meta:
        model = get_user_model()
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "is_superuser",
            "is_staff",
            "is_active",
            "access_expires",
        ]
        labels = {"is_superuser": _("Administrator")}
        help_texts = {
            "is_superuser": _(
                "Everything, users and site settings included; the permissions "
                "below do not apply."
            ),
            "is_staff": _("May manage users and site settings."),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs["instance"]
        if user:
            reads, writes, read_all, write_all = roles.effective(user)
            kwargs["initial"].update(
                {
                    "access_expires": user.settings.access_expires,
                    "read_all": read_all,
                    "write_all": write_all,
                }
            )
            for t in reads:
                kwargs["initial"]["read_" + t] = True
            for t in writes:
                kwargs["initial"]["write_" + t] = True
        super(BabubiUserForm, self).__init__(*args, **kwargs)
        for t in roles.ENTRY_TYPES:
            for column in ("read", "write"):
                self.fields[f"{column}_{t}"] = forms.BooleanField(
                    required=False,
                    label=roles.label(t),
                    widget=forms.CheckboxInput(attrs={"data-matrix": column}),
                )
        for name in ("read_all", "write_all"):
            self.fields[name].widget.attrs["data-matrix-all"] = name[:-4]

    @property
    def matrix(self):
        """The rows of the permission matrix: a kind with its two fields."""
        return [
            {
                "icon": roles.icon(t),
                "label": roles.label(t),
                "read": self["read_" + t],
                "write": self["write_" + t],
            }
            for t in roles.ENTRY_TYPES
        ]

    def kinds(self, column):
        """The kinds whose box of `column` ("read" or "write") is ticked."""
        return {t for t in roles.ENTRY_TYPES if self.cleaned_data.get(f"{column}_{t}")}

    def clean(self):
        cleaned_data = super().clean()
        # Writing a kind implies reading it.
        if cleaned_data.get("write_all"):
            cleaned_data["read_all"] = True
        for t in self.kinds("write"):
            cleaned_data["read_" + t] = True
        return cleaned_data

    def save(self, commit=True):
        user = super(BabubiUserForm, self).save(commit=False)
        if commit:
            user.save()
            flags = user.settings
            flags.access_expires = self.cleaned_data.get("access_expires")
            # An administrator's matrix is left as it was: it does not apply.
            if not user.is_superuser:
                flags.read_all = self.cleaned_data["read_all"]
                flags.write_all = self.cleaned_data["write_all"]
                # A column covered by its "All" keeps no permissions of its own.
                reads = set() if flags.read_all else self.kinds("read")
                writes = set() if flags.write_all else self.kinds("write")
                roles.grant(user, reads, writes)
            flags.save(update_fields=["access_expires", "read_all", "write_all"])
        return user


class UserAddForm(BabubiUserForm, UserCreationForm):
    pass


class UserUpdateForm(BabubiUserForm):
    pass


class UserForm(forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = ["first_name", "last_name", "email"]


class UserPasswordForm(PasswordChangeForm):
    class Meta:
        fields = ["old_password", "new_password1", "new_password2"]


class UserSettingsForm(forms.ModelForm):
    class Meta:
        model = Settings
        fields = [
            "dashboard_refresh_rate",
            "dashboard_hide_empty",
            "dashboard_hide_age",
            "language",
            "timezone",
            "theme",
            "pagination_count",
        ]
