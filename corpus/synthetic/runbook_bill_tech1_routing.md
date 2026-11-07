# IVR Routing Runbook: BILL and TECH-1

## Purpose and Scope

This runbook covers how inbound calls reach the BILL and TECH-1 queues and what to check when routing looks wrong. It is for duty supervisors, the workforce planning team, and anyone on the out-of-hours rota who gets paged about queue volumes.

The Switchboard IVR routes calls to the BILL queue. The Switchboard IVR also routes calls to the TECH-1 queue. Other queues, menu wording, and recorded announcements are out of scope. Raise changes to those through the normal change request process.

Keep this document current. If you change a step, update the revision note at the bottom and tell the shift lead at the next handover.

## Normal Routing Behaviour

Under normal conditions you should see the following:

- **BILL**: calls about invoices, payments, direct debits, refunds and charges the customer disputes. The Switchboard IVR sends these to BILL once the caller has picked a billing option and passed the account lookup step.
- **TECH-1**: first-line technical calls, such as no service, slow speeds, and equipment that won't power on or sync. The Switchboard IVR sends these to TECH-1 once the caller has picked a fault option.

Expected patterns:

- BILL peaks in the first three working days after the monthly billing run and on Monday mornings.
- TECH-1 peaks in the early evening and after any widespread service disruption.
- Abandonment above 10% on either queue for more than 30 minutes is not normal and needs investigating.

## Checks When Routing Looks Wrong

Work through these in order. Write down the time you started each step in the shift log.

1. **Confirm the symptom.** Check whether one queue is empty while the other is flooded, or whether both are quiet. Compare live volumes with the same hour last week.
2. **Test call.** Use a test handset to dial the main number. Select the billing option and confirm you land in BILL. Repeat with the fault option and confirm you land in TECH-1. Record what you hear at each menu step.
3. **Check for recent changes.** Look at the change calendar for anything deployed in the last 24 hours that touches the Switchboard IVR. If you find something, contact the change owner before doing anything else.
4. **Check announcements.** An emergency outage message left active by mistake can deflect callers before they reach either queue. Confirm with the incident manager whether any message should still be playing.
5. **Escalate.** If the test calls fail, or the cause isn't clear within 20 minutes, page the on-call telephony engineer and open a priority ticket.

Do not move agents between BILL and TECH-1 to hide a routing fault. Rebalancing staff covers up the problem and makes the post-incident review harder.

## Escalation and Follow-up

- **During the issue:** post updates in the supervisors' channel every 30 minutes, even when nothing has changed.
- **After resolution:** run the test calls again for both BILL and TECH-1 and record the results.
- **Within two working days:** the duty supervisor writes a short summary covering the timeline, the cause if known, how many calls were affected, and any customer callbacks needed.
- **Weekly review:** routing incidents go on the agenda for the Thursday operations meeting.

Action items from the last review:

- Add the test-call script to the out-of-hours pack. Owner: the training team.
- Confirm the abandonment alert threshold with workforce planning. Owner: a supervisor.

*Revision note: steps reordered so the change calendar is checked before announcements.*
