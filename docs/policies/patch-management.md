---
title: "Patch Management Policy"
---
# Patch Management Policy

## Purpose

Keep operating systems, container images, platform software and application
dependencies current, so known defects and vulnerabilities are fixed promptly
and systems stay on supported versions.

## Scope

Everything we build, deploy or run for systems in scope of these
[policies](index.md):

- application dependencies (Python, JavaScript and other packages),
- container base images and the images we build,
- machine images (AMIs) and their operating systems,
- Kubernetes (EKS) clusters, add-ons and Helm charts,
- platform software (Vault, Consul, Concourse, Keycloak, Open edX and similar),
- infrastructure tooling (Pulumi providers, GitHub Actions).

Managed services where AWS or another vendor patches the underlying system
(RDS, ElastiCache, OpenSearch) are in scope for keeping engine versions
supported and maintenance windows configured.

## Roles and responsibilities

| Role | Responsibility |
|---|---|
| Platform Engineering | Patches platform software, images, clusters and infrastructure tooling, and runs the build pipelines. |
| MIT Learn team | Reviews and merges dependency updates for MIT Learn repositories. |
| Reviewers | Review update pull requests like any other change ([Change Management](change-management.md)). |

## Requirements

**PM-1. Dependency updates are automated with Renovate.**
In-scope repositories use Renovate and extend the shared organization
configuration, `mitodl/.github:renovate-config`
([Updating Renovate Configuration](../application_specific_guides/renovate/updating_renovate_config.md)).
That configuration:

- raises routine updates on a weekly schedule (every weekend),
- automerges minor and patch updates once the repository's required checks
  pass, under the review rules in [`CM-1`](change-management.md), and keeps
  major updates in separate pull requests for human review, and
- has vulnerability alerts on (GitHub advisories and OSV), so security updates
  are raised straight away instead of waiting for the schedule.

In ol-infrastructure, versions pinned outside package manifests are tracked
with `# renovate:` markers so Renovate can update them too.

**PM-2. Update pull requests are handled on Renovate Day.**
Developers take turns on a weekly rotation in which each working day is
assigned to one developer as their **Renovate Day**. On their day, that
developer reviews open Renovate pull requests, verifies them and merges them,
or closes them with a reason. Security updates follow the timelines in `PM-3`.

**PM-3. Security patches meet the remediation timelines.**
Patches that fix a vulnerability are applied in Production within the
[Vulnerability Management](vulnerability-management.md#requirements)
timelines: Critical in 7 days, High in 30 days, Medium in 90 days, and Low in
the next routine update.

**PM-4. Container images are rebuilt on patched bases.**
First-party application images build from `mitodl/ol-python-base`, which is
based on Docker Hardened Images. Its pipeline rebuilds the base when Docker
publishes a patched upstream image, and applications pick up the new base on
their next build.

**PM-5. Machine images are immutable and rebuilt regularly.**
AMIs are built with Packer from the latest image of a supported Debian
release (one that still receives Debian security updates), and don't run
unattended upgrades, so servers are patched by replacing them with a new
image, not by updating them in place. The baseline image is rebuilt when the
software it carries is released. Servers are also redeployed at least monthly,
partly so their dynamic secrets are renewed, and each redeploy uses the latest
baseline image, so operating system patches land on a predictable schedule
([Testing and Deploying Pulumi Packer Projects](../platform_services/cloud_infrastructure/test_and_deploy_pulumi_packer_projects.md),
[Tagging AMIs with Software Metadata](../platform_services/cloud_infrastructure/tagging_amis_with_installed_software_metadata.md)).

**PM-6. Kubernetes stays on supported versions.**
EKS clusters run a Kubernetes version within AWS standard support. There's no
fixed upgrade cadence: Platform Engineering upgrades a cluster when AWS
announces the end of standard support for its version (through AWS Health
notifications), and plans and tests the upgrade in CI and QA before that date.
EKS add-ons that Renovate can't track are checked and updated with
each cluster upgrade.

**PM-7. Open edX and platform software follow their release cadence.**
The Open edX deployment for MIT Learn follows the main development branch of
Open edX (`master`), so it picks up upstream fixes continuously instead of
waiting for named releases. Other Open edX deployments are upgraded on the
schedule in [Release Upgrades](../application_specific_guides/openedx/release_upgrades.md).
Other platform software is kept on a release that still receives security
fixes from its maintainers.

**PM-8. Patches go through change management.**
Patches are deployed through the normal pipelines and environments
([Change Management](change-management.md)), CI first, then QA, then
Production. Emergency patches for actively exploited vulnerabilities may use
the emergency process in `CM-7`.

## Exceptions

When a patch can't be applied in time (for example, it breaks compatibility),
record an exception as described in [Policies: Exceptions](index.md#exceptions)
with the compensating control in place until it's applied.

## Related documents

- [Vulnerability Management Policy](vulnerability-management.md)
- [Change Management Policy](change-management.md)
- [Updating Renovate Configuration](../application_specific_guides/renovate/updating_renovate_config.md)
- [Release Upgrades (Open edX)](../application_specific_guides/openedx/release_upgrades.md)

## Review

| Owner | Version | Last reviewed |
|---|---|---|
| Platform Engineering | 1.0 (draft) | 2026-10-13 |
