/* Interaction layer for the generated C4 architecture diagrams
 * (architecture_maps/c4gen). Material renders Mermaid to inline SVG fit to the
 * content column; this:
 *   1. puts each diagram in a fixed-height, resizable, scrollable viewport,
 *   2. attaches svg-pan-zoom (drag to pan, scroll/buttons to zoom),
 *   3. wires C4 "drill-down": clicking a shape navigates to a linked page,
 *      using a JSON map emitted next to the diagram (Mermaid C4 has no native
 *      click syntax).
 *
 * Scoped to /architecture/ pages so other Mermaid diagrams are untouched.
 * Robust to Mermaid's async render via a MutationObserver, and runs immediately
 * (not only on load) so it works regardless of script ordering.
 */
(function () {
  "use strict";

  function onArchPage() {
    return location.pathname.indexOf("/architecture/") !== -1;
  }

  // Pair each .mermaid with the JSON link map emitted right after it.
  function linksFor(index) {
    var scripts = document.querySelectorAll("script.c4-links");
    if (!scripts[index]) return {};
    try {
      return JSON.parse(scripts[index].textContent || "{}");
    } catch (e) {
      return {};
    }
  }

  function wireDrillDown(svg, container, links) {
    var labels = Object.keys(links);
    if (!labels.length) return;

    // Track drag so a pan doesn't count as a click.
    var moved = false;
    var sx = 0;
    var sy = 0;
    container.addEventListener("mousedown", function (e) {
      moved = false;
      sx = e.clientX;
      sy = e.clientY;
    });
    container.addEventListener("mousemove", function (e) {
      if (Math.abs(e.clientX - sx) + Math.abs(e.clientY - sy) > 5) moved = true;
    });

    var texts = svg.querySelectorAll("text, .nodeLabel, tspan");
    labels.forEach(function (label) {
      var href = links[label];
      for (var i = 0; i < texts.length; i++) {
        if ((texts[i].textContent || "").trim() !== label) continue;
        // Climb to the shape group (the <g> that holds the rect + texts).
        var shape = texts[i].closest("g");
        if (!shape) continue;
        shape.classList.add("c4-clickable");
        var title = document.createElementNS("http://www.w3.org/2000/svg", "title");
        title.textContent = "Open: " + label;
        shape.appendChild(title);
        shape.addEventListener("click", function (e) {
          if (moved) return; // was a pan, not a click
          e.preventDefault();
          e.stopPropagation();
          window.location.href = href;
        });
        break;
      }
    });
  }

  function enhance(container, index) {
    if (container.dataset.c4zoom) return;
    var svg = container.querySelector("svg");
    if (!svg) return; // Mermaid hasn't rendered this one yet
    container.dataset.c4zoom = "1";
    container.classList.add("c4-zoom");

    var hint = document.createElement("div");
    hint.className = "c4-zoom-hint";
    hint.textContent = "drag to pan · scroll to zoom · click a box to drill in";
    container.appendChild(hint);

    var links = linksFor(index);
    if (typeof window.svgPanZoom === "function") {
      try {
        var pz = window.svgPanZoom(svg, {
          zoomEnabled: true,
          controlIconsEnabled: true,
          fit: true,
          center: true,
          minZoom: 0.2,
          maxZoom: 20,
          zoomScaleSensitivity: 0.4,
        });
        if (window.ResizeObserver) {
          new ResizeObserver(function () {
            try {
              pz.resize();
              pz.fit();
              pz.center();
            } catch (e) {
              /* container transiently unsized — ignore */
            }
          }).observe(container);
        }
      } catch (e) {
        /* pan/zoom failed to init — drill-down below still works */
      }
    }
    // Drill-down works with or without the pan/zoom library present.
    wireDrillDown(svg, container, links);
  }

  function scan() {
    if (!onArchPage()) return;
    document.querySelectorAll(".mermaid").forEach(enhance);
  }

  function init() {
    if (!onArchPage()) return;
    scan();
    // Mermaid injects the <svg> asynchronously; catch it whenever it appears.
    var root = document.querySelector(".md-content") || document.body;
    var obs = new MutationObserver(function () {
      scan();
    });
    obs.observe(root, { childList: true, subtree: true });
  }

  // Run now (script is at end of body) and again on Material instant-nav.
  init();
  var doc$ = window["document$"];
  if (doc$ && typeof doc$.subscribe === "function") {
    doc$.subscribe(function () {
      setTimeout(init, 0);
    });
  }
})();
