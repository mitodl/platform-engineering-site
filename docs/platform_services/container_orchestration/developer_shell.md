# Application Developer Shell

Most applications deployed to Kubernetes with the shared `OLApplicationK8s`
component can have a **developer shell**: a launch-on-request pod running the
application's own image, where you can run `manage.py` commands, a Django
shell, or ad-hoc scripts against a live environment without the session being
OOMKilled or scaled away mid-command.

Nothing routes to it and it costs nothing while idle. You scale it up when you
need it and scale it back down when you are done.

Introduced in
[ol-infrastructure#5958](https://github.com/mitodl/ol-infrastructure/pull/5958).

## Why this exists

None of an application's regular pods are a safe place for interactive work:

- **The webapp** is autoscaled by KEDA and resized by the VPA. A pod you are
  shelled into can be evicted or scaled away at any moment.
- **Celery workers** are KEDA-scaled to zero when idle and sized for their task
  mix, not for a one-off management command that loads a lot of data.
- **The pre-deploy migration Job** only runs during a rollout.

The dev shell is a separate Deployment named `<app>-dev-shell` in the
application's namespace. Its labels match no autoscaler and no VPA, it has no
Service, and it carries a `karpenter.sh/do-not-disrupt` annotation so node
consolidation cannot evict it. By default it has a fixed `4Gi` memory request
and limit and a `250m` CPU request.

## Where it is enabled

The shell is opt-in per application and per environment. An application that
has not opted in has no `<app>-dev-shell` Deployment at all.

| Application | Namespace | Environments | Deployment name |
| --- | --- | --- | --- |
| MITx Online | `mitxonline` | Production | `mitxonline-dev-shell` |

To check whether an application has one, look for the Deployment in its
namespace:

```bash
kubectl -n <namespace> get deploy <app>-dev-shell
```

/// admonition | Adding an application to this table
    type: note

Opt an application in by passing `dev_shell_config=OLApplicationK8sDevShellConfig()`
to its `OLApplicationK8sConfig` in `ol-infrastructure`, usually gated on a
per-stack flag so it can be enabled only where needed. Then add a row here.
///

## Prerequisites

- `kubectl` access to the cluster hosting the environment you need, for
  example `applications-production`. Follow
  [EKS Access Setup](../../getting_started_and_how_tos/eks_access_setup.md) if
  you have not done this yet. You need write access to scale the Deployment,
  so a read-only context will not work.
- The application and environment must be listed in the table above.

## Getting a shell

The examples below use `<namespace>` and `<app>` as placeholders. For MITx
Online production both are `mitxonline`.

Select the cluster:

```bash
kubectl config use-context applications-production
```

Confirm the Deployment exists and is idle (expect `0/0`):

```bash
kubectl -n <namespace> get deploy <app>-dev-shell
```

Scale it up and wait for the pod to become ready. The init containers render the
application config first, so this takes a minute or so:

```bash
kubectl -n <namespace> scale deploy/<app>-dev-shell --replicas=1
kubectl -n <namespace> rollout status deploy/<app>-dev-shell
```

Open a shell:

```bash
kubectl -n <namespace> exec -it deploy/<app>-dev-shell -- bash
```

You land in the image's working directory as the image's application user,
with the same environment variables, Vault-sourced secrets, service account,
volumes, and pod security group as the webapp. The database, Redis, and AWS
resources are all reachable exactly as they are from the app. From there:

```bash
python manage.py shell
python manage.py <your_command> --help
```

/// admonition | If someone else already scaled it up
    type: tip

The Deployment is shared per application. If `get deploy` shows `1/1`,
someone is probably using it. You can `exec` into the same pod for a second
session, but check with the team before scaling it down.
///

## Limitations

/// admonition | A deploy will kill your session
    type: warning

The pod runs the same image as the webapp, so **every deploy of that
application rolls its dev shell**. Any command running in it gets a 60 second
grace period and is then killed. This is deliberate: a shell running last
week's code against a freshly migrated database is worse than an interrupted
session. Start long-running commands with the release schedule in mind, or
coordinate with whoever is releasing.
///

- **Nothing scales it back down automatically.** A forgotten shell holds its
  memory request (`4Gi` by default) until someone scales it to zero. There is
  no reaper.
- **A deploy does not reset the replica count.** Pulumi ignores `spec.replicas`
  on this Deployment, so if you leave it at 1, it stays at 1 across releases
  until someone scales it down by hand.
- **Vault credential rotation may restart it.** The shell is included in the
  application's list of Deployments, so apps that wire that list into Vault
  secret restart targets will have the shell restarted when credentials rotate.
- **Fixed resources.** The memory limit is fixed (`4Gi` by default). A command
  that needs more will be OOMKilled like any other container. If that happens,
  ask the DevOps team to raise the limit for that application in Pulumi rather
  than working around it.
- **No sidecars and no ingress.** There is no nginx, no log shipper, and no
  Service. Output from your commands is only visible in your terminal. Nothing
  you do here is reachable from the outside.
- **Only where enabled.** Each application chooses which environments get a
  shell. Do not expect one in QA or CI unless the table above says so.
- **Single pod.** Do not scale it above 1. The `Recreate` strategy assumes one
  replica, and two shells share nothing useful anyway.

## Cleaning up

When you are finished, scale it back to zero:

```bash
kubectl -n <namespace> scale deploy/<app>-dev-shell --replicas=0
```

Confirm it is idle:

```bash
kubectl -n <namespace> get deploy <app>-dev-shell
```

The pod gets its termination grace period to exit and the Deployment shows
`0/0` again. The Deployment object itself stays. It is managed by Pulumi and
should not be deleted.
