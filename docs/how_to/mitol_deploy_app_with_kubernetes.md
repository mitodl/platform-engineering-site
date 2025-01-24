# Deploying an Application at MIT Open Learning with Kubernetes

## Assumptions

- You'll be deploying an app that includes a
[helm](https://github.com/helm/helm) chart.
- You've installed [helm](https://github.com/helm/helm#install) and [kubectl](https://kubernetes.io/docs/tasks/tools/install-kubectl/).
- You plan to manage your Kubernetes app's infra and deployment with
[Pulumi](https://www.pulumi.com/).

## Questions

- Will you need to create a new Kubernetes cluster along with this new
application you're deploying? Generally we'd like the answer to be "no".

## Structure

### Application

All the files and configuration directly pertaining to the app itself. These
usually live
[here](https://github.com/mitodl/ol-infrastructure/tree/main/src/ol_infrastructure/applications).

For example our Open Metadata application is
[here](https://github.com/mitodl/ol-infrastructure/tree/main/src/ol_infrastructure/applications/open_metadata).

We'll use Open Metadata QA's example to help guide us on a tour of how the
architecture hangs together.

This will generally be your home base for this project.

### Infrastructure

All the component infrastructure required to support your application.

#### Network

General Rules:

- There will only be one EKS cluster in any given VPC
- Pods and EKS nodes share the same subnet
    - Pod + node subnets reside in different availability zones
    - Pod + node subnets should be positioned "in the middle of the VPC"
    - Pod + node subnets are at least  `/21`  -> ~2048 addresses per space
    - Pod + node subnets are 'private'.
      - Outbound connections to the internet are routed through a NAT Gateway placed in one of the 'public' subnets below. 
    - There are at least 4 pod and node subnets per vpc -> at least ~8192 addresses per cluster
- Every 'private' Pod and EKS subnet should be paired with a public subnet.
    - Public subnets are used for load balancers and other services that need to be accessed from the internet
    - Public subnets MAY also contain a NAT gateway which is used by the private subnets for outgoing connections not served by another route.
    - AT LEAST one public subnet must contain a NAT Gateway. 
    - Private subnets MAY reference NAT gateways 'outside their pairing'.
      - This limits the number of NAT gateways required and helps control costs.
    - Public subnets are at least `/24` -> ~256 addresses per space
- Service Address spaces are arbitrary but CANNOT be a subnet of the VPC.
    - Service address spaces do not correspond to an actual AWS 'subnet' resource. 
    - Service address spaces should not overlap from cluster to cluster
    - Service address spaces jump +60 on the third octet for CI->QA->Production
    - Service address spaces are at least `/23` -> ~512 addresses per space


| VPC | CI | QA | Production| 
|--|--|--|--|
| Applications |Services:<br/>10.110.24.0/23<br/>Pods and Nodes:<br/>172.18.128.0/21<br/>172.18.136.0/21<br/>172.18.144.0/21<br/>172.18.152.0/21<br/>Public:<br/>172.18.124.0/24<br/>172.18.125.0/24<br/>172.18.126.0/24<br/>172.18.127.0/24| Services:<br/>10.110.84.0/23<br/>Pods and Nodes:<br/>10.12.128.0/21<br/>10.12.136.0/21<br/>10.12.144.0/21<br/>10.12.152.0/21<br/>Public:<br/>10.12.124.0/24<br/>10.12.125.0/24<br/>10.12.126.0/24<br/>10.12.127.0/24| Services:<br/>10.110.144.0/23<br/>Pods and Nodes:<br/>10.13.128.0/21<br/>10.13.136.0/21<br/>10.13.144.0/21<br/>10.13.152.0/21<br/>Public:<br/>10.13.124.0/24<br/>10.13.125.0/24<br/>10.13.126.0/24<br/>10.13.127.0/24|
| Data |Services:<br/>10.110.22.0/23<br/>Pods and Nodes:<br/>172.23.128.0/21<br/>172.23.136.0/21<br/>172.23.144.0/21<br/>172.23.152.0/21 <br/>Public:<br/>172.23.124.0/24<br/>172.23.125.0/24<br/>172.23.126.0/24<br/>172.23.127.0/24| Services:<br/>10.110.82.0/23<br/>Pods and Nodes:<br/>10.2.128.0/21<br/>10.2.136.0/21<br/>10.2.144.0/21<br/>10.2.152.0/21<br/>Public:<br/>10.2.124.0/24<br/>10.2.125.0/24<br/>10.2.126.0/24<br/>10.2.127.0/24 | Services:<br/>10.110.142.0/23<br/>Pods and Nodes:<br/>10.3.128.0/21<br/>10.3.136.0/21<br/>10.3.144.0/21<br/>10.3.152.0/21 <br/>Public:<br/>10.3.124.0/24<br/>10.3.125.0/24<br/>10.3.126.0/24<br/>10.3.127.0/24 |
| Operations |Services:<br/>10.110.20.0/23<br/>Pods and Nodes:<br/>172.16.128.0/21<br/>172.16.136.0/21<br/>172.16.144.0/21<br/>172.16.152.0/21 <br/>Public:<br/>172.16.124.0/24<br/>172.16.125.0/24<br/>172.16.126.0/24<br/>172.16.127.0/24| Services:<br/>10.110.80.0/23<br/>Pods and Nodes:<br/>10.1.128.0/21<br/>10.1.136.0/21<br/>10.1.144.0/21<br/>10.1.152.0/21 <br/>Public:<br/>10.1.124.0/24<br/>10.1.125.0/24<br/>10.1.126.0/24<br/>10.1.127.0/24| Services:<br/>10.110.140.0/23<br/>Pods and Nodes:<br/>10.0.128.0/21<br/>10.0.136.0/21<br/>10.0.144.0/21<br/>10.0.152.0/21 <br/>Public:<br/>10.0.124.0/24<br/>10.0.125.0/24<br/>10.0.126.0/24<br/>10.0.127.0/24|
| ... | ... | ... | ... |

Example Pulumi Config

```yaml
  operations_vpc:k8s_subnet_pair_configs:
  - public_cidr: 172.16.124.0/24
    private_cidr: 172.16.128.0/21
    nat_gateway_index: 2
  - public_cidr: 172.16.125.0/24
    private_cidr: 172.16.136.0/21
    nat_gateway_index: 2
  - public_cidr: 172.16.126.0/24
    private_cidr: 172.16.144.0/21
    nat_gateway_address: 172.16.126.100
  - public_cidr: 172.16.127.0/24
    private_cidr: 172.16.152.0/21
    nat_gateway_index: 2
  operations_vpc:k8s_service_subnet: 10.110.20.0/23
```

- If `nat_gateway_address` is provided, it must be within the associated `public_cidr`. 
- If `nat_gateway_index` is provided, it must reference the index of a pairing that has `nat_gateway_address` defined. 
- At least one pairing must provide `nat_gateway_address`. 
- A pairing must provide either `nat_gateway_address` or `nat_gateway_index`, but not both.

Networking Configuration YAML
 
 - [src/ol_infrastructure/infrastructure/aws/network/Pulumi.infrastructure.aws.network.CI.yaml](https://github.com/mitodl/ol-infrastructure/blob/main/src/ol_infrastructure/infrastructure/aws/network/Pulumi.infrastructure.aws.network.CI.yaml)
 - [src/ol_infrastructure/infrastructure/aws/network/Pulumi.infrastructure.aws.network.QA.yaml](https://github.com/mitodl/ol-infrastructure/blob/main/src/ol_infrastructure/infrastructure/aws/network/Pulumi.infrastructure.aws.network.QA.yaml)
 - [src/ol_infrastructure/infrastructure/aws/network/Pulumi.infrastructure.aws.network.Production.yaml](https://github.com/mitodl/ol-infrastructure/blob/main/src/ol_infrastructure/infrastructure/aws/network/Pulumi.infrastructure.aws.network.Production.yaml)

#### EKS Cluster

[This](https://github.com/mitodl/ol-infrastructure/blob/main/src/ol_infrastructure/infrastructure/aws/eks/Pulumi.infrastructure.aws.eks.data.QA.yaml) is the beating heart of where your kubernetes cluster is defined in Pulumi.
It contains a multitude of configuration optioons including namespaces defined
in this cluster, what operating environment (e.g. CI, QA, or Production) the
cluster will operate in.

It also contains such details as how Vault ties in, and the instance type (size,
etc) for its workers.

### Substructure

There's not much to configure
[here](https://github.com/mitodl/ol-infrastructure/blob/main/src/ol_infrastructure/substructure/aws/eks/Pulumi.substructure.aws.eks.data.QA.yaml), but the code that this section embodies is
critical. It builds critical path components like SSL certs and the components
(like Traefik and Vault!) that manage them as well as authentication and other
secrets.

## Building the Foundation - EKS Cluster

If you'll need to build a new EKS cluster as we did the data cluster used for
the Open metadata application, you'll need to create the necessary configuration
in the [infrastructure](#infrastructure) and [substructure](#substructure)
sections.

### Networking

You'll need to choose pod and service subnets for your cluster. 

For now, use the example of the data-qa
cluster's definitions and pay attention to the relationship between the subnets
we chose and the VPC subnets they live in.

### Namespace

You'll likely need to add a new namespace for your application whether you're
creating a new cluster or not to the cluster's
[configuration](https://github.com/mitodl/ol-infrastructure/blob/main/src/ol_infrastructure/infrastructure/aws/eks/Pulumi.infrastructure.aws.eks.data.CI.yaml).

## Application

When we deploy our Kubernetes applications with Pulumi we use the [Pulumi
Kubernetes Provider](https://github.com/pulumi/pulumi-kubernetes).

Helm charts are deployed by Pulumi by translating the helm chart into a
[kubernetes.helm.v3.release](https://github.com/mitodl/ol-infrastructure/blob/3321e8499509199ffd2002bd15ac255e6ce3e2c2/src/ol_infrastructure/applications/open_metadata/__main__.py#L295)
object. Click the link about for an example of how we translated Open Metadata's
helm chart. Pay particular attention to the Values dictionary.

## Make It So

We use CI to prove things out. So you'll want to start with that environment.

If your application will require its own EKS cluster, you'll want to build that
first.

So change directories to
ol-infrastructure/src/ol_infrastructure/infrastructure/aws/eks and run pulumi
up.

For instance, were you building the data CI cluster, you'd run:
```bash
pulumi up -s infrastructure.aws.eks.data.CI
```

You'll almost certainly need to fix issues as you go. There's lots of complex
configuration here that can't be covered in a simple doc.

Then you'll want to build the resources in substructure for your project, so
once again for the data CI cluster we'd want to change directory to
ol-infrastructure/src/ol_infrastructure/substructure/aws/eks and run pulumi up.

```bash
pulumi up -s substructure.aws.eks.data.CI
```

Then you'll want to deploy your application. So for OMD as an example, cd to
ol-infrastucture/src/ol_infrastructure/applications/open_metadata and run pulumi
up.

```bash
pulumi up -s applications.open_metadata.CI
```
