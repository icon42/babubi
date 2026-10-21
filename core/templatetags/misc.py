# -*- coding: utf-8 -*-
from django import template

from core.models import Feeding, Sleep

register = template.Library()


@register.filter
def next(some_list, current_index):
    """
    Returns the element at the next index of the zero-indexed list
    :param some_list: a list
    :param current_index: the current index to increment
    :returns: the element at the next index or an empty string
    """
    if not some_list or current_index >= len(some_list) - 1:
        return ""
    return some_list[current_index + 1]


@register.filter
def prev(some_list, current_index):
    """
    Returns the element at the previous index of the zero-indexed list
    :param some_list: a list
    :param current_index: the current index to decrement
    :returns: the element at the previous index or an empty string
    """
    if not some_list or current_index <= 0:
        return ""
    return some_list[current_index - 1]


@register.simple_tag(takes_context=True)
def feeding_time_diff_base(context, feeding):
    if feeding:
        return feeding.end if Feeding.settings.feeding_diff_end else feeding.start
    else:
        return None


@register.simple_tag
def sleep_diff_end():
    """Whether the time between sleeps is counted from the end of the last one."""
    return Sleep.diff_settings.sleep_diff_end


@register.simple_tag
def sleep_time_diff_base(sleep):
    if sleep:
        return sleep.end if sleep_diff_end() else sleep.start
    return None
