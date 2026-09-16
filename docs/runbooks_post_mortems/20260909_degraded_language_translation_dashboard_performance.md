# Degraded language translation dashboard performance #17

## Overview

- **Author:** Peter Pinch
- **Severity:** P2
- **Type:** Customer-facing performance degradation
- **Functionality:** MIT Learn
- **Started:** 2026-09-09 10:18 AM EDT
- **Mitigated:** 2026-09-09 3:11 PM EDT
- **Resolved:** 2026-09-09 3:11 PM EDT

## Links

- [Incident page](https://rootly.com/account/incidents/17-degraded-dashboard-performance)
- [Slack channel](https://slack.com/app_redirect?channel=C0C064DMHMM&team=T04JRPJF6)
- [mitodl/mitxonline#3939 — optimize course API pagination query](https://github.com/mitodl/mitxonline/pull/3939)
- [mitodl/hq#11517 — `/api/v2/courses/` performance is poor](https://github.com/mitodl/hq/issues/11517)
- [Production Grafana query for contract-filtered course API response times](https://mitolproduction.grafana.net/explore?schemaVersion=1&panes=%7B%228g6%22:%7B%22datasource%22:%22grafanacloud-logs%22,%22queries%22:%5B%7B%22refId%22:%22A%22,%22expr%22:%22quantile_over_time%280.99,%20%7Bcontainer%3D%5C%22apisix%5C%22%7D%20%7C%3D%20%60request_uri%3D%2Fmitxonline%2Fapi%2Fv2%2Fcourses%2F%3F%60%20%7C%3D%20%60contract_id%3D%60%20%7C%20logfmt%20%7C%20unwrap%20request_time%20%5B$__auto%5D%29%20by%20%28service_name%29%22,%22queryType%22:%22range%22,%22datasource%22:%7B%22type%22:%22loki%22,%22uid%22:%22grafanacloud-logs%22%7D,%22editorMode%22:%22builder%22,%22direction%22:%22backward%22%7D%5D,%22range%22:%7B%22from%22:%22now-12h%22,%22to%22:%22now%22%7D,%22panelsState%22:%7B%22logs%22:%7B%22visualisationType%22:%22logs%22%7D%7D,%22compact%22:false%7D%7D)

## Summary

On September 9, 2026, a language translation organization's learner dashboard loaded much more slowly than expected and was at times unusable. The dashboard depends on MITx Online's contract-filtered `/api/v2/courses/` endpoint. For the affected production-shaped request, the pagination count query exceeded the 10-second PostgreSQL statement timeout and could produce HTTP 504 responses.

The team replaced expensive aggregate annotations in the course queryset with a correlated `Exists` expression. This reduced the affected count query to approximately 0.06 seconds, but the full endpoint still took approximately 4.2 seconds because serializing the deeply nested response required hundreds of database queries. Production response times had already improved before the change reached production, so the deployment cannot be credited as the cause of the immediate recovery. The precise trigger for the transient 9:00–11:00 AM slowdown was not established.

## Impact

Learners using organization dashboards backed by large contracts experienced slow page loads, and some dashboards were unusable. Contract-filtered course API requests could time out with HTTP 504 responses. The incident record does not establish how many users or organizations were affected.

## Leadup

The authenticated `/api/v2/courses/` endpoint was already known to perform poorly when filtered by an organization or contract, especially for contracts containing many courses and course runs. That ongoing problem was tracked in [mitodl/hq#11517](https://github.com/mitodl/hq/issues/11517).

The endpoint returns a deeply nested data structure. The amount of work grows with the number of courses, and the serializer performed roughly four to eight queries per course. At a page size of 100, the endpoint could execute approximately 350–400 queries for one response.

## Fault

Two distinct performance problems were present:

1. The paginator's count query inherited course-run aggregate annotations. Joining those aggregates across thousands of course runs caused the count query for the affected contract to exceed PostgreSQL's 10-second statement timeout.
2. After the count query was optimized, constructing the full API response still required approximately 391–408 queries. No individual query was exceptionally slow; the accumulated work kept the endpoint slow.

The aggregate count was a confirmed defect and a contributor to HTTP 504 responses. However, production metrics showed that the incident-period latency spike subsided before the fix was deployed. The data available during the incident therefore did not identify the trigger for that transient spike.

## Detection

The incident was opened in Rootly at 10:18 AM EDT after reports that learner dashboards were loading slowly or were unusable. Investigation focused on the MITx Online course-list request used by the affected dashboard. The team used production query measurements, a production-shaped contract in RC, Sentry traces, and Grafana response-time data to distinguish the count-query timeout from the endpoint's broader query-volume problem.

## Five whys

1. **Why was the language translation dashboard slow or unusable?**
   - Its contract-filtered `/api/v2/courses/` request was slow and could return a 504.
2. **Why could the course API request time out?**
   - The pagination count query included expensive aggregate joins across thousands of course runs and exceeded the 10-second statement timeout for the affected dataset.
3. **Why did the endpoint remain slow after that count query was optimized?**
   - Building the nested response still required hundreds of ORM queries, roughly four to eight per course.
4. **Why did the first fix not fully address the user-visible latency?**
   - It targeted the known count-query timeout, not the separate query-volume problem in response serialization.
5. **Why did production improve before the fix was deployed?**
   - The incident evidence did not establish a cause. Grafana showed elevated response times from roughly 9:00–11:00 AM followed by recovery before the production rollout.

## Timeline

All times are EDT on September 9, 2026.

| Time | Event |
| --- | --- |
| 10:18 AM | Peter Pinch created Rootly incident #17, set the incident start time, and Rootly created the incident Slack channel. |
| 10:25 AM | MIT Learn was added as the affected functionality. |
| 10:31 AM | Peter asked about a suspected contract-configuration problem. Christopher Patti reported that the production 504 came from the PostgreSQL course-list query: aggregate joins over thousands of course runs caused the pagination count to exceed 10 seconds. Replacing the aggregates with `Exists` reduced the production-shaped count to approximately 0.06 seconds and the full endpoint to approximately 4.2 seconds. No production Redis changes were made. |
| 10:43 AM | Nathan Levesque noted that the data queried grows rapidly with the number of courses. Christopher proposed [mitodl/mitxonline#3939](https://github.com/mitodl/mitxonline/pull/3939) to remove expensive aggregate joins while preserving certificate-availability behavior with a correlated `Exists` subquery. |
| 10:44 AM | Rootly attached PR #3939 to the incident. |
| 11:53 AM | James Kachel supplied a larger RC contract for validation. Christopher reported that Nathan had approved PR #3939 and that it had merged as commit `3ec3dde9`. |
| 12:15 PM | Christopher confirmed that the fix had reached QA. |
| 12:23 PM | Christopher reported that Nathan was validating the fix in RC. |
| 12:58 PM | Nathan began the production rollout. |
| 1:13 PM | Nathan reported that the affected API was not measurably faster in production. |
| 1:21–1:22 PM | Pipeline evidence confirmed that PR #3939 had reached production. Because the user-visible improvement was not apparent, the team continued investigating instead of treating deployment as proof of mitigation. |
| 1:24–1:28 PM | Nathan identified the remaining query-volume problem: approximately four to eight queries per course and about 350 queries at a 100-course page size. A Sentry trace showed a four-second response without one dominant slow query. Nathan's draft follow-up reduced the request to a fixed 18 queries. |
| 1:33–1:34 PM | Christopher summarized the distinction: the original count no longer exceeded the 10-second timeout, but approximately 391–408 queries per response still explained the poor overall performance. |
| 1:36 PM | Nathan confirmed that the deeply nested response structure compounded the query count and began reevaluating the broader optimization. |
| 1:38 PM | Chris Chudzicki measured the originally reported dashboard's course API response at approximately two seconds. |
| 1:39 PM | Nathan measured responses as slow as approximately six seconds for the MIT contract. |
| 1:41–1:42 PM | Christopher asked for confirmation from the original reporter before declaring the user-visible problem fixed. |
| 1:48 PM | Peter contacted the Sales stakeholders for confirmation. Nathan reported that performance was better, but Grafana showed the contract-filtered endpoint's latency spike occurring around 9:00–11:00 AM and improving before the deployment, so the recovery did not correlate with PR #3939. Peter proposed moving the incident to monitoring. |
| 1:49 PM | Christopher agreed that the incident could move to monitoring and that the remaining endpoint optimization should become a post-incident action item. |
| 1:50 PM | The public MIT Learn status page was updated to **Monitoring**: “We have deployed a performance fix. We are monitoring the affected Learner dashboards.” Nathan added the Grafana query to the incident record. |
| 1:53 PM | Christopher asked Peter to report back after hearing from the stakeholders so the incident could be resolved. |
| 1:56 PM | Christopher linked [mitodl/hq#11517](https://github.com/mitodl/hq/issues/11517) as the post-incident work for authenticated, organization-filtered, and contract-filtered `/api/v2/courses/` performance. |
| 2:13–2:15 PM | Christopher proposed closing the incident barring objections, with a new incident to be opened if users continued to experience the problem. |
| 3:11 PM | Rootly marked the incident mitigated and resolved. |

## Mitigation and resolution

The team merged and deployed [mitodl/mitxonline#3939](https://github.com/mitodl/mitxonline/pull/3939). The change:

- removed two unused course-run aggregate annotations from the course querysets;
- replaced the verified-course-run aggregate count, which was only used as a boolean, with a correlated `Exists` expression; and
- applied the optimization to both the v2 and internal course querysets.

This eliminated the demonstrated pagination-count timeout. The team then monitored production, requested confirmation from the original stakeholders, and moved the public status to Monitoring. Rootly marked the incident resolved at 3:11 PM.

The deployment fixed a real timeout-producing query, but it did not explain the incident's immediate recovery because the production latency spike had already subsided. The remaining full-response performance problem is tracked separately.

## Corrective actions

- [x] Replace the aggregate-based pagination count with a correlated `Exists` expression and deploy it to production ([mitodl/mitxonline#3939](https://github.com/mitodl/mitxonline/pull/3939)).
- [ ] Reduce the number of ORM queries required by authenticated organization- and contract-filtered `/api/v2/courses/` requests ([mitodl/hq#11517](https://github.com/mitodl/hq/issues/11517)). **Owner:** Nathan Levesque

## Lessons learned

- **A genuine bottleneck is not necessarily the whole incident.** The aggregate count exceeded the database timeout and needed to be fixed, but removing it left hundreds of smaller queries in the full request path.
- **Deployment is not proof of mitigation.** Pipeline status proved that the code reached production; Grafana showed that the observed recovery happened earlier. The team correctly avoided attributing the recovery to the deployment.
- **Validate the complete user path.** Query-level measurements, endpoint traces, and confirmation from the original reporter answer different questions and were all needed before resolution.
- **Large contracts expose scaling behavior that small datasets hide.** The larger RC contract and production-shaped query were necessary to reproduce the count-query problem and evaluate the fix.
