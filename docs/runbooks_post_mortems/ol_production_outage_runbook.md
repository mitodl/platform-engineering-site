# OL Production Incident Response Runbook

This runbook serves as a guide to best practices for handling production incidents at MIT OL.

## What is a production outage incident?

Any production outage where functionality we and our users expect is not working or not working as expected such that
users' productivity is impacted.

## When to open an incident

Once a production outage is reported and is not mitigated within five minutes, the following sequence of events should
be set in motion.

## Who can create a Rootly incident?

Right now only Peter Pinch and members of DevOps can create Rootly incidents. Expanding this to all of engineering is
under consideration, but the associated per-seat costs are a constraint.

## Opening the incident

In the `#team-engineering` Slack channel, the on-call types:

```
/rootly new
```

Rootly will prompt you for everything you need from there. Incident name, severity, etc. You should include the
environment in the incident name — production, in this case.

Creating the incident automatically does several things for us:

- Creates a new Slack channel specific to the incident, e.g. `#mitlearn-production-db-outage`
- Records all Slack traffic during the incident
- Creates a timeline
- Tracks action items during and after the incident

The incident Leader and whoever created the incident then invite everyone involved to that channel and assign roles.
In addition to the on-call, make sure the developers for the affected product area are pulled in.

## Start a Zoom call (optional)

A Zoom call is **optional** and at the Leader's discretion. It is most useful for severe or fast-moving incidents where
real-time coordination among key participants beats typing. Many incidents are handled perfectly well in Slack alone.

If the Leader does start one, ensure the invite link is posted in the incident Slack channel, and the Communicator
should echo key points from the discussion into Slack so they are captured in the incident record. Anything decided on
the call that never makes it into Slack is invisible to the retrospective.

## Incident lifecycle phases

Every incident moves through four phases. The Leader decides when a phase advances and communicates that to everyone
involved.

- **Triage** — the initial investigation of the incident after it is reported. This phase is complete when the Leader
  understands the "shape" of the outage. Precisely what systems are affected? Are there any obvious cascade effects?
  How severe is the outage?
- **Active** — the Leader understands the dimensions of the outage and all necessary data is being gathered to proceed
  to mitigation. All observable effects are documented in the Slack channel. Concordance around the path to mitigation
  is reached and the Leader assigns tasks to actually mitigate the issue causing the outage.
- **Mitigated** — the Leader and Contributors concur that all metrics and other observations indicate that the outage
  is ended and functionality has returned to normal.
- **Resolved** — stakeholders have validated that functionality has returned to normal and the incident officially
  concludes. Post-incident work begins.

## What are the roles and their responsibilities?

### Leader

This person will "run" the incident. This will usually be the current DevOps on-call but could potentially be anyone.

Responsibilities include:

- Keeping things focused and crisp. When a production incident is in progress we all need to treat it like our house is
  on fire. Because **it is**.
- Assigning tasks as appropriate. That way people can stay focused but the incident can progress through the various
  phases: Triage, Active, Mitigated and Resolved.
- Acting as the sole point of contact for the Communicator so they can update stakeholders and, after Mitigation,
  ensure that the pain is stopped so the incident can conclude and be Resolved.

### Communicator

This should be someone who is not directly involved in mitigation. During a severe or prolonged outage it is difficult
to focus on mitigation while also handling administrative tasks, responding to Slack pings from interested third
parties and the like.

Responsibilities include:

- Identifying key end user stakeholders, ideally including the people who reported the incident.
- Keeping time. At reasonable intervals the Communicator reminds everyone involved how long the incident has been open.
  This helps keep everyone on track and aware of the fact that a serious problem is afoot that demands their attention.
  It also helps surface when a given mitigation is taking too long and a different approach may be warranted —
  ultimately the Leader's judgment, but it can be hard to avoid tunnel vision in stressful situations.
- Keeping said stakeholders updated during the incident as progress is made.
- Working with stakeholders after Mitigation takes place to ensure their pain is at an end.
- Updating the Rootly status page as appropriate. See below.

#### Updating the status page

Use the `/rootly update_status_page` Slack command. Rootly will prompt you to select the status page, choose the
affected components, set the incident impact level, and provide a message describing the current situation. Key updates
include which systems are affected and what functionality is affected, as well as the current lifecycle phase.

You will need to update the status page as the incident moves through each lifecycle phase. Coordinate with the Leader
to clearly understand when the phase advances.

When the outage is resolved, **the status page must be updated again to close out the incident and return the page to
its normal state.** Run `/rootly update_status_page` again, mark the incident as resolved, and set all affected
components back to their normal (operational) status. Failure to do this leaves users seeing an incorrect outage
notice.

Currently, the status page has Functionalities that don't match our needs very well. Take your best guess as you'll be
required to pick one, but don't sweat this choice too much until we can get this aspect sorted.

### Contributor

This person is actually working the incident. They take direction from their own experience and from the incident
Leader as appropriate.

- Actual tasks will vary with their experience and the particular needs of the incident.
- All communication must happen in the Rootly Slack incident channel. That way it will be recorded and used in the
  retrospective.
- When in doubt, Contributors coordinate with the Leader to resolve ambiguity, ensure no duplication of work and
  maintain sharp focus on completion of the current phase.
- Contributors should notify the Leader if they have to step away. This is critical so a replacement can be found if
  appropriate and everyone stays on the same page.

## Post incident

### Incident wrap-up

The Leader ends the incident in Rootly. This closes out the incident document and begins the retrospective process,
during which action items can be assigned to responsible individuals and a more formal incident document can be filed
on the Platform Engineering team [website](https://engineering.ol.mit.edu) for posterity.

### Postmortem (retrospective)

The on-call engineer who handled the incident is also responsible for preparing a postmortem, if one is warranted.
Postmortems are useful whenever there is a significant outage or when questions remain about the exact nature of the
incident.

Rootly has automation that can assist in the creation of the postmortem / retrospective document. We are still not
entirely up to speed on how to best use this but are working on it.

If the incident was at all severe, the Leader will need to schedule a postmortem meeting after the fact with everyone
involved in the incident. The point of the meeting is **not** to exhaustively detail events that occurred, but to help
the organization learn from the incident and iterate on its best practices to prevent similar incidents in the future.
