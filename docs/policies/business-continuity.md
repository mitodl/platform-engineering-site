---
title: "Business Continuity Policy"
---
# Business Continuity Policy

## Purpose

Keep the services we operate available through disruptions, and restore them
quickly when they fail, so learners and partners are affected as little as
possible.

## Scope

The production services in scope of these [policies](index.md), along with
the systems, data flows, people and processes that deliver them. The
[Disaster Recovery Policy](disaster-recovery.md) sets the technical recovery
targets and backup rules that support this policy.

Out of scope:

- **Loss of an entire AWS region.** All production systems run in AWS
  `us-east-1`. If that region is unavailable as a whole, service is restored
  once AWS restores the region, and the recovery targets in
  [`DR-1`](disaster-recovery.md) don't apply. Failure of a single
  availability zone *is* in scope, and production is built to survive it
  (`BC-2`).
- External sites that MIT Learn imports course and content listings from,
  such as edX.org, YouTube and podcast feeds. We don't run them, so we can't
  plan their recovery. If one is unavailable, its import fails and MIT Learn
  keeps showing the listings from the last successful import.
- Local development environments.

## Roles and responsibilities

| Role | Responsibility |
|---|---|
| Platform Engineering | Owns this policy, the [Disaster Recovery Policy](disaster-recovery.md) and the [Disaster Recovery Runbook](../runbooks_post_mortems/disaster_recovery_runbook.md); runs the on-call rotation and the yearly exercises. |
| On-call engineer | First responder for any disruption, as described in the [Incident Response Policy](incident-response.md). |
| Incident leader | Declares a disaster when one is needed (`BC-5`) and coordinates recovery. |
| Communicator | Keeps users, partners and MIT Open Learning leadership informed (`BC-6`). |
| Application teams | Keep their application's critical-service information current, and take part in recovery and exercises. |

## Critical services

These are the services and platform components that delivering the services
depends on. Their containers, data stores and dependencies are described in
[System Architecture](../system_architecture/landscape.md).

| Service or component | What it provides |
|---|---|
| MIT Learn web application, API and frontend | The learner-facing platform. |
| learn-ai | AI chat and tutoring features in MIT Learn and in courses. |
| Open edX (LMS and Studio) | Where courses are built and taken. |
| Background workers (Celery) | Content ingestion, search indexing, email and scheduled jobs. |
| Amazon RDS (PostgreSQL and MariaDB) | Application and Open edX databases. |
| MongoDB Atlas | Open edX course content and discussion forums. |
| Amazon EKS | Runs the applications and the shared platform services. |
| Vault | Secrets and database credentials for every application. |
| Keycloak and APISIX | Sign-in and the API gateway. |
| Amazon S3 | Media, uploaded files and application data. |
| Fastly and Amazon Route 53 | CDN and DNS. |
| OpenSearch and Qdrant Cloud | Search and vector search. |

## Requirements

**BC-1. Plans are maintained and available on request.**
This policy, the [Disaster Recovery Policy](disaster-recovery.md) and the
[Disaster Recovery Runbook](../runbooks_post_mortems/disaster_recovery_runbook.md)
together make up our business continuity and disaster recovery plans. They
are published on this site and kept current through the review process in
[Policies](index.md#changing-a-policy). When a partner or client asks for
copies, Platform Engineering provides the current versions, with any updates
since the last copy, within five working days of the request.

**BC-2. Production is built to tolerate the failure of a single component.**
Production databases run Multi-AZ. The EKS clusters span several
availability zones, and user-facing services (web applications, APIs and the
API gateway) run as multiple replicas, so the loss of one server or
availability zone doesn't take a critical service down. Background workers
that run as a single replica are restarted automatically on another node.
Applications are stateless, and their state lives in the data stores covered
by [`DR-2`](disaster-recovery.md).

**BC-3. Everything needed to rebuild production is kept in code.**
Infrastructure, deployment pipelines and configuration are defined in code
and deployed through reviewed pipelines
([`CM-5`](change-management.md), [`CM-6`](change-management.md)). Container
images for every release are kept in a registry, so any service can be
redeployed or rebuilt from source without relying on undocumented manual
steps.

**BC-4. No single person is required for recovery.**
Production is supported by a weekly on-call rotation in Rootly
([`IR-1`](incident-response.md), [`IR-2`](incident-response.md)). Recovery
procedures are written so that any Platform Engineering engineer with the
standard production access can carry them out. If on-call can't be reached,
anyone can page Platform Engineering through the
[Emergency Oncall Break Glass Procedure](../getting_started_and_how_tos/emergency-break-glass.md).
Platform Engineering checks at least once a year that every member of the
rotation has the access the runbook needs.

**BC-5. Disasters are handled as incidents.**
A disaster is any SEV1 incident where a critical service must be restored
from backups or rebuilt, rather than fixed in place. The incident leader
declares it in the Rootly incident and follows the
[Disaster Recovery Runbook](../runbooks_post_mortems/disaster_recovery_runbook.md).
Everything else about the response, including roles, severity, escalation
and post-mortems, follows the [Incident Response Policy](incident-response.md).

**BC-6. Users and partners are kept informed.**
During a disruption the communicator updates the status page as required by
[`IR-5`](incident-response.md). If a SEV1 is expected to last more than two
hours, the communicator also notifies MIT Open Learning leadership, who
inform affected partners as their agreements require.

**BC-7. Third-party providers are part of the plan.**
We rely on the resilience of the providers listed in [Dependencies](#dependencies).
An outage at one of them is handled as an incident.

**BC-8. The plans are exercised every year.**
Platform Engineering runs a tabletop exercise at least once a year, walking
through a disaster scenario with the runbook, alongside the restore test in
[`DR-7`](disaster-recovery.md). Gaps found in an exercise or a real incident
are filed as GitHub issues with an owner, as for post-mortem actions
([`IR-9`](incident-response.md)).

## Dependencies

| Provider | What we rely on it for |
|---|---|
| Amazon Web Services | Compute, databases, storage, DNS and key management. |
| Fastly | CDN in front of the public sites. |
| MongoDB Atlas | Open edX course content and forums. |
| Qdrant Cloud | Vector search for MIT Learn. |
| GitHub | Source code, pull requests and the infrastructure code needed to rebuild. |
| Concourse (self-hosted) | Build and deployment pipelines. |
| Docker Hub | Application container images. |
| Rootly | Alerting, on-call paging, incidents and the status page. |

## Exceptions

Handled as described in [Policies: Exceptions](index.md#exceptions).

## Related documents

- [Disaster Recovery Policy](disaster-recovery.md)
- [Disaster Recovery Runbook](../runbooks_post_mortems/disaster_recovery_runbook.md)
- [Incident Response Policy](incident-response.md)
- [Change Management Policy](change-management.md)
- [OL Production Incident Response Runbook](../runbooks_post_mortems/ol_production_outage_runbook.md)
- [Emergency Oncall Break Glass Procedure](../getting_started_and_how_tos/emergency-break-glass.md)
- [System Architecture](../system_architecture/landscape.md)

## Review

| Owner | Version | Last reviewed |
|---|---|---|
| Platform Engineering | 1.0 (draft) | 2026-10-15 |
