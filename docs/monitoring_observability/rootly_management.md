# Managing Rootly with ol-rootly-manager

[Rootly](https://rootly.com/) is our on-call and incident management platform. It handles alert routing, escalation policies, service definitions, status pages, and incident workflows. We manage Rootly configuration as code using the [`ol-rootly-manager`](https://github.com/mitodl/ol-rootly-manager) Python CLI.

## Why code-managed Rootly config?

Rootly's web UI is easy to use but makes drift and accidental changes hard to detect. Managing configuration in code gives us:

- **Auditability** — every change is a commit with a diff and author
- **Idempotency** — safe to re-run; nothing is created twice
- **Bulk edits** — add or rename a service across hundreds of alert routes in one pass
- **Review workflow** — changes go through PRs before they reach production Rootly

## Repository

```
~/src/mit/ol-rootly-manager/
├── main.py        # CLI entrypoint
├── data.py        # exported Rootly state (source of truth for --import)
├── pyproject.toml
└── uv.lock
```

## Setup

Requires Python 3.14+ and [uv](https://docs.astral.sh/uv/).

```bash
export ROOTLY_API_KEY=<your-api-key>
```

Retrieve the API key from the team Vault path or 1Password vault. The key needs read/write access to all Rootly resource types.

## Commands

### `--report`

Prints a human-readable summary of every resource currently in Rootly — services, roles, teams, alert sources, alert routes, and escalation policies.

```bash
uv run python main.py --report
```

Use this for a quick sanity check after applying changes, or to look up a resource ID without going to the UI.

### `--export`

Fetches all Rootly resources and writes them to `data.py` as Python data structures. This is **read-only** against Rootly; it only overwrites the local file.

```bash
uv run python main.py --export
```

Run this to capture the current live state before making edits, or to pull in changes that were made through the Rootly UI and reconcile them back into the file.

### `--import [FILE]`

Creates or updates Rootly resources from a Python data file (defaults to `data.py`). The operation is idempotent — existing resources are updated and missing ones are created.

```bash
uv run python main.py --import           # uses data.py
uv run python main.py --import my_data.py
```

This is the primary write path. Edit `data.py`, review the diff, then run `--import` to apply.

### `--pulumi-import [FILE]`

Generates a [Pulumi bulk-import JSON file](https://www.pulumi.com/docs/cli/commands/pulumi_import/) listing every Rootly resource with its Pulumi type and UUID. **Strictly read-only.**

```bash
uv run python main.py --pulumi-import                  # writes pulumi_imports.json
uv run python main.py --pulumi-import my_imports.json
```

See [Migrating to Pulumi IaC](#migrating-to-pulumi-iac) below.

## The day-to-day workflow

```
export ──► edit data.py ──► import
```

1. Run `--export` to capture current state into `data.py`
2. Edit `data.py` directly — add services, adjust alert route rules, update escalation policies, etc.
3. Run `--import` to apply the changes

For large structural changes (new application launch, team reorganisation), commit `data.py` changes in a PR so they get reviewed before being applied.

## Resource types managed

| Resource | What it controls |
|---|---|
| **Services** | Named components (e.g. `MIT Learn - Django Webapp`) that alerts and incidents attach to |
| **Teams** | On-call groups; own services and receive escalations |
| **Roles** | Incident roles (Incident Commander, Communications Lead, etc.) |
| **Alert Sources** | Inbound integrations (Datadog, CloudWatch, Sentry, etc.) |
| **Alert Routes** | Rules that match incoming alerts and route them to services |
| **Escalation Policies** | Who gets paged and in what order when an alert fires |

## Alert routing in depth

Alert routes are the most complex resource. Each route is attached to one or more alert sources and contains an ordered list of **rules**. Each rule has:

- A **condition group** — one or more payload field checks (e.g. `$.Message.AlarmName contains "learn-ai"`)
- A **destination** — the service (or team) the matching alert is tagged to

Example rule from our CloudWatch route:

```python
{
    'name': 'learn-ai AlarmName to MIT Learn AI - Django Webapp',
    'condition_type': 'all',
    'condition_groups': [{
        'conditions': [{
            'property_field_type': 'payload',
            'property_field_name': '$.Message.AlarmName',
            'property_field_condition_type': 'contains',
            'property_field_value': 'learn-ai',
        }]
    }],
    'destination': {'target_type': 'Service', 'target_id': '<uuid>'},
}
```

Rules are evaluated top-to-bottom; the first match wins. A rule with `fallback_rule: True` catches anything that did not match an earlier rule.

---

## Using LLMs to map alerts to services

Alert routing is a judgment call: given an alert name or payload, which of our ~50+ services should own it? When setting up new alert sources or reviewing unmapped alerts, we use Claude to accelerate this work.

### The general pattern

1. Run `--export` to get fresh data in `data.py`
2. Open a Claude Code session in the repo directory
3. Feed Claude the relevant context and ask for routing suggestions
4. Review Claude's output, edit `data.py`, and run `--import`

### Mapping a new alert source

When a new integration (e.g. a new CloudWatch namespace) starts sending alerts and none of the existing rules cover its alarm names:

```
Open ol-rootly-manager in Claude Code.

Prompt:
"Look at the SERVICES list in data.py and the ALERT_ROUTES list.
 Here are the CloudWatch alarm names coming in from our new ECS namespace:
   - mitlearn-ecs-api-cpu-high
   - mitlearn-ecs-worker-memory
   - mitlearn-ecs-redis-connections
 Suggest alert route rules (in the same dict format as the existing rules
 in ALERT_ROUTES) that tag each alarm to the most appropriate service."
```

Claude will read the service names and existing route patterns from `data.py`, infer naming conventions, and generate ready-to-paste rule dicts. Review them, adjust the `target_id` UUIDs to match the correct services (use `--report` to look up IDs), then paste into the relevant route in `data.py`.

### Auditing coverage gaps

To find alarms that are routing to the fallback rule (i.e. not matched by any specific rule):

```
Prompt:
"Read ALERT_ROUTES in data.py.
 Which routes have a fallback rule? List all services in SERVICES that
 do NOT appear as a destination target_id in any route rule."
```

This surfaces services that exist but will never receive a routed alert — usually meaning either the service is new and routes haven't been written yet, or the service name changed and old route rules are pointing to a stale UUID.

### Bulk renaming or restructuring services

When a service is renamed (e.g. `XPro - Open edX - LMS` → `MIT XPro - LMS`) or split into sub-services, alert route rules that reference the old service by UUID need updating:

```
Prompt:
"In data.py, the service named 'MIT XPro - Open edX - LMS - Webapp' is
 being split into two services: 'MIT XPro - LMS - Webapp' and
 'MIT XPro - LMS - Celery Worker'.
 Identify every alert route rule whose destination target_id is <old-uuid>
 and suggest which of the two new services each alarm name most likely
 belongs to, based on the rule name and condition values."
```

### Generating descriptions for undocumented services

Many services in `data.py` have blank `description` fields. Claude can suggest descriptions based on naming conventions and context from your other services:

```
Prompt:
"Look at the SERVICES list in data.py. For every service where description
 is an empty string, suggest a one-sentence description based on the
 service name and the descriptions of similar services.
 Output as a Python list of (name, suggested_description) tuples."
```

### Tips for effective LLM-assisted Rootly work

- **Always export first.** Claude works from the file on disk; stale state leads to wrong suggestions.
- **Name-based matching is reliable.** Our alarm names (e.g. `mitlearn`, `learn-ai`, `xpro`, `rds`) closely follow our service naming conventions, so Claude can match them accurately without deep Rootly knowledge.
- **Verify UUIDs.** Claude can identify the right service by name, but UUIDs must be confirmed — use `--report` or search `data.py` after Claude gives you a service name.
- **Review before importing.** Treat Claude's output as a first draft. Check that each `target_id` maps to a real service and that rule ordering makes sense (more specific rules before broader ones).
- **Commit the result.** After a successful `--import`, commit `data.py` so the change is tracked.

---

## Migrating to Pulumi IaC

The tool can generate a Pulumi bulk-import file to bring Rootly resources under Infrastructure as Code management in `ol-infrastructure`.

```bash
uv run python main.py --pulumi-import
# then, from the Pulumi monitoring stack directory:
pulumi import --file /path/to/pulumi_imports.json --generate-code
```

Once imported, Pulumi owns those resources. Manual UI edits will be **reverted** on the next `pulumi up`. The recommended approach is to start with one resource, verify `pulumi preview` shows no diff, then expand from there.

See the `README.md` in `ol-rootly-manager` for the full Pulumi import workflow.

## Related

- [Monitoring Overview](overview.md)
- [Rootly API docs](https://docs.rootly.com/api)
- [ol-rootly-manager repository](https://github.com/mitodl/ol-rootly-manager)
