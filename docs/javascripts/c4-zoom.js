/* Self-rendered, interactive C4 diagrams for architecture_maps/c4gen.
 *
 * Each diagram is emitted as:
 *   <div class="c4-diagram">
 *     <script type="text/x-mermaid" class="c4-src">…mermaid source…</script>
 *     <script type="application/json" class="c4-links">{ "Label": "url" }</script>
 *   </div>
 *
 * We render the source with Mermaid ourselves (loaded on demand) instead of
 * relying on Material's built-in Mermaid handling, whose async render is
 * unreliable and hard to hook. After rendering we:
 *   1. drop the SVG into a fixed-height, resizable, pannable viewport,
 *   2. attach svg-pan-zoom (drag to pan, scroll/buttons to zoom),
 *   3. wire C4 drill-down (click a shape -> navigate to its linked page).
 *
 * Scoped to /architecture/ pages. Mermaid is loaded only when a diagram is
 * present, so other pages are unaffected.
 */
(function () {
  "use strict";

  var MERMAID_URL = "https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js";
  var mermaidReady = false;

  function onArchPage() {
    return location.pathname.indexOf("/architecture/") !== -1;
  }

  function loadMermaid(cb) {
    if (window.mermaid) return cb();
    var existing = document.getElementById("c4-mermaid-lib");
    if (existing) return existing.addEventListener("load", cb);
    var s = document.createElement("script");
    s.id = "c4-mermaid-lib";
    s.src = MERMAID_URL;
    s.onload = cb;
    s.onerror = function () {
      console.error("c4: failed to load Mermaid from " + MERMAID_URL);
    };
    document.head.appendChild(s);
  }

  function initMermaid() {
    if (mermaidReady || !window.mermaid) return;
    window.mermaid.initialize({ startOnLoad: false, securityLevel: "loose" });
    mermaidReady = true;
  }

  // --- pan/zoom + drill-down on a rendered SVG -------------------------
  function wireDrillDown(svg, container, links) {
    var labels = Object.keys(links || {});
    if (!labels.length) return;
    var moved = false,
      sx = 0,
      sy = 0;
    container.addEventListener("mousedown", function (e) {
      moved = false;
      sx = e.clientX;
      sy = e.clientY;
    });
    container.addEventListener("mousemove", function (e) {
      if (Math.abs(e.clientX - sx) + Math.abs(e.clientY - sy) > 5) moved = true;
    });
    var texts = svg.querySelectorAll("text, tspan");
    labels.forEach(function (label) {
      var href = links[label];
      for (var i = 0; i < texts.length; i++) {
        if ((texts[i].textContent || "").trim() !== label) continue;
        var shape = texts[i].closest("g");
        if (!shape) continue;
        shape.classList.add("c4-clickable");
        var title = document.createElementNS("http://www.w3.org/2000/svg", "title");
        title.textContent = "Open: " + label;
        shape.appendChild(title);
        shape.addEventListener("click", function (e) {
          if (moved) return;
          e.preventDefault();
          e.stopPropagation();
          window.location.href = href;
        });
        break;
      }
    });
  }

  function enhance(container, svg, links) {
    container.classList.add("c4-zoom");
    var hint = document.createElement("div");
    hint.className = "c4-zoom-hint";
    hint.textContent = "drag to pan · scroll to zoom · click a box to drill in";
    container.appendChild(hint);

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
              /* transiently unsized */
            }
          }).observe(container);
        }
      } catch (e) {
        /* pan/zoom init failed — drill-down still works */
      }
    }
    wireDrillDown(svg, container, links);
  }

  function hashCode(s) {
    var h = 0;
    for (var i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
    return h;
  }

  // The drill-down link map is emitted right after each diagram; find the
  // nearest following script.c4-links before the next diagram.
  function linksForPre(pre) {
    var n = pre.nextElementSibling;
    for (var hops = 0; n && hops < 4; hops++, n = n.nextElementSibling) {
      if (n.matches && n.matches("pre.c4-diagram, .c4-box")) break;
      var s =
        n.matches && n.matches("script.c4-links")
          ? n
          : n.querySelector && n.querySelector("script.c4-links");
      if (s) {
        try {
          return JSON.parse(s.textContent || "{}");
        } catch (e) {
          return {};
        }
      }
    }
    return {};
  }

  function renderOne(pre) {
    if (pre.dataset.c4done || !window.mermaid) return;
    initMermaid();
    pre.dataset.c4done = "1";
    var code = pre.querySelector("code") || pre;
    var src = code.textContent;
    var links = linksForPre(pre);
    var box = document.createElement("div");
    box.className = "c4-box";
    pre.replaceWith(box);
    var id = "c4_" + Math.abs(hashCode(src)).toString(36);
    Promise.resolve(window.mermaid.render(id, src))
      .then(function (out) {
        box.innerHTML = out.svg;
        enhance(box, box.querySelector("svg"), links);
      })
      .catch(function (e) {
        box.textContent = "(C4 diagram failed to render)";
        console.error("c4: Mermaid render failed", e);
      });
  }

  function renderAll() {
    document.querySelectorAll("pre.c4-diagram").forEach(renderOne);
  }

  function init() {
    if (!onArchPage()) return;
    if (!document.querySelector("pre.c4-diagram")) return;
    loadMermaid(function () {
      initMermaid();
      renderAll();
    });
  }

  init();
  var doc$ = window["document$"];
  if (doc$ && typeof doc$.subscribe === "function") {
    doc$.subscribe(function () {
      setTimeout(init, 0);
    });
  }
})();
