# -*- coding: utf-8 -*-
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class DashboardLayout(models.Model):
    """
    How a user arranges one child's dashboard (each child is followed for
    different things at different ages): lists of card and quick action keys
    from dashboard/layout.py, which cleans them up on every read.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="dashboard_layouts",
    )
    child = models.ForeignKey(
        "core.Child", on_delete=models.CASCADE, related_name="dashboard_layouts"
    )
    # A list of columns, each a list of card keys, top to bottom.
    columns = models.JSONField(default=list, verbose_name=_("Columns"))
    hidden = models.JSONField(default=list, verbose_name=_("Hidden cards"))
    actions = models.JSONField(default=list, verbose_name=_("Quick actions"))
    hidden_actions = models.JSONField(
        default=list, verbose_name=_("Hidden quick actions")
    )
    # Each configurable card's settings, by card key.
    options = models.JSONField(default=dict, verbose_name=_("Card settings"))

    class Meta:
        default_permissions = ()
        constraints = [
            models.UniqueConstraint(
                fields=["user", "child"], name="unique_dashboard_layout"
            )
        ]

    @classmethod
    def of(cls, user, child):
        """The user's layout for a child's dashboard, saved or a new one."""
        found = cls.objects.filter(user=user, child=child).first()
        return found or cls(user=user, child=child)

    def __str__(self):
        return "{}: {}".format(self.user, self.child)


class ChildProfile(models.Model):
    """
    What Babubi records about a child beyond upstream's Child model, kept
    apart so upstream's migrations of core stay untouched: for now, the sex
    that picks the WHO growth standards (none when unspecified).
    """

    SEXES = [("boy", _("Boy")), ("girl", _("Girl"))]

    child = models.OneToOneField(
        "core.Child", on_delete=models.CASCADE, related_name="profile"
    )
    sex = models.CharField(
        blank=True, default="", max_length=8, choices=SEXES, verbose_name=_("Sex")
    )

    class Meta:
        default_permissions = ()

    def __str__(self):
        return str(self.child)
