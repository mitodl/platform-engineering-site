# MIT OL Kubernetes Cookbook

## kubectl Recipes

### Port-forward to a pod

https://kubernetes.io/docs/tasks/access-application-cluster/port-forward-access-application-cluster/

```bash
kubectl port-forward <podname> <local port>:<remote port> -n <namespace>

kubectl port-forward grafana-alloy-dnqj2 12345:12345 -n operations
```

### Get a pgsql Prompt

```bash
kubectl run -i --tty postgres --image=postgres --restart=Never -n airbyte -- sh
```

### Deleting k8s Namespaces With Stuck Vault Finalizers

```bash
kubectl patch -n airbyte vaultauth airbyte-auth -p '{"metadata":{"finalizers":null}}' --type=merge
kubectl patch -n airbyte vaultconnection airbyte-vault-connection -p '{"metadata":{"finalizers":null}}' --type=merge
kubectl patch -n airbyte vaultstaticsecret airbyte-basic-auth-config -p '{"metadata":{"finalizers":null}}' --type=merge
kubectl patch -n airbyte vaultstaticsecret airbyte-forward-auth-oidc-config -p '{"metadata":{"finalizers":null}}' --type=merge
kubectl patch -n airbyte vaultdynamicsecret airbyte-app-db-creds -p '{"metadata":{"finalizers":null}}' --type=merge
kubectl patch -n open-metadata vaultdynamicsecret open-metadata-app-db-creds -p '{"metadata":{"finalizers":null}}' --type=merge
kubectl patch -n open-metadata vaultdynamicsecret openmetadata-app-db-creds -p '{"metadata":{"finalizers":null}}' --type=merge
kubectl patch -n open-metadata vaultdynamicsecret openmetadata-db-creds -p '{"metadata":{"finalizers":null}}' --type=merge
kubectl patch -n open-metadata vaultstaticsecret openmetadata-oidc-config -p '{"metadata":{"finalizers":null}}' --type=merge
kubectl patch -n open-metadata vaultstaticsecret openmetadata-oidc-config -p '{"metadata":{"finalizers":null}}' --type=merge
kubectl patch -n open-metadata vaultauth open-metadata-auth -p '{"metadata":{"finalizers":null}}' --type=merge
kubectl patch -n open-metadata vaultauth open-metadata-auth -p '{"metadata":{"finalizers":null}}' --type=merge
kubectl patch -n open-metadata vaultconnection open-metadata-vault-connection -p '{"metadata":{"finalizers":null}}' --type=merge
kubectl patch -n operations vaultstaticsecret vault-kv-global-odl-wildcard -p '{"metadata":{"finalizers":null}}' --type=merge
```

### Get Overview Of a Namespace

Shows things like open ports, pod status and the like.
```bash
kubectl get all -n open-metadata
```

### Get Information / Status On A Particular Resource

```bash
kubectl describe <resource> <optional-resource-name> -n <namespace>
```
e.g.
```bash
kubectl describe pod -n open-metadata openmetadata-5f78b769d4-4wgs9                                                                                                                 feoh@prometheus
```

### Pulumi Server Side Complaints

Sometimes pulumi will complain about being unable to manage a field or something on k8s resources. Something like this: 

```bash

Diagnostics:
  pulumi:pulumi:Stack (ol-infrastructure-open_metadata-application-applications.open_metadata.CI):
    error: preview failed

  kubernetes:core/v1:ServiceAccount (open-metadata-vault-service-account):
    error: Preview failed: 1 error occurred:
    	* the Kubernetes API server reported that "open-metadata/open-metadata-vault" failed to fully initialize or become live: Server-Side Apply field conflict detected. See https://www.pulumi.com/registry/packages/kubernetes/how-to-guides/managing-resources-with-server-side-apply/#handle-field-conflicts-on-existing-resources for troubleshooting help.
    The resource managed by field manager "pulumi-kubernetes-51b738f0" had an apply conflict: Apply failed with 1 conflict: conflict with "pulumi-kubernetes-cef7f602": .metadata.labels.pulumi_stack

  kubernetes:rbac.authorization.k8s.io/v1:ClusterRoleBinding (open-metadata-vault-cluster-role-binding):
    error: Preview failed: 1 error occurred:
    	* the Kubernetes API server reported that "open-metadata-vault:cluster-auth" failed to fully initialize or become live: Server-Side Apply field conflict detected. See https://www.pulumi.com/registry/packages/kubernetes/how-to-guides/managing-resources-with-server-side-apply/#handle-field-conflicts-on-existing-resources for troubleshooting help.
    The resource managed by field manager "pulumi-kubernetes-0e168a03" had an apply conflict: Apply failed with 2 conflicts: conflicts with "pulumi-kubernetes-0754bbed":
    - .metadata.labels.pulumi_stack
    conflicts with "pulumi-kubernetes-f4f83ba0":
    - .metadata.labels.pulumi_stack
```

Easiest thing to do is set an env var on execution which will bring the questionable fields back into pulumi management and keep you moving. There is still probably a bigger issue at play, though.

```bash
PULUMI_K8S_ENABLE_PATCH_FORCE="true" pr pulumi up -s applications.open_metadata.CI
```
