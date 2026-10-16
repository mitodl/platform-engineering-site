---
title: "Disaster Recovery Policy"
---
# Disaster Recovery Policy

## Purpose

Make sure production data is backed up and every critical service can be
restored within defined time and data-loss limits, so a failure can't cause
lasting loss of service or data.

## Scope

The critical services and components listed in the
[Business Continuity Policy](business-continuity.md#critical-services), in
the production environment. Loss of an entire AWS region is out of scope, as
described in that policy.

## Roles and responsibilities

| Role | Responsibility |
|---|---|
| Platform Engineering | Owns this policy and the [Disaster Recovery Runbook](../runbooks_post_mortems/disaster_recovery_runbook.md), configures backups in code and runs the yearly restore test. |
| Incident leader | Declares a disaster, decides the restore point and approves the recovery steps ([`CM-7`](change-management.md)). |
| On-call engineer | Carries out recovery following the runbook. |
| Application teams | Confirm their application works after a restore, and say which data can be rebuilt rather than restored. |

## Recovery objectives

| Objective | Target | Meaning |
|---|---|---|
| Recovery Point Objective (RPO) | 24 hours or less | The most data that can be lost, measured back from the moment of failure. |
| Recovery Time Objective (RTO) | 24 hours or less | The longest a critical service can be unavailable, measured from when the incident is opened ([`IR-3`](incident-response.md)) to when the service is restored. |

These targets apply to every component that is material to delivering the
services.

## How each component is protected

| Component | Protection | Retention | Recovered by |
|---|---|---|---|
| RDS databases (PostgreSQL, and MariaDB for Open edX) | Automated backups with point-in-time recovery; Multi-AZ; encrypted; deletion protection; final snapshot on deletion | 30 days | Point-in-time restore |
| MongoDB Atlas (Open edX) | Atlas cloud backups with point-in-time recovery; three-node replica set | Atlas backup policy | Point-in-time restore in Atlas |
| Vault | Raft snapshot to S3 every 3 hours, with an alert if a backup fails; KMS auto-unseal | 365 days | Snapshot restore |
| EKS persistent volumes | Daily AWS Backup | 14 days | AWS Backup restore |
| S3 buckets with application data | Object versioning | Previous versions kept | Restore the previous version |
| Pulumi state | Object versioning on the state bucket | Previous versions kept | Restore the previous version |
| ElastiCache (Valkey) | Daily snapshots; holds only data that can be regenerated | 5 days | Rebuilt empty, or from a snapshot |
| OpenSearch and Qdrant Cloud search indexes | Rebuilt from the database | Not applicable | Reindex from the database |
| Applications and platform services | Defined in code; images in a registry | 90 days of release images | Redeploy through the pipelines |

## Requirements

**DR-1. Critical services meet the recovery objectives.**
Every critical service can be restored within the RTO, with no more data
loss than the RPO allows, as set out in [Recovery objectives](#recovery-objectives).
A component whose protection can't meet them needs an
[exception](index.md#exceptions).

**DR-2. Data that can't be rebuilt is backed up at least daily.**
Every production data store that holds data we can't regenerate is backed up
automatically at least once every 24 hours, with backups kept for at least 7
days. Backups are configured in code (in
[ol-infrastructure](https://github.com/mitodl/ol-infrastructure), for example
the shared [RDS component](https://github.com/mitodl/ol-infrastructure/blob/main/src/ol_infrastructure/components/aws/database.py)),
not by hand.

**DR-3. Data that can be rebuilt is documented.**
Caches and search indexes don't need backups if they can be regenerated from
backed-up data. For each one, the runbook says how it's rebuilt and roughly
how long that takes, so the RTO accounts for it.

**DR-4. Backups and production data are protected from loss.**
Backups are encrypted at rest. Production databases have deletion protection
on and take a final snapshot if deleted. S3 buckets that hold application or
user data, and the Pulumi state bucket, have versioning on.

**DR-5. Backup failures alert on-call.**
A failed or missing backup alerts the on-call engineer through Rootly
([`IR-1`](incident-response.md)), and is treated as a SEV3 until backups are
running again.

**DR-6. Production can be rebuilt from code.**
Everything except data is recreated from infrastructure code, pipelines and
stored release images ([`BC-3`](business-continuity.md)). A manual change
that isn't in code is a gap in this plan and must be brought into code
([`CM-6`](change-management.md)).

**DR-7. Restores are tested every year.**
At least once a year, Platform Engineering restores a production database
backup and a Vault snapshot to a non-production environment, checks the data,
and records how long it took. The result is filed as a GitHub issue in
[mitodl/hq](https://github.com/mitodl/hq). If the test shows the RTO or RPO
can't be met, the gap is fixed or covered by an exception.

**DR-8. Recovery follows the runbook.**
When a disaster is declared ([`BC-5`](business-continuity.md)), responders
follow the [Disaster Recovery Runbook](../runbooks_post_mortems/disaster_recovery_runbook.md).
Steps taken outside it are recorded in the Rootly incident.

**DR-9. Every disaster gets a post-mortem.**
Every declared disaster is a SEV1 and gets a post-mortem
([`IR-8`](incident-response.md)). It records the actual recovery time and
data loss against the objectives, and any changes the runbook needs.

## Exceptions

Handled as described in [Policies: Exceptions](index.md#exceptions).

## Related documents

- [Business Continuity Policy](business-continuity.md)
- [Disaster Recovery Runbook](../runbooks_post_mortems/disaster_recovery_runbook.md)
- [So you broke Vault?](../platform_services/secrets_management/restore_vault_backups.md)
- [Incident Response Policy](incident-response.md)
- [Change Management Policy](change-management.md)

## Review

| Owner | Version | Last reviewed |
|---|---|---|
| Platform Engineering | 1.0 (draft) | 2026-10-15 |
