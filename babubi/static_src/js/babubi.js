if (typeof jQuery === "undefined") {
  throw new Error("Babubi requires jQuery.");
}

/**
 * Babubi Namespace
 *
 * Default namespace for the Babubi app.
 *
 * @type {{}}
 */
var Babubi = (function () {
  return {};
})();

/**
 * Pull to refresh.
 *
 * @type {{init: Babubi.PullToRefresh.init, onRefresh: Babubi.PullToRefresh.onRefresh}}
 */
Babubi.PullToRefresh = (function (ptr) {
  return {
    init: function () {
      ptr.init({
        mainElement: "body",
        onRefresh: this.onRefresh,
      });
    },

    onRefresh: function () {
      window.location.reload();
    },
  };
})(PullToRefresh);

/**
 * Show a loading spinner on the submit button when a form is submitted and
 * prevent double-submission.
 */
(function handleFormSubmit() {
  $("form").on("submit", function (event) {
    var submitter =
      (event.originalEvent && event.originalEvent.submitter) ||
      $(this).find('[type="submit"]')[0];
    if (!submitter || $(submitter).prop("disabled")) return;
    // A disabled button is left out of the submitted data, so a named one
    // (e.g. one of several actions in a form) passes its value on first.
    if (submitter.name) {
      $("<input>", {
        type: "hidden",
        name: submitter.name,
        value: submitter.value,
      }).appendTo(this);
    }
    $(submitter)
      .prop("disabled", true)
      .prepend(
        '<span class="spinner-border spinner-border-sm me-1" role="status" aria-hidden="true"></span>',
      );
  });
})();

/**
 * Quick picks under a form field (core/suggestions.py): a click fills the
 * field with the picked value.
 */
document.addEventListener("click", function (event) {
  var button = event.target.closest("[data-suggestion-for]");
  if (!button) return;
  var input = document.getElementById(button.dataset.suggestionFor);
  if (!input) return;
  input.value = button.dataset.value;
  input.dispatchEvent(new Event("input", { bubbles: true }));
  input.dispatchEvent(new Event("change", { bubbles: true }));
  input.focus();
});

/**
 * Recent entries to repeat, above a form (core/presets.py): a click fills
 * every field of the entry at once, without submitting the form.
 */
document.addEventListener("click", function (event) {
  var button = event.target.closest("[data-preset]");
  if (!button || !button.form) return;
  var values = JSON.parse(button.dataset.preset);
  Object.keys(values).forEach(function (name) {
    var field = button.form.elements[name];
    if (!field) return;
    if (field.type === "checkbox") {
      field.checked = Boolean(values[name]);
    } else {
      // A RadioNodeList checks the radio whose value is set on it.
      field.value = values[name];
    }
    var inputs = field.length === undefined ? [field] : Array.from(field);
    inputs.forEach(function (input) {
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.dispatchEvent(new Event("change", { bubbles: true }));
    });
  });
});

/**
 * The permission matrix of the user form (babubi/roles.py): an "All" ticks
 * and greys out its column, the top "All" both columns, and the administrator
 * box the whole matrix; writing a kind ticks reading it. Greyed boxes are
 * enabled again on submit so their state is sent.
 */
Babubi.PermissionMatrix = (function () {
  function init() {
    var matrix = document.querySelector(".permission-matrix");
    var admin = document.getElementById("id_is_superuser");
    if (!matrix || !admin) return;
    var both = matrix.querySelector('[data-matrix-all="both"]');
    var all = {
      read: matrix.querySelector('[data-matrix-all="read"]'),
      write: matrix.querySelector('[data-matrix-all="write"]'),
    };
    var boxes = {
      read: matrix.querySelectorAll('[data-matrix="read"]'),
      write: matrix.querySelectorAll('[data-matrix="write"]'),
    };

    function force(input, on) {
      input.disabled = on;
      if (on) input.checked = true;
    }

    function sync() {
      var locked = admin.checked;
      force(both, locked);
      if (!locked && both.checked) {
        all.read.checked = all.write.checked = true;
      }
      ["read", "write"].forEach(function (column) {
        force(all[column], locked || both.checked);
        boxes[column].forEach(function (box) {
          force(box, locked || all[column].checked);
        });
      });
    }

    matrix.addEventListener("change", function (event) {
      var box = event.target;
      if (box.dataset.matrix === "write" && box.checked) {
        var row = box.closest("tr");
        row.querySelector('[data-matrix="read"]').checked = true;
      }
      if (box === all.write && box.checked) all.read.checked = true;
      sync();
    });
    admin.addEventListener("change", sync);
    matrix.closest("form").addEventListener("submit", function () {
      matrix.querySelectorAll("input").forEach(function (input) {
        input.disabled = false;
      });
    });
    both.checked = all.read.checked && all.write.checked;
    sync();
  }

  return { init: init };
})();

Babubi.RememberAdvancedToggle = function (ptr) {
  localStorage.setItem("advancedForm", event.newState);
};

(function toggleAdvancedFields() {
  window.addEventListener("load", function () {
    if (localStorage.getItem("advancedForm") !== "open") {
      return;
    }

    document.querySelectorAll(".advanced-fields").forEach(function (node) {
      node.open = true;
    });
  });
})();

/**
 * A graph's range selector as one joined button group, for the reports and
 * the dashboard's graph cards alike, in place of Plotly's separate buttons:
 * each button sets the same span back from the graph's last date.
 */
Babubi.GraphRanges = (function () {
  function pad(n) {
    return (n < 10 ? "0" : "") + n;
  }

  function plotlyDate(date) {
    return (
      date.getFullYear() +
      "-" +
      pad(date.getMonth() + 1) +
      "-" +
      pad(date.getDate()) +
      " " +
      pad(date.getHours()) +
      ":" +
      pad(date.getMinutes()) +
      ":" +
      pad(date.getSeconds())
    );
  }

  function lastDate(graph) {
    var end = null;
    graph.data.forEach(function (trace) {
      (trace.x || []).forEach(function (x) {
        var date = new Date(String(x).replace(" ", "T"));
        if (!isNaN(date) && (end === null || date > end)) end = date;
      });
    });
    return end;
  }

  return {
    // The button group for a graph's rangeselector buttons; the caller places
    // it and hides Plotly's own.
    group: function (graph, buttons) {
      var end = lastDate(graph);
      var group = document.createElement("div");
      group.className = "btn-group btn-group-sm graph-ranges";
      group.setAttribute("role", "group");
      buttons.forEach(function (button) {
        var element = document.createElement("button");
        element.type = "button";
        element.className = "btn";
        // The reports leave the full range unlabelled, as Plotly names it itself.
        element.textContent =
          button.label || (button.step === "all" ? "all" : "");
        if (button.step === "all") element.classList.add("active");
        element.addEventListener("click", function () {
          group.querySelectorAll(".btn").forEach(function (other) {
            other.classList.toggle("active", other === element);
          });
          if (button.step === "all" || end === null) {
            Plotly.relayout(graph, { "xaxis.autorange": true });
            return;
          }
          var start = new Date(end);
          var count = button.count || 1;
          if (button.step === "hour") start.setHours(start.getHours() - count);
          else if (button.step === "day")
            start.setDate(start.getDate() - count);
          else if (button.step === "month")
            start.setMonth(start.getMonth() - count);
          else if (button.step === "year")
            start.setFullYear(start.getFullYear() - count);
          Plotly.relayout(graph, {
            "xaxis.range": [plotlyDate(start), plotlyDate(end)],
          });
        });
        group.appendChild(element);
      });
      return group;
    },

    // Replaces the range selector of every graph in a report page, in the
    // same place: centred over the plot, just above it.
    replaceAll: function (container) {
      container.querySelectorAll(".plotly-graph-div").forEach(function (graph) {
        var selector = (graph.layout.xaxis || {}).rangeselector;
        if (!selector || !selector.buttons || !selector.buttons.length) return;
        Plotly.relayout(graph, { "xaxis.rangeselector.visible": false });
        var group = Babubi.GraphRanges.group(graph, selector.buttons);
        group.classList.add("graph-ranges_over");
        graph.style.position = "relative";
        graph.appendChild(group);
        var place = function () {
          var size = graph._fullLayout._size;
          group.style.left = size.l + size.w / 2 + "px";
          group.style.top = Math.max(size.t - group.offsetHeight - 6, 0) + "px";
        };
        place();
        graph.on("plotly_afterplot", place);
      });
    },
  };
})();
