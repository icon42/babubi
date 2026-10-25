/* Babubi Dashboard edit mode
 *
 * Arranges the cards of a child dashboard without reloading the page
 * (dashboard/layout_views.py saves what is dragged):
 * - on wide screens (lg up) a card drags between the three columns by its
 *   control bar (SortableJS), and the columns are saved;
 * - on narrow ones the cards, collapsed one per row, are a single list in
 *   the order narrow screens show them (--dash-order), dragged by their
 *   handle or moved by their arrows, and that order is saved on its own.
 *   The columns mean nothing there (display: contents), so the cards are
 *   taken out of them while the screen is narrow and put back (data-column,
 *   data-row) when it widens.
 * An editable card, one with settings in edit mode, unfolds on a narrow
 * screen with its toggle.
 */
Babubi.DashboardEdit = (function () {
  var root = null;
  var sortables = [];
  // Bootstrap's lg breakpoint, where the columns stand side by side.
  var wide = window.matchMedia("(min-width: 992px)");

  function keyOf(card) {
    return card.id.replace(/^dashboard-/, "");
  }

  function cardsIn(element) {
    return Array.from(element.children).filter(function (child) {
      return child.classList.contains("dash-card");
    });
  }

  function columns() {
    return Array.from(root.querySelectorAll(".dash-column"));
  }

  function position(card) {
    return parseInt(card.style.getPropertyValue("--dash-order"), 10) || 0;
  }

  var Edit = {
    init: function (element_id) {
      root = document.getElementById(element_id);
      if (!root || typeof Sortable === "undefined") {
        console.error(
          "Babubi: Dashboard edit mode needs its element and Sortable.",
        );
        return false;
      }
      root.addEventListener("click", Edit.onClick);
      Edit.arrange();
      wide.addEventListener("change", Edit.arrange);
    },

    // Sets the cards up for the current width.
    arrange: function () {
      sortables.forEach(function (sortable) {
        sortable.destroy();
      });
      sortables = [];
      if (wide.matches) {
        Edit.gather();
        columns().forEach(function (column) {
          sortables.push(
            Sortable.create(column, {
              group: "dash",
              handle: ".dash-controls",
              animation: 150,
              ghostClass: "dash-ghost",
              onEnd: Edit.saveColumns,
            }),
          );
        });
      } else {
        Edit.flatten();
        sortables.push(
          Sortable.create(root, {
            draggable: ".dash-card",
            handle: ".dash-handle",
            animation: 150,
            ghostClass: "dash-ghost",
            onEnd: Edit.saveOrder,
          }),
        );
      }
    },

    // The cards back into their columns, in their rows.
    gather: function () {
      var where = columns();
      cardsIn(root)
        .sort(function (a, b) {
          return a.dataset.row - b.dataset.row;
        })
        .forEach(function (card) {
          where[card.dataset.column].appendChild(card);
        });
    },

    // The cards out of their columns, as one list in narrow-screen order.
    flatten: function () {
      Array.from(root.querySelectorAll(".dash-card"))
        .sort(function (a, b) {
          return position(a) - position(b);
        })
        .forEach(function (card) {
          root.appendChild(card);
        });
      Edit.renumber();
    },

    // Each card's narrow-screen position and arrows, from the list.
    renumber: function () {
      var cards = cardsIn(root);
      cards.forEach(function (card, i) {
        card.style.setProperty("--dash-order", i);
        card.querySelector('[data-move="up"]').disabled = i === 0;
        card.querySelector('[data-move="down"]').disabled =
          i === cards.length - 1;
      });
    },

    onClick: function (event) {
      var button = event.target.closest("[data-move], .dash-toggle");
      if (!button || !root.contains(button)) return;
      var card = button.closest(".dash-card");
      if (button.dataset.move) {
        var up = button.dataset.move === "up";
        var sibling = up
          ? card.previousElementSibling
          : card.nextElementSibling;
        if (!sibling || !sibling.classList.contains("dash-card")) return;
        root.insertBefore(up ? card : sibling, up ? sibling : card);
        Edit.saveOrder();
      } else {
        var open = card.classList.toggle("dash-card_open");
        button.setAttribute("aria-expanded", open ? "true" : "false");
      }
    },

    saveOrder: function () {
      Edit.renumber();
      Edit.save("order", cardsIn(root).map(keyOf));
    },

    saveColumns: function () {
      var keys = columns().map(function (column, c) {
        return cardsIn(column).map(function (card, row) {
          card.dataset.column = c;
          card.dataset.row = row;
          return keyOf(card);
        });
      });
      Edit.save("columns", keys);
    },

    // Posts an arrangement; if that fails, the page goes back to what is
    // saved.
    save: function (op, keys) {
      var body = new URLSearchParams({
        csrfmiddlewaretoken: document.querySelector(
          'input[name="csrfmiddlewaretoken"]',
        ).value,
        kind: "card",
        op: op,
        keys: JSON.stringify(keys),
      });
      fetch(root.dataset.layoutUrl, {
        method: "POST",
        credentials: "same-origin",
        headers: { Accept: "application/json" },
        body: body,
      })
        .then(function (response) {
          if (!response.ok) throw new Error(response.status);
        })
        .catch(function (error) {
          console.error(
            "Babubi: Saving the dashboard arrangement failed.",
            error,
          );
          location.reload();
        });
    },
  };

  return Edit;
})();
