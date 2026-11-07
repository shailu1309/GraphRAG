# NETESC Queue Runbook

**Owner:** Contact centre operations
**Audience:** Agents and supervisors working the NETESC queue
**Review cycle:** Quarterly, or after any significant change to call routing

## 1. Purpose and Scope

This runbook covers day-to-day handling of the NETESC queue. It is for agents taking escalated network calls and for supervisors covering the queue. It does not replace the general complaints procedure or the outage communications process. Where those apply, follow them and use this document only for queue-specific steps.

If anything here conflicts with a current notice from a supervisor, follow the notice and raise the conflict at the next team huddle so this document can be updated.

## 2. How Calls Arrive

Calls reach the NETESC queue through the Switchboard IVR. Agents do not transfer callers in from the front door, and should not advise customers to dial a different number to "get through faster".

When a call lands:

1. Read the routing notes on screen before you greet the customer. They show the options the caller selected in the IVR.
2. Confirm identity using the standard security questions. Do not skip this because the caller has already passed through the IVR.
3. Check whether the customer has an open case. If one exists, update it rather than opening a duplicate.
4. If the caller has been routed incorrectly, warm-transfer them using the normal transfer process. Note the misroute on the misroute tracker so the pattern can be reviewed.

Some callers will have asked for a callback rather than waiting in queue. These come back to the queue as outbound attempts and are covered in Section 3.

## 3. Callback Failures and Manual Logging

When an IVR callback fails, NETESC agents must log the case by hand. Do not assume the system has recorded the attempt or the customer's issue. A failed callback includes any of the following:

- The callback was not placed at all.
- The callback connected but dropped before the customer was verified.
- The callback reached voicemail or an unanswered line.
- The callback was placed to the wrong number.

**Manual logging checklist:**

- [ ] Customer account number and contact number
- [ ] Time of the original request (from the IVR notes, if visible)
- [ ] Time and outcome of each callback attempt
- [ ] Summary of the reported fault, as far as known
- [ ] Next action and who owns it
- [ ] Tag the case "callback failure" so it appears in the weekly count

Make one further manual call attempt within the same shift where possible. If that also fails, leave the case assigned to yourself with a clear next step, or hand it to the shift supervisor before you log off. Do not close a case because the customer could not be reached.

## 4. Escalation and Shift Handover

Escalate to the on-shift supervisor when:

- the queue wait time is visibly climbing and calls are abandoning,
- three or more callback failures occur within an hour, or
- a customer reports a fault that appears to affect multiple addresses.

At handover, the outgoing supervisor briefs the incoming one on open manual cases, any unresolved callback failures, and any routing oddities seen during the shift. Record the handover in the shift log.

**Standing actions:**

- Supervisors review callback-failure tags at the Monday team meeting.
- Agents flag unclear IVR routing notes to a supervisor rather than guessing.
- Operations reviews this runbook every quarter and records the review date at the top.
