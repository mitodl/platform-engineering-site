# platform-engineering-site
The MIT Online Learning Platform Engineering Site Repository

Here are [instructions](https://engineering.ol.mit.edu/getting_started_and_how_tos/update_this_site/) on how to update this site.

Built with [Zensical](https://zensical.org/) (the successor to Material for
MkDocs). The site is still configured through `mkdocs.yml`, which Zensical reads
directly.

## Development

Code checks run with [prek](https://prek.j178.dev/), which reads `.pre-commit-config.yaml`. The `prek` check runs the same hooks on every pull request. When the hooks' own fixes make every hook pass, [autofix.ci](https://autofix.ci/) pushes them to the pull request as one commit. It refuses fixes to files under `.github/`, so fix those locally.

```bash
uv sync                     # installs prek from uv.lock
uv run prek install -f      # replaces a pre-commit git hook, if one is installed
uv run prek run --all-files
```
