# MIT xPRO outage #7

## Overview

- **Author:** Christopher Patti
- **Severity:** SEV1
- **Type:** Customer-facing outage
- **Started:** 2026-06-03 3:38 PM EDT
- **Mitigated:** 2026-06-03 4:38 PM EDT
- **Resolved:** 2026-06-03 4:38 PM EDT

## Links

- [Incident page](https://rootly.com/account/incidents/7-https-xpro-mit-edu-outage)
- [Slack channel](https://slack.com/app_redirect?channel=C0B821X9N3G&team=T04JRPJF6)
- [Preventative fix PR](https://github.com/mitodl/ol-infrastructure/pull/4713)

## Summary

The public xPRO site (`https://xpro.mit.edu`) returned 503 errors because the Kubernetes origin certificate for `xpro-web.odl.mit.edu` expired. The certificate failed to renew because Fastly was incorrectly configured to manage TLS validation for both the public frontend domain and the Kubernetes/APISIX backend origin domain. Fastly's validation CNAME for `_acme-challenge.xpro-web.odl.mit.edu` prevented cert-manager from creating the Let's Encrypt DNS-01 TXT challenge needed to renew the backend certificate.

The immediate mitigation was to manually recreate the cert-manager certificate resources. The durable fix was to change the non-OpenEdX xPRO Fastly TLS subscription so Fastly manages only the public edge certificate for `xpro.mit.edu`, leaving cert-manager responsible for the backend origin certificate for `xpro-web.odl.mit.edu`.

## Impact

Customers could not reliably access the xPRO production site while Fastly could not connect successfully to the Kubernetes/APISIX origin because of the expired origin certificate.

## Detection

At 3:38 PM EDT, alerts fired for both the xPRO Production CMS and the main xPRO application returning 503 errors:

- [CMS alert](https://rootly.com/account/alerts/MIBSZ8)
- [Main xPRO site alert](https://rootly.com/account/alerts/B6RY2m)

Tobias investigated the live Kubernetes and cert-manager state around 4:27 PM EDT. The first diagnosis identified that `xpro-cert` had expired, that the cert-manager ACME order was stale, and that cert-manager was unable to complete the renewal.

A later review identified the missing causal link: the stale DNS-01 challenge failed because Fastly had claimed the `_acme-challenge.xpro-web.odl.mit.edu` record that cert-manager needed to use for the backend origin certificate.

## Root cause

The affected application was the non-OpenEdX xPRO application:

```text
src/ol_infrastructure/applications/xpro/__main__.py
```

Its production configuration used separate frontend and backend domains:

```yaml
xpro:backend_domain: xpro-web.odl.mit.edu
xpro:frontend_domain: xpro.mit.edu
```

in:

```text
src/ol_infrastructure/applications/xpro/Pulumi.Production.yaml
```

`xpro-web.odl.mit.edu` is the Kubernetes/APISIX backend origin domain. Its certificate is managed by cert-manager and Let's Encrypt through DNS-01 validation in Route 53.

However, the Fastly TLS subscription in the non-OpenEdX xPRO app was configured from all Fastly service domains:

```python
domains=xpro_service.domains.apply(
    lambda domains: [domain.name for domain in domains]
),
```

That included both:

- `xpro.mit.edu`, the public Fastly frontend domain
- `xpro-web.odl.mit.edu`, the backend Kubernetes/APISIX origin domain

As a result, Fastly attempted to create DNS validation records for both domains, including:

```text
_acme-challenge.xpro-web.odl.mit.edu CNAME ...
```

That CNAME conflicted with cert-manager's Let's Encrypt DNS-01 TXT challenge for the same backend origin domain. cert-manager could not complete validation, the ACME order eventually became stale, and the existing origin certificate expired.

## Five whys

1. **Why was xPRO returning 503 errors?**
   - Fastly could not connect successfully to the backend origin because the origin certificate had expired.
2. **Why did the origin certificate expire?**
   - cert-manager's renewal attempt for `xpro-web.odl.mit.edu` failed and did not recover before expiry.
3. **Why did cert-manager's DNS-01 validation fail?**
   - Fastly had created a conflicting `_acme-challenge.xpro-web.odl.mit.edu` CNAME.
4. **Why did Fastly create validation DNS for the backend origin?**
   - The non-OpenEdX xPRO Pulumi code passed all Fastly service domains into the Fastly TLS subscription.
5. **Why was this not caught earlier?**
   - We did not have a validation guard or test asserting that backend origin domains managed by cert-manager must not be included in Fastly TLS subscriptions.

## Timeline

| Time | Event |
| --- | --- |
| 2026-03-05 | `xpro-cert` revision 1 was issued with a 90-day validity period. |
| 2026-05-04 | cert-manager entered the 30-day renewal window and created `xpro-cert-2`, including a new CertificateRequest, Order, and DNS-01 Challenge for `xpro-web.odl.mit.edu`. |
| 2026-05-04 to 2026-05-11 | The DNS-01 challenge did not complete because Fastly owned `_acme-challenge.xpro-web.odl.mit.edu` with a CNAME validation record, blocking cert-manager's required TXT challenge. Let's Encrypt eventually deactivated the ACME authorization. |
| Late May / early June 2026 | The challenge remained expired and the Let's Encrypt order became stale / garbage-collected. |
| 2026-06-03 3:29 PM EDT / 19:29 UTC | The Kubernetes/APISIX origin certificate for `xpro-web.odl.mit.edu` expired. |
| 2026-06-03 3:38 PM EDT | Alerts fired for xPRO Production CMS and the main xPRO site returning 503 errors. |
| 2026-06-03 4:08 PM EDT | Rootly incident was created. |
| 2026-06-03 4:16 PM EDT / 20:16 UTC | cert-manager pod restarted and re-evaluated the stale order. |
| 2026-06-03 4:18 PM EDT / 20:18 UTC | cert-manager queried Let's Encrypt and received `404: No order for ID 507326254665`; issuance was marked failed. |
| 2026-06-03 4:27 PM EDT | Tobias investigated the cert-manager state and identified the expired certificate / stale ACME order path. |
| 2026-06-03 4:38 PM EDT | Tobias manually recreated the relevant certificate resources, restoring service. Incident was marked mitigated and resolved. |
| After resolution | Follow-up diagnosis identified the Fastly TLS subscription for the non-OpenEdX xPRO app as the configuration defect. |
| After resolution | PR [mitodl/ol-infrastructure#4713](https://github.com/mitodl/ol-infrastructure/pull/4713) updated the Fastly TLS subscription so Fastly manages only `xpro.mit.edu`. |

## Mitigation and resolution

The immediate mitigation was to delete and recreate the stale cert-manager resources so cert-manager would issue a fresh certificate for the backend origin. That restored service.

The durable fix was to update only the non-OpenEdX xPRO Fastly TLS subscription in:

```text
src/ol_infrastructure/applications/xpro/__main__.py
```

from:

```python
domains=xpro_service.domains.apply(
    lambda domains: [domain.name for domain in domains]
),
```

to:

```python
domains=[frontend_domain],
```

This keeps responsibility separated:

- Fastly manages the public edge certificate for `xpro.mit.edu`.
- cert-manager manages the Kubernetes/APISIX backend origin certificate for `xpro-web.odl.mit.edu`.

No edxapp or xpro-openedx changes were required.

## Corrective actions

- [x] Remove the backend origin domain from the non-OpenEdX xPRO Fastly TLS subscription.
- [x] Deploy the Pulumi update for `src/ol_infrastructure/applications/xpro` Production.
- [x] Trigger or allow cert-manager renewal for the non-OpenEdX xPRO certificate in the `xpro` namespace after the conflicting Fastly validation CNAME is removed.
- [ ] Consider adding tests or policy checks that prevent cert-manager-managed origin domains from being included in Fastly TLS subscriptions.
- [ ] Consider alerting earlier on failed cert-manager CertificateRequests / Orders so stale ACME failures are detected before certificate expiry.

## Deployment notes for the durable fix

```bash
cd src/ol_infrastructure/applications/xpro
pulumi stack select Production
pulumi preview
pulumi up
```

After the Fastly validation CNAME is removed, trigger cert-manager renewal for the non-OpenEdX xPRO certificate in the `xpro` namespace.

## Lessons learned

This outage was initially understood as a cert-manager / ACME renewal failure. That was true but incomplete. The important missing diagnosis was that Fastly had been configured to manage validation for a backend origin domain that belongs to cert-manager.

We should add guardrails around ownership boundaries for TLS certificates and DNS validation records. In particular, public Fastly frontend domains and Kubernetes/APISIX backend origin domains should not be treated as interchangeable service domains when configuring TLS automation.
