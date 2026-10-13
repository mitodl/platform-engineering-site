# Incident Response Policy

## Purpose

Detect, respond to and recover from incidents that affect availability,
integrity or confidentiality of our systems quickly and consistently, and
learn from every significant incident.

## Scope

Any unplanned interruption or degradation of a production service in scope of
these [policies](index.md), and any suspected or confirmed security incident:
unauthorized access, credential compromise, data exposure, or malicious
activity against our systems or accounts.

## Roles and responsibilities

These are the incident roles in Rootly, described in the
[OL Production Incident Response Runbook](../runbooks_post_mortems/ol_production_outage_runbook.md).

| Role | Responsibility |
|---|---|
| On-call engineer | Acknowledges alerts, triages, and opens an incident when needed. |
| Incident leader | Coordinates the response, decides on mitigation, approves emergency changes ([`CM-7`](change-management.md)). Usually the Platform Engineering on-call. |
| Communicator | Keeps stakeholders and the status page up to date. |
| Contributor | Investigates and fixes as directed by the leader. |
| Platform Engineering | Owns this policy, and makes sure post-mortems are written and corrective actions are completed. |

## Severity levels

| Severity | Definition | Examples |
|---|---|---|
| SEV1 | A production service is down or unusable for most users, data loss or corruption is happening, or a security incident is confirmed. | Site outage, expired production certificate, domain hijack, compromised admin account. |
| SEV2 | A major feature is broken or badly degraded for many users, with no reasonable workaround. | Checkout failing, login broken for one identity provider. |
| SEV3 | A feature is degraded or broken for a subset of users, or a workaround exists. | Errors on a single endpoint, slow dashboards. |
| SEV4 | Minor issue with little user impact. | Cosmetic errors, a non-critical background job failing. |

## Requirements

**IR-1. Alerts route to on-call through Rootly.**
Production alerts from Grafana, Sentry and uptime checks are sent to Rootly,
which pages the on-call engineer according to the escalation policies kept in
code ([Managing Rootly](../monitoring_observability/rootly_management.md)).
Responders follow the [On-Call Runbook](../runbooks_post_mortems/oncall_runbook.md)
for known alerts.

**IR-2. Acknowledge within the target time.**

| Severity | Acknowledge within |
|---|---|
| SEV1 | 15 minutes, any time |
| SEV2 | 1 to 2 hours, any time |
| SEV3 | Next business day |
| SEV4 | 2 business days |

**IR-3. Open an incident when a problem isn't mitigated quickly.**
If a production problem isn't mitigated within five minutes, or any security
incident is suspected, open an incident with `/rootly new` in
`#team-engineering`. Rootly creates the incident channel, timeline and action
items. All incident communication happens in that channel.

**IR-4. Follow the incident phases.**
Incidents move through Triage, Active, Mitigated and Resolved in Rootly. The
leader sets the severity during triage and updates it if the impact changes.

**IR-5. Keep users informed.**
For SEV1 and SEV2 incidents, the communicator updates the status page with
`/rootly update_status_page` when the incident starts, when it's mitigated and
when it's resolved.

**IR-6. Contain security incidents first and preserve evidence.**
For a suspected compromise, follow the
[Compromised Account Response Runbook](../runbooks_post_mortems/compromised_account_runbook.md).
In order:

1. **Contain** the attacker's access: disable sessions, revoke tokens and
   rotate exposed credentials.
2. **Preserve evidence**: keep the logs, the affected accounts and any other
   artifacts the investigation needs. Disable affected accounts; don't delete
   or retire them.
3. **Investigate and recover** only once access is contained and the evidence
   is safe.

**IR-7. Escalate security incidents.**
Confirmed security incidents, including any exposure of personal data or
credentials, are reported to MIT IS&T Security (<security@mit.edu>) by the
incident leader as soon as possible, and no later than 24 hours after
confirmation. Platform Engineering decides with MIT IS&T whether
users or other parties must be notified.

**IR-8. Write a post-mortem.**
A blameless post-mortem is required for every SEV1 incident (which includes
every confirmed security incident). For SEV2 incidents, one is written if it's
warranted, as decided by the incident leader. For SEV3 and SEV4 it's optional.
The incident leader publishes it in [Runbooks & Post-Mortems](../runbooks_post_mortems/ol_production_outage_runbook.md)
within five business days of resolution. It covers the summary, impact,
detection, root cause, timeline, mitigation and corrective actions. The
[2026-08-10 post-mortem](../runbooks_post_mortems/20260810_http_406_errors_on_cart_endpoints.md)
is a good example.

**IR-9. Track corrective actions to completion.**
Corrective actions from a post-mortem are filed as GitHub issues with an owner,
and Platform Engineering reviews open actions until they're closed.

## Exceptions

Handled as described in [Policies: Exceptions](index.md#exceptions).

## Related documents

- [OL Production Incident Response Runbook](../runbooks_post_mortems/ol_production_outage_runbook.md)
- [On-Call Runbook](../runbooks_post_mortems/oncall_runbook.md)
- [Compromised Account Response Runbook](../runbooks_post_mortems/compromised_account_runbook.md)
- [Emergency Oncall Break Glass Procedure](../getting_started_and_how_tos/emergency-break-glass.md)
- [Managing Rootly](../monitoring_observability/rootly_management.md)
- [Change Management Policy](change-management.md)

## Review

| Owner | Version | Last reviewed |
|---|---|---|
| Platform Engineering | 1.0 (draft) | 2026-10-13 |
