# Change Management Policy

## Purpose

Make sure every change to production systems is reviewed, tested, traceable
and reversible, so changes don't cause avoidable outages or security
regressions.

## Scope

Any change to code, configuration or infrastructure that runs in, deploys to,
or controls a production environment in scope of these [policies](index.md).
That includes application code, infrastructure as code (Pulumi), CI/CD
pipelines (Concourse, GitHub Actions), Kubernetes manifests and Helm values,
secrets and access configuration (Vault, Keycloak, IAM), CDN configuration
(Fastly) and SaaS configuration managed as code (GitHub, Rootly, Grafana,
Sentry).

## Roles and responsibilities

| Role | Responsibility |
|---|---|
| Author | Opens the pull request, describes the change and how it was tested, and deploys or monitors it. |
| Reviewer | Reviews the change for correctness, security and operational risk, and approves it. |
| Release manager | Runs an application release through QA and Production and watches it after deploy ([release process](../handbook/delivering/release-process/index.md)). |
| Platform Engineering | Owns infrastructure changes, the deployment pipelines and the GitHub rulesets that enforce this policy. |

## Change types

| Type | What it is | Approval |
|---|---|---|
| Standard | Every planned change: features, fixes, dependency updates, configuration and infrastructure changes. | Pull request review (`CM-1`), then deployed to CI, tested in QA and released to Production (`CM-3`). |
| Emergency | A change needed right away to restore service or close an actively exploited vulnerability. | As described in `CM-7`. |

## Requirements

**CM-1. Every change is made through a reviewed pull request.**
Changes are proposed as GitHub pull requests and need at least one approving
review from someone other than the author, with all review threads resolved,
before merging. GitHub organization rulesets enforce this on default branches
([`org_rulesets.py`](https://github.com/mitodl/ol-infrastructure/blob/main/src/ol_infrastructure/saas/github/organization/org_rulesets.py)),
and only designated teams can bypass them. Automated dependency updates from
Renovate are approved by the `renovate-approve` GitHub App under the same
rules. See [Code Review](../handbook/delivering/code-review.md) and
[Development Process](../handbook/delivering/development-process.md).

**CM-2. Required checks pass before merge.**
Each repository's required status checks (tests, linting, type checking,
secret detection and static analysis) must pass. Advisory AI reviews (Sentry
Seer, GitHub Copilot) inform the reviewer but don't replace human review.

**CM-3. Changes are proven in a pre-production environment first.**
Changes move through CI, then QA (also called RC), then Production
([Environments](../handbook/delivering/environments.md),
[Production Ready](../handbook/delivering/production-ready.md)). The artifact
promoted to Production is the same one tested in QA.

**CM-4. Application releases use the release workflow.**
MIT Learn and other applications on the
[Concourse release workflow](../handbook/delivering/release-process/concourse-release-workflow.md)
are released with `/doof release`. Closing the release issue is the approval
that authorizes promotion to Production. It doesn't by itself mean the release
is running there: GitHub Deployments record what is actually deployed, and the
release manager confirms the deploy finished. Production releases happen Monday to Thursday, 8am to 4pm Eastern,
unless an exception in the [release process](../handbook/delivering/release-process/index.md)
applies.

**CM-5. Infrastructure changes are previewed and gated.**
Pulumi changes are run with `pulumi preview` and the plan is reviewed before
`pulumi up`. Infrastructure pipelines deploy to CI automatically. QA and
Production deploys need a person to close the gate issue the pipeline opens
([Concourse GitHub Issues User Guide](../platform_services/ci_cd/concourse_github_issues_user_guide.md)).
Drift detection opens pull requests for a person to review and never applies
changes on its own.

**CM-6. Manual production changes are limited and recorded.**
Only Platform Engineering may apply infrastructure changes to Production
outside a pipeline (for example, a local `pulumi up`). Each such change must
be tied to a merged pull request, or recorded in a GitHub issue that is linked
from the follow-up pull request. Direct console or `kubectl` edits to
production resources are allowed only during an incident (`CM-7`) and must be
brought back into code afterwards.

**CM-7. Emergency changes.**
During an incident, the incident leader may approve a change that skips the
usual review or release window to restore service or contain a security
issue. Within one business day, the change must be recorded in the Rootly
incident or a GitHub issue, brought into code through a reviewed pull request
if it was made by hand, and reviewed in the post-mortem when one is required
([Incident Response](incident-response.md)). `/doof hotfix` is the expected
path for urgent application fixes.

**CM-8. Every change can be rolled back.**
Authors note how to roll back any change that isn't trivially reversible.
Accepted rollback paths include reverting the pull request, `/doof abandon`
for a release still in QA, redeploying the previous release, and reverting an
infrastructure change through the pipeline.

**CM-9. Changes are traceable.**
Every production change can be traced from the deployed artifact to the merged
pull request, its review and the issue it addresses. Commits require sign-off,
and the release and deploy issues record when each change reached each
environment.

## Exceptions

Handled as described in [Policies: Exceptions](index.md#exceptions).

## Related documents

- [How We Deliver](../handbook/delivering/index.md)
- [Release Process](../handbook/delivering/release-process/index.md)
- [Release Workflow Machinery](../platform_services/ci_cd/release_workflow_machinery.md)
- [Emergency Oncall Break Glass Procedure](../getting_started_and_how_tos/emergency-break-glass.md)
- [Incident Response Policy](incident-response.md)

## Review

| Owner | Version | Last reviewed |
|---|---|---|
| Platform Engineering | 1.0 (draft) | 2026-10-13 |
