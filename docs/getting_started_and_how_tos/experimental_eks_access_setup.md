# Experimental EKS Access Setup

This guide covers the **new** `eks.py`-based workflow for gaining access to MIT
Open Learning EKS clusters. It replaces the older `login_helper.py`-based flow
described in [Developer EKS Access](developer_eks_access.md) and is the
preferred approach going forward.

The script discovers all OL EKS clusters automatically via the AWS API, handles
Vault OIDC authentication through your browser, and writes a ready-to-use
`~/.kube/config` for you. You do not need to manually export AWS credentials or
run separate login steps.

/// admonition | Experimental
    type: warning

This workflow is under active development. The underlying `eks.py` script lives
in `scripts/eks/eks.py` inside the `ol-infrastructure` repository and may
change. If you run into issues, check `KUBE_ACCESS.md` in that same directory
for the latest notes.
///

---

## Prerequisites

Before running the setup script you need the following tools and access in
place.

### Required tools

| Tool | Minimum version | Notes |
| --- | --- | --- |
| [Python](https://www.python.org/) | 3.13 | Must match the `ol-infrastructure` requirement |
| [uv](https://docs.astral.sh/uv/) | latest | Used to run the script with its dependencies |
| [AWS CLI v2](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) | latest | `aws eks get-token` must be on your `$PATH` |
| [kubectl](https://kubernetes.io/docs/tasks/tools/) | ≥ 1.30 | Newer is better |

Install `uv` if you do not already have it:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Access requirements

- **Vault access** — you must be able to authenticate to
  `https://vault-production.odl.mit.edu` via MIT OIDC. If you have never logged
  in before, ask a DevOps team member to verify your Vault policy is in place.
- **ol-infrastructure repository** — clone the repo if you have not already:

  ```bash
  git clone https://github.com/mitodl/ol-infrastructure.git
  cd ol-infrastructure
  ```

### No manual AWS configuration needed

The script generates short-lived AWS credentials through Vault and caches them
locally under `~/.cache/ol-infrastructure/eks/`. You do **not** need a
pre-configured AWS profile or permanent AWS credentials on your machine.

---

## How authentication works

When you run `eks.py setup` for the first time (or after your cached token
expires) the script:

1. Opens a Vault OIDC authorization URL in your browser.
2. Starts a short-lived local HTTP server on port `8250` to receive the
   callback.
3. Exchanges the callback code for a Vault token and caches it under
   `~/.cache/ol-infrastructure/eks/`.
4. Uses the Vault token to generate temporary AWS STS credentials.
5. Calls the AWS EKS API to discover all clusters and writes `~/.kube/config`.

On subsequent runs the cached Vault token and AWS credentials are reused until
they expire, so no browser interaction is required.

The generated kubeconfig uses an `exec` plugin that calls back into `eks.py`
each time `kubectl` needs a bearer token. This means you never need to re-run
the setup command unless you want to regenerate the config itself.

---

## Setup scenarios

### Developer access (default)

Use this if you are a developer who needs read/write access to the clusters for
debugging, shelling into pods, port-forwarding, and similar day-to-day tasks.

From the root of `ol-infrastructure`:

```bash
uv run python scripts/eks/eks.py setup
```

Or equivalently, specifying the mode explicitly:

```bash
uv run python scripts/eks/eks.py setup --mode developer
```

This writes `~/.kube/config` with **two contexts per cluster**:

- `<cluster-name>` — full developer read/write access (e.g. `applications-qa`)
- `<cluster-name>-readonly` — read-only access for agents or safe exploration
  (e.g. `applications-qa-readonly`)

The default active context is set to `applications-qa` when that cluster exists,
otherwise the first cluster found.

Switch between clusters at any time:

```bash
kubectl config use-context applications-production
kubectl config use-context operations-ci
```

List all available contexts:

```bash
kubectl config get-contexts
```

### Agent / read-only access

Use this if you are setting up an automated agent, a CI job, or you simply want
a safe read-only view of the clusters with no risk of accidentally changing
anything.

```bash
uv run python scripts/eks/eks.py setup --mode readonly
```

This writes `~/.kube/config` with a **single read-only context per cluster**.
The contexts use a Vault AWS role bound to `AmazonEKSViewPolicy`, which allows
listing and describing resources but cannot create, update, or delete anything.

### Admin access (DevOps only)

/// admonition | DevOps engineers only
    type: danger

Admin mode grants `cluster-admin` privileges. It is intended exclusively for
DevOps engineers performing cluster maintenance. Do not run this unless you have
been explicitly granted admin access.
///

Admin mode authenticates via a separate Vault OIDC role (`admin`) and uses
per-cluster IAM roles to assume cluster-admin access entries in each EKS
cluster.

```bash
uv run python scripts/eks/eks.py setup --mode admin
```

This writes `~/.kube/config` with **two contexts per cluster**:

- `<cluster-name>` — cluster-admin credentials via the cluster's dedicated admin
  IAM role
- `<cluster-name>-readonly` — read-only credentials for safe inspection

/// admonition | Note
    type: note

Admin mode uses readonly Vault AWS credentials for cluster discovery (listing
and describing clusters). The elevated cluster-admin token is obtained at
`kubectl` invocation time via `aws eks get-token --role`, not at setup time.
///

---

## Optional flags

### Setting a custom default context

By default the script sets `applications-qa` as the active context (if it
exists). Override this at setup time:

```bash
uv run python scripts/eks/eks.py setup --current-context applications-production
```

### Writing to a custom kubeconfig path

By default the script overwrites `~/.kube/config`. Write to a different path
instead:

```bash
uv run python scripts/eks/eks.py setup --output-path ~/kubeconfigs/ol.yaml
```

Then point `kubectl` at it:

```bash
KUBECONFIG=~/kubeconfigs/ol.yaml kubectl get nodes
```

---

## Verifying your access

After setup, confirm everything is working:

```bash
# Check which context is active
kubectl config current-context

# List all nodes in the current cluster
kubectl get nodes

# List all namespaces
kubectl get namespaces
```

---

## Common kubectl commands

Once your kubeconfig is in place, here are useful commands to get started.

List all pods in a namespace:

```bash
kubectl get pods -n <namespace>
```

Describe a pod (shows events, IP, node, containers):

```bash
kubectl describe pod <pod-name> -n <namespace>
```

Tail logs from a specific container:

```bash
kubectl logs -f <pod-name> -n <namespace> -c <container-name>
```

Open an interactive shell in a running container:

```bash
kubectl exec -it <pod-name> -n <namespace> -c <container-name> -- /bin/bash
```

Port-forward a service to your local machine:

```bash
kubectl port-forward svc/<service-name> 8080:80 -n <namespace>
```

Switch to a different cluster context:

```bash
kubectl config use-context <context-name>
```

---

## Troubleshooting

**Port 8250 is already in use during OIDC login** Another process is occupying
the OIDC callback port. Find and stop it:

```bash
lsof -i :8250
```

**`aws: command not found` when kubectl fetches a token** The `aws` CLI is not
on the `PATH` seen by the exec plugin. Ensure `aws` is installed and available
in your standard shell `PATH` (not only a virtualenv-scoped install).

**Vault authentication fails or token is rejected** Your cached Vault token may
be invalid. Remove it and re-run setup:

```bash
rm -rf ~/.cache/ol-infrastructure/eks/
uv run python scripts/eks/eks.py setup
```

**No clusters found** The script logs a warning if it discovers zero clusters.
Verify that your Vault AWS role has been granted the correct permissions by
checking with a DevOps engineer.

---

## Further reading

- [Kubernetes kubeconfig
  documentation](https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/)
- [Configuring access to multiple
  clusters](https://kubernetes.io/docs/tasks/access-application-cluster/configure-access-multiple-clusters/)
- [Developer EKS Access](developer_eks_access.md) — the older workflow, kept for
  reference
