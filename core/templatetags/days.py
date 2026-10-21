import datetime

from django import template
from django.utils import formats, timezone
from django.utils.text import capfirst
from django.utils.translation import gettext as _

register = template.Library()


@register.filter
def short_duration(duration):
    """
    Format a duration compactly for the activity lists (e.g. "1 h 52 min").
    :param duration: a timedelta instance.
    :returns: the hours and minutes, joined by non-breaking spaces, or "".
    """
    if not duration:
        return ""
    minutes = int(duration.total_seconds() // 60)
    hours, minutes = divmod(minutes, 60)
    if hours and minutes:
        text = _("%(hours)d h %(minutes)d min") % {"hours": hours, "minutes": minutes}
    elif hours:
        text = _("%(hours)d h") % {"hours": hours}
    else:
        text = _("%(minutes)d min") % {"minutes": minutes}
    # Non-breaking spaces: a duration never splits across lines.
    return text.replace(" ", "\u00a0")


@register.filter
def duration_percent(duration, hours=12):
    """
    How much of `hours` a duration fills, for the bars of the activity lists.
    :param duration: a timedelta instance.
    :param hours: the duration that fills the whole bar.
    :returns: a whole percentage between 0 and 100.
    """
    if not duration:
        return 0
    return min(100, round(duration.total_seconds() / (int(hours) * 36)))


@register.filter
def day_label(date):
    """
    Name a day of an activity list: "Today", "Yesterday · Tue 20/10" or
    "Mon 19/10", with the year added outside the current one.
    :param date: a date instance, in local time.
    :returns: the label of the day.
    """
    today = timezone.localdate()
    if date == today:
        return _("Today")
    if date.year == today.year:
        day_format = formats.get_format("SHORT_MONTH_DAY_FORMAT")
        if day_format == "SHORT_MONTH_DAY_FORMAT":
            day_format = "j/n"
    else:
        day_format = "SHORT_DATE_FORMAT"
    label = "{} {}".format(
        capfirst(formats.date_format(date, "D")), formats.date_format(date, day_format)
    )
    if date == today - datetime.timedelta(days=1):
        return "{} · {}".format(_("Yesterday"), label)
    return label


@register.filter
def ends_next_day(instance):
    """
    Whether an activity with a start and an end finishes on a later local day.
    :param instance: a model instance with `start` and `end`.
    :returns: True if it ends on a later day than it starts.
    """
    if not instance.end:
        return False
    return timezone.localtime(instance.end).date() > timezone.localtime(
        instance.start
    ).date()
