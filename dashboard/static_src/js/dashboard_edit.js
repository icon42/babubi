/* Babubi Dashboard edit mode
 *
 * Runs the edit mode of a child dashboard without reloading the page. Every
 * operation, a form of the page (hide, show, add or remove a card, reset,
 * a card's own settings, the quick actions) or an arrangement dragged on
 * it, is posted by fetch to the layout view (dashboard/layout_views.py),
 * which redirects to the fresh edit page; the parts that changed are then
 * swapped in while the cards keep their nodes, so an unfolded card stays
 * unfolded, a drawn graph stays drawn and the page stays where it was.
 *
 * Arranging the cards:
 * - on wide screens (lg up) a card drags between the three columns by its
 *   control bar (SortableJS), and the columns are saved;
 * - on narrow ones the cards, collapsed one per row, are a single list in
 *   the order narrow screens show them (--dash-order), dragged by their
 *   handle or moved by their arrows, and that order is saved on its own.
 *   The columns mean nothing there (display: contents), so the cards are
 *   taken out of them while the screen is narrow and put back (data-column,
 *   data-row) when it widens.
 * An editable card, one with settings in edit mode, unfolds on a narrow
 * screen with its toggle. The quick actions list drags by its handles too.
 */
Babubi.DashboardEdit = (function () {
  var root = null;
  var sortables = [];
  var actionSortable = null;
  // The button that posted the pending operation, disabled meanwhile.
  var busy = null;
  // The requests sent so far: a response that arrives after a later request
  // was sent is stale and ignored.
  var sent = 0;
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

  function controlsOf(card) {
    return card.querySelector(":scope > .dash-controls");
  }

  function bodyOf(card) {
    return card.querySelector(":scope > .card-dashboard");
  }

  // The page's edit-mode block below the columns: report picker and hidden
  // cards (dashboard/child.html), there only when it has something.
  function extra(document_) {
    return document_.querySelector(".dash-extra");
  }

  function isLayoutForm(form) {
    var action = form.getAttribute("action");
    if (!action) return false;
    var layoutUrl = new URL(root.dataset.layoutUrl, location.href);
    return new URL(action, location.href).pathname === layoutUrl.pathname;
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
      // The graphs on the page are drawn: their scripts never run again.
      document
        .querySelectorAll(".dash-card[data-dash-static] > .card-dashboard")
        .forEach(Edit.drawn);
      // Before the page's own submit handler (babubi.js), which would
      // disable the button and let the form go.
      document.addEventListener("submit", Edit.onSubmit, true);
      Edit.arrange();
      Edit.sortActions();
      wide.addEventListener("change", Edit.arrange);
    },

    // Sets the cards up for the current width.
    arrange: function () {
      sortables.forEach(function (sortable) {
        sortable.destroy();
      });
      sortables = [];
      Edit.place();
      if (wide.matches) {
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

    // Puts the cards where the current width wants them: in their columns
    // and rows on a wide screen, one list in narrow-screen order otherwise.
    place: function () {
      if (wide.matches) {
        Edit.gather();
      } else {
        Edit.flatten();
      }
    },

    // The cards back into their columns, in their rows.
    gather: function () {
      var where = columns();
      Array.from(root.querySelectorAll(".dash-card"))
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

    // The quick actions list drags into an order; its markup is replaced
    // on every change, so this is set up again after each.
    sortActions: function () {
      if (actionSortable) {
        actionSortable.destroy();
        actionSortable = null;
      }
      var list = root.querySelector(".quick-actions-edit_sortable");
      if (!list) return;
      actionSortable = Sortable.create(list, {
        handle: ".dash-handle",
        animation: 150,
        ghostClass: "dash-ghost",
        onEnd: function () {
          Edit.save(
            "action",
            "order",
            Array.from(list.children).map(function (row) {
              return row.dataset.key;
            }),
          );
        },
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
        card.classList.toggle("dash-card_open");
        Edit.syncToggle(card);
      }
    },

    // The toggle's state from its card's.
    syncToggle: function (card) {
      var toggle = card.querySelector(".dash-toggle");
      if (toggle) {
        toggle.setAttribute(
          "aria-expanded",
          card.classList.contains("dash-card_open") ? "true" : "false",
        );
      }
    },

    // A form of the edit mode goes by fetch, its pressed button included.
    onSubmit: function (event) {
      var form = event.target;
      if (!isLayoutForm(form)) return;
      event.preventDefault();
      event.stopImmediatePropagation();
      var body = new FormData(form);
      var button = event.submitter;
      if (button && button.name) body.append(button.name, button.value);
      if (button) {
        button.disabled = true;
        busy = button;
      }
      Edit.post(body);
    },

    saveOrder: function () {
      Edit.renumber();
      Edit.save("card", "order", cardsIn(root).map(keyOf));
    },

    saveColumns: function () {
      var keys = columns().map(function (column, c) {
        return cardsIn(column).map(function (card, row) {
          card.dataset.column = c;
          card.dataset.row = row;
          return keyOf(card);
        });
      });
      Edit.save("card", "columns", keys);
    },

    // Posts a dragged arrangement.
    save: function (kind, op, keys) {
      var body = new FormData();
      body.append(
        "csrfmiddlewaretoken",
        document.querySelector('input[name="csrfmiddlewaretoken"]').value,
      );
      body.append("kind", kind);
      body.append("op", op);
      body.append("keys", JSON.stringify(keys));
      Edit.post(body);
    },

    // Posts an operation and swaps in what the fresh page changed; if that
    // fails, the page goes back to what is saved.
    post: function (body) {
      var request = ++sent;
      fetch(root.dataset.layoutUrl, {
        method: "POST",
        credentials: "same-origin",
        body: body,
      })
        .then(function (response) {
          if (!response.ok) throw new Error(response.status);
          return response.text();
        })
        .then(function (html) {
          if (request !== sent) return;
          var page = new DOMParser().parseFromString(html, "text/html");
          if (!page.getElementById(root.id)) throw new Error("no dashboard");
          Edit.morph(page);
        })
        .catch(function (error) {
          console.error("Babubi: Saving the dashboard failed.", error);
          location.reload();
        });
    },

    // Brings the page to the fresh one, keeping every card's node: a card
    // gets its fresh attributes and control bar, and its fresh body unless
    // it is a graph (drawn once by its own script) or nothing in it changed;
    // cards that left the page go, cards that arrived come. Then the cards
    // are placed for the width and the block below the columns is replaced,
    // its graphs taken over as drawn.
    morph: function (page) {
      var freshRoot = page.getElementById(root.id);
      var graphs = false;
      var old = {};
      document.querySelectorAll(".dash-card[id]").forEach(function (card) {
        old[card.id] = card;
      });
      var kept = {};
      freshRoot.querySelectorAll(".dash-card[id]").forEach(function (fresh) {
        var card = old[fresh.id];
        var arrived = !card;
        if (arrived && fresh.hasAttribute("data-dash-static")) {
          // The first graph card of the page needs Plotly, which the page
          // only loads when it has one.
          if (typeof Plotly === "undefined") throw new Error("no Plotly");
          graphs = true;
        }
        if (arrived) {
          card = document.importNode(fresh, true);
        } else {
          Edit.update(card, fresh);
        }
        kept[fresh.id] = card;
        root.appendChild(card);
        if (arrived) {
          Edit.revive(card);
          if (graphs) Edit.drawn(bodyOf(card));
        }
      });
      if (graphs) {
        // Drawn by their scripts, compacted for the cards once laid out.
        requestAnimationFrame(Babubi.DashboardGraphs.fit);
      }
      var freshExtra = extra(page);
      if (freshExtra) {
        freshExtra = document.importNode(freshExtra, true);
        freshExtra.querySelectorAll(".dash-card[id]").forEach(function (fresh) {
          var card = old[fresh.id];
          if (
            card &&
            !kept[fresh.id] &&
            card.hasAttribute("data-dash-static")
          ) {
            // The graph, drawn already, moves along.
            bodyOf(fresh).replaceWith(bodyOf(card));
          }
        });
      }
      Object.keys(old).forEach(function (id) {
        if (!kept[id]) old[id].remove();
      });
      var oldExtra = extra(document);
      if (freshExtra && oldExtra) {
        oldExtra.replaceWith(freshExtra);
      } else if (freshExtra) {
        root.insertAdjacentElement("afterend", freshExtra);
      } else if (oldExtra) {
        oldExtra.remove();
      }
      if (freshExtra) Edit.revive(freshExtra);
      Edit.place();
      Edit.sortActions();
      // A button whose form did not change stays, enabled again.
      if (busy && busy.isConnected) busy.disabled = false;
      busy = null;
    },

    // A card's node brought to its fresh markup.
    update: function (card, fresh) {
      var open = card.classList.contains("dash-card_open");
      Array.from(card.attributes).forEach(function (attribute) {
        if (!fresh.hasAttribute(attribute.name)) {
          card.removeAttribute(attribute.name);
        }
      });
      Array.from(fresh.attributes).forEach(function (attribute) {
        card.setAttribute(attribute.name, attribute.value);
      });
      if (open) card.classList.add("dash-card_open");
      var controls = controlsOf(card);
      var freshControls = controlsOf(fresh);
      if (controls && freshControls) {
        controls.replaceWith(document.importNode(freshControls, true));
      } else if (controls) {
        controls.remove();
      } else if (freshControls) {
        card.prepend(document.importNode(freshControls, true));
      }
      Edit.syncToggle(card);
      var body = bodyOf(card);
      var freshBody = bodyOf(fresh);
      if (
        !card.hasAttribute("data-dash-static") &&
        body &&
        freshBody &&
        Edit.content(body) !== Edit.content(freshBody)
      ) {
        // What was unfolded in the old body stays unfolded in the new.
        var unfolded = Array.from(body.querySelectorAll("details")).map(
          function (details) {
            return details.open;
          },
        );
        freshBody.querySelectorAll("details").forEach(function (details, i) {
          if (unfolded[i]) details.open = true;
        });
        body.replaceWith(document.importNode(freshBody, true));
      }
    },

    // An element's markup without its CSRF tokens, which differ on every
    // render, and without the busy state of a pressed button.
    content: function (element) {
      var copy = element.cloneNode(true);
      copy
        .querySelectorAll('input[name="csrfmiddlewaretoken"]')
        .forEach(function (input) {
          input.removeAttribute("value");
        });
      copy.querySelectorAll("button[disabled]").forEach(function (button) {
        button.removeAttribute("disabled");
      });
      return copy.innerHTML;
    },

    // A drawn graph's body, whose script must not run again.
    drawn: function (body) {
      if (body) body.dataset.drawn = "1";
    },

    // Scripts inside imported markup do not run; a graph card's drawing
    // script has to, so once the markup is on the page they are put in
    // again as live scripts. A body taken over as drawn keeps its script
    // as it is.
    revive: function (element) {
      element.querySelectorAll("script").forEach(function (script) {
        if (script.closest("[data-drawn]")) return;
        var live = document.createElement("script");
        Array.from(script.attributes).forEach(function (attribute) {
          live.setAttribute(attribute.name, attribute.value);
        });
        live.textContent = script.textContent;
        script.replaceWith(live);
      });
    },
  };

  return Edit;
})();
