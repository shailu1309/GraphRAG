# Post-Incident Review: INC-0312

**Review lead:** W. Lin
**Incident:** INC-0312, fibre outage, March 2026
**Status:** Final, circulated to contact centre management and the operations leads
**Classification:** Internal

## Summary

W. Lin led this post-incident review of INC-0312, the fibre outage in March 2026. The network fault is covered in a separate engineering review. This document covers only the effect on the contact centre and how the centre responded.

The outage itself was handled through the normal escalation route. The main contact centre problem was that IVR callback requests failed. Customers who chose a callback did not receive one. Many of them then called again, often more than once. This raised inbound volume well above the level the outage alone would have caused. It also lengthened queue times for every caller, including those with problems unrelated to the outage.

## Timeline (contact centre view)

All times are approximate and come from shift logs and supervisor notes. Telephony reporting for part of the window was incomplete.

- **Outage start:** Inbound calls began rising soon after the first customer reports. A supervisor confirmed a known network incident and asked for an outage message to be added to the IVR.
- **Early phase:** The IVR offered callbacks as normal. Agents reported no unusual problems at this stage.
- **Mid phase:** Agents began receiving calls from customers who said they had requested a callback and heard nothing. A team leader escalated this to the duty manager.
- **Identification:** The duty manager confirmed with the telephony support function that callback requests were not being completed. The callback option stayed live while the team investigated.
- **Mitigation:** The IVR message was changed to stop promising callbacks. It pointed customers to the service status page instead. Repeat call volume began to fall.
- **Recovery:** The callback function was restored and tested with a small number of internal test calls before it was re-enabled for customers.

## Impact

- Inbound volume stayed high for most of the incident window. A large share of these calls were repeat contacts from customers whose callbacks had failed.
- Average wait times rose sharply. Abandonment increased during the busiest period.
- Agents spent extra handling time apologising for missed callbacks and re-explaining the outage.
- Complaints about the failed callbacks were logged separately from complaints about the outage. The complaints team is reviewing them.
- No customer data was affected.

## Findings

1. **No monitoring of callback completion.** Nothing alerted staff when callback requests were accepted but never fulfilled. Staff only learned of the problem because customers reported it to agents.
2. **The callback option stayed live too long.** No one on shift had clear authority, or a documented step, to switch callbacks off during an incident.
3. **IVR outage messaging was slow to change.** The first message did not set expectations about callbacks or wait times.
4. **Repeat contacts were hard to see.** Real-time reporting did not show repeat callers clearly. This delayed recognition that the extra volume came from failed callbacks.
5. **Agent briefing worked well.** Once the issue was understood, team leaders briefed agents quickly. Agents gave customers consistent wording.

## Actions

| # | Action | Owner (role) | Due |
|---|--------|--------------|-----|
| 1 | Add an alert for callback requests that stay unfulfilled beyond a set threshold | Telephony support function | Next quarter |
| 2 | Add a "disable callbacks" step to the major incident checklist, with named shift authority | Contact centre operations manager | Within 4 weeks |
| 3 | Prepare pre-approved IVR outage messages covering callbacks and wait times | Workforce and planning team | Within 4 weeks |
| 4 | Add a repeat-caller indicator to the real-time wallboard | Reporting analyst | Next quarter |
| 5 | Run a desk exercise of the updated checklist with duty managers | Training lead | Within 8 weeks |

Progress on these actions will be reviewed at the monthly operations meeting until all items are closed.
