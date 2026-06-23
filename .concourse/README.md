# Concourse pipeline

`pipeline.py` defines the publishing pipeline using the **ol-concourse** Python
DSL (the same DSL used in `ol-infrastructure`). It builds the docs with
`zensical` and pushes the result to the `gh-pages` branch on every push to
`main`.

## Generate and set

```bash
# ol-concourse provides the DSL; run from the repo root
uv run --with ol-concourse python .concourse/pipeline.py   # writes definition.json
fly -t <target> set-pipeline -p platform-engineering-site -c definition.json
```

`definition.json` is a generated artifact (git-ignored).

## Required credential

`((platform_engineering_site.deploy_key))` — a GitHub **deploy key with write
access**, used to clone `main` and push `gh-pages`. Provide it through the team's
credential manager (Vault).

## Notes

- The C4 architecture diagrams are **pre-rendered to SVG and committed** (under
  `docs/application_specific_guides/*/architecture/_diagrams/`). This pipeline
  does not re-render them — that needs the witan-code graph + a Kroki server,
  which live in the authoring environment (see `architecture_maps/README.md`).
- `ghp-import --no-jekyll` writes `.nojekyll` so GitHub Pages serves the
  underscore-prefixed `_diagrams/` directory.
