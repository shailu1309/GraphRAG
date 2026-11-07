# Project Charter: Clearline

**Document status:** Draft for steering approval
**Project owner:** Grace Kim
**Last reviewed:** At the most recent weekly project check-in

## 1. Purpose and Background

Project Clearline will upgrade the Switchboard IVR to version 2. The current Switchboard configuration has built up years of incremental changes. These include menu branches that no longer match how calls are handled, prompts recorded at different times in different styles, and routing rules that only a few people fully understand. Agents regularly report callers arriving in the wrong queue after pressing options that seemed correct to them. Supervisors spend time on manual transfers that the IVR should avoid.

The upgrade gives us a supported platform version and a chance to rationalise the call flow at the same time. This charter sets out the scope, ownership, measures of success and governance. Grace Kim owns Project Clearline and is accountable for delivery against this charter.

## 2. Scope

**In scope**

- Upgrade of the Switchboard IVR from its current version to version 2.
- Review and redesign of the top-level and second-level menu options.
- Re-recording of customer-facing prompts in a consistent voice and style.
- Rebuild of routing rules in version 2, with each rule documented and assigned an owner.
- Regression testing of all existing entry points before cutover.
- Updated knowledge articles and a short briefing for frontline agents and team leaders.

**Out of scope**

- Changes to workforce planning or staffing models.
- New contact channels such as chat or messaging.
- Changes to billing, provisioning or other back-office systems, except where a data lookup the IVR already uses must be reconnected.
- Any change to tariffs, pricing or customer terms.

## 3. Objectives and Success Measures

| Objective | Measure | Target |
|---|---|---|
| Reduce misrouted calls | Share of calls transferred by an agent within the first minute | Reduce against the pre-upgrade baseline |
| Shorten time in IVR | Median time from answer to queue entry | Reduce against the pre-upgrade baseline |
| Maintain stability | Unplanned IVR outages in the first four weeks after cutover | Zero |
| Agent confidence | Team leader sign-off that agents have received the briefing | 100% of teams before go-live |

The reporting analyst will capture baselines in the four weeks before build starts. Targets will be confirmed at the first steering meeting once the baseline is available.

## 4. Roles and Governance

- **Project owner:** Grace Kim. She owns scope, budget decisions within delegated limits, and the go/no-go call for cutover.
- **Steering group:** contact centre operations management, a representative from the IT change team, and a representative from the finance team. The group meets fortnightly.
- **Working group:** a business analyst, an IVR configuration specialist, a test lead, a quality and compliance reviewer, and two frontline team leaders. The group meets weekly for 30 minutes.
- **Change control:** any change to scope, cutover date or budget goes to the project owner in writing. Changes above delegated limits go to the steering group.

## 5. Risks, Assumptions and Next Actions

**Key risks**

- Version 2 behaviour may differ from the current version in ways that testing does not catch. *Mitigation:* run a parallel test line and a staged cutover during a low-volume period.
- Prompt re-recording may slip. *Mitigation:* agree the scripts early and keep the existing prompts as a fallback.
- Agents may be unfamiliar with the new menu paths. *Mitigation:* deliver the briefing at least one week before go-live and give team leaders a quick-reference sheet.

**Assumptions**

- The IVR configuration specialist has enough time allocated to cover the build and test phases.
- No major contact centre change events are scheduled during the cutover window.

**Next actions**

1. Business analyst to circulate the current call-flow map for review.
2. Reporting analyst to start baseline data capture.
3. Test lead to draft the regression test plan.
4. Project owner to confirm steering group membership and the first meeting date.
