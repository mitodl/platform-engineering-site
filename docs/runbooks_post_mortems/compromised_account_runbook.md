# Compromised Account Response Runbook

This runbook covers suspected or confirmed compromise of MIT Open Learning (OL)
learner, staff, administrator, and service accounts. It is intended for OL
support, application, and Platform Engineering responders.

/// admonition | Contain first, but preserve enough evidence
    type: danger

Disable access and revoke sessions as soon as the affected identity is known.
Before deleting credentials, federated-identity links, tokens, or accounts,
record the minimum information needed to investigate: the stable user ID,
realm/application, credential types, active sessions, roles/groups, relevant
UTC timestamps, and the reported indicators.

**Do not delete or retire the account as an incident-containment step.** Those
workflows are difficult to reverse and may destroy evidence or learner records.
///

## When to use this runbook

Use this runbook when any of the following is reported or observed:

- A user sees logins, profile changes, purchases, enrollments, messages, or
  other activity they did not perform.
- A password, passkey, MFA seed, recovery link, browser session, API token,
  SSH key, or client secret may have been exposed.
- A staff member's email account, browser profile, laptop, or developer
  workstation is lost or compromised.
- An identity-provider administrator reports that one of its users is
  compromised.
- Logs show suspicious authentication, token use, privilege changes, or bulk
  access associated with one identity.

A forgotten password, ordinary lockout, or failed login by itself is an account
recovery issue rather than evidence of compromise. If there is uncertainty,
treat the account as compromised until triage shows otherwise.

## Identity map

An email address is not a globally unique OL identity. The same person can have
records in multiple Keycloak realms, Django applications, Open edX deployments,
and external identity providers. Find and contain every affected record.

| Surface | Primary authentication authority | Important downstream checks |
| --- | --- | --- |
| MIT Learn, learn-ai, MITx Online, and MITx Online Open edX | Keycloak `olapps`; MIT and partner users may be brokered from Touchstone or an organization's OIDC/SAML IdP | APISIX/OIDC sessions, Django sessions, linked Open edX account and OAuth tokens |
| MIT-affiliated MIT Learn users | MIT Touchstone brokered through Keycloak `olapps` | The MIT account must also be remediated by MIT IS&T; Keycloak containment alone is incomplete |
| MIT Learn B2B/organization users | Organization IdP brokered through Keycloak `olapps` | The partner's IdP administrator must disable/revoke the upstream account |
| MITx Pro and xPRO Open edX | MITx Pro's Django account plus its paired Open edX identity/OAuth records | Sessions and tokens on both systems; financial, enrollment, and course activity |
| OCW Studio and ODL Video Service | Keycloak `ol-mit`, normally backed by MIT Touchstone and MIT LDAP group data | Upstream MIT account, Keycloak sessions, and application sessions |
| Platform tools such as Vault, Concourse, Grafana, Airbyte, and Dagster | Keycloak `ol-platform-engineering`, followed by each tool's own session or token | Vault tokens/leases, cloud credentials, CLI tokens, and tool-local sessions |
| Data platform tools such as Superset, OpenMetadata, StarRocks, and JupyterHub | Keycloak `ol-data-platform`, normally brokered from MIT Touchstone | Tool-local sessions, database credentials, exports, and role assignments |
| Keycloak administration | Keycloak `master` realm | Treat as an identity-platform incident; assess all realms, admin events, clients, and secrets |
| Legacy Django/Open edX applications | Application-local password and/or social-auth/OAuth linkage | Django sessions, OAuth access/refresh tokens, linked courseware account, and any local API keys |
| Service accounts and integrations | Keycloak client/service account, application token, Vault secret, cloud IAM identity, or SaaS provider | Every consumer of the credential and every place the old credential can still be accepted |

Architecture changes over time. Confirm the current source of truth in
[`ol-infrastructure`](https://github.com/mitodl/ol-infrastructure) and the
application repository before assuming one logout reaches every system.

## Immediate response checklist

1. **Open or escalate the incident.** A compromised staff, administrator, or
   service account is a security incident. Use `/rootly new` in
   `#team-engineering` when Rootly is appropriate, following the
   [OL Production Outage Runbook](ol_production_outage_runbook.md). Assign an
   incident commander for broad or high-privilege compromise.
2. **Keep sensitive material out of chat and tickets.** Never paste passwords,
   reset links, cookies, bearer tokens, private keys, SAML assertions, or full
   identity documents into Slack, Rootly, GitHub, or support tickets. If the
   incident channel is not restricted, keep sensitive evidence in an approved
   restricted location and link only to it.
3. **Verify the report out of band.** Contact the account owner through a known
   phone number, manager, partner administrator, or other trusted channel. Do
   not rely solely on the potentially compromised account or email inbox.
4. **Identify the account precisely.** Record the environment, realm or
   application, stable user ID, username, normalized email address, identity
   provider, privilege level, and affected services. Search other relevant
   realms and paired applications for the same person.
5. **Preserve minimum volatile evidence.** Record active sessions, credential
   types, federated identity links, roles/groups/organizations, recent login and
   admin events, and the earliest/latest suspected activity in UTC. Do not delay
   urgent containment to gather perfect evidence.
6. **Disable the identity at the authoritative layer.** Follow the appropriate
   section below. For a federated account, disable both the OL-side account and
   the upstream IdP account.
7. **Revoke sessions and tokens downstream.** Disabling a user usually prevents
   new logins but does not guarantee that every existing browser session,
   access token, refresh token, offline token, CLI token, or cloud credential
   stops working immediately.
8. **Protect recovery channels.** If email compromise is possible, do not send
   password-reset or account-recovery links to that mailbox until it has been
   secured. Do not send a temporary password over the same channel that
   reported the compromise.
9. **Scope unauthorized activity.** Review identity, application, cloud,
   source-control, Vault, and SaaS audit trails appropriate to the account.
10. **Recover only after the cause is addressed.** Re-enable access after the
    owner has a trusted device and secure identity provider, all suspect
    credentials are replaced, downstream access is reviewed, and the incident
    commander or responder approves restoration.

## Contain a Keycloak user

The production admin console is at
[https://sso.ol.mit.edu/admin/](https://sso.ol.mit.edu/admin/). Use an approved
administrator identity. Do not use Keycloak impersonation during containment:
it creates more activity under the affected identity and can confuse the audit
trail. See [Impersonating Users in Keycloak](../getting_started_and_how_tos/impersonate_users_keycloak.md)
only for normal support work.

The exact labels can change between Keycloak releases, but the required actions
are the same.

### 1. Locate and verify the user

1. Select the correct realm: `olapps`, `ol-mit`,
   `ol-platform-engineering`, `ol-data-platform`, or, for an administrator,
   `master`.
2. Open **Users** and search by both email and username.
3. Confirm the stable Keycloak user ID and the linked identity provider before
   making changes. Do not act on a same-name account without confirming it.
4. Capture the current enabled state, required actions, organizations,
   groups/roles, federated-identity links, credential types, and sessions.
   Record metadata, not credential values.

### 2. Disable and sign out the user

1. Set **Enabled** to **Off** and save.
2. Open the user's **Sessions** view and sign out all sessions.
3. Check for offline sessions or client-specific sessions and revoke them if
   the console displays them.
4. Confirm that no active user sessions remain.

/// admonition | Session revocation has limits
    type: warning

Keycloak logout invalidates Keycloak sessions and prevents token refresh, but a
previously issued access token can remain usable until the receiving service
re-checks it or the token expires. APISIX and applications may also maintain
their own cookies or sessions. Continue with downstream containment rather than
waiting for natural expiry. The learner `olapps` realm intentionally permits
longer SSO sessions than the staff realms.
///

### 3. Remove or replace suspect credentials

Use the user's **Credentials** view to identify password, OTP, WebAuthn, and
passkey credentials.

- **Keycloak-local password:** remove/reset it and require a new password at the
  next login. Deliver recovery through a verified channel.
- **TOTP:** remove the suspect OTP credential and require enrollment of a new
  authenticator.
- **WebAuthn/passkey:** remove credentials associated with a lost or
  untrusted device. If device ownership is uncertain, remove all passkeys and
  re-enroll them after recovery.
- **Recovery codes:** invalidate and regenerate them if the realm/account uses
  them.
- **Federated identity:** do not delete the link merely to force logout. Disable
  the Keycloak user and remediate the upstream IdP. Removing a valid link can
  cause a duplicate account or unsafe re-linking on the next login. Delete or
  repair a link only when investigation shows that the link itself is
  unauthorized or incorrect.

Keep the account disabled while upstream and downstream remediation continues.

### 4. Review Keycloak events

Review **Realm settings → Events** and the user's event history for:

- Successful and failed logins, identity-provider logins, refreshes, and
  logouts.
- Password resets, email changes, MFA/passkey enrollment, and required-action
  changes.
- New or changed federated-identity links.
- Admin changes to the user, groups, roles, organizations, clients, or realm.
- Unexpected source IP addresses, clients, redirect URIs, and user agents.

Staff-oriented realms currently retain Keycloak events for a limited period,
and Keycloak events are also sent to server logging. Start collection promptly
and ask Platform Engineering to preserve the relevant application and Keycloak
logs. Use UTC in the incident timeline.

## Federated accounts

### MIT Touchstone or MIT LDAP-backed user

Keycloak is a relying party, not the password or MFA authority, for Touchstone
users. This includes MIT users brokered into `olapps` and users of `ol-mit` or
`ol-data-platform`.

1. Disable the Keycloak user and revoke Keycloak sessions immediately.
2. Have the account owner contact MIT IS&T through an independently verified
   channel to secure the MIT account, revoke upstream sessions, replace
   credentials/MFA as directed, and assess the user's devices.
3. If the incident is significant or affects OL administrative access, engage
   MIT's security-response process in addition to OL incident response.
4. Review LDAP-derived group membership (`ol-mit`'s user federation reads from
   MIT's Okta-hosted LDAP, `ldaps://mitprod.ldap.okta.com`; the Keycloak group
   named `moira` is populated by this sync, not by MIT's classic Moira service)
   and Keycloak roles for unauthorized or stale privilege.
5. Keep the Keycloak account disabled until MIT account recovery is confirmed.

Do not attempt to change a Touchstone password in Keycloak. A local credential
on a user that is expected to be federated is worth investigating; it can be an
unexpected alternate login path.

### Partner organization OIDC/SAML user

1. Disable the user and revoke sessions in `olapps`.
2. Contact the partner's known SSO administrator, not contact information
   supplied in the suspicious message.
3. Require the partner to disable the upstream account, revoke its sessions,
   reset credentials/MFA, and report the relevant UTC timeline and indicators.
4. Check whether other users at the organization show the same source IP,
   user-agent, or activity pattern. Escalate from a single-account response if
   the IdP or organization integration may be affected.
5. Do not disable an entire organization or identity provider without incident
   commander approval; doing so affects every partner learner.

## Contain application-local and Open edX accounts

Keycloak containment is not sufficient for every OL product. MITx Pro, legacy
Django applications, and paired Open edX deployments can have their own user
records, sessions, social-auth associations, and OAuth access/refresh tokens.

Ask the owning application engineer to perform the following in each affected
production application:

1. Record the local user ID, username/email, staff/superuser state, social-auth
   links, and paired Open edX username.
2. Set the user inactive or otherwise block authentication without retiring or
   deleting the learner.
3. Invalidate all Django/browser sessions for that user. A password change alone
   is not a substitute for explicit session invalidation.
4. Reset or make unusable any application-local password, as appropriate to the
   recovery plan.
5. Revoke user-specific OAuth access and refresh tokens, including stored
   `OpenEdxApiAuth` credentials and corresponding tokens on the Open edX side.
   Do not immediately regenerate tokens while the account remains compromised.
   This step is not optional cleanup: `django-oauth-toolkit`'s `OAuth2Backend`
   looks up the user by primary key only and does not check whether the user
   is active, so a disabled user's existing bearer tokens keep working against
   the API until the token rows themselves are revoked or deleted.
6. Disable/sign out the paired Open edX user and revoke Open edX sessions or
   tokens if courseware access was in scope.
7. Review social-auth associations before changing them. Remove an association
   only if it was added or altered by the attacker.
8. Inspect profile/email changes, purchases/refunds, enrollments, grades,
   certificates, messages, exports, and staff/admin actions during the incident
   window.

Do not use an account-retirement command to accomplish these steps. Retirement
is a privacy/deletion workflow, not a reversible security lock.

/// admonition | MITx Pro: disabling alone is not durable
    type: warning

MITx Pro's social-auth login pipeline includes an `activate_user` step that
can silently flip a disabled user back to `is_active=True` the next time they
complete login, if export-compliance verification passes or is not enabled.
Setting `is_active=False` by itself is not a durable containment action here.
Use the existing `block_users` management command (adds a hashed-email entry
to the `BlockList` table, enforced earlier in the pipeline at
`validate_email`, before `activate_user` runs) in addition to disabling the
account. Reverse with `unblock_users` only after the account is confirmed
safe to restore.
///

## Staff or administrator workstation compromise

If a staff member's browser profile, laptop, or workstation is compromised,
presume that every credential usable from that device may have been copied.
Keycloak logout is only one part of containment.

In addition to disabling the relevant Keycloak identities, inventory and revoke
as applicable:

- MIT account sessions, passwords, MFA authenticators, certificates, and
  recovery methods through MIT IS&T.
- GitHub sessions, personal access tokens (classic and fine-grained), SSH and
  GPG keys, OAuth app authorizations, and newly added collaborator/deploy-key/
  webhook/Actions-secret access on repositories the user could reach. Review
  the organization audit log, not just the user's own activity, since a
  compromised member account can be used to add persistence elsewhere in the
  org. See [GitHub](#github) below for the shared and automation identities
  that need separate handling.
- Vault tokens, token accessors, and entity aliases; leased credentials,
  wrapped tokens, and any secrets read during the suspected window. See
  [Vault](#vault) below — Keycloak logout does not by itself revoke an
  already-issued Vault token.
- AWS or other cloud sessions, access keys, role assumptions, CLI caches, and
  Kubernetes credentials. Temporary cloud credentials may require an explicit
  deny or permission removal while they age out.
- `fly`, Pulumi, database, package-registry, observability, incident-management,
  and other SaaS/API credentials.
- Local SSH keys, signing keys, `.env` files, shell history, browser password
  stores, and copied recovery codes.

Remove the device from service and follow MIT security guidance before using it
for account recovery. Perform recovery from a known-good device.

### GitHub

GitHub compromise is a direct path to source, CI secrets, and release
pipelines, and it involves more than one identity type:

- **An individual staff GitHub account:** revoke sessions, reset the password
  and 2FA, revoke all personal access tokens and SSH/GPG keys, revoke OAuth
  app authorizations, and review/remove any org access, repository
  collaborators, deploy keys, webhooks, or Actions secrets the account added.
  Check the `mitodl` organization audit log for actions taken by the account,
  not just its own commit history.
- **The shared `mitx-devops@mit.edu` automation account:** this identity backs
  legacy release tooling (the "Doof"/odlbot personal access token, deployed as
  a Heroku config var, with its 2FA stored in Vault under
  `platform-secrets/github`). Because it is shared and high-privilege, treat
  any suspected compromise as organization-wide, not repo-scoped: rotate its
  password/2FA, revoke and reissue the PAT, and update both the Heroku config
  var and the Vault secret. Audit everywhere that account has access, not just
  the service it is known for.
- **The shared GitHub App used for release automation and Concourse CI
  login:** newer release-flow and CI-login integrations authenticate via a
  GitHub App rather than a PAT. Containment here means rotating/regenerating
  the App's private key and reviewing (or temporarily suspending) its org
  installation — hunting for a leaked token string does not apply to this
  identity.

### Vault

Vault's only interactive human authentication path is OIDC through Keycloak's
`ol-platform-engineering` realm — there is no GitHub-based Vault auth (it was
deliberately removed to avoid coupling a GitHub credential compromise to
Vault access). Disabling the Keycloak user stops new Vault logins, but the
readonly/developer/admin OIDC roles issue tokens with an **8-hour, non-
renewable TTL**, so a token issued before containment remains usable for up
to 8 hours unless explicitly revoked. Do not rely on Keycloak disablement
alone:

- Look up and revoke the user's Vault token(s) and entity by accessor
  (`vault token lookup` / `vault token revoke -accessor=...`), or revoke by
  entity (the OIDC roles bind on the `email` claim, so the entity alias is the
  user's email).
- Revoke any leased dynamic secrets (AWS credentials, database credentials,
  etc.) issued during the suspected window rather than waiting for natural
  lease expiry.
- If the identity had elevated (`admin`) policy, treat every secret it could
  read as potentially exposed and assess rotation accordingly.
- Machine identities (EC2 instances authenticating via the per-environment
  `aws-<env>` IAM auth backends) are a separate, non-human path — relevant
  only if a compromised workload, not a user, is in scope.

## Service account, OAuth client, or shared secret compromise

A machine identity often has more consumers and a larger blast radius than a
human account.

1. Identify the exact credential, owner, scopes/roles, environments, issuance
   time, and all consumers. Search infrastructure and application configuration
   by credential name, never by secret value.
2. Disable the service account/client or revoke the exposed credential first
   when doing so will not create a greater safety risk. If an emergency overlap
   is necessary, keep it as short as possible and document it.
3. Create a replacement with the minimum required privilege at the authoritative
   provider.
4. Update the normal encrypted configuration source (SOPS/Vault/provider secret)
   and deploy every consumer. Never put the replacement value in Git, Slack,
   Rootly, command history, or a ticket.
5. Verify consumers are using the replacement, then revoke/delete the old
   credential everywhere it can be accepted.
6. Audit use of the old identity throughout the exposure window. For a Keycloak
   client, include service-account roles, client sessions, protocol mappers,
   redirect URIs, and generated secrets. For a shared signing or IdP key, assess
   every relying party.
7. If the credential could read other secrets, treat those secrets as
   potentially exposed and rotate them according to risk and evidence.

Do not rotate a shared client or signing key blindly. First map its consumers so
that containment does not turn into an avoidable production outage.

## Investigation and impact assessment

Build one UTC timeline across identity and application systems. Preserve raw
records where practical and record query parameters so another responder can
repeat the work.

Check the sources relevant to the account:

- Keycloak user/admin events and Keycloak server logs.
- APISIX access logs and application authentication/audit logs.
- Django admin history, database audit records, Open edX logs, and OAuth token
  records.
- Vault audit logs and leases; AWS CloudTrail and IAM activity; Kubernetes audit
  and workload logs.
- GitHub organization/repository audit logs and recent commits, releases,
  workflow runs, keys, tokens, and membership changes.
- SaaS audit logs for observability, data, CI/CD, support, payment, and incident
  systems reached by the account.

Answer at least these questions:

- What was the earliest plausible compromise and the last unauthorized action?
- Was the password/IdP compromised, or was an existing session/token stolen?
- Which roles, groups, organizations, clients, applications, and environments
  could the identity reach?
- Did the attacker add a credential, MFA method, federated link, API key, SSH
  key, role, group, or recovery method for persistence?
- Was personal, learner, financial, course, source-code, infrastructure, or
  secret data viewed, changed, or exported?
- Were other accounts targeted from the same indicators?
- Which credentials and sessions have been conclusively revoked, and which are
  only waiting to expire?

Engage the appropriate OL privacy, legal, finance, HR, communications, and MIT
security contacts when regulated data, payment activity, employee matters, or
notification obligations may be involved. Do not promise a user that no data
was accessed before the investigation supports that conclusion.

## Recovery

Recover access in this order:

1. Confirm the account owner's identity through a trusted channel.
2. Confirm the upstream email/IdP account and recovery device are secure.
3. Replace passwords, MFA, passkeys, recovery codes, and tokens that may have
   been exposed. Do not reuse a temporary password.
4. Restore only expected identity-provider links, organizations, groups, and
   least-privilege roles, using the pre-containment snapshot as a reference
   rather than blindly restoring every privilege.
5. Re-enable the authoritative account and test login in a separate browser
   profile.
6. Confirm old sessions and credentials no longer work in Keycloak and each
   important downstream service.
7. Re-enable paired application/Open edX accounts and generate new tokens only
   after the primary identity is secure.
8. Monitor authentication and sensitive actions for recurrence.
9. Tell the owner which actions were taken and which behaviors to report, but do
   not disclose unrelated users' data or sensitive detection details.

## Closure criteria

Do not resolve the incident until all applicable items are complete:

- [ ] Every affected identity record and environment was identified.
- [ ] The account was disabled at OL and, when federated, at the upstream IdP.
- [ ] Keycloak, application, Open edX, CLI, cloud, and SaaS sessions or tokens
      were revoked or their residual lifetime/risk was documented.
- [ ] Vault tokens/entity were revoked by accessor (not left to the 8-hour
      OIDC token TTL) and any leased dynamic secrets were revoked.
- [ ] If GitHub was in scope: the individual account's PATs/SSH keys/OAuth
      grants were revoked, or the shared `mitx-devops` PAT and 2FA were
      rotated, or the release-automation GitHub App key was rotated —
      whichever identity was affected.
- [ ] Suspect password, MFA, passkey, API, SSH, client, and recovery credentials
      were replaced or removed.
- [ ] Unauthorized persistence and privilege changes were removed.
- [ ] The investigation window, indicators, affected systems, and data impact
      were documented in UTC.
- [ ] Required privacy, legal, financial, HR, partner, MIT security, and user
      notifications were completed or assigned.
- [ ] Access was restored from a trusted device with least privilege and tested.
- [ ] A monitoring period and owner were assigned.
- [ ] Follow-up work has owners and a retrospective was scheduled when warranted.

## Common mistakes to avoid

- Resetting a password but leaving active sessions, refresh tokens, or passkeys.
- Disabling only the Keycloak shadow user for a compromised federated identity.
- Assuming Keycloak logout immediately invalidates every JWT or application
  cookie.
- Assuming a disabled MITx Pro user stays disabled — the social-auth
  activation pipeline can re-enable it on next login; use `block_users`.
- Assuming Keycloak disablement revokes an already-issued Vault token — Vault
  OIDC tokens are valid for up to 8 hours and must be revoked explicitly.
- Treating a compromised shared automation identity (the `mitx-devops` GitHub
  account, a GitHub App key, or a Keycloak/Vault service account) as scoped to
  one integration instead of auditing everywhere it has access.
- Searching only one realm or only by email address.
- Sending recovery material to a potentially compromised mailbox.
- Deleting federated links, users, or learner records before preserving evidence.
- Using impersonation to test the compromised account.
- Rotating a shared secret before identifying and coordinating all consumers.
- Posting sensitive authentication artifacts in the incident channel.
- Re-enabling a staff account before the endpoint and downstream developer
  credentials are secured.
