# HTTP 406 errors on cart endpoints

## Overview

- **Author:** Michael Davidson
- **Severity:** P3
- **Type:** Customer facing
- **Cause:** Configuration change
- **Environment:** Production
- **Functionality:** E-Commerce/Enrollment
- **Service:** MITx Online - Django - Webapp
- **Team:** Platform Engineering, Engineering
- **Started:** 2026-08-05 4:35 PM
- **Detected:** 2026-08-07 1:46 PM
- **Acknowledged:** 2026-08-07 1:51 PM
- **Mitigated:** 2026-08-07 2:12 PM
- **Resolved:** 2026-08-07 2:12 PM
- **Total elapsed:** 1d 21h

## Links

- [Slack thread where the incident was handled](https://mitodl.slack.com/archives/C02649X2P1V/p1786124814875349)
- [mitodl/ol-infrastructure#5243 — allow anonymous access to `/cart` in mitxonline](https://github.com/mitodl/ol-infrastructure/pull/5243)
- [mitodl/ol-infrastructure#5244 — add missing wildcard route to mitxonline anonymous checkout](https://github.com/mitodl/ol-infrastructure/pull/5244)
- [mitodl/ol-infrastructure#5313 — revert of #5243 (the fix)](https://github.com/mitodl/ol-infrastructure/pull/5313)
- [mitodl/hq#12530 — tracking issue](https://github.com/mitodl/hq/issues/12530)

## Summary

On August 5th, 2026, at 4:35 PM, a change was made to the MITx Online APISIX configuration. This change inadvertently caused HTTP 406 errors on the cart endpoints, affecting users' ability to complete their purchases. The issue was detected on August 7th, 2026, at 1:46 PM and was acknowledged shortly after at 1:51 PM. The mitigation steps were implemented by 2:12 PM on the same day, resolving the issue.

## Impact

Users who attempted to access the cart endpoints during the affected period received HTTP 406 errors, preventing them from completing their transactions. This led to a temporary disruption in the e-commerce functionality of the MITx Online platform, potentially affecting user satisfaction and revenue.

## Detection

This incident was caught by a person paying attention, not by our monitoring.

User issues were reported in the lead up to detection by Chris C., however they were not reproducible by Peter and the association between those user reports and this outage was not made.

No alert fired for the elevated 406 rate on the cart endpoints. The bad routing configuration was live in production from 2026-08-05 4:35 PM and went unnoticed by automated alerting for the full 1 day 21 hours that followed. At 2026-08-07 1:46 PM, Chris C. noticed the rise in 406 errors and raised it with `@sre` in Slack:

- [Slack thread where the incident was handled](https://mitodl.slack.com/archives/C02649X2P1V/p1786124814875349)

Note also that the failure mode was quiet by nature. A 406 on the cart endpoints does not take the site down or produce a visible error page for every visitor, so it generated no groundswell of user reports to compensate for the missing alert. Filling that alerting gap is the leading corrective action below.

## Root cause

Two APISIX routing changes to the MITx Online direct route group in `src/ol_infrastructure/applications/mitxonline/__main__.py`, both merged on 2026-08-04 and deployed to production on 2026-08-05:

- [mitodl/ol-infrastructure#5243 — allow anonymous access to `/cart` in mitxonline](https://github.com/mitodl/ol-infrastructure/pull/5243)
- [mitodl/ol-infrastructure#5244 — add missing wildcard route to mitxonline anonymous checkout](https://github.com/mitodl/ol-infrastructure/pull/5244)

PR #5243 reordered the checkout flow to be "anonymous first." It renamed the existing `cart` route to `checkout-anonymous` and swapped its paths:

```python
OLApisixRouteConfig(
    route_name="cart",
    priority=20,
    hosts=[api_domain, frontend_domain],
    paths=[
        "/cart/",
        "/cart",
        "/cart/*",
    ],
```

became:

```python
OLApisixRouteConfig(
    route_name="checkout-anonymous",
    priority=20,
    hosts=[api_domain, frontend_domain],
    paths=[
        "/checkout/anonymous",
        "/checkout/anonymous/",
    ],
```

PR #5244 then added `/checkout/anonymous/*` to that route's paths so it would catch its own request-path-relative OIDC callback (`/checkout/anonymous/.apisix/redirect`) rather than relying on the pass-auth `/*` route to complete it.

The net effect of #5243 is that `/cart` no longer has a dedicated APISIX route with the `unauth_action="auth"` OIDC gate. It now falls through to the pass-auth wildcard route, which carries a different plugin configuration than the route that previously served it — and that is where the HTTP 406 responses on the cart endpoints originate.

## Timeline

| Time | Event |
| --- | --- |
| 2026-08-05 4:35 PM | [Concourse `deploy-ol-application-mitxonline-production` build 63](https://cicd.odl.mit.edu/teams/infrastructure/pipelines/mitxonline-pipeline/jobs/deploy-ol-application-mitxonline-production/builds/63) deployed the #5243 / #5244 APISIX route changes to production. |
| 2026-08-07 1:46 PM | Chris C. alerts @sre on Slack about the rise of 406 errors. |
| 2026-08-07 1:51 PM | Tobias acknowledges Chris' message. |
| 2026-08-07 2:01 PM | Tobias commits and deploys a revert of the routing change (#5313) to production. |
| 2026-08-07 2:12 PM | Chris C. verifies the fix. |

## Mitigation and resolution

The incident was mitigated and resolved by reverting the routing change:

- [mitodl/ol-infrastructure#5313 — Revert "move APISIX auth gate from /cart to /checkout/anonymous" (#5243)](https://github.com/mitodl/ol-infrastructure/pull/5313)

Merged 2026-08-07 2:01 PM, followed by a `pulumi up` against the mitxonline `Production` stack. The revert restored the `cart` route as the OIDC login gate on the direct route group and dropped the `checkout-anonymous` route entirely:

```python
OLApisixRouteConfig(
    route_name="cart",
    priority=20,
    hosts=[api_domain, frontend_domain],
    paths=[
        "/cart/",
        "/cart",
        "/cart/*",
    ],
```

This was not a straight `git revert`. Because #5244 had added `/checkout/anonymous/*` on top of #5243's change to the same path list, the revert was resolved manually to also remove that wildcard and restore the original three `/cart*` paths. The KEDA request-rate doc comment above `create_webapp_prometheus_trigger_auth` was reverted alongside it, since it describes the live route matcher and the route name changed back.

The revert restored the pre-incident behavior — `/cart` is once again gated behind OIDC login rather than falling through to the pass-auth wildcard route. The anonymous-checkout work it undoes ([mitodl/hq#12530](https://github.com/mitodl/hq/issues/12530)) remains outstanding and will need to be re-landed with the 406 cause addressed first.

## Corrective actions

### Detection

- [ ] Add an alert on elevated 4xx rates by APISIX route for MITx Online. Detection here was entirely human — Chris noticed the 406s and raised them with `@sre` 45 hours after the deploy. Nothing paged. **Owner:** @tobias

### Re-landing the anonymous checkout work

- [ ] We don't need to reland this work in MITx Online provided we implement this change in Learn. **Owner:** Carey

### Preventing recurrence of this class of change

- [ ] Development used a non-standard APISIX configuration locally, rather than the default. Switching over to `local-dev` resolves this issue. **Owner:** Carey to poll `local-dev` to the team
- [ ] APISIX configuration exists twice, once in the application repo as yaml config and once in the ol-infrastructure repo as code. **Owner:** None, addressed by the adoption of `local-dev`

### Incident management

- [ ] Better incident management practices. This incident didn't really follow the incident management practices we are trying to implement. We need to make sure that we are following the incident management practices we have in place. **Owner:** Chris Patti, incident management seats cost $$$

## Lessons learned

- **Removing a route is a change to whichever route absorbs its traffic.** #5243 was reviewed as "add an anonymous checkout gate," but its larger effect was moving all `/cart` traffic onto the pass-auth wildcard and its different plugin configuration. The wildcard route was never part of the review.
- **Our alerting is keyed to availability, not correctness.** The site was up and most routes were serving 200s, so a single endpoint class returning 406 for 45 hours triggered nothing. Quiet, partial failures need signals of their own.
- **Route names are load-bearing beyond routing.** The same rename touched the KEDA request-rate matcher and the Grafana route labels, and the flip back three days later moved them again. Renaming a route has blast radius outside the route definition. Rather than doing stringly based types, we should extract the names that we rely on into a single source of truth and reference them from there. A shared constant between the APISIX route definition and the KEDA config.
