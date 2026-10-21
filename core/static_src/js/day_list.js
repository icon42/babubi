/* Babubi day lists
 *
 * Keeps each note of an activity list (core/templates/core/day_list.html) in
 * its column while it fits on one line, and otherwise marks the row so the
 * note shows in full on the row below. Measured again when the width changes.
 */
(function () {
  var rowClass = "day-item_note-below";

  function place() {
    var rows = document.querySelectorAll(".day-item[data-note]");
    rows.forEach(function (row) {
      row.classList.remove(rowClass);
    });
    var overflowing = Array.prototype.filter.call(rows, function (row) {
      var text = row.querySelector(".day-note-text");
      return text && text.scrollWidth > text.clientWidth;
    });
    overflowing.forEach(function (row) {
      row.classList.add(rowClass);
    });
  }

  var pending = null;
  function schedule() {
    if (pending) {
      window.cancelAnimationFrame(pending);
    }
    pending = window.requestAnimationFrame(place);
  }

  document.addEventListener("DOMContentLoaded", place);
  window.addEventListener("resize", schedule);
})();
