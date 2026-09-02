# Data Platform Notebooks

Browser-based Python notebooks with authenticated access to the OL data
warehouse. Users sign in with MIT OL SSO, get a private environment, and query
the warehouse as themselves.

- **Production** — <https://nb.data.ol.mit.edu>
- **QA** — <https://nb-qa.data.ol.mit.edu>

/// admonition | Not the course-notebook JupyterHub
    type: warning

There are two unrelated JupyterHub deployments. This page covers the **data
platform** one: `nb.data.ol.mit.edu`, the `ol-data-platform` Keycloak realm,
`GenericOAuthenticator`, and marimo notebooks against the warehouse.

The [JupyterHub Admin Guide](jupyterhub_admin_guide.md) covers the **course**
notebooks: `nb.learn.mit.edu`, the `olapps` realm, `TmpAuthenticator`, and
per-course images built from the `ol-notebooks` GitHub Enterprise org. Different
Pulumi stack, different image, different audience.
///

/// admonition | Pending two deployments
    type: warning

This page describes the environment **after** two changes land:
[ol-data-platform#2630](https://github.com/mitodl/ol-data-platform/pull/2630)
(the OAuth2-enabled templates) and
[ol-infrastructure#5700](https://github.com/mitodl/ol-infrastructure/pull/5700)
(which seeds all three template files instead of only `getting_started.py`, and
supplies `TRINO_CATALOG`).

There are three states, and they differ:

- **Neither landed.** `~/notebooks/` holds only a `getting_started.py` that
  authenticates with a Keycloak token Galaxy rejects, so every query 401s and
  the sign-in flow below does not exist yet.
- **#2630 merged and its image published, #5700 not yet applied.** The existing
  hook copies only `getting_started.py` — but from the new image, so a user
  spawning a fresh server gets the working OAuth2 template. `demo.py` and
  `README.md` are still absent.
- **Both applied.** All three files arrive.

In every state, a user who *already* has `~/notebooks/getting_started.py` keeps
their old copy, because the hook uses `cp -n` — see Troubleshooting for the
reseed. Remove this notice once both stacks are deployed.
///

## Audience

Anyone who needs to answer a question from warehouse data that a dashboard
cannot express: analysts, researchers, graduate students, and engineers
prototyping against the dimensional model. No local Python setup, no credential
request, no VPN.

## Getting started

1. Open the environment and sign in through MIT OL SSO.
2. Choose a resource profile. **Standard** (2 CPU / 8 GB) suits almost
   everything; **Large** (4 CPU / 32 GB) is for genuinely heavy local
   computation, not for making queries faster — query work happens on the
   warehouse cluster, not in the pod.
3. Open `getting_started.py` from `~/notebooks/` and run the cells top to
   bottom.
4. The first query prints a Starburst Galaxy login link. Open it, sign in with
   the same SSO account, and the query resumes on its own.

Three files are seeded into every user's `~/notebooks/`:

| File | Purpose |
|---|---|
| `getting_started.py` | Minimal template — signs in, registers the warehouse engine, loads the usual libraries. Copy it to start something new. |
| `demo.py` | Full tour — finding tables, both query styles, star-schema joins, reactive inputs, charts, and the traps. |
| `README.md` | In-notebook quick reference; this page is the fuller version. |

## marimo, not classic Jupyter

The environment runs JupyterLab, so `.ipynb` notebooks still work, but the
templates are [marimo](https://docs.marimo.io) notebooks.

A marimo notebook is a **Python file**, not JSON. It diffs and code-reviews like
source, and `marimo edit --sandbox demo.py` runs it outside JupyterLab. (Plain
`python demo.py` does not: it ignores the PEP 723 header described below, and
the image carries none of the notebook packages, so the connection cell fails on
import. Sandbox mode builds the environment from that header and adds marimo
itself.) It also has no hidden
state: marimo tracks which cells read which variables and re-runs the affected
cells when a value changes, so out-of-order execution — the most common source
of results that cannot be reproduced — is not possible. In exchange, two cells
cannot both define the same name.

The practical upside is `mo.ui`: a dropdown or slider is a value other cells
read, so a parameterised analysis needs no re-run button and no callback
plumbing.

## Sandbox mode: one environment per notebook

Each notebook gets its own isolated Python environment, built from a
[PEP 723](https://peps.python.org/pep-0723/) header at the top of the file:

```python
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "polars>=1.0",
#   "trino[sqlalchemy]>=0.330",
# ]
# ///
```

**`pip install` does not persist.** Packages go in that list, then restart the
kernel. This is deliberate: the header is a complete, versioned record of what
the notebook needs, so it runs the same way for the next person.

The templates ship with polars, pandas, numpy, pyarrow, and altair. Heavier
libraries (scikit-learn, statsmodels, scipy) are intentionally not
pre-declared — adding them per notebook keeps notebooks that do not need them
starting quickly.

## How warehouse authentication works

Two separate sign-ins, which is worth understanding before something looks
broken:

1. **Into the notebook environment.** JupyterHub authenticates the user against
   the `ol-data-platform` Keycloak realm via `GenericOAuthenticator`. This is
   the login at the start.
2. **Into the warehouse.** Starburst Galaxy authenticates query clients
   *itself*, through its own OAuth2 flow, federating the login to the same SSO.
   The notebook prints a link, the user opens it, Galaxy issues its own token.

The second step is not redundant, and this is the part that most often surprises
people:

/// admonition | Galaxy does not accept externally-issued JWTs
    type: danger

JWT authentication against a customer's own JWKS is a Starburst **Enterprise**
feature. Starburst **Galaxy** authenticates query clients only by Galaxy
username/password (including service accounts) over HTTP Basic, or by Galaxy's
own OAuth2 `externalAuthentication` flow in which Galaxy is the authorization
server.

A Keycloak access token handed to Galaxy as a bearer JWT is rejected with
`error 401: b'Authentication required'`. The original template did exactly
that, and no amount of Keycloak audience, scope, or mapper configuration can
fix it — the mechanism does not exist.

See [issue #2624](https://github.com/mitodl/ol-data-platform/issues/2624).
///

The upside of Galaxy owning the handshake is real: queries run as the individual
user, so access is exactly what that user's Galaxy role grants, and queries are
attributable in the audit log.

The token is cached in memory for the life of the kernel, so users sign in once
per session. Restarting the kernel means signing in again.

Only the endpoint is configured for users:

| Variable | Meaning |
|---|---|
| `TRINO_HOST` | Starburst Galaxy endpoint |
| `TRINO_PORT` | `443` |
| `TRINO_CATALOG` | Default warehouse catalog |

`TRINO_USER` is deliberately **not** set. marimo's environment scanner offers a
one-click "Quick add" Trino connection when `TRINO_HOST`, `TRINO_USER` and
`TRINO_CATALOG` are all present, and the snippet it generates uses
`BasicAuthentication` or no auth at all — neither of which Galaxy accepts here.
Setting it would surface a one-click connection that 401s.

## Finding data

The **Explore variables and data sources** panel lists the `warehouse` engine;
expanding it lists schemas and tables. Schemas load on expand rather than up
front — marimo does not eagerly scan a remote warehouse (`trino` is not in its
cheap-discovery list), so an unexpanded tree is not an empty one.

The warehouse is built by dbt in layers, and the schema suffix names the layer:

| Schema suffix | Contents | Query it? |
|---|---|---|
| `_raw` | Untransformed source loads, ~1,400 tables | No — no cleaning, no keys |
| `_staging` | One model per source table, lightly cleaned | Rarely — no conformed keys |
| `_intermediate` | Reusable joins and reshapes | No — implementation detail |
| `_dimensional` | The star schema | **Start here** |
| `_mart` | Purpose-built wide tables per business area | Yes, if one fits |
| `_reporting` | Shaped for specific dashboards | Only to reproduce a dashboard figure |
| `_external` | Extracts shaped for outside consumers | Only if you are that consumer |
| `_integrations` | Payloads for other MIT applications | No |

Within `_dimensional`: `dim_*` is something to group or filter by, `tfact_*` is
a transaction fact (one row per event), `afact_*` is a pre-summarised aggregate
fact, and `bridge_*` is a many-to-many link.

**Most of what you see in the panel is not on that list.** There are also dozens
of `ol_warehouse_production_<username>_*` schemas — developer sandboxes from
`ol-dbt local`, not authoritative and not maintained. If a schema name has a
person in it, it is not for you.


/// admonition | The SCD2 trap
    type: warning

Several dimensions are slowly-changing (type 2): editing a course run writes a
new row and keeps the old one, marked by `effective_date`, `end_date` and
`is_current`. The surrogate key is **stable across versions** — the same
`courserun_pk` appears on the current row and on every historical row.

So a join on the key alone matches every version, and counts multiply by the
number of times that row has been edited. **Every join to an SCD2 dimension
needs `AND <dim>.is_current`.**

This produces plausible wrong numbers rather than an error, which is why
`demo.py` §4 is built around it.
///

## Two ways to query

**SQL cells** — `mo.sql("SELECT ...", engine=warehouse)`. The editor treats it
as SQL with column completion, the result is a dataframe, and the cell joins the
reactive graph so downstream cells update by themselves. One statement, one
result, whole result in memory, no parameter binding.

**The DB-API cursor** — `cur.execute("SELECT ...")`. Ordinary Python: loop it,
build the SQL from a list, stream with `fetchmany`. It also holds
connection-scoped state — `SET SESSION` and `USE` survive on the cursor but not
in a SQL cell, which opens a fresh connection per statement — and `cur.stats` is
how to find out why a query is slow. Returns tuples, no SQL editing support, and
marimo cannot see the dependency.

Reach for a SQL cell. It is not restricted to `SELECT`: `SHOW`, `EXPLAIN` and
DDL run there too, and any statement returning rows comes back as a dataframe.
Drop to the cursor for a loop, a stream, session state, or `cur.stats`.

## Working with personal data

`dim_user` holds names and email addresses. Joining to it is sometimes right,
but neither template does, on purpose — a getting-started file should not
normalise `SELECT *` on a table full of identifiers.

- Aggregate where possible. The fact tables carry `user_fk`, so
  `count(DISTINCT user_fk)` answers most questions about people without
  returning a person.
- Select named columns, never `*`.
- Put a floor on group sizes. A pass rate over four learners identifies them to
  anyone who knows the cohort.
- Home directories are persistent volumes. A CSV of learner rows written there
  outlives the question it was written to answer.
- Queries run as the individual user and are logged.

## Resource limits

|                | Standard | Large |
|----------------|----------|-------|
| CPU            | 2        | 4     |
| Memory         | 8 GB     | 32 GB |
| Home directory | 5 GB persistent (EFS) | 5 GB persistent (EFS) |

After **4 hours idle** the culler stops your whole single-user server — the pod
and JupyterLab with it, not just the kernels — and there is no absolute session
limit. Home directories survive; anything held only in memory does not, and you
sign in to Galaxy again on the next server.

## Sharing work

- `marimo run --sandbox <file>.py` serves the notebook as an app with the code
  hidden — `mo.ui` inputs become the controls. `--sandbox` is what builds the
  environment from the `/// script` header; without it marimo uses the base
  environment, which has none of the notebook packages.
- Export to self-contained HTML, or to `.ipynb` for a Jupyter collaborator.
- The notebook is a `.py` file, so commit it. It reviews like code.

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| `401 Authentication required`, and no login link ever appears | You are on an old `getting_started.py` from before the Galaxy OAuth2 change. The seeding hook uses `cp -n`, so it never overwrites a file you already have — a pre-existing copy is left in place and keeps using the rejected Keycloak token. Delete or rename `~/notebooks/getting_started.py`, then restart your server so the hook reseeds it. Only that file is affected — `demo.py` ships with the OAuth2 flow already, so leave it alone rather than risk your edits. |
| `401 Authentication required` | Galaxy sign-in never completed, or the kernel restarted. Re-run the connect cell and open the link. |
| The login link never appears | It renders as a callout in the cell's own output while the cell blocks. If that output is empty, check the cell's **console** pane — the templates also `print()` the URL as a fallback for when the callout cannot reach the frontend. |
| The login link does not work | Each retry mints a new link and retires the previous one. Re-run the connect cell for a fresh link. |
| `Catalog must be specified` | An unqualified table name with no session catalog. Qualify it, or query through the `warehouse` engine. |
| Counts look too high | A join to an SCD2 dimension missing `AND is_current`. |
| Data sources panel looks empty | Expand `warehouse`; schemas load lazily. An entry reading *no databases available* is a raw DB-API connection and can never show a tree. |
| Query never returns | Missing `LIMIT` on a fact table. `cur.stats` shows what the cluster is processing. |
| `ModuleNotFoundError` right after `pip install` | Sandbox mode. Add the package to the `/// script` header and restart the kernel. |
| Pod will not start | Check the chosen profile; **Large** needs a node with room. Retry with **Standard**. |

## Operating this environment

| Piece | Location |
|---|---|
| Image and notebook templates | [`ol-data-platform/images/marimo-jupyterlab/`](https://github.com/mitodl/ol-data-platform/tree/main/images/marimo-jupyterlab) |
| JupyterHub deployment | [`ol-infrastructure/src/ol_infrastructure/applications/jupyterhub_data/`](https://github.com/mitodl/ol-infrastructure/tree/main/src/ol_infrastructure/applications/jupyterhub_data) |
| Published notebook apps | [`ol-infrastructure/src/ol_infrastructure/applications/marimo_data/`](https://github.com/mitodl/ol-infrastructure/tree/main/src/ol_infrastructure/applications/marimo_data) |
| Keycloak clients (`ol-marimo-client`, `ol-marimo-app-client`) | [`substructure/keycloak/ol_data_platform.py`](https://github.com/mitodl/ol-infrastructure/blob/main/src/ol_infrastructure/substructure/keycloak/ol_data_platform.py) |
| Warehouse models | [`ol-data-platform/src/ol_dbt/models/`](https://github.com/mitodl/ol-data-platform/tree/main/src/ol_dbt/models) |

The image builds and publishes to `ghcr.io/mitodl/marimo-jupyterlab` on every
push to `main` that touches `images/marimo-jupyterlab/`. Templates are baked
into the image at `/usr/local/share/marimo/templates/` and copied into
`~/notebooks/` by a `singleuser.lifecycleHooks.postStart` hook using `cp -n`, so
a user's edited copy on the persistent volume is never overwritten.

### Changing the templates

Edit them in `ol-data-platform`, merge to `main`, wait for the image build, then
restart notebook servers so users pull the new image. Because `cp -n` will not
overwrite, **users who already have a copy keep their old one** — that is the
right trade-off for not destroying someone's work, but it means template fixes
do not reach existing users automatically. Tell them to delete their copy, or
rename the file when a change matters.

### Known gaps

- **Published (run-mode) marimo apps cannot authenticate to Galaxy yet.** The
  `marimo_data` stack provisions the `ol-marimo-app-client` service account for
  Trino access, but client credentials against Keycloak yield a Keycloak JWT,
  which Galaxy rejects for the same reason described above. Published apps have
  no user session, so the OAuth2 flow is not available to them either — they
  need a Galaxy service account. Nothing consumes that Vault secret yet, so
  nothing is broken in production today.
- **All three stacks point `trino_host` at the production Galaxy cluster** while
  the IRSA role grants S3 and Glue on `ol-data-lake-*-<environment>`. Notebooks
  on `nb-ci` and `nb-qa` therefore query production through Trino while holding
  AWS credentials scoped to their own environment — the policy is parameterised
  by `stack_info.env_suffix`, so `nb-ci` gets CI-scoped and `nb-qa` QA-scoped
  access. Either way the two access paths disagree about which environment the
  pod is in.
- **Direct lake access is not authorized or attributed per user.** That IRSA
  policy is attached to one service-account role shared by every single-user
  pod, so a notebook can read a table from S3/Glue even where the user's Galaxy
  role denies it, and CloudTrail records the pod identity rather than their SSO
  identity. The notebook templates deliberately document no direct-read recipe,
  but that is documentation, not a control. Narrowing the role or issuing
  per-user credentials is the actual fix.
