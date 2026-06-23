1. Clone the repo at https://github.com/mitodl/platform-engineering-site
2. Run `uv sync` to install dependencies.
3. Make your changes to the Markdown files or add new ones.
4. Run `uv run zensical build` to build the site.
5. Run `uv run zensical serve` to preview the site locally (add `-o` to open it in your browser).
6. When you're happy, deploy to GitHub Pages with:

   ```bash
   uv run zensical build
   uv run ghp-import --no-jekyll --push --force site
   ```

   Zensical has no `gh-deploy` command of its own, so we build the site and push
   the `site/` directory to the `gh-pages` branch with `ghp-import` (the same tool
   `mkdocs gh-deploy` used under the hood; it is declared in `pyproject.toml` and
   locked via `uv.lock`).

> **Note:** the site is configured through `mkdocs.yml`, which Zensical reads
> directly — there is no separate `zensical.toml`. Per the Zensical team's
> guidance, existing Material for MkDocs projects should keep using `mkdocs.yml`.
