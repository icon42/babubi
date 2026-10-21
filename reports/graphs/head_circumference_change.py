# -*- coding: utf-8 -*-
from django.utils.translation import gettext as _

from datetime import timedelta

import plotly.offline as plotly
import plotly.graph_objs as go

from reports import utils


def head_circumference_change(objects, curves=None, birthday=None):
    """
    Create a graph showing head_circumference over time.
    :param objects: a QuerySet of Head Circumference instances.
    :param curves: optionally, the WHO percentile curves to draw behind it,
        a dict of percentile → values by day of age (core.growth.curves).
    :param birthday: the child's birth date, where the curves start.
    :returns: a tuple of the graph's html and javascript.
    """
    objects = objects.order_by("-date")

    trace = go.Scatter(
        name=_("Head Circumference"),
        x=list(objects.values_list("date", flat=True)),
        y=list(objects.values_list("head_circumference", flat=True)),
        # Over the curves, a line: a filled area would hide them.
        fill=None if curves else "tozeroy",
    )

    layout_args = utils.default_graph_layout_options()
    layout_args["barmode"] = "stack"
    layout_args["title"] = "<b>" + _("Head Circumference") + "</b>"
    layout_args["xaxis"]["title"] = _("Date")
    layout_args["xaxis"]["rangeselector"] = utils.rangeselector_date()
    layout_args["yaxis"]["title"] = _("Head Circumference")

    data = [trace]
    if curves:
        dates = [birthday + timedelta(days=day) for day in range(len(curves[50]))]
        for percentile in sorted(curves, reverse=True):
            data.append(
                go.Scatter(
                    name="P{}".format(percentile),
                    x=dates,
                    y=curves[percentile],
                    **utils.percentile_line(percentile),
                )
            )
        last = max(objects.values_list("date", flat=True))
        layout_args["xaxis"]["range"] = [birthday, last + timedelta(days=1)]
        # Around the curves and the measurements, not from zero: head
        # circumference grows a few centimetres over a scale of fifty.
        values = list(objects.values_list("head_circumference", flat=True))
        low = min(values + curves[3])
        high = max(values + curves[97])
        layout_args["yaxis"]["range"] = [low - 2, high + 2]

    fig = go.Figure({"data": data, "layout": go.Layout(**layout_args)})
    output = plotly.plot(fig, output_type="div", include_plotlyjs=False)
    return utils.split_graph_output(output)
