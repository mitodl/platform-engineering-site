# OL Production Outage Runbook

This runbook serves as a guide to best practices for handling production outages at MIT OL.

## When an Outage Is Reported

Once a production outage is reported and is not mitigated within 1 to 2 minutes, the following sequence of events should be set in motion.

### On-Call Creates a New Rootly Incident

This will automatically do several things for us:

- Record all Slack traffic during the incident
- Create a timeline
- Track action items during and after the incident

### Start a Zoom Call

Ensure the invite link is posted in the Slack channel where the incident is being managed. This allows real-time coordination among key participants.

If available, the communications lead should echo key points from the discussion into Slack so they are captured in the incident record.

### Deputize a Communications Lead

During a severe or prolonged outage, it can be difficult for stakeholders to focus on mitigation while also responding to Slack pings from interested third parties. Assign someone who is not directly involved in mitigation to handle communications, primarily by answering questions from others.

Ensure they are in the Slack channel so they receive implicit updates. At each milestone, provide explicit updates they can pass along.
### Keep Time

Someone, possibly the communications lead, should track the overall duration of the outage, as well as whether a given mitigation is taking too long and whether a different approach may be warranted. Ultimately this is the on-call engineer’s judgment, but it can be hard to avoid tunnel vision in stressful situations.

### Incident Wrap-Up

The on-call engineer ends the incident in Rootly. This closes out the incident document and begins the retrospective process, during which action items can be assigned to responsible individuals and a more formal incident document can be filed on the Platform Engineering team [website](https://pe.ol.mit.edu) for posterity.

## Postmortem

The on-call engineer who handled the incident is also responsible for preparing a postmortem, if one is warranted. Postmortems are useful whenever there is a significant outage or when questions remain about the exact nature of the incident.

We should err on the side of holding one, because learning from past mistakes is how we raise the bar for ourselves as a team.
