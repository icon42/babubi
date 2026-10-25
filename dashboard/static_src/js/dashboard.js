/* Babubi Dashboard
 *
 * Keeps an open child dashboard current without reloading it:
 * - at the user's refresh rate and when the page gets focus, it asks the
 *   server for the version of the child's data (a counter bumped by any
 *   change, dashboard/versions.py) and only when it changed, or the day did,
 *   fetches the page again and swaps the cards whose content changed;
 * - every half minute it rewrites the "… ago" times from their timestamps,
 *   with no request at all.
 * Graph cards are left as drawn; a different arrangement of cards, e.g.
 * edited in another window, reloads the whole page.
 * On tablets (sm up to lg) it also deals the cards into two columns, see
 * deal().
 */
Babubi.Dashboard = (function () {
  var dashboardElement = null;
  var words = null;
  // Bootstrap's sm and lg breakpoints: two cards abreast in between.
  var tablet = window.matchMedia(
    "(min-width: 576px) and (max-width: 991.98px)",
  );

  var Dashboard = {
    watch: function (element_id, refresh_rate) {
      dashboardElement = document.getElementById(element_id);
      if (!dashboardElement) {
        console.error("Babubi: Dashboard element not found.");
        return false;
      }
      var wordsElement = document.getElementById("dashboard-time-words");
      words = wordsElement ? JSON.parse(wordsElement.textContent) : null;

      Dashboard.deal();
      tablet.addEventListener("change", Dashboard.deal);

      Dashboard.tick();
      setInterval(Dashboard.tick, 30000);

      window.addEventListener("focus", Dashboard.check, false);
      if (refresh_rate) {
        setInterval(function () {
          if (!document.hidden) Dashboard.check();
        }, refresh_rate);
      }
    },

    // Between sm and lg the cards would go two abreast in rows, and rows of
    // unequal heights leave holes. So there the cards are dealt into the
    // first two columns by their narrow-screen order (--dash-order), odd
    // ones left and even ones right, as the wide screen deals its three
    // (dash-columns_dealt); outside that range they go back where the
    // server put them, which each card remembers as data-home.
    deal: function () {
      var columns = Array.from(
        dashboardElement.querySelectorAll(".dash-column"),
      );
      var cards = Array.from(dashboardElement.querySelectorAll(".dash-card"));
      cards.forEach(function (card) {
        if (!card.dataset.home) {
          var column = columns.indexOf(card.parentElement);
          var row = Array.from(card.parentElement.children).indexOf(card);
          card.dataset.home = column + ":" + row;
        }
      });
      var home = function (card, part) {
        return parseInt(card.dataset.home.split(":")[part], 10);
      };
      if (tablet.matches) {
        cards
          .sort(function (a, b) {
            return Dashboard.position(a) - Dashboard.position(b);
          })
          .forEach(function (card, i) {
            columns[i % 2].appendChild(card);
          });
      } else {
        cards
          .sort(function (a, b) {
            return home(a, 1) - home(b, 1);
          })
          .forEach(function (card) {
            columns[home(card, 0)].appendChild(card);
          });
      }
      dashboardElement.classList.toggle("dash-columns_dealt", tablet.matches);
    },

    position: function (card) {
      return parseInt(card.style.getPropertyValue("--dash-order"), 10) || 0;
    },

    today: function () {
      var now = new Date();
      var pad = function (n) {
        return (n < 10 ? "0" : "") + n;
      };
      return (
        now.getFullYear() +
        "-" +
        pad(now.getMonth() + 1) +
        "-" +
        pad(now.getDate())
      );
    },

    check: function () {
      var url = dashboardElement.dataset.versionUrl;
      if (!url) return;
      fetch(url, { credentials: "same-origin" })
        .then(function (response) {
          if (!response.ok) throw new Error(response.status);
          return response.json();
        })
        .then(function (data) {
          if (
            data.version !== dashboardElement.dataset.version ||
            Dashboard.today() !== dashboardElement.dataset.day
          ) {
            Dashboard.update();
          }
        })
        .catch(function (error) {
          console.error("Babubi: Dashboard version check failed.", error);
        });
    },

    // Fetches the page again (with "refresh" set, so the server skips the
    // graph cards) and swaps only the cards whose content changed.
    update: function () {
      var url = new URL(window.location.href);
      url.searchParams.set("refresh", "1");
      fetch(url, { credentials: "same-origin" })
        .then(function (response) {
          if (!response.ok) throw new Error(response.status);
          return response.text();
        })
        .then(function (html) {
          var page = new DOMParser().parseFromString(html, "text/html");
          var fresh = page.getElementById(dashboardElement.id);
          if (
            !fresh ||
            Dashboard.cardIds(fresh) !== Dashboard.cardIds(dashboardElement)
          ) {
            location.reload();
            return;
          }
          fresh.querySelectorAll(".dash-card[id]").forEach(function (card) {
            if (card.hasAttribute("data-dash-static")) return;
            var old = document.getElementById(card.id);
            if (Dashboard.content(old) !== Dashboard.content(card)) {
              old.innerHTML = card.innerHTML;
            }
          });
          dashboardElement.dataset.version = fresh.dataset.version;
          dashboardElement.dataset.day = fresh.dataset.day;
          Dashboard.tick();
        })
        .catch(function (error) {
          console.error("Babubi: Dashboard update failed.", error);
        });
    },

    // The cards on the page, whatever their order: deal() moves them about.
    cardIds: function (element) {
      return Array.from(element.querySelectorAll(".dash-card[id]"))
        .map(function (card) {
          return card.id;
        })
        .sort()
        .join(" ");
    },

    // A card's markup without its CSRF tokens, which differ on every render.
    content: function (card) {
      var copy = card.cloneNode(true);
      copy
        .querySelectorAll('input[name="csrfmiddlewaretoken"]')
        .forEach(function (input) {
          input.removeAttribute("value");
        });
      return copy.innerHTML;
    },

    // "4 hours, 10 minutes ago" from a timestamp, in the page's language:
    // the words come from the server (dashboard/child.html).
    ago: function (since) {
      var minutes = Math.floor((Date.now() - since.getTime()) / 60000);
      if (!words || isNaN(minutes) || minutes < 0) return null;
      var hours = Math.floor(minutes / 60);
      var plural = function (forms, n) {
        return (n === 1 ? forms[0] : forms[1]).replace("%(n)s", n);
      };
      var text = plural(words.minute, minutes % 60);
      if (hours > 0) text = plural(words.hour, hours) + ", " + text;
      return words.ago.replace("%(time_ago)s", text);
    },

    tick: function () {
      dashboardElement
        .querySelectorAll("[data-since]")
        .forEach(function (element) {
          var text = Dashboard.ago(new Date(element.dataset.since));
          if (text !== null) element.textContent = text;
        });
    },
  };

  return Dashboard;
})();
