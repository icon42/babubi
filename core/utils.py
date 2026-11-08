# -*- coding: utf-8 -*-
import datetime
import random

from django.utils import timezone
from django.utils.translation import ngettext

random.seed()

COLORS = [
    "#ff0000",
    "#00ff00",
    "#0000ff",
    "#ff00ff",
    "#ffff00",
    "#00ffff",
    "#ff7f7f",
    "#7fff7f",
    "#7f7fff",
    "#ff7fff",
    "#ffff7f",
    "#7fffff",
    "#7f0000",
    "#007f00",
    "#00007f",
    "#7f007f",
    "#7f7f00",
    "#007f7f",
]


def duration_string(duration, precision="s"):
    """Format hours, minutes and seconds as a human-friendly string (e.g. "2
    hours, 25 minutes, 31 seconds") with precision to h = hours, m = minutes or
    s = seconds.
    """
    h, m, s = duration_parts(duration)

    duration = ""
    if h > 0:
        duration = ngettext("%(hours)s hour", "%(hours)s hours", h) % {"hours": h}
    if m >= 0 and precision != "h":
        if duration != "":
            duration += ", "
        duration += ngettext("%(minutes)s minute", "%(minutes)s minutes", m) % {
            "minutes": m
        }
    if s > 0 and precision != "h" and precision != "m":
        if duration != "":
            duration += ", "
        duration += ngettext("%(seconds)s second", "%(seconds)s seconds", s) % {
            "seconds": s
        }

    return duration


def duration_parts(duration):
    """Get hours, minutes and seconds from a timedelta."""
    if not isinstance(duration, timezone.timedelta):
        raise TypeError("Duration provided must be a timedelta")
    h, remainder = divmod(duration.seconds, 3600)
    h += duration.days * 24
    m, s = divmod(remainder, 60)
    return h, m, s


def random_color():
    return COLORS[random.randrange(0, len(COLORS))]


def _srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _linear_to_srgb(c):
    c = min(max(c, 0.0), 1.0)
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def _hex_to_oklab(hex_color):
    r, g, b = (_srgb_to_linear(int(hex_color[i : i + 2], 16) / 255) for i in (1, 3, 5))
    l = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    return (
        0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
        1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
        0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s,
    )


def _oklab_to_hex(lab):
    L, a, b = lab
    l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    rgb = (
        4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
        -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
        -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s,
    )
    return "#" + "".join("%02x" % round(_linear_to_srgb(c) * 255) for c in rgb)


def mix_colors(hex_colors):
    """
    Average "#rrggbb" colors in the OKLab space, which mixes perceptually
    (a plain RGB mean drifts towards grey and mud).
    :param hex_colors: a non-empty list of "#rrggbb" strings.
    :returns: the mixed color as a "#rrggbb" string.
    """
    labs = [_hex_to_oklab(c) for c in hex_colors]
    return _oklab_to_hex(tuple(sum(v) / len(labs) for v in zip(*labs)))


def timezone_aware_duration(
    start: timezone.datetime, end: timezone.datetime
) -> datetime.timedelta:
    """
    Calculate a duration between timezone aware dates in UTC. This accounts for DST changes between dates.
    """
    utc = datetime.timezone.utc
    return end.astimezone(utc) - start.astimezone(utc)
