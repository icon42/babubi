"""
Activity lists grouped by local day, each day headed by a summary of the
whole day (core/templates/core/day_list.html).
"""

import datetime
from collections import Counter
from dataclasses import dataclass
from typing import Callable, Optional

from django.utils import formats, timezone
from django.utils.translation import gettext as _, ngettext

from core import models
from core.templatetags.days import short_duration


def _count(singular, plural, count):
    return ngettext(singular, plural, count) % {"count": count}


def _total(items, attribute):
    return sum(getattr(item, attribute) or 0 for item in items)


def _total_duration(items):
    durations = (item.duration or datetime.timedelta() for item in items)
    return sum(durations, datetime.timedelta())


def _part(text, icon=None):
    return {"text": text, "icon": icon}


def _diaperchange_summary(items):
    return [
        _part(_count("%(count)d change", "%(count)d changes", len(items))),
        _part(sum(item.wet for item in items), "icon-wet"),
        _part(sum(item.solid for item in items), "icon-solid"),
    ]


def _feeding_summary(items):
    parts = [
        _part(_count("%(count)d feeding", "%(count)d feedings", len(items))),
        _part(short_duration(_total_duration(items))),
    ]
    amount = _total(items, "amount")
    if amount:
        parts.append(_part(formats.number_format(amount)))
    return parts


def _pumping_summary(items):
    return [
        _part(_count("%(count)d pumping", "%(count)d pumpings", len(items))),
        _part(formats.number_format(_total(items, "amount"))),
    ]


def _sleep_summary(items):
    naps = sum(item.nap for item in items)
    parts = [_part(short_duration(_total_duration(items)))]
    if naps:
        parts.append(_part(_count("%(count)d nap", "%(count)d naps", naps)))
    return parts


def _tummytime_summary(items):
    return [
        _part(_count("%(count)d session", "%(count)d sessions", len(items))),
        _part(short_duration(_total_duration(items))),
    ]


def _medication_summary(items):
    names = Counter(item.name for item in items)
    return [_part(_count("%(count)d dose", "%(count)d doses", len(items)))] + [
        _part("{} ×{}".format(name, count)) for name, count in names.items()
    ]


def _temperature_summary(items):
    highest = max(item.temperature for item in items)
    return [
        _part(_count("%(count)d reading", "%(count)d readings", len(items))),
        _part(
            _("max. %(temperature)s")
            % {"temperature": formats.number_format(highest)}
        ),
    ]


def _note_summary(items):
    return [_part(_count("%(count)d note", "%(count)d notes", len(items)))]


def _since_previous_start(field):
    return lambda item, older: getattr(item, field) - getattr(older, field)


def _since_previous_feeding(item, older):
    base = older.end if models.Feeding.settings.feeding_diff_end else older.start
    return item.start - base


def _since_previous_sleep(item, older):
    base = older.end if models.Sleep.diff_settings.sleep_diff_end else older.start
    return item.start - base


def _mark_next_doses(items):
    """Flags the doses whose next one is still to come: each medication's latest."""
    now = timezone.now()
    for item in items:
        due = item.next_dose_time
        item.next_dose_due = (
            due
            if due
            and due > now
            and not models.Medication.objects.filter(
                child=item.child, name=item.name, time__gt=item.time
            ).exists()
            else None
        )


@dataclass(frozen=True)
class DayList:
    # The datetime field the list is ordered by, or a date field for a flat list.
    field: str
    # Prefix of the list's URL names, e.g. "core:diaperchange".
    url: str
    # Number of cells the list's template adds between the time and the notes.
    cells: int
    summary: Optional[Callable] = None
    previous: Optional[Callable] = None
    decorate: Optional[Callable] = None
    notes: bool = True

    @property
    def grouped(self):
        return self.field != "date"


DAY_LISTS = {
    "diaperchange": DayList(
        "time",
        "core:diaperchange",
        4,
        _diaperchange_summary,
        _since_previous_start("time"),
    ),
    "feeding": DayList(
        "start", "core:feeding", 5, _feeding_summary, _since_previous_feeding
    ),
    "pumping": DayList(
        "start", "core:pumping", 3, _pumping_summary, _since_previous_start("start")
    ),
    "sleep": DayList("start", "core:sleep", 3, _sleep_summary, _since_previous_sleep),
    "tummytime": DayList(
        "start",
        "core:tummytime",
        3,
        _tummytime_summary,
        _since_previous_start("start"),
    ),
    "medication": DayList(
        "time", "core:medication", 4, _medication_summary, decorate=_mark_next_doses
    ),
    "temperature": DayList("time", "core:temperature", 1, _temperature_summary),
    "note": DayList("time", "core:note", 2, _note_summary, notes=False),
    "weight": DayList("date", "core:weight", 1),
    "height": DayList("date", "core:height", 1),
    "headcircumference": DayList("date", "core:head-circumference", 1),
    "bmi": DayList("date", "core:bmi", 1),
}


class DayGroupedListMixin:
    """
    Adds `days` to a list view's context: the page's entries grouped by local
    day, each with the summary of the whole day (not only of the page), and
    `day_list`, what core/templates/core/day_list.html needs to draw them.
    """

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        spec = DAY_LISTS[self.model._meta.model_name]
        items = list(context["object_list"])

        if spec.previous and items:
            older = self.object_list.filter(
                **{spec.field + "__lt": getattr(items[-1], spec.field)}
            ).first()
            for item, previous in zip(items, items[1:] + [older]):
                item.since_previous = (
                    spec.previous(item, previous) if previous else None
                )
        if spec.decorate:
            spec.decorate(items)

        if spec.grouped:
            days = {}
            for item in items:
                day = timezone.localtime(getattr(item, spec.field)).date()
                days.setdefault(day, []).append(item)
            context["days"] = [
                {"date": day, "items": entries, "summary": self._summary(spec, day)}
                for day, entries in days.items()
            ]
        else:
            context["days"] = (
                [{"date": None, "items": items, "summary": None}] if items else []
            )

        model_name = self.model._meta.model_name
        user = self.request.user
        columns = 1 + spec.cells + spec.notes + 2 + (not context.get("unique_child"))
        context["day_list"] = {
            "activity": spec.url.split(":")[1],
            "add_url": spec.url + "-add",
            "update_url": spec.url + "-update",
            "delete_url": spec.url + "-delete",
            "can_add": user.has_perm("core.add_" + model_name),
            "can_change": user.has_perm("core.change_" + model_name),
            "can_delete": user.has_perm("core.delete_" + model_name),
            "notes": spec.notes,
            "columns": columns,
            "note_columns": columns - 2,
        }
        return context

    def _summary(self, spec, day):
        if not spec.summary:
            return None
        start = timezone.make_aware(datetime.datetime.combine(day, datetime.time.min))
        end = timezone.make_aware(
            datetime.datetime.combine(
                day + datetime.timedelta(days=1), datetime.time.min
            )
        )
        entries = list(
            self.object_list.filter(
                **{spec.field + "__gte": start, spec.field + "__lt": end}
            )
        )
        return spec.summary(entries)
