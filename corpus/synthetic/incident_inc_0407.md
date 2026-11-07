# Post-Incident Review: INC-0407

**Status:** Final
**Severity:** High (customer financial impact)
**Review type:** Blameless post-incident review

## Summary

In April 2026, a sync bug in the Relay CRM caused INC-0407, a double-charge incident affecting about 4,200 customers. Each affected customer was charged twice for their March bill. The Billing Support team handled the resulting customer contacts.

This review covers detection, customer impact, the contact centre response, and follow-up actions. Root-cause detail beyond the sync bug sits with the engineering team's technical write-up and is not repeated here.

## Impact

- **Customers affected:** approximately 4,200
- **Nature of impact:** duplicate charge for the March bill
- **Contact volume:** inbound contacts rose sharply on the first business day after the duplicate charges posted, and stayed high for several days.
- **Secondary effects:**
  - Some customers reported bank overdraft fees caused by the second charge.
  - Some customers raised a dispute with their bank before contacting us, which made reconciliation harder.
  - Average handle time rose because advisors had to confirm each duplicate charge by hand before the scripted response was in place.

There was no evidence of any data exposure. The fault was limited to how billing records were synced.

## Timeline and Response

| Phase | Activity |
|---|---|
| Detection | Advisors noticed a cluster of "charged twice" contacts and escalated to a supervisor. |
| Triage | The supervisor raised an incident. Engineering confirmed duplicate billing records linked to the Relay CRM sync. |
| Containment | The sync process was paused to stop further duplicates being created. |
| Customer handling | The Billing Support team took all INC-0407 contacts through a dedicated contact reason code. |
| Remediation | The finance team processed refunds for the duplicate charges in batches. Advisors confirmed the refund timing with each customer. |
| Close-out | Contact volume returned to baseline. The incident was closed after reconciliation was signed off. |

**What went well**

- Front-line advisors spotted the pattern early and escalated it straight away.
- A single contact reason code made it easy to track volume and spot repeat contacts.
- An interim script was drafted and approved within the first day.

**What did not go well**

- No proactive customer notification went out until after contact volume had already peaked.
- Advisors had no quick way to confirm whether a given customer was in the affected group.
- Guidance on reimbursing bank fees was unclear at first, which led to inconsistent answers.

## Actions

| # | Action | Owner | Due |
|---|---|---|---|
| 1 | Add an alert for duplicate charges against the same bill period before payment collection runs. | Engineering team | Next release cycle |
| 2 | Create a reusable outbound notification template for billing errors. | Communications team | 30 days |
| 3 | Publish a standing policy on reimbursing bank fees caused by our billing errors. | Finance team | 30 days |
| 4 | Give advisors an affected-customer lookup list for any future billing incident. | Billing Support team lead role | 45 days |
| 5 | Add a billing-incident scenario to quarterly advisor refresher training. | Training team | Next quarter |

**Follow-up checklist**

- [ ] All duplicate charges refunded and reconciled
- [ ] Bank fee reimbursement claims closed
- [ ] Repeat-contact rate for affected customers reviewed at 30 days
- [ ] Action status reviewed at the fortnightly operations meeting until closed
