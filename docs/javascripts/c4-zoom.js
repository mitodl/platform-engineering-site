/* Pan/zoom for the generated C4 architecture diagrams (architecture_maps/c4gen).
 *
 * Material renders Mermaid to inline SVG that is fit to the content column, so
 * larger diagrams become cramped and the relationship labels tiny. This wraps
 * each diagram in a fixed-height, resizable viewport (see c4.css) and attaches
 * svg-pan-zoom so it can be zoomed and panned.
 *
 * Scope: only diagrams on `/architecture/` pages are enhanced, so other Mermaid
 * diagrams across the site are left exactly as they were. Relies on svg-pan-zoom
 * being loaded first (see extra_javascript order in mkdocs.yml).
 */
(function () {
  function onArchPage() {
    return location.pathname.indexOf("/architecture/") !== -1;
  }

  function enhance(container) {
    if (container.dataset.c4zoom) return;
    if (typeof window.svgPanZoom !== "function") return; // library not ready yet
    var svg = container.querySelector("svg");
    if (!svg) return; // Mermaid hasn't finished rendering this one

    container.dataset.c4zoom = "1";
    container.classList.add("c4-zoom");

    var hint = document.createElement("div");
    hint.className = "c4-zoom-hint";
    hint.textContent = "scroll to zoom · drag to pan";
    container.appendChild(hint);

    var pz = window.svgPanZoom(svg, {
      zoomEnabled: true,
      controlIconsEnabled: true,
      fit: true,
      center: true,
      minZoom: 0.2,
      maxZoom: 20,
      zoomScaleSensitivity: 0.4,
    });

    // Keep the diagram fitted when the user drags the viewport taller/shorter.
    if (window.ResizeObserver) {
      new ResizeObserver(function () {
        pz.resize();
        pz.fit();
        pz.center();
      }).observe(container);
    }
  }

  function scan() {
    if (!onArchPage()) return;
    document.querySelectorAll(".mermaid").forEach(enhance);
  }

  function schedule() {
    // Mermaid renders asynchronously and the pan-zoom lib loads async too, so
    // poll briefly until both are ready. enhance() is idempotent.
    var tries = 0;
    var timer = setInterval(function () {
      scan();
      if (++tries > 40) clearInterval(timer); // ~10s ceiling
    }, 250);
  }

  // Material's instant navigation re-renders content per page; document$ emits
  // on each load. Fall back to a plain load listener if it isn't present.
  var doc$ = window["document$"]; // Material instant-navigation observable
  if (doc$ && typeof doc$.subscribe === "function") {
    doc$.subscribe(schedule);
  } else {
    window.addEventListener("load", schedule);
  }
})();
