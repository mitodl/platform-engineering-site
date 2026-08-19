# Write Performant APIs

A fast API is really two problems: the shape of the response you return, and the cost of the queries
that fill it.

/// admonition | The short version
    type: tip

- Keep response nesting to two levels or less; split deeper data into a second endpoint.
- Paginate every list endpoint, cap the client-supplied page size, and order deterministically.
- Narrow the pagination `count` query to the primary key; it is a second query over your whole
  result set.
- Pick the narrowest prefetch tool that works - `select_related()` for foreign keys,
  `prefetch_related()` for to-many relationships, `prefetch()` for data the model has no direct
  relationship to.
- Declare `required_prefetches` on every serializer so a missing prefetch fails loudly.
- Back a prefetch with a same-named `cached_property` so non-API callers get the same answer.
- Test list APIs with 5-10 records at each level, or the N+1 checks won't fire.
///

## Shape the response

### Keep nesting to two levels

As a rule of thumb, an API shouldn't return an object structure deeper than two levels. If you find
yourself needing more depth, that's a signal consumers should be making a subsequent call to another
API instead.

**Avoid this:**

`GET /api/enrollments/`
```json
[{
    "id": 1,
    "course": {
        "id": 234,
        "topics": [{
            "name": "Chemistry"
        }]
    }
}, {
    "id":2,
    "course": {
        "id": 62,
        "topics": [{
            "name": "Physics"
        }]
    }
}]
```

Two things go wrong here:

- More deeply nested responses are increasingly difficult to write optimized queries for.
- Data is duplicated in-memory on the clients, resulting in a larger runtime footprint and worse
  performance.

**Do this instead** - normalize the data and split it across two calls:

`GET /api/enrollments/`
```json
[{
    "id": 1,
    "course_id": 234
}, ...]
```

`GET /api/courses/?id=234,62`
```json
[{
    "id": 62,
    "topics": [{
        "name": "Physics"
    }]
}, {
    "id": 234,
    "topics": [{
        "name": "Chemistry"
    }]

}]
```

/// admonition | Trade-off: one extra round trip
    type: info

The client makes an extra network request, and gets two things back:

- A much faster initial request, because it's loading less data.
- A cacheable second request - the results from `/api/courses/?id=234,62` may in fact already be
  loaded and not need to be requested at all.
///

### Paginate every list endpoint

Every list endpoint must be paginated. An unpaginated endpoint is a latency and memory cliff that
grows with your data - it passes review, passes tests, passes RC, and then falls over in production
when the table it reads is an order of magnitude larger. "This table is small" is a statement about
today, not about the endpoint.

#### Set one default and opt out explicitly

Define pagination once in a shared module rather than per app. Before
[mit-learn#3106](https://github.com/mitodl/mit-learn/pull/3106), an identical `DefaultPagination`
had been copy-pasted into several apps' `views.py`, so there was no single place to fix any of this.
Consolidating to two implementations was half the point of that change:

```python
# main/pagination.py
from rest_framework.pagination import LimitOffsetPagination


class DefaultPagination(LimitOffsetPagination):
    """Default pagination class for rest APIs"""

    count_fields = ("pk",)

    default_limit = 10
    max_limit = 100

    def get_count(self, queryset):
        """Get the count of objects in the queryset"""
        # we additionally filter this down to a subset of fields
        return queryset.only(*self.count_fields).count()


class LargePagination(DefaultPagination):
    """Large pagination for small resources, e.g., topics."""

    default_limit = 1000
    max_limit = 1000
```

`max_limit` is not optional. Without it, `?limit=100000` defeats the pagination you just configured.

Make it the framework default so a new viewset is paginated without opting in:

```python
REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "main.pagination.DefaultPagination",
}
```

With that set, delete the per-viewset `pagination_class = DefaultPagination` lines - they're now
redundant. Views that genuinely must return an unpaginated list opt out **explicitly**, which keeps
the exemption visible in review instead of implied by an absent setting:

```python
class UserSearchSubscriptionViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    pagination_class = None  # unpaginated by design; preserves the existing interface
```

#### Pick the right pagination class

| Class | Use it for | Watch out for |
| --- | --- | --- |
| `LimitOffsetPagination` | The default for most list APIs | Deep offsets get slower; computes `count` |
| `PageNumberPagination` | APIs whose clients think in page numbers | Same as above |
| `CursorPagination` | Large or append-heavy tables, feeds, exports | Requires a stable indexed `ordering`; no random access to page N |

`LIMIT/OFFSET` does not skip rows for free - Postgres still walks and discards everything before the
offset, so page 500 costs far more than page 1. `CursorPagination` instead filters on an indexed
ordering column, so every page costs the same, and it omits `count` entirely.

/// admonition | Order deterministically or pages will lie
    type: warning

Pagination on a non-deterministic ordering silently duplicates and skips records across pages,
because the database is free to return equal-ranked rows in any order. Always order on something
unique, or append a unique tiebreaker:

```python
queryset = Enrollment.objects.order_by("-created_on", "id")
```
///

#### Keep the count query cheap

/// admonition | `count` is a second query over your whole result set
    type: danger

DRF's paginated response includes a `count`, which it computes as a separate `SELECT COUNT(*)`
wrapping your queryset. That is cheap for a plain filter and expensive once the query carries
aggregations or wide joins - and the cost scales with production data, not with your fixtures.

This is not hypothetical: it is the proximate cause of the
[2026-03-24 MIT Learn outage](../../runbooks_post_mortems/20260324_mitlearn_outage.md), where moving
an aggregation into the main query was fine locally and on RC, then exhausted the production
database's temp space and storage under real cardinality.
///

DRF's default `get_count()` is just `queryset.count()`. When the queryset is `DISTINCT` and carries
annotations, that count wraps a subquery selecting **every** column the page would have selected -
including the joins and aggregates that exist only to produce them. Counting rows needs none of that.
For `/api/v1/featured/` the count query looked like this:

```sql
SELECT COUNT(*)
FROM (
  SELECT DISTINCT "learningresource"."id" AS "col1",
    "learningresource"."created_on" AS "col2",
    -- ... 37 more columns ...
    COUNT("learningresourceviewevent"."id") AS "_views_count",
    "learningresourcerelationship"."position" AS "position"
  FROM "learningresource"
  LEFT OUTER JOIN "learningresourceviewevent" ON (...)
  INNER JOIN "learningresourcerelationship" ON (...)
  WHERE (...)
)
```

Narrowing the count to the primary key - the `get_count()` override in `DefaultPagination` above -
reduces it to this, dropping the view-event join and its aggregate entirely:

```sql
SELECT COUNT(*)
FROM (
  SELECT DISTINCT "learningresource"."id" AS "col1",
    "learningresourcerelationship"."position" AS "position"
  FROM "learningresource"
  INNER JOIN "learningresourcerelationship" ON (...)
  WHERE (...)
) subquery;
```

**On that endpoint the count went from ~500ms to ~0.3ms.** Don't expect ~1000x everywhere - the win
is that the count stops going to disk for data it never needed and can often be served from indexes
alone.

/// admonition | Widen `count_fields` when `DISTINCT` is doing real work
    type: warning

`count_fields` is a class attribute precisely so it can be overridden. Narrowing to `pk` preserves
the count when the `DISTINCT` already includes a unique column, because the row count can't change.

If a queryset is `DISTINCT` over *non-unique* columns specifically to collapse duplicate rows, then
dropping columns changes what "distinct" means and therefore changes the count. Subclass and widen
`count_fields` to include the columns the distinctness depends on.
///

If you need an aggregate in the response, prefer computing it outside the paginated queryset, or use
`CursorPagination`, which doesn't count at all.

## Load the data efficiently

### Pick the right prefetch tool

| Tool | Use it for | Cost |
| --- | --- | --- |
| `select_related(...)` | Foreign key relationships only | Joins onto the main query |
| `prefetch_related(...)` | One-to-many and many-to-many relationships | A separate query per relationship |
| `prefetch(...)` | Nested data the model has no direct relationship to | A separate query per prefetcher |

### `select_related()` vs `prefetch_related()`

It is possible to overuse `select_related()` to the point that you're actually harming performance -
too much data and too many joins will slow down the main query. It's best to profile the difference.

**When in doubt, reach for `prefetch_related()`** - splitting the work into a separate query is the
safer default.

### `prefetch()` for indirect relationships

`prefetch()` extends Django's prefetching capabilities via the
[`django-prefetch`](https://pypi.org/project/django-prefetch/) library. A prefetcher is good to reach
for when you need to fetch data that the base model does not directly depend on.

#### The data model

An enrollment relates to a course, and a course to programs - but an enrollment has no direct
relationship to a program:

```mermaid
erDiagram
    direction LR
    Enrollment }|--|| Course : in
    Course }|--|{ Program : in
    Program {
        string title
    }
```

#### Writing a prefetcher

A prefetcher is a join Django can't express, executed in Python. The hooks are the two sides of that
join:

1. `mapper()` runs over the objects already in your queryset and computes one **key** for each.
2. `filter()` receives all the distinct keys at once and returns the related rows in a single query.
3. `reverse_mapper()` runs over those related rows and says which keys each one belongs to.
4. The library matches the two sets of keys and calls `decorator()` to attach the results.

| Hook | Returns | Purpose |
| --- | --- | --- |
| `mapper(obj)` | one hashable key | The join key for an object in your queryset. Defaults to `obj.pk`. |
| `filter(keys)` | `QuerySet` | One query fetching every related row for all the collected keys |
| `reverse_mapper(related)` | `list` of keys | The keys a related row belongs to |
| `decorator(obj, related=None)` | `None` | Attaches the matches to the base object |
| `collect` | `bool` | Set `True` when several objects can share a key |

The asymmetry between the two mappers is deliberate: **`mapper()` returns a single key, while
`reverse_mapper()` returns a list of them**, because one related row can belong to many of your
objects. In the example below a `Program` contains many courses, so its `reverse_mapper` hands back
every course id in the program.

`collect` defaults to `False`, which keeps only one object per key - if two objects in your queryset
produce the same key, only the last of them gets decorated. Set it to `True` whenever `mapper()`
isn't unique across the queryset, as here, where several enrollments can share a course.

```python
from django.contrib.postgres.aggregates import ArrayAgg
from prefetch import Prefetcher, PrefetchManagerMixin, PrefetchQuerySet

class ProgramTitlesPrefetcher(Prefetcher):
    collect = True

    def mapper(self, enrollment):
        return enrollment.course_id

    def filter(self, ids):
        if not ids:
            return Program.objects.none()
        # one query to fetch everything
        return Program.objects.filter(
            course__id__in=ids
        ).annotate(
            # postgres-specific aggregation
            course_ids=ArrayAgg("course__id")
        ).only("title")  # only the fields we will use

    def reverse_mapper(self, program):
        return program.course_ids

    def decorator(self, enrollment, programs=None):
        enrollment.program_titles = [program.title for program in programs] if programs else []

# NOTE: this is named mixin, but it's actually a subclass of models.Manager
class EnrollmentManager(PrefetchManagerMixin):
    prefetch_definitions = {
        "program_titles": ProgramTitlesPrefetcher
    }

class Enrollment(models.Model):

    objects = EnrollmentManager()


# Now you can do this and it will only perform 2 queries
Enrollment.objects.prefetch("program_titles")
```

/// admonition | Footguns
    type: danger

- **Return an explicit empty queryset when there are no keys.** Otherwise you risk weird edge cases
  where `filter()` returns the entire table.
- **Give `decorator()`'s related argument a default.** It is called once for *every* object with no
  related argument at all, and then a second time only for the objects that matched - so the default
  you supply is the final answer for everything that matched nothing.
- **Don't use a key that can be falsy.** Matching skips falsy keys, so a key of `0` or `""` silently
  drops the relation. Tuples are safe here: any non-empty tuple is truthy.
///

#### Joining on a composite key

The key is only ever used as a dictionary key, so it just has to be hashable. An `int` or `str`
covers most cases - but when the relationship is identified by more than one column, return a
**tuple**.

mitxonline's certificate and grade prefetchers join on `(run, user)` rather than a single id
([`courses/models.py`](https://github.com/mitodl/mitxonline/blob/main/courses/models.py)):

```python
class CourseRunEnrollmentCertificatePrefetcher(Prefetcher):
    """Prefetcher for CourseRunEnrollment certificates"""

    @staticmethod
    def mapper(course_run_enrollment):
        """Map each enrollment to (run_id, user_id)"""
        return (course_run_enrollment.run_id, course_run_enrollment.user_id)

    @staticmethod
    def filter(course_run_and_user_ids):
        if not course_run_and_user_ids:
            return CourseRunCertificate.objects.none()

        id_filters = Q()

        # django 5.1 supports this via
        # django.db.models.fields.tuple_lookups.{Tuple,TupleIn}
        for course_run_id, user_id in course_run_and_user_ids:
            id_filters |= Q(course_run_id=course_run_id, user_id=user_id)

        return CourseRunCertificate.objects.filter(id_filters)

    @staticmethod
    def reverse_mapper(certificate):
        return [(certificate.course_run_id, certificate.user_id)]

    @staticmethod
    def decorator(course_run_enrollment, certificates=None):
        course_run_enrollment._certificate = certificates[0] if certificates else None
```

Three things to notice:

- **`reverse_mapper()` still returns a list**, just a one-element one - a certificate belongs to
  exactly one `(run, user)` pair. Contrast the program prefetcher above, which returns many keys.
- **A composite key can't be a single `__in` lookup**, so `filter()` ORs the pairs together with `Q`.
  On Django 5.1+ you can express this directly with
  `django.db.models.fields.tuple_lookups.{Tuple,TupleIn}`.
- **`mapper()` is unique per enrollment here**, so these prefetchers leave `collect` at its default.

`decorator()` writes to `_certificate` rather than `certificate`, because `certificate` is a
`cached_property` that falls back to querying when the prefetch didn't run - see
[making one property work with and without a prefetch](#make-one-property-work-with-and-without-a-prefetch).

#### Custom `QuerySet`s

`PrefetchManagerMixin` overrides `get_queryset()` and builds the queryset from
`get_queryset_class()`, which is hardcoded to return `PrefetchQuerySet`. It never looks at
`_queryset_class` - the attribute `models.Manager.from_queryset()` sets.

**So `models.Manager.from_queryset(EnrollmentQuerySet) + PrefetchManagerMixin` is not enough on its
own.** The mixin's `get_queryset()` wins the MRO, hands back a plain `PrefetchQuerySet`, and your
custom queryset is silently ignored - its methods then raise `AttributeError` at the call site. You
have to name the queryset a second time:

```python
class EnrollmentQuerySet(TimestampedModelQuerySet, PrefetchQuerySet):
    ...

class EnrollmentManager(
    models.Manager.from_queryset(EnrollmentQuerySet), PrefetchManagerMixin
):
    """Base manager class for enrollments"""

    @classmethod
    def get_queryset_class(cls):
        return EnrollmentQuerySet
```

Two requirements, both load-bearing:

- **The queryset must subclass `PrefetchQuerySet`.** `PrefetchManagerMixin.get_queryset()` passes
  `prefetch_definitions=` to the constructor, and `.prefetch()` only exists there.
- **`get_queryset_class` must be a `@classmethod`**, matching the mixin's own declaration.

Naming `EnrollmentQuerySet` in both places looks redundant, but the two do different jobs:
`from_queryset()` copies the queryset's methods onto the manager, while `get_queryset_class()`
decides what the manager actually instantiates. mitxonline repeats this pattern for every
prefetch-enabled model - see `CourseManager`, `CourseRunManager`, and `EnrollmentManager` in
[`courses/models.py`](https://github.com/mitodl/mitxonline/blob/main/courses/models.py).

### Make one property work with and without a prefetch

A prefetch only happens on the queryset that asked for it. The same derived data is usually also
wanted from a celery task, a management command, the admin, or a shell session - none of which went
through your API's queryset. Writing it twice means two implementations that can drift apart.

One `cached_property` can serve both paths. `cached_property` is a **non-data descriptor** - it
defines `__get__` but not `__set__` - so if the instance's `__dict__` already holds that name, the
property body never runs. Both of Django's `Prefetch(..., to_attr=...)` and django-prefetch's
`Prefetcher.decorator()` fill `__dict__` with a plain `setattr`. Give the property the same name as
the prefetch and you get the prefetched value when it's there and a query when it isn't, with no
extra wiring.

This is a supported pattern, not a trick: Django's prefetch machinery explicitly checks
`to_attr in instance.__dict__` rather than `hasattr()` when the attribute is a `cached_property`,
specifically so it doesn't trigger the fallback while deciding whether the value is already loaded.

#### With `prefetch_related()`

If you only need to *read* a relation, you need none of this - `.all()` already uses a warm prefetch
cache and queries when there isn't one:

```python
class Course(models.Model):
    @cached_property
    def topic_names(self) -> list[str]:
        return [topic.name for topic in self.topics.all()]
```

/// admonition | Filtering after `.all()` bypasses the prefetch cache
    type: warning

`self.topics.filter(published=True)` ignores a warm cache and issues a fresh query for every object -
the N+1 you thought you had prefetched away. Either filter in Python over `.all()`, or move the
filter into the prefetch itself.
///

Moving the filter into the prefetch is where `to_attr` earns its keep. Prefetch under the same name
the property uses:

```python
Course.objects.prefetch_related(
    Prefetch("topics", queryset=Topic.objects.published(), to_attr="published_topics")
)
```

```python
from django.utils.functional import cached_property

class Course(models.Model):
    @cached_property
    def published_topics(self) -> list["Topic"]:
        # Fallback: runs only when the prefetch above didn't fill __dict__.
        return list(self.topics.published())
```

- **Prefetched** - `to_attr`'s `setattr` filled `__dict__`, so the property never runs.
- **Not prefetched** - the property runs, queries for this one course, and caches the result on the
  instance.

#### With `prefetch()`

Same mechanism, for the indirect case from above - `decorator()` does the `setattr` instead of
`to_attr`:

```python
class Enrollment(models.Model):
    objects = EnrollmentManager()

    @cached_property
    def program_titles(self) -> list[str]:
        # Fallback: runs only when prefetch("program_titles") didn't fill __dict__.
        return list(
            Program.objects.for_course_ids([self.course_id]).values_list("title", flat=True)
        )
```

Either way callers just read `course.published_topics` or `enrollment.program_titles` and never need
to know which path they got.

#### Keep the two paths querying the same thing

The pattern is only safe if both paths mean the same thing by the data. Put the predicate in one
queryset method and call it from both, rather than writing the filter twice:

```python
class TopicQuerySet(models.QuerySet):
    def published(self):
        return self.filter(published=True)

class Topic(models.Model):
    objects = TopicQuerySet.as_manager()
```

Now `Prefetch("topics", queryset=Topic.objects.published(), ...)` and the `cached_property`'s
`self.topics.published()` share one definition of "published topics", so a change to the predicate
can't reach only one of them. The same discipline applies to a `Prefetcher.filter()` - have it call
the same queryset method with all the collected ids at once.

/// admonition | The fallback is the N+1 you were avoiding
    type: warning

Per-object querying is exactly what prefetching exists to prevent. That's a fine trade in a celery
task walking a handful of records, and unacceptable in a list API.

The real danger is that the fallback is *silent* - a missing prefetch doesn't raise, it just quietly
issues one query per row. That is why serializers declare
[`required_prefetches`](#require-prefetches-in-serializers): it turns the silent N+1 back into a loud
failure on the path where it matters.
///

### Require prefetches in serializers

Subclass `mitol.common.serializers.BaseSerializer` and define `required_prefetches`. If you don't
define it, a `RequiredPrefetchesNotDefinedError` is raised on serializer init:

```python
from mitol.common.serializers import BaseSerializer

class EnrollmentSerializer(BaseSerializer):
    required_prefetches: list[str] = [
        "program_titles"
    ]
```

This ensures the serializer can't be used without that prefetch having been done - otherwise it
raises a `RequiredPrefetchMissingError` naming the prefetch that wasn't requested. A "prefetch" in
this situation is anything that should be `prefetch()`, `prefetch_related()`, or `select_related()`.

/// admonition | The escape hatch is not for API code
    type: danger

Tests and async code such as celery tasks can opt out by passing
`{"skip_prefetch_checks": THIS_IS_NOT_AN_API}`. As the name (and you) attests to, this should not be
used _anywhere_ near an API - including when other serializers call it, since DRF propagates the
context into child serializers as well.
///

## Test it

### Give N+1 checks enough data

Projects are set up with N+1 checks on tests. To ensure these checks can detect problems, make sure
you test APIs with data of enough cardinality.

For a list API, create 5-10 records at each level of the response. Taking `/api/courses/?id=234,62`
from above, that means creating several courses and then several topics per course. If you use a
lower count, the quantity may not exceed the N+1 checker's detection thresholds.

## Resources

- [Django: `select_related()`](https://docs.djangoproject.com/en/stable/ref/models/querysets/#select-related)
- [Django: `prefetch_related()`](https://docs.djangoproject.com/en/stable/ref/models/querysets/#prefetch-related)
- [Django: `Prefetch` objects](https://docs.djangoproject.com/en/stable/ref/models/querysets/#prefetch-objects)
- [Django: `cached_property`](https://docs.djangoproject.com/en/stable/ref/utils/#django.utils.functional.cached_property)
- [DRF: Pagination](https://www.django-rest-framework.org/api-guide/pagination/)
- [mit-learn#3106: Query for less data on pagination count](https://github.com/mitodl/mit-learn/pull/3106)
- [`django-prefetch`](https://pypi.org/project/django-prefetch/)
- [2026-03-24 MIT Learn outage post-mortem](../../runbooks_post_mortems/20260324_mitlearn_outage.md)
