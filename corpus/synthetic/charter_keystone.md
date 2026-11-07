# Project Charter: Keystone

**Document status:** Draft for steering review
**Project owner:** Luis Ortega
**Version:** 0.3

## Purpose and Background

Project Keystone will deliver a support chatbot for Kestrel Telecom customers. Its job is to handle routine broadband and mobile queries that currently take up advisor time. Common examples are router setup, roaming charges, bill dates and fault-reporting steps.

The chatbot answers questions from the Beacon knowledge base. It does not write its own answers. If an article is wrong or out of date in Beacon, the chatbot will be wrong too. Content quality is therefore treated as a project dependency, not a separate workstream.

Keystone also reads customer account data from the Relay CRM. This lets it give account-specific answers, such as "your next bill is due on the 14th", once the customer has been verified. Access is read-only. The chatbot will not change account records, process payments or raise orders.

## Scope

**In scope:**
- Customer-facing chat on the web self-service pages.
- Answers based on Beacon knowledge base articles. Each answer links to the article it came from.
- Read-only lookups of account data from the Relay CRM after customer verification.
- Handover to a live advisor when the bot cannot answer, the customer asks for a person, or the conversation hits a defined trigger such as complaints, vulnerability indicators or cancellation.
- Transcript capture for quality review.

**Out of scope (this phase):**
- Changes to account data, payments, plan changes or cancellations.
- Voice channel and mobile app integration.
- Proactive or outbound messaging.
- Rewriting the knowledge base. Fixing gaps found during testing is in scope. A full content overhaul is not.

## Objectives and Success Measures

| Objective | Measure | Target |
|---|---|---|
| Resolve routine queries without an advisor | Contained conversations as a share of total chats | Baseline in pilot; target set at gate 2 |
| Accurate answers | Sampled transcripts rated correct by QA | 95% or above |
| Clean handover | Handovers that arrive with full transcript and verification status | 100% |
| Customer acceptance | Post-chat satisfaction score | No lower than current live chat |
| Data protection | Account data shown to unverified users | Zero |

## Governance and Roles

- **Project owner:** Luis Ortega. Accountable for scope, budget and go/no-go decisions.
- **Contact centre operations lead:** owns handover rules and advisor readiness.
- **Knowledge management:** owns article accuracy and fixes gaps flagged by the bot.
- **IT / integration:** owns the CRM connection, access controls and monitoring.
- **Data protection officer:** signs off the verification flow and transcript retention.
- **QA team:** reviews transcripts weekly during the pilot.

**Cadence:**
- Weekly project stand-up (30 minutes).
- Fortnightly steering review with the owner.
- Gate reviews at design sign-off, pilot start and full launch.

## Risks, Assumptions and Next Actions

**Key risks:**
- *Stale knowledge content* leads to confident wrong answers. Mitigation: pre-launch article audit and a weekly gap report.
- *CRM data exposure* through a weak verification step. Mitigation: DPO sign-off and penetration testing before the pilot.
- *Advisor workload spikes* from poor handovers. Mitigation: staged rollout and a capped pilot traffic share.

**Assumptions:**
- CRM read access can be granted with a service account limited to agreed fields.
- Knowledge base articles carry enough structure to cite reliably.

**Next actions:**
1. Confirm the CRM field list with IT and the DPO. Owner: IT / integration.
2. Run a top-50 query audit against current articles. Owner: knowledge management.
3. Draft the handover trigger list for steering review. Owner: operations lead.
4. Circulate the charter for sign-off. Owner: Luis Ortega.
