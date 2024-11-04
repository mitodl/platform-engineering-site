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
