# SAVE Queue Runbook

**Owner:** Contact centre operations
**Review cycle:** Quarterly, or after any major incident affecting the queue
**Audience:** Queue supervisors, team leads, on-shift workforce planners

## 1. Purpose and Scope

This runbook covers day-to-day operation of the SAVE queue, which handles customers who have signalled intent to cancel broadband or mobile services. It sets out start-of-shift checks, routine monitoring, escalation, and what to do when routing misbehaves.

It does not cover retention offer eligibility or pricing. Those sit in the retention policy document maintained by the commercial team. If an agent asks whether an offer is allowed, point them there. Do not improvise.

Note: the SAVE queue still runs on Switchboard Lite, the legacy in-house IVR. Most of the quirks below come from that. Do not assume behaviour seen on other queues applies here.

## 2. Start-of-Shift Checks

Complete these within the first 15 minutes of the shift and initial the shift log.

1. Confirm the queue is open and accepting calls. Place a test call from the supervisor desk line and check that it reaches the SAVE menu option.
2. Check that agent skill assignments match the published rota. Switchboard Lite does not always pick up overnight rota changes. Correct any mismatches manually.
3. Review the overnight callback list. Assign any callbacks older than 24 hours first.
4. Check the shared inbox for any out-of-hours notices from the IT on-call engineer.
5. Confirm the wallboard is showing live figures, not cached ones. Cached figures show a stale timestamp in the top corner.

If the test call fails, go straight to Section 4. Do not open the queue to agents until routing is confirmed.

## 3. Routine Monitoring

Check these every 30 minutes during core hours:

| Metric | Target | Action if breached |
|---|---|---|
| Calls waiting | Under 10 | Pull agents from general queues, with the floor manager's agreement |
| Longest wait | Under 4 minutes | Offer callback message, see below |
| Abandon rate (rolling hour) | Under 8% | Log in shift notes, flag at next huddle |
| Agents in wrap-up over 5 min | None | Team lead to check in with the agent |

To switch on the callback message, the supervisor must change the menu setting by hand. There is no automatic threshold. Remember to switch it off again when waits fall back under 2 minutes. This is the most common thing missed at handover.

Wallboard figures can lag by up to a few minutes. If figures look wrong, cross-check against the raw call log before acting.

## 4. Incidents and Escalation

**Calls not reaching the queue / dead air / looping menus**

1. Place a second test call to confirm the fault.
2. Raise a priority ticket with the IT service desk. State "SAVE queue, Switchboard Lite" in the summary line so it routes to the right resolver group.
3. Inform the floor manager and post a notice in the supervisors' channel.
4. If the fault is not fixed within 20 minutes, ask the floor manager to approve the fallback: SAVE calls are diverted to the general queue, and agents tag cancellations for retention follow-up within one working day.

**Partial faults** (for example, skills not updating or the wallboard frozen): raise a standard ticket and work around manually. Log the workaround in the shift notes.

Keep a timeline of every incident: the time it was spotted, the time the ticket was raised, the actions taken and the time it was resolved. This is needed for the weekly operations review.

## 5. Handover and Actions

At end of shift, the outgoing supervisor confirms the following in the shift log:

- The callback message state (on or off)
- Any open tickets and their reference numbers
- Any manual skill changes still in place
- Callbacks outstanding

**Standing actions:**
- Operations to review callback-message switching at the next quarterly review.
- Team leads to refresh new starters on Section 4 during induction week.
