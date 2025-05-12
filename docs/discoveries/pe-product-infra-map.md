# This Document Will Help Map Formal Product Names To Infrastructure

## Projects That Live In Kubernetes

| Formal Product Name   | Kubernetes Cluster    | Environments (e.g. CI, QA, Production)  |
|-----------------------|-----------------------|-----------------------------------------|
| MIT Learn             | Applications          | CI, QA, Production                      |
| MIT Learn AI          | Applications          | CI, QA, Production                      |
| MITx Online           | Applications          | CI, QA, Production                      |

## Pre K8s Projects

Nota Bene: For infra like Consul or Vault, we're not enumerating each combination because
you get the idea :)

| Formal Product Name   | EC2 Instance Greoup Name      |       Deployment Technology     |
|-----------------------|-------------------------------|---------------------------------|
| MIT x Residential     | edxapp-worker-mitx-production,|       docker compose            |
|                       | edxapp-web-mitx-production,   |       docker compose            |
| ODL Video Service     | odl-video-service-production  |       docker compose            |
| OpenEdX Forum V2      | open-edx-forum-server-production|                               |
| Consul                | consul-mitx-production        |                                 |
| OpenEdX Notes         | edx-notes-server-mitx-production|     docker compose            |
| Hashicorp Vault       | vault-server-operations-production|                             |

