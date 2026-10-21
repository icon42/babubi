# -*- coding: utf-8 -*-
from django import template

from core.growth import sex_of

register = template.Library()


@register.filter
def child_sex(child):
    """The child's sex for the WHO standards: "boy", "girl" or ""."""
    return sex_of(child)
