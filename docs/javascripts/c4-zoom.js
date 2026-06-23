/* Pan/zoom for the C4 architecture diagrams.
 *
 * The diagrams are C4-PlantUML rendered to SVG by Kroki at build time and
 * inlined into the page (see hooks/c4_inline.py) inside a `.c4-box`. This wraps
 * each in a fixed-height, resizable viewport with svg-pan-zoom. Drill-down is
 * native (PlantUML `$link` -> a real <a> in the SVG), so no click handling here.
 *
 * Scoped to /architecture/ pages.
 */
(function () {
  "use strict";

  function onArchPage() {
    return location.pathname.indexOf("/architecture/") !== -1;
  }

  function enhance(box) {
    if (box.dataset.c4done) return;
    var svg = box.querySelector("svg");
    if (!svg) return;
    box.dataset.c4done = "1";
    box.classList.add("c4-zoom");

    var hint = document.createElement("div");
    hint.className = "c4-zoom-hint";
    hint.textContent = "drag to pan · scroll to zoom · click a linked box to drill in";
    box.appendChild(hint);

    // svg-pan-zoom preventDefaults mouse events, which blocks the native <a>
    // links PlantUML emits ($link). Re-implement the click: navigate when a
    // link is clicked without a drag (so panning doesn't trigger navigation).
    var moved = false,
      sx = 0,
      sy = 0;
    box.addEventListener("mousedown", function (e) {
      moved = false;
      sx = e.clientX;
      sy = e.clientY;
    });
    box.addEventListener("mousemove", function (e) {
      if (Math.abs(e.clientX - sx) + Math.abs(e.clientY - sy) > 5) moved = true;
    });
    box.addEventListener(
      "click",
      function (e) {
        if (!e.target.closest) return;
        var a = e.target.closest("a");
        if (!a) return;
        e.preventDefault();
        e.stopPropagation();
        if (moved) return; // ended a pan over a link — don't navigate
        var href = a.getAttribute("xlink:href") || a.getAttribute("href");
        if (href) window.location.href = new URL(href, location.href).href;
      },
      true,
    );

    if (typeof window.svgPanZoom !== "function") return;
    try {
      var pz = window.svgPanZoom(svg, {
        zoomEnabled: true,
        controlIconsEnabled: true,
        fit: true,
        center: true,
        minZoom: 0.2,
        maxZoom: 20,
        zoomScaleSensitivity: 0.4,
        // Let click events reach the SVG's native <a> links (drill-down).
        preventMouseEventsDefault: false,
      });
      if (window.ResizeObserver) {
        new ResizeObserver(function () {
          try {
            pz.resize();
            pz.fit();
            pz.center();
          } catch (e) {
            /* transiently unsized */
          }
        }).observe(box);
      }
    } catch (e) {
      /* pan/zoom init failed — the static diagram still shows */
    }
  }

  function scan() {
    if (!onArchPage()) return;
    document.querySelectorAll(".c4-box").forEach(enhance);
  }

  function init() {
    if (!onArchPage()) return;
    scan();
    var root = document.querySelector(".md-content") || document.body;
    new MutationObserver(scan).observe(root, { childList: true, subtree: true });
  }

  init();
  var doc$ = window["document$"];
  if (doc$ && typeof doc$.subscribe === "function") {
    doc$.subscribe(function () {
      setTimeout(init, 0);
    });
  }
})();
