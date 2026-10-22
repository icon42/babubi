# -*- coding: utf-8 -*-
"""
Where a child's measurements fall on the WHO Child Growth Standards: the
exact percentile, from the L, M and S parameters of the WHO expanded tables
(one row per day of age, 0 to 1856). Weight and height read the tables the
upstream percentile reports import (core/migrations); head circumference
reads the WHO tables kept here, in the same format, converted from the WHO's
expanded tables (who.int/tools/child-growth-standards).
"""

import csv
import math
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from django.conf import settings
from django.utils.translation import gettext_lazy as _

from core import models

HERE = Path(__file__).resolve().parent
CORE_TABLES = Path(settings.BASE_DIR, "core", "migrations")
SEXES = ("boy", "girl")


@dataclass(frozen=True)
class Measure:
    key: str
    label: str
    model: type
    field: str
    unit: str
    # The table for a sex, as a format string over "boys" or "girls".
    table: Path

    @property
    def activity(self):
        return {"head_circumference": "head-circumference"}.get(self.key, self.key)


MEASURES = {
    measure.key: measure
    for measure in [
        Measure(
            "weight",
            _("Weight"),
            models.Weight,
            "weight",
            "kg",
            CORE_TABLES / "weight_percentile_{}.csv",
        ),
        Measure(
            "height",
            _("Height"),
            models.Height,
            "height",
            "cm",
            CORE_TABLES / "height_percentile_{}.csv",
        ),
        Measure(
            "head_circumference",
            _("Head Circumference"),
            models.HeadCircumference,
            "head_circumference",
            "cm",
            HERE / "head_circumference_percentile_{}.csv",
        ),
    ]
}


CURVES = (3, 15, 50, 85, 97)


@cache
def _table(measure_key, sex):
    """The rows of a measure's table for a sex, one per day of age."""
    path = str(MEASURES[measure_key].table).format(sex + "s")
    with open(path, newline="") as table:
        return [
            {column: float(value) for column, value in row.items()}
            for row in csv.DictReader(table)
        ]


@cache
def _lms(measure_key, sex):
    """The (L, M, S) of each day of age, for a measure and a sex."""
    return [(row["L"], row["M"], row["S"]) for row in _table(measure_key, sex)]


def curves(measure_key, sex, days):
    """
    The WHO percentile curves P3, P15, P50, P85 and P97 for the first days
    of age.
    :returns: a dict of percentile → list of values, one per day.
    """
    rows = _table(measure_key, sex)[:days]
    return {p: [row["P{}".format(p)] for row in rows] for p in CURVES}


def sex_of(child):
    """
    The sex in the child's profile (dashboard.ChildProfile), which picks the
    WHO standards: "boy", "girl", or "" when unspecified.
    """
    from django.core.exceptions import ObjectDoesNotExist

    try:
        return child.profile.sex
    except ObjectDoesNotExist:
        return ""


def set_sex(child, sex):
    """Sets the sex in the child's profile; an unknown one clears it."""
    from dashboard.models import ChildProfile

    sex = sex if sex in SEXES else ""
    ChildProfile.objects.update_or_create(child=child, defaults={"sex": sex})
    return sex


def percentile(measure_key, sex, age_in_days, value):
    """
    The percentile of a measurement, by the WHO's LMS method.
    :returns: a float between 0 and 100, or None outside the tables' ages.
    """
    table = _lms(measure_key, sex)
    if not 0 <= age_in_days < len(table) or value <= 0:
        return None
    lam, mu, sigma = table[age_in_days]
    if lam == 0:
        z = math.log(value / mu) / sigma
    else:
        z = ((value / mu) ** lam - 1) / (lam * sigma)
    return 50 * (1 + math.erf(z / math.sqrt(2)))


def latest(child, measure_key, sex):
    """
    The child's latest measurement of a kind and its percentile.
    :returns: a dict with the measure, the instance, its value and its
        percentile (None when out of the tables), or None without data.
    """
    measure = MEASURES[measure_key]
    instance = measure.model.objects.filter(child=child).order_by("-date").first()
    if instance is None:
        return None
    value = getattr(instance, measure.field)
    age = (instance.date - child.birth_date).days
    return {
        "measure": measure,
        "instance": instance,
        "value": value,
        "percentile": percentile(measure_key, sex, age, value),
    }
