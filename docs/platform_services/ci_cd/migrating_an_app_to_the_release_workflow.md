# Migrating an App to the Release Workflow

Moving an app off the legacy release-candidate/release pipeline and onto the
[modernized release workflow](release_workflow_machinery.md) is a one-field change
in `src/bridge/settings/apps.py`, but the field is only safe to flip once the
app's repo is ready for it. This is the per-app checklist, the verification, and
the failures that have actually happened. What the app's engineers get on the
other side is described in
[Concourse Release Workflow](../../handbook/delivering/release-process/concourse-release-workflow.md).

## Preconditions

- The App is installed. `ol-release-bot` must be installed on the app's
  repo. A missing installation fails at authentication and looks nothing like a
  ruleset denial. The installation is `repository_selection: selected`, so check
  the org installation settings page, or read the installation id from
  `gh api /orgs/mitodl/installations` and call
  `/app/installations/<id>/repositories` with an App JWT.
- The ruleset bypass covers the repo. Read `gh api /orgs/mitodl/rulesets`,
  then GET each id (the list response omits `bypass_actors`). The App id is
  4437866, and it needs mode `always` on every ruleset governing a default-branch
  push, including repo-level rulesets that add required status checks. Rulesets
  scoped to `refs/heads/release` and `refs/heads/release-candidate` are the
  legacy branch names and cannot match `releases/<version>`, so they need no
  bypass.
- Version bumping works. The app needs a `[tool.bumpversion]` config and a
  version file the release resource can bump. A repo with no `current_version`
  key is handled (the task seeds it), but only on ol-concourse 0.18.1 or later.
- The Pulumi project exists at
  `src/ol_infrastructure/applications/<app_with_underscores>` with CI, QA and
  Production stacks, since the generated jobs assume that path.
- The Docker Hub repo `mitodl/<app>-app` exists. The ECR repository does not need
  creating: both build jobs create it idempotently.
- No stale release refs. A leftover `releases/<version>` branch, usually from an
  earlier experiment, reads as an in-flight release and the first cut will
  supersede it. Check with `git ls-remote --heads origin 'releases/*'` and delete
  what you find before flipping.
- A non-`main` default branch, or a repo name that differs from the app name,
  is handled by the registry (`repo_main_branch`, `github_repo`), but check the
  entry is right before flipping.
- Fastly purge config and Sentry sourcemap upload survive the port if the app
  has them.

## The flip

Set `release_resource_workflow=True` on the app's `AppRegistration` in
`src/bridge/settings/apps.py` and merge.

That file is on the trigger paths of both control surfaces, so merging:

1. fires `create-<app>-pipeline` in the `k8s-apps-meta` pipeline, which
   regenerates the app's pipeline in the new shape, and
2. rebuilds the release bot image with the new `REPOS_CONFIG`, which is what
   makes the bot stop refusing commands for the app.

The bot's deploy is preview-gated: `deploy-ol-infrastructure-release-bot-default`
only runs after someone closes its gate issue in the Concourse workflow issue
repo (see the
[Concourse GitHub Issues User Guide](concourse_github_issues_user_guide.md)).
Until that issue is closed
the running pod still has the old config and refuses every release command,
including for apps that are already migrated.

## Verifying the flip

```bash
# The pipeline regenerated in the new shape (zero means it did not).
fly -t <your-target> get-pipeline -p <app>-pipeline | grep -c NEEDS_SEED

# The bot picked up the app.
kubectl -n operations get deploy release-bot-production \
  -o jsonpath='{.spec.template.spec.containers[0].env}' | jq
```

A `NEEDS_SEED` count of zero on an app that is _not_ yet migrated says nothing:
the legacy pipeline has no `bump-version` task at all. It only discriminates for
an app already on the new workflow.

Then run the real end-to-end test, which is a release:

1. `/doof preview <app>` to confirm the version and the commit list look right.
2. `/doof release <app>`, and watch `build-<app>-release-image`.
3. Check the release issue appears with a per-author checklist, and that the RC
   GitHub Deployment is recorded.
4. Promote, and confirm that the production deploy runs, the Production
   Deployment is recorded, `releases/<version>` is merged back and deleted, and
   the default branch's `current_version` advanced.

## After the flip

- Remove the app from Doof's `repos_info.json` in `mitodl/release-script`, and
  merge that _after_ the ol-infrastructure change, not before.
- Confirm the bot is in the app's Slack channel. Private channels need an
  invite, and a channel name is resolved through `conversations.list`, which
  needs `groups:read` on the bot token.
- Retire the app's `release-candidate` and `release` branches, and anything keyed
  on them.
- The ruleset bypass is granted to every registered app repo, not only the ones
  on the new workflow, so that flipping a pipeline never requires a privileged
  GitHub operation at the same moment. That over-grant is deliberate, and is
  meant to be narrowed once every app is on the workflow.

## Troubleshooting

`GH013: Repository rule violations found` on `action: finish`. The App is not
a bypass actor on one of the rulesets governing that branch. Every ruleset has
its own bypass list, so being registered on one grants nothing on the others.
It is how a release ends up shipped to production with its branch stranded,
needing a hand-merged PR to clear.

A release reuses the previous version and commit list. The `<app>-release`
resource is `check_every: never`. The job bound the last recorded version because
the resource was not checked before the trigger. Force a check on the resource
and re-trigger.

The bump-version task fails, or silently does nothing. Repos with no
`[tool.bumpversion] current_version` key crashed the transition script before
ol-concourse 0.18.1. Generated pipelines only carry the fix after the
`mitodl/ol-infrastructure` image is rebuilt and the pipeline regenerated, because
the task code comes from the image, not from the checkout.

A `/doof` command 404s in Concourse. Either the app is still on the legacy
pipeline (the bot should refuse before it gets that far, so check the bot
actually redeployed), or the call went to the wrong Concourse team. The bot runs
everything under `infrastructure`; the image builds and library publish pipelines
are in `main`.

A release is cut but never finishes. The release branch stays on the remote
and the bot nags after 24h. Look at the production deploy job: `action: finish`
is deliberately not wrapped in a `try`, so a failure there is a red build with a
real cause. Merging the branch by hand clears the block, and the next `check`
advances normally.

A superseded release lost its tag. Expected when that release never reached
production. A release that _did_ reach production keeps its tag, decided by
asking the GitHub Deployments API. If the answer cannot be established, the tag
is kept: an extra tag is recoverable, a deleted one is not.
