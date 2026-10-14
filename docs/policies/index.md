---
title: "Policies"
---
# Policies

These policies set the rules MIT Open Learning engineering follows to change,
operate and secure its production systems. They describe how we work today and
link to the guides and runbooks that explain the details. Where a policy sets a
new requirement, the requirement applies from the date the policy was adopted.

## Scope

These policies apply to:

- **Platform Engineering**: AWS accounts, EKS clusters, Pulumi-managed
  infrastructure, Concourse, Vault, Keycloak, Fastly, and the other shared
  platform services.
- **MIT Learn**: the MIT Learn application, its API, frontends and supporting
  services (including learn-ai), and the people who build and operate them.

## Policies

| Policy | ID prefix | Owner | Last reviewed |
|---|---|---|---|
| [Change Management](change-management.md) | `CM` | Platform Engineering | 2026-10-13 |
| [Incident Response](incident-response.md) | `IR` | Platform Engineering | 2026-10-13 |
| [Patch Management](patch-management.md) | `PM` | Platform Engineering | 2026-10-13 |
| [Vulnerability Management](vulnerability-management.md) | `VM` | Platform Engineering | 2026-10-13 |

Each requirement has an ID (for example `CM-3`) so it can be cited in audits,
issues and exceptions.

## Changing a policy

1. Open a pull request against this repository with the change.
2. Platform Engineering, which owns all of these policies, reviews and approves
   it.
3. Update the policy's **Last reviewed** date here and in the policy's
   *Review* section.

Every policy is reviewed at least once a year, and after any SEV1 incident
that shows a gap in it.

## Exceptions

When a requirement can't be met, record an exception as a GitHub issue in
[mitodl/hq](https://github.com/mitodl/hq) before (or, in an emergency, as soon
as possible after) the deviation. The issue must name:

- the requirement ID,
- why it can't be met and the risk it leaves,
- any compensating control,
- who in Platform Engineering approved it, and
- an expiry date, no more than six months out.

Expired exceptions must be renewed or closed.
