---
title: "Disaster Recovery Runbook"
---
# Disaster Recovery Runbook

How to restore production services from backups or rebuild them from code.
It supports the [Disaster Recovery Policy](../policies/disaster-recovery.md)
and the [Business Continuity Policy](../policies/business-continuity.md).
The recovery objectives are an RPO and an RTO of 24 hours each.

Use this runbook once the incident leader has declared a disaster in the
Rootly incident ([`BC-5`](../policies/business-continuity.md)). Everything
else, including communication, roles and status page updates, follows the
[OL Production Incident Response Runbook](ol_production_outage_runbook.md).
Record every step you take, with timestamps, in the incident channel.

## Before you start

You need:

- AWS console and CLI access to the production account.
- `kubectl` access to the `applications-production` EKS cluster.
- A checkout of [ol-infrastructure](https://github.com/mitodl/ol-infrastructure)
  and the Pulumi CLI, logged in with `pulumi login s3://mitol-pulumi-state`.
- Vault access with a Platform Engineering role.

If you're missing any of these, page Platform Engineering through the
[Emergency Oncall Break Glass Procedure](../getting_started_and_how_tos/emergency-break-glass.md).

Pulumi changes made by hand during recovery are emergency changes
([`CM-7`](../policies/change-management.md)). Prefer re-running the
Concourse pipeline for the stack when it's available.

## Decide what to recover

| What failed | Go to |
|---|---|
| Database lost, corrupted, or damaged by a bad migration or deletion | [Restore a database](#restore-a-database) |
| Open edX course content or forum data lost or corrupted | [Restore MongoDB Atlas](#restore-mongodb-atlas) |
| Application pods or Kubernetes resources lost, database intact | [Redeploy an application](#redeploy-an-application) |
| Vault sealed and won't unseal, or its data is lost | [Restore Vault](#restore-vault) |
| Files deleted or overwritten in S3 | [Restore S3 objects](#restore-s3-objects) |
| A persistent volume in EKS lost or corrupted | [Restore an EKS volume](#restore-an-eks-volume) |
| Pulumi state corrupted | [Restore Pulumi state](#restore-pulumi-state) |
| Search results missing or stale after a restore | [Rebuild search indexes](#rebuild-search-indexes) |

When several components are affected, recover them in this order: Vault,
then databases, then applications, then search indexes. Applications can't
start without Vault.

## Restore a database

RDS keeps automated backups for 30 days and can restore to any point in that
window, to within about five minutes. Restoring always creates a new
instance. To keep the same endpoint, so that Vault and the application
reconnect without configuration changes, move the damaged instance out of
the way first.

1. Pick the restore time: just before the corruption or deletion. Check the
   latest restorable time:

    ```bash
    aws rds describe-db-instances --db-instance-identifier <instance> \
      --query 'DBInstances[0].LatestRestorableTime'
    ```

    Application instance names follow the pattern `ol-<app>-db-production`,
    for example `ol-mitlearn-db-production`.

2. Stop writes: scale the application's web and worker deployments to zero
   in its namespace, so nothing writes to the old instance.
3. Delete the read replica, if the instance has one (named
   `<instance>-replica`). It would stay attached to the damaged instance and
   block Pulumi from creating a new replica under the same name. Replicas
   hold no data of their own, so no snapshot is needed:

    ```bash
    aws rds delete-db-instance --db-instance-identifier <instance>-replica \
      --skip-final-snapshot
    aws rds wait db-instance-deleted --db-instance-identifier <instance>-replica
    ```

    If deletion protection is on, turn it off first with
    `aws rds modify-db-instance --no-deletion-protection --apply-immediately`.

4. Rename the damaged instance. Keep it until the recovery is confirmed:

    ```bash
    aws rds modify-db-instance --db-instance-identifier <instance> \
      --new-db-instance-identifier <instance>-damaged --apply-immediately
    ```

    The rename reboots the instance and takes a few minutes. Wait until the
    renamed instance is available and the original name is free, or the
    restore fails with `DBInstanceAlreadyExists`:

    ```bash
    aws rds wait db-instance-available \
      --db-instance-identifier <instance>-damaged
    aws rds describe-db-instances --db-instance-identifier <instance>
    ```

    The second command should return `DBInstanceNotFound`.

5. Restore into the original name, using the same subnet group, security
   groups and parameter group as the original:

    ```bash
    aws rds restore-db-instance-to-point-in-time \
      --source-db-instance-identifier <instance>-damaged \
      --target-db-instance-identifier <instance> \
      --restore-time <ISO-8601 time> \
      --db-subnet-group-name <subnet group> \
      --vpc-security-group-ids <security group ids> \
      --db-parameter-group-name <parameter group> \
      --multi-az
    ```

6. Wait for the instance to become available (usually under an hour,
   longer for large databases):

    ```bash
    aws rds wait db-instance-available --db-instance-identifier <instance>
    ```

7. Run `pulumi refresh` and then `pulumi up` on the application's stack (for
   MIT Learn, project `ol-application-mit-learn`, stack `Production`, in
   `src/ol_infrastructure/applications/mit_learn`). The refresh drops the
   deleted replica from the state, and the update reconciles settings and
   creates a new replica from the restored instance.
8. Scale the application back up, then run its migrations if the restored
   data is older than the deployed code.
9. Check the application works, then hand over to the application team to
   confirm the data.
10. Once everyone agrees the recovery is good, remove deletion protection
    from `<instance>-damaged` and delete it, keeping a final snapshot.

## Restore MongoDB Atlas

Open edX keeps course content and discussion forums in MongoDB Atlas, with
one Atlas project per Open edX deployment. Production clusters have cloud
backups and point-in-time recovery on.

1. Pick the restore time: just before the corruption or deletion.
2. Stop writes: put the affected Open edX deployment's LMS, Studio and
   workers into maintenance, or scale them to zero.
3. In the Atlas console, open the project's cluster, go to **Backup**, and
   choose the point-in-time restore option, restoring to the chosen time and
   into the same cluster.
4. When Atlas reports the restore is complete, scale Open edX back up and
   check that courses load in the LMS and Studio.
5. Learner data in Open edX's MariaDB database (for example, course
   progress and grades) is separate. If it's affected too, restore it to the
   same time as described in [Restore a database](#restore-a-database).

## Redeploy an application

Applications are stateless, so they're recovered by deploying them again.

1. Check the cluster is healthy:

    ```bash
    aws eks describe-cluster --name applications-production \
      --query 'cluster.status'
    ```

2. Re-run the application's deploy pipeline in Concourse. If Concourse is
   unavailable, run `pulumi up` on the application's stack from
   ol-infrastructure.
3. Watch the pods start with `kubectl get pods -n <namespace> -w`.
4. Check the application through its public URL and the status page checks.

If the cluster itself has to be rebuilt, run the EKS stack for the
cluster first (`src/ol_infrastructure/infrastructure/aws/eks`, stack
`applications.Production`), then the platform services, then each
application.

## Restore Vault

Vault runs on EC2 with integrated Raft storage and unseals itself with AWS
KMS, so a restarted node normally needs no manual unseal. Production takes a
snapshot to S3 every three hours.

1. Check the cluster with `vault status` on a Vault node.
2. If the nodes are lost, redeploy them with the Vault stack
   (`src/ol_infrastructure/infrastructure/vault`, stack
   `operations.Production`).
3. If the data is lost or the cluster can't be initialized, restore the
   latest snapshot by following
   [So you broke Vault?](../platform_services/secrets_management/restore_vault_backups.md).
4. Restart the applications so they log in to Vault again:
   `kubectl rollout restart deployment -n <namespace>`.

## Restore S3 objects

Application buckets have versioning on, so deleted or overwritten objects can
be brought back.

1. List the versions of the affected objects:

    ```bash
    aws s3api list-object-versions --bucket <bucket> --prefix <prefix>
    ```

2. For a deleted object, delete its delete marker. For an overwritten
   object, copy the previous version back over the current one:

    ```bash
    aws s3api copy-object --bucket <bucket> --key <key> \
      --copy-source "<bucket>/<key>?versionId=<version id>"
    ```

3. For data that the application ingests from upstream sources, re-running
   the ingestion is often faster than restoring object by object.

## Restore an EKS volume

AWS Backup takes a daily backup of the persistent volumes in each EKS
cluster and keeps it for 14 days.

1. In the AWS Backup console, open the backup vault for the cluster and find
   the recovery point for the volume.
2. Restore it to a new EBS volume in the same availability zone.
3. Point the PersistentVolume at the restored volume, or replace the
   volume behind it, then restart the workload.

## Restore Pulumi state

The `mitol-pulumi-state` bucket has versioning on.

1. List the versions of the stack's state file:

    ```bash
    aws s3api list-object-versions --bucket mitol-pulumi-state \
      --prefix .pulumi/stacks/<project>/<stack>.json
    ```

2. Copy the last good version back over the current one, as in
   [Restore S3 objects](#restore-s3-objects).
3. Run `pulumi refresh` on the stack, and check that the preview shows no
   unexpected changes before running `pulumi up`.

## Rebuild search indexes

Search indexes in OpenSearch and the vectors in Qdrant Cloud are built from
the database, so they're rebuilt rather than restored. Once the application
is healthy, run the reindexing and embedding commands for the application
(for MIT Learn, the `recreate_index` and `generate_embeddings` management
commands). Search can run degraded while this happens, which doesn't count
against the RTO as long as the rest of the service is available.

## After recovery

- Confirm with the application team that the service and its data are
  correct, then move the incident to Mitigated.
- Note the actual recovery time and data loss in the incident, for the
  post-mortem ([`DR-9`](../policies/disaster-recovery.md)).
- Update this runbook with anything that didn't match reality.
