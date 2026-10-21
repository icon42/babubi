# -*- coding: utf-8 -*-
from django.db import models
from django.utils.translation import gettext_lazy as _


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
