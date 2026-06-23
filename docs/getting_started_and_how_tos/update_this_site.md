# Updating This Site

1. Clone the repo at <https://github.com/mitodl/platform-engineering-site>
2. Run `uv sync` to install dependencies.
3. Make your changes to the Markdown files or add new ones.
4. Run `uv run zensical serve` to preview the site locally (add `-o` to open it
   in your browser). `uv run zensical build` writes the static site to `site/`.

> **Note:** the site is configured through `mkdocs.yml`, which Zensical reads
> directly — there is no separate `zensical.toml`. Per the Zensical team's
> guidance, existing Material for MkDocs projects should keep using `mkdocs.yml`.

## Publishing

**Publishing is automated.** Open a PR, get it reviewed, and merge to `main`.
The Concourse pipeline (`.concourse/pipeline.py`) then builds the site with
`zensical` and pushes it to the `gh-pages` branch, which GitHub Pages serves.
You don't need to deploy by hand.

### Manual deploy (fallback)

If the pipeline is unavailable and you need to publish directly from `main`:

```bash
uv run zensical build
uv run ghp-import --no-jekyll --push --force site
```

Zensical has no `gh-deploy` command of its own, so we build the site and push the
`site/` directory to the `gh-pages` branch with `ghp-import` (the same tool
`mkdocs gh-deploy` used under the hood; it is declared in `pyproject.toml` and
locked via `uv.lock`). `--no-jekyll` writes a `.nojekyll` file so GitHub Pages
serves the underscore-prefixed `_diagrams/` directory used by the architecture
diagrams.

## Updating the C4 architecture diagrams

The MIT Learn architecture pages are **generated**, and their diagrams are
**pre-rendered to SVG and committed**. If you change an architecture model
(`architecture_maps/models/*.yaml`) you must regenerate before committing —
editing the generated Markdown directly will be overwritten. Regeneration needs
a local Kroki server:

```bash
docker compose -f architecture_maps/docker-compose.yml up -d kroki
cd architecture_maps
uv run --group c4gen python -m c4gen render mit-learn   # re-renders pages + _diagrams/*.svg
```

See [`architecture_maps/README.md`](https://github.com/mitodl/platform-engineering-site/tree/main/architecture_maps)
for the full process (including the deterministic witan-code extraction step).
Commit the regenerated Markdown and SVGs along with your model change; the
publish pipeline serves them as-is.
