/* Babubi Dashboard graph cards
 *
 * A report card shows a compact version of the report's graph: no titles
 * (the card header names it), small ticks, the card's background, and the
 * activity's colour for a single series or the first of several. The graph
 * draws while the page still loads, before its column has its final width,
 * so the cards are fitted once the page is laid out, and again (fit) for a
 * card added in edit mode (dashboard_edit.js); a graph is compacted once.
 */
Babubi.DashboardGraphs = (function () {
  function rgbOf(color, where) {
    var probe = document.createElement("span");
    probe.style.color = color;
    where.appendChild(probe);
    var rgb = getComputedStyle(probe).color;
    probe.remove();
    return rgb;
  }
  function compact(graph) {
    if (graph.dataset.compacted) return;
    graph.dataset.compacted = "1";
    var box = graph.closest(".card-report-graph");
    var card = graph.closest(".card-dashboard");
    var style = getComputedStyle(card);
    var update = {
      autosize: true,
      width: null,
      height:
        parseInt(
          getComputedStyle(box).getPropertyValue("--graph-height"),
          10,
        ) || 280,
      "title.text": "",
      "xaxis.title.text": "",
      "yaxis.title.text": "",
      "xaxis.tickfont.size": 9,
      "xaxis.tickangle": 0,
      "xaxis.nticks": 6,
      "yaxis.tickfont.size": 9,
      "xaxis.rangeselector.font.size": 9,
      margin: { l: 36, r: 8, t: 36, b: 28 },
      paper_bgcolor: "rgba(0, 0, 0, 0)",
      plot_bgcolor: "rgba(0, 0, 0, 0)",
      "font.color": style.color,
      showlegend: graph.data.length > 1 && !box.dataset.seriesColor,
      "legend.font.size": 9,
      "legend.orientation": "h",
    };
    // Fixed ticks (e.g. every half hour of a day) crowd a card:
    // keep about eight of them.
    var y = graph.layout.yaxis || {};
    if (y.tickvals && y.tickvals.length > 12) {
      var step = Math.ceil(y.tickvals.length / 8);
      var keep = function (value, i) {
        return i % step === 0;
      };
      update["yaxis.tickvals"] = y.tickvals.filter(keep);
      update["yaxis.ticktext"] = (y.ticktext || []).filter(keep);
    }
    var selector = (graph.layout.xaxis || {}).rangeselector;
    if (selector && selector.buttons && selector.buttons.length) {
      update["xaxis.rangeselector.visible"] = false;
      update.margin.t = 8;
      box.insertBefore(
        Babubi.GraphRanges.group(graph, selector.buttons),
        box.firstChild,
      );
    }
    Plotly.relayout(graph, update);
    // The activity's colour: for the series of the report's own
    // colour when it names one, otherwise for the first series.
    var accent = rgbOf(style.getPropertyValue("--card-accent").trim(), card);
    var series = [0];
    if (box.dataset.seriesColor) {
      series = [];
      graph.data.forEach(function (trace, i) {
        if (trace.marker && trace.marker.color === box.dataset.seriesColor)
          series.push(i);
      });
    }
    if (series.length) {
      Plotly.restyle(
        graph,
        {
          "marker.color": accent,
          "line.color": accent,
          fillcolor: accent.replace("rgb(", "rgba(").replace(")", ", 0.35)"),
        },
        series,
      );
    }
    // Beside a named series the others are filler (e.g. the
    // awake time between sleeps): a faint neutral.
    if (box.dataset.seriesColor) {
      var others = graph.data
        .map(function (trace, i) {
          return i;
        })
        .filter(function (i) {
          return series.indexOf(i) < 0;
        });
      if (others.length) {
        var faint = rgbOf(style.color, card)
          .replace("rgb(", "rgba(")
          .replace(")", ", 0.08)");
        Plotly.restyle(graph, { "marker.color": faint }, others);
      }
    }
  }
  function fit() {
    document
      .querySelectorAll(".card-report-graph .plotly-graph-div")
      .forEach(function (graph) {
        try {
          compact(graph);
        } catch (error) {
          console.error(error);
        }
      });
  }
  window.addEventListener("load", fit);
  window.addEventListener("resize", function () {
    document
      .querySelectorAll(".card-report-graph .plotly-graph-div")
      .forEach(function (graph) {
        Plotly.Plots.resize(graph);
      });
  });
  return { fit: fit };
})();
