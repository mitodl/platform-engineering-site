/* Interactive C4 architecture diagrams.
 *
 * Diagrams are C4-PlantUML rendered to SVG by Kroki at generation time and
 * written to sibling `_diagrams/*.svg` files. Each page carries a placeholder
 *   <div class="c4-box" data-c4-svg="../_diagrams/<name>.svg"></div>
 * which this script fills with the static SVG (client-side, so it is independent
 * of the static-site generator — works under zensical and mkdocs), then:
 *   - wraps it in a fixed-height, resizable pan/zoom viewport (svg-pan-zoom),
 *   - navigates on a click of a native PlantUML `$link` (drag-guarded).
 *
 * Scoped to /architecture/ pages.
 */
(function () {
  "use strict";

  function onArchPage() {
    return location.pathname.indexOf("/architecture/") !== -1;
  }

  function enhance(box) {
    var svg = box.querySelector("svg");
    if (!svg) return;
    box.classList.add("c4-zoom");

    var hint = document.createElement("div");
    hint.className = "c4-zoom-hint";
    hint.textContent = "drag to pan · scroll to zoom · click a linked box to drill in";
    box.appendChild(hint);

    // Drag guard so a pan doesn't trigger a drill-down on the native <a> links.
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
        preventMouseEventsDefault: false, // let clicks reach the native <a> links
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

  function loadOne(box) {
    if (box.dataset.c4done) return;
    var src = box.getAttribute("data-c4-svg");
    if (!src) return;
    box.dataset.c4done = "1";

    var url;
    try {
      url = new URL(src, location.href);
    } catch (e) {
      box.dataset.c4done = "";
      return;
    }
    // Same-origin only: these are pre-rendered local SVGs; never fetch remote.
    if (url.origin !== location.origin) {
      box.dataset.c4done = "";
      console.error("c4: refusing cross-origin diagram", url.href);
      return;
    }

    fetch(url.href)
      .then(function (r) {
        if (!r.ok) throw new Error("HTTP " + r.status);
        return r.text();
      })
      .then(function (text) {
        // Parse as SVG and adopt only the <svg> root, so a bad URL / HTML error
        // page can't be injected into the DOM. Fail closed otherwise.
        var doc = new DOMParser().parseFromString(text, "image/svg+xml");
        var root = doc.documentElement;
        if (doc.querySelector("parsererror") || !root || root.nodeName.toLowerCase() !== "svg") {
          throw new Error("response is not valid SVG");
        }
        box.replaceChildren(document.importNode(root, true));
        enhance(box);
      })
      .catch(function (e) {
        // Leave dataset.c4done set so the MutationObserver (which fires on this
        // DOM change) does not re-trigger loadOne -> infinite request loop.
        box.textContent = "(diagram failed to load)";
        console.error("c4: failed to load diagram", e);
      });
  }

  function scan() {
    if (!onArchPage()) return;
    document.querySelectorAll(".c4-box[data-c4-svg]").forEach(loadOne);
  }

  function init() {
    if (!onArchPage()) return;
    scan();
    new MutationObserver(scan).observe(document.body, { childList: true, subtree: true });
  }

  init();
  var doc$ = window["document$"];
  if (doc$ && typeof doc$.subscribe === "function") {
    doc$.subscribe(function () {
      setTimeout(init, 0);
    });
  }
})();
