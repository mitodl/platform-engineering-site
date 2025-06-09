# Developer EKS Access

## Pre-reqs

- an environment variable `GITHUB_TOKEN` set to a classic GitHub [token](https://github.com/settings/tokens) with `read:org` permissions.
- Latest (as of 02-19-2025) `aws-cli` is installed and available on your `$PATH`.
- `kubectl` >= 1.30 is installed and available on your `$PATH`. (Newer is better, usually)
- Cloned copy of [ol-infrastructure](https://github.com/mitodl/ol-infrastructure)
- Should run with a standard python install with `hvac` installed. Alternatively, follow the instructions in ol-infrastructure/README.md. 

## Overview

This document will guide you through the process of setting up your local environment to access the EKS cluster. This will allow you to interact with applications deployed into EKS, including tailing logs and opening a shell into the running containers.

## Extra Reading

For more information about `kubeconfig` files, refer to the Kubernetes documentation [here](https://kubernetes.io/docs/concepts/configuration/organize-cluster-access-kubeconfig/) and [here](https://kubernetes.io/docs/tasks/access-application-cluster/configure-access-multiple-clusters/).

## Steps

1. Within your cloned copy of `ol-infrastructure`, navigate to the `eks` directory at `src/ol_infrastructure/infrastructure/aws/eks`. 
2. There is a script in this directory called `login_helper.py` that will help you set up your local environment to access the EKS cluster. Run this script with the following command:

```bash
python login_helper.py aws_creds
```

3. This will return several `export AWS_` statements on `stdout` that you can then run in your current shell. You need ALL of them. Additionally, it will include the timestamp of when these credentials will expire. By default they expire in one hour, but you can change that to 8 hours with `-d 480` argument. 8 hours is the maximum allowed.

4. After running the `export` commands on your shell, run the following command to generate a `kubeconfig` file:

```bash
python login_helper.py kubeconfig
```

5. This will generate a `kubeconfig` file on `stdout` that will define contexts to all active clusters. Each context is named for the cluster so for example `operations-ci`, `applications-qa`, and so on. 
6. You can save this `kubeconfig` file to your local machine for kubectl to use with the following:

```bash
python login_helper.py kubeconfig > ~/.kube/config
```

7. Additionally, you can specify a default current context with `--set-current-context <context>` argument. 

```bash
python login_helper.py kubeconfig --set-current-context applications-qa > ~/.kube/config
```

8. Or you can set it by hand once you've saved your `kubeconfig` file:

```bash
kubectl config use-context applications-qa
```

9. You can now interact with the EKS cluster using `kubectl`. For example, to list all pods in the `learn-ai` namespace of the `applications-qa` cluster:

```bash
kubectl get pods -n learn-ai
```

## Other Interesting `kubectl` Commands

- Get all the pods for the learn-ai namespace:
```bash
kubectl get pods -n learn-ai
```

- Get all the pods in the learn-ai namespace with more information:
```bash
kubectl get pods -n learn-ai -o wide
```

- Describe a pod, which can tell you interesting things like the pod's IP address, the node it's running on, and the events that have happened to it, as well as the containers that make up the pod:
```bash
kubectl describe pod <pod-name> -n learn-ai
```

- Output the logs of a pod in the learn-ai namespace. `kubectl` will makes its best guess at which container to output logs from:
```bash
kubectl logs <pod-name> -n learn-ai
```

- Be specific and output the logs from the `nginx` container. 
```bash
kubectl logs <pod-name> -n learn-ai -c nginx
```

- `tail` or follow the logs of the nginx container in a pod in the learn-ai namespace:
```bash
kubectl logs -f <pod-name> -n learn-ai -c nginx 
```

- Open a shell into the nginx container of a pod in the learn-ai namespace:
```bash
kubectl exec -it <pod-name> -n learn-ai -c nginx -- /bin/bash
```

