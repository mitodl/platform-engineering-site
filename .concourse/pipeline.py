"""Concourse pipeline (ol-concourse DSL) for the Platform Engineering docs site.

Builds the site with zensical and publishes it to GitHub Pages (gh-pages) on
every push to ``main`` — automating the previously-manual flow documented in
``docs/getting_started_and_how_tos/update_this_site.md``:

    uv run zensical build
    uv run ghp-import --no-jekyll --push --force site

The C4 architecture diagrams are pre-rendered to SVG (committed under
``docs/application_specific_guides/*/architecture/_diagrams/``) by ``c4gen``
against a Kroki server — see ``architecture_maps/README.md``. They are NOT
re-rendered here: regeneration needs the witan-code graph (authoring environment
only), so this pipeline builds and deploys the committed site as-is.

Generate and set the pipeline (ol-concourse provides the DSL):

    uv run --with ol-concourse python .concourse/pipeline.py
    fly -t <target> set-pipeline -p platform-engineering-site -c definition.json

``((platform_engineering_site.deploy_key))`` is a GitHub deploy key with WRITE
access (used both to clone ``main`` and to push ``gh-pages``); provide it via the
team's credential manager (Vault).
"""

from ol_concourse.lib.constants import REGISTRY_IMAGE
from ol_concourse.lib.models.pipeline import (
    AnonymousResource,
    Command,
    GetStep,
    Identifier,
    Input,
    Job,
    Pipeline,
    Platform,
    RegistryImage,
    TaskConfig,
    TaskStep,
)
from ol_concourse.lib.resources import ssh_git_repo

REPO_URI = "git@github.com:mitodl/platform-engineering-site.git"
DEPLOY_KEY = "((platform_engineering_site.deploy_key))"

DEPLOY_SCRIPT = """
apt-get update -qq
apt-get install -y -qq --no-install-recommends git openssh-client ca-certificates >/dev/null

# SSH key so ghp-import can push the built site to gh-pages.
install -m 700 -d ~/.ssh
printf '%s\\n' "$DEPLOY_KEY" > ~/.ssh/id_deploy
chmod 600 ~/.ssh/id_deploy
ssh-keyscan -t rsa,ed25519 github.com >> ~/.ssh/known_hosts 2>/dev/null
export GIT_SSH_COMMAND="ssh -i ~/.ssh/id_deploy -o IdentitiesOnly=yes"

cd site-repo
git config user.name "$GIT_USER_NAME"
git config user.email "$GIT_USER_EMAIL"
git remote set-url origin "$REPO_URI"

# Build the static site (zensical reads mkdocs.yml).
uv sync --frozen
uv run zensical build

# Publish to gh-pages. --no-jekyll writes .nojekyll so GitHub Pages serves the
# underscore-prefixed _diagrams/ SVG directory.
uv run ghp-import --no-jekyll --push --force --branch gh-pages site
"""

site_repo = ssh_git_repo(
    name=Identifier("site-repo"),
    uri=REPO_URI,
    private_key=DEPLOY_KEY,
    branch="main",
)


def site_pipeline() -> Pipeline:
    build_and_publish = Job(
        name=Identifier("build-and-publish"),
        serial=True,
        plan=[
            GetStep(get=site_repo.name, trigger=True),
            TaskStep(
                task=Identifier("build-and-deploy"),
                config=TaskConfig(
                    platform=Platform.linux,
                    image_resource=AnonymousResource(
                        type=REGISTRY_IMAGE,
                        source=RegistryImage(
                            repository="ghcr.io/astral-sh/uv",
                            tag="python3.12-bookworm-slim",
                        ),
                    ),
                    inputs=[Input(name=site_repo.name)],
                    params={
                        "DEPLOY_KEY": DEPLOY_KEY,
                        "REPO_URI": REPO_URI,
                        "GIT_USER_NAME": "odlbot",
                        "GIT_USER_EMAIL": "odlbot@mit.edu",
                    },
                    run=Command(path="bash", args=["-ec", DEPLOY_SCRIPT]),
                ),
            ),
        ],
    )
    return Pipeline(resources=[site_repo], jobs=[build_and_publish])


if __name__ == "__main__":
    import sys
    from pathlib import Path

    definition = site_pipeline().model_dump_json(indent=2, exclude_none=True)
    Path("definition.json").write_text(definition)
    sys.stdout.write(definition)
    sys.stdout.write(
        "\n\nfly -t <target> set-pipeline -p platform-engineering-site -c definition.json\n"
    )
