# engineering.ol.mit.edu domain hijack

## Overview

- **Author:** Christopher Patti
- **Severity:** SEV1
- **Type:** Domain hijack / security incident
- **Started:** 2026-07-20 11:19 AM
- **Resolved:** 2026-07-20 2:10 PM

## Links

- [GitHub Pages: Configuring a custom domain for your GitHub Pages site](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site)

## Summary

A malicious actor took over the `https://engineering.ol.mit.edu` domain and replaced its content with an unaffiliated website containing undesirable content, including malware and sexually explicit material. The root cause was a stale `CNAME` file left over in a GitHub Pages repository from when the site was previously hosted at `https://pe.ol.mit.edu`. Because the domain was moved to `engineering.ol.mit.edu` without updating that file, and because the domain was likely never properly marked Verified in GitHub Pages, the old `pe.ol.mit.edu` domain mapping was left available for an outside party to claim.

## Impact

Anyone visiting `https://engineering.ol.mit.edu` during the incident window was served malicious/inappropriate content instead of the intended Platform Engineering site.

## Timeline

| Time | Event |
| --- | --- |
| 2026-07-20 11:19 AM | Chris reported in Slack that `https://engineering.ol.mit.edu` appeared to be showing a different site than intended and asked if anyone knew anything. |
| 2026-07-20 2:10 PM | Tobias Macey posted that the site was fixed and all affected domains were verified. |

## Root cause

The `CNAME` file at the root of a GitHub Pages repository is the source of truth GitHub uses to determine which custom domain serves that site. When the site was moved from `pe.ol.mit.edu` to `engineering.ol.mit.edu`, the custom domain setting was updated in the GitHub Pages settings UI, but the `CNAME` file in the repository itself was never updated to match. The old `pe.ol.mit.edu` domain was also likely never properly marked Verified in GitHub Pages. Between the stale `CNAME` reference and the lack of domain verification, `pe.ol.mit.edu` was left in a state that allowed a malicious actor to claim it and serve their own content.

## Lessons learned

- The `CNAME` file at the root of a GitHub Pages repo does **not** change automatically when the custom domain is changed in the settings UI. Updating it is critical any time a GitHub Pages custom domain is changed.
- All domains and subdomains involved, parent and child, must be marked Verified in GitHub Pages. As a result of this incident, we now have `ol.mit.edu` verified in addition to both `pe.ol.mit.edu` and `engineering.ol.mit.edu`.

## Corrective actions

- [x] Update the `CNAME` file to reflect the correct current custom domain.
- [x] Verify `pe.ol.mit.edu` and `engineering.ol.mit.edu` in GitHub Pages.
- [x] Verify the parent `ol.mit.edu` domain in GitHub Pages.
- [x] Audit other GitHub Pages repositories under mitodl for stale `CNAME` files or unverified domains from past migrations.

### Audit results (2026-07-31)

Every mitodl repository with GitHub Pages enabled (20 repos) was checked for a `CNAME` file at its actual Pages publishing source (branch/path), comparing that file's contents against the custom domain configured via the GitHub Pages API, and confirming domain verification status.

Only two repos use a custom domain at all:

- `platform-engineering-site` — `CNAME` file and configured domain both correctly point to `engineering.ol.mit.edu`, and the domain is Verified.
- `webcast.mit.edu` — `CNAME` file and configured domain both correctly point to `webcast.mit.edu`, and the domain is Verified.

No stale or mismatched `CNAME` files and no unverified custom domains were found among the remaining repos (none of which use a custom domain).
