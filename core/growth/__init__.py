# -*- coding: utf-8 -*-
"""
The WHO Child Growth Standards, from the WHO expanded tables (one row per
day of age, 0 to 1856). Weight and height read the tables the upstream
percentile reports import (core/migrations); head circumference reads the
WHO tables kept here, in the same format, converted from the WHO's expanded
tables (who.int/tools/child-growth-standards).
"""
import csv
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


def curves(measure_key, sex, days):
    """
    The WHO percentile curves P3, P15, P50, P85 and P97 for the first days
    of age.
    :returns: a dict of percentile → list of values, one per day.
    """
    rows = _table(measure_key, sex)[:days]
    return {p: [row["P{}".format(p)] for row in rows] for p in CURVES}
