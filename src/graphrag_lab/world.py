"""The ground-truth world for the synthetic corpus: Kestrel Telecom's contact centre.

This is the answer key, and it exists before any text does. Every fact is a
(subject, predicate, object) triple plus the sentence that states it. Each
document renders only a slice of the facts, so a multi-hop answer needs
several documents.

Planted on purpose:
  - Chains of 3+ hops across documents (q_multi_*)
  - A scattered person: Wei Lin appears in 5 documents, as "Wei Lin", "W. Lin", "Lin"
  - Corpus-wide themes that no single document summarises (q_global_*)
  - Near-miss distractors: Project Clearline vs Clearview, Switchboard vs Switchboard Lite
  - Absences: events that never happened (q_absent_*)

validate_world() turns the Phase 1 gate into code: no single document may hold
every fact that a cross-document question needs.
"""

from __future__ import annotations

from dataclasses import dataclass

COMPANY = "Kestrel Telecom"


@dataclass(frozen=True)
class Entity:
    id: str
    name: str
    type: str
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class Fact:
    id: str
    subject: str
    predicate: str
    object: str | None  # None when the fact is an attribute, not a relation
    text: str


@dataclass(frozen=True)
class Document:
    id: str
    title: str
    genre: str
    fact_ids: tuple[str, ...]


@dataclass(frozen=True)
class Question:
    id: str
    shape: str
    text: str
    answer: str
    fact_ids: tuple[str, ...]


SHAPES = (
    "local_factual",
    "multi_hop",
    "global_thematic",
    "entity_gather",
    "set_count",
    "absent_info",
)
# Shapes whose answer must need more than one document.
CROSS_DOCUMENT_SHAPES = frozenset(
    {"multi_hop", "global_thematic", "entity_gather", "set_count"}
)


ENTITIES = (
    Entity("kestrel", COMPANY, "organization"),
    # people
    Entity("maya_okafor", "Maya Okafor", "person", ("M. Okafor",)),
    Entity("daniel_reyes", "Daniel Reyes", "person", ("Dan Reyes",)),
    Entity("wei_lin", "Wei Lin", "person", ("W. Lin", "Lin")),
    Entity("sofia_marchetti", "Sofia Marchetti", "person"),
    Entity("tom_becker", "Tom Becker", "person"),
    Entity("aisha_rahman", "Aisha Rahman", "person"),
    Entity("grace_kim", "Grace Kim", "person"),
    Entity("luis_ortega", "Luis Ortega", "person"),
    # teams
    Entity("billing_support", "Billing Support", "team"),
    Entity("network_escalations", "Network Escalations", "team"),
    Entity("tech_support_t1", "Tier 1 Technical Support", "team"),
    Entity("tech_support_t2", "Tier 2 Technical Support", "team"),
    Entity("retention", "Retention", "team"),
    Entity("quality_assurance", "Quality Assurance", "team"),
    Entity("workforce_mgmt", "Workforce Management", "team"),
    Entity("cx_platforms", "CX Platforms", "team"),
    # queues
    Entity("q_network", "NETESC queue", "queue"),
    Entity("q_billing", "BILL queue", "queue"),
    Entity("q_tier1", "TECH-1 queue", "queue"),
    Entity("q_retention", "SAVE queue", "queue"),
    # systems
    Entity("switchboard", "Switchboard", "system", ("Switchboard IVR",)),
    Entity("switchboard_lite", "Switchboard Lite", "system"),
    Entity("relay_crm", "Relay CRM", "system", ("Relay",)),
    Entity("beacon_kb", "Beacon", "system", ("Beacon knowledge base",)),
    Entity("pulse_wfm", "Pulse", "system"),
    # vendors
    Entity("voxroute", "VoxRoute", "vendor"),
    Entity("corvane", "Corvane Systems", "vendor", ("Corvane",)),
    Entity("shiftwise", "ShiftWise", "vendor"),
    Entity("telvio", "Telvio", "vendor"),
    # incidents
    Entity("inc_0312", "INC-0312", "incident", ("March 2026 fibre outage",)),
    Entity("inc_0407", "INC-0407", "incident", ("April 2026 double-charge incident",)),
    # projects
    Entity("clearline", "Project Clearline", "project"),
    Entity("clearview", "Project Clearview", "project"),
    Entity("keystone", "Project Keystone", "project"),
    Entity("winback", "Win-back campaign", "project"),
    # recurring issues (the corpus-wide themes)
    Entity("outdated_kb", "outdated knowledge-base articles", "issue"),
    Entity("monday_understaffing", "Monday-morning understaffing", "issue"),
    Entity("callback_failures", "IVR callback failures", "issue"),
    Entity("overage_charges", "vendor overage charges", "issue"),
)


FACTS = (
    # --- leadership ---------------------------------------------------------
    Fact("f01", "daniel_reyes", "leads", "billing_support",
         "Dan Reyes leads the Billing Support team."),
    Fact("f02", "wei_lin", "leads", "network_escalations",
         "Wei Lin leads the Network Escalations team."),
    Fact("f03", "luis_ortega", "leads", "tech_support_t2",
         "Luis Ortega leads Tier 2 Technical Support."),
    Fact("f04", "aisha_rahman", "leads", "retention",
         "Aisha Rahman leads the Retention team."),
    Fact("f05", "tom_becker", "leads", "quality_assurance",
         "Tom Becker leads Quality Assurance."),
    Fact("f06", "sofia_marchetti", "leads", "workforce_mgmt",
         "Sofia Marchetti manages Workforce Management."),
    Fact("f07", "maya_okafor", "heads_customer_operations_at", "kestrel",
         "M. Okafor, Head of Customer Operations, chaired the February review."),
    Fact("f08", "grace_kim", "leads", "cx_platforms",
         "Grace Kim leads CX Platforms, the team that owns the vendor contracts."),
    # --- queues and routing -------------------------------------------------
    Fact("f10", "network_escalations", "manages", "q_network",
         "The Network Escalations team manages the NETESC queue."),
    Fact("f11", "q_network", "routed_by", "switchboard",
         "Calls reach the NETESC queue through the Switchboard IVR."),
    Fact("f12", "q_billing", "routed_by", "switchboard",
         "The Switchboard IVR routes calls to the BILL queue."),
    Fact("f13", "q_tier1", "routed_by", "switchboard",
         "The Switchboard IVR routes calls to the TECH-1 queue."),
    Fact("f14", "q_retention", "routed_by", "switchboard_lite",
         "The SAVE queue still runs on Switchboard Lite, the legacy in-house IVR."),
    Fact("f15", "billing_support", "manages", "q_billing",
         "Billing Support agents answer the BILL queue."),
    Fact("f16", "retention", "manages", "q_retention",
         "The Retention team answers the SAVE queue."),
    Fact("f17", "tech_support_t1", "manages", "q_tier1",
         "Tier 1 Technical Support answers the TECH-1 queue."),
    # --- vendors ------------------------------------------------------------
    Fact("f20", "voxroute", "supplies", "switchboard",
         "VoxRoute supplies the Switchboard IVR."),
    Fact("f21", "corvane", "supplies", "relay_crm",
         "Corvane Systems supplies the Relay CRM."),
    Fact("f22", "shiftwise", "supplies", "pulse_wfm",
         "ShiftWise supplies Pulse, the workforce scheduling tool."),
    Fact("f23", "telvio", "takes_overflow_from", "q_tier1",
         "Telvio, an outsourced partner, takes overflow calls from the TECH-1 queue."),
    Fact("f24", "grace_kim", "manages_contract_with", "voxroute",
         "Grace Kim manages the VoxRoute contract."),
    # --- incidents ----------------------------------------------------------
    Fact("f30", "wei_lin", "led_review_of", "inc_0312",
         "W. Lin led the post-incident review of INC-0312, the March 2026 fibre outage."),
    Fact("f31", "inc_0312", "caused", "callback_failures",
         "During INC-0312, IVR callback requests failed, so many customers called again."),
    Fact("f32", "relay_crm", "caused", "inc_0407",
         "A sync bug in the Relay CRM caused INC-0407, the April 2026 double-charge incident."),
    Fact("f33", "billing_support", "handled", "inc_0407",
         "The Billing Support team handled the customer contacts from INC-0407."),
    Fact("f34", "inc_0407", "impact", None,
         "INC-0407 charged about 4,200 customers twice for their March bill."),
    # --- projects -----------------------------------------------------------
    Fact("f40", "clearline", "upgrades", "switchboard",
         "Project Clearline upgrades the Switchboard IVR to version 2."),
    Fact("f41", "grace_kim", "owns", "clearline",
         "Grace Kim owns Project Clearline."),
    Fact("f42", "clearview", "depends_on", "relay_crm",
         "Project Clearview depends on the Relay CRM for statement data."),
    Fact("f43", "daniel_reyes", "owns", "clearview",
         "Daniel Reyes owns Project Clearview."),
    Fact("f44", "clearview", "objective", None,
         "The objective of Project Clearview is to redesign customer bills so that "
         "30% fewer customers call about charges they do not understand."),
    Fact("f45", "keystone", "depends_on", "beacon_kb",
         "Project Keystone, a support chatbot, answers questions from the Beacon knowledge base."),
    Fact("f46", "keystone", "depends_on", "relay_crm",
         "Project Keystone reads customer account data from the Relay CRM."),
    Fact("f47", "luis_ortega", "owns", "keystone",
         "Luis Ortega owns Project Keystone."),
    Fact("f48", "winback", "depends_on", "relay_crm",
         "The Win-back campaign pulls lapsed-customer lists from the Relay CRM."),
    Fact("f49", "aisha_rahman", "runs", "winback",
         "Aisha Rahman runs the Win-back campaign."),
    # --- workforce ----------------------------------------------------------
    Fact("f55", "workforce_mgmt", "uses", "pulse_wfm",
         "Workforce Management schedules agents with Pulse."),
    # --- Wei Lin, scattered -------------------------------------------------
    Fact("f60", "wei_lin", "previously_in", "tech_support_t2",
         "Before the promotion, Lin was a senior agent in Tier 2 Technical Support."),
    Fact("f61", "wei_lin", "promoted", None,
         "Wei Lin was promoted to lead Network Escalations in January 2026."),
    Fact("f62", "wei_lin", "trained", "tech_support_t1",
         "W. Lin ran the escalation-handling training for Tier 1 agents in Q1."),
    Fact("f63", "wei_lin", "reported_on", "q_network",
         "Wei Lin reported that NETESC handle time fell by 12% in April."),
    # --- themes: repeat contacts and escalations ----------------------------
    Fact("f70", "quality_assurance", "found", "outdated_kb",
         "Quality Assurance found that outdated Beacon articles caused 18% of "
         "repeat contacts in Q1."),
    Fact("f71", "q_tier1", "affected_by", "outdated_kb",
         "In February, TECH-1 agents reported that Beacon articles about the new "
         "router were out of date, which led to repeat calls."),
    Fact("f72", "outdated_kb", "top_cause_in", None,
         "Outdated knowledge-base articles were again a top cause of escalations in April."),
    Fact("f73", "kestrel", "affected_by", "monday_understaffing",
         "The contact centre was understaffed on Monday mornings in February, and "
         "the service level fell to 61%."),
    Fact("f74", "pulse_wfm", "causes", "monday_understaffing",
         "Sofia Marchetti says Pulse forecasts underestimate Monday-morning demand."),
    Fact("f75", "telvio", "covered", "monday_understaffing",
         "Monday-morning understaffing continued in April, and Telvio took the overflow."),
    Fact("f76", "q_network", "affected_by", "callback_failures",
         "When an IVR callback fails, NETESC agents must log the case by hand."),
    # --- themes: vendor cost overruns ---------------------------------------
    Fact("f80", "voxroute", "has_issue", "overage_charges",
         "The VoxRoute contract ran 22% over budget because of per-minute overage charges."),
    Fact("f81", "corvane", "has_issue", "overage_charges",
         "Corvane Systems billed seat overage charges, and the Relay CRM contract "
         "ran 15% over budget."),
    Fact("f82", "shiftwise", "has_issue", "overage_charges",
         "ShiftWise added overage charges for extra Pulse forecasting runs."),
    Fact("f83", "maya_okafor", "requested_review_of", "overage_charges",
         "Maya Okafor asked CX Platforms to review every vendor overage clause."),
)


DOCUMENTS = (
    Document("team_billing_support", "Billing Support - Team Page", "team page",
             ("f01", "f15")),
    Document("team_network_escalations", "Network Escalations - Team Page", "team page",
             ("f02", "f10")),
    Document("team_technical_support", "Technical Support - Team Page", "team page",
             ("f03", "f17", "f23")),
    Document("team_retention", "Retention - Team Page", "team page",
             ("f04", "f16", "f48", "f49")),
    Document("runbook_netesc_queue", "NETESC Queue Runbook", "queue runbook",
             ("f11", "f76")),
    Document("runbook_bill_tech1_routing", "IVR Routing Runbook: BILL and TECH-1",
             "queue runbook", ("f12", "f13")),
    Document("runbook_save_queue", "SAVE Queue Runbook", "queue runbook",
             ("f14",)),
    Document("incident_inc_0312", "Post-Incident Review: INC-0312", "incident report",
             ("f30", "f31")),
    Document("incident_inc_0407", "Post-Incident Review: INC-0407", "incident report",
             ("f32", "f33", "f34")),
    Document("contract_voxroute", "Vendor Contract Summary: VoxRoute", "vendor contract",
             ("f20", "f24", "f80")),
    Document("contract_corvane", "Vendor Contract Summary: Corvane Systems",
             "vendor contract", ("f08", "f21", "f81")),
    Document("contract_shiftwise", "Vendor Contract Summary: ShiftWise", "vendor contract",
             ("f22", "f82")),
    Document("charter_clearline", "Project Charter: Clearline", "project charter",
             ("f40", "f41")),
    Document("charter_clearview", "Project Charter: Clearview", "project charter",
             ("f42", "f43", "f44")),
    Document("charter_keystone", "Project Charter: Keystone", "project charter",
             ("f45", "f46", "f47")),
    Document("review_2026_02", "Customer Operations Monthly Review - February 2026",
             "monthly review", ("f07", "f71", "f73")),
    Document("plan_workforce_q2", "Workforce Management Q2 Plan", "planning memo",
             ("f06", "f55", "f74")),
    Document("review_qa_q1", "Quality Assurance Review - Q1 2026", "quality review",
             ("f05", "f62", "f70")),
    Document("review_2026_05", "Customer Operations Monthly Review - May 2026",
             "monthly review", ("f63", "f72", "f75", "f83")),
    Document("announcement_wei_lin", "Announcement: New Network Escalations Lead",
             "personnel announcement", ("f60", "f61")),
)


QUESTIONS = (
    # --- local_factual: one document is enough ------------------------------
    Question("q_local_1", "local_factual",
             "What is the objective of Project Clearview?",
             "To redesign customer bills so that 30% fewer customers call about "
             "charges they do not understand.",
             ("f44",)),
    Question("q_local_2", "local_factual",
             "Who owns Project Clearline, and what does it upgrade?",
             "Grace Kim owns it. It upgrades the Switchboard IVR to version 2.",
             ("f40", "f41")),
    # --- multi_hop: a chain across documents --------------------------------
    Question("q_multi_1", "multi_hop",
             "Which vendor supplies the IVR that routes calls to the queue managed "
             "by the team whose lead ran the INC-0312 review?",
             "VoxRoute. Wei Lin led the INC-0312 review and leads Network Escalations, "
             "which manages the NETESC queue; Switchboard routes NETESC, and VoxRoute "
             "supplies Switchboard.",
             ("f30", "f02", "f10", "f11", "f20")),
    Question("q_multi_2", "multi_hop",
             "Who leads the team that handled the incident caused by the CRM that "
             "Corvane Systems supplies?",
             "Daniel (Dan) Reyes. Corvane supplies Relay CRM, a Relay sync bug caused "
             "INC-0407, Billing Support handled it, and Dan Reyes leads Billing Support.",
             ("f21", "f32", "f33", "f01")),
    # --- global_thematic: needs the whole corpus ----------------------------
    Question("q_global_1", "global_thematic",
             "What are the recurring causes of repeat contacts and escalations "
             "across the contact centre?",
             "Three recurring causes: outdated knowledge-base (Beacon) articles, "
             "Monday-morning understaffing (Pulse under-forecasts demand), and IVR "
             "callback failures.",
             ("f31", "f76", "f70", "f71", "f72", "f73", "f74", "f75")),
    Question("q_global_2", "global_thematic",
             "What cost problem recurs across the contact centre's vendor contracts?",
             "Overage charges: VoxRoute per-minute overages (22% over budget), Corvane "
             "seat overages (15% over budget), and ShiftWise forecasting-run overages. "
             "Maya Okafor asked for a review of every overage clause.",
             ("f80", "f81", "f82", "f83")),
    # --- entity_gather: one entity, many documents --------------------------
    Question("q_entity_1", "entity_gather",
             "What do we know about Wei Lin?",
             "Former senior Tier 2 agent, promoted in January 2026 to lead Network "
             "Escalations; led the INC-0312 review; ran Tier 1 escalation training in "
             "Q1; reported a 12% drop in NETESC handle time in April.",
             ("f02", "f30", "f60", "f61", "f62", "f63")),
    Question("q_entity_2", "entity_gather",
             "What do we know about Grace Kim?",
             "Leads CX Platforms, which owns the vendor contracts; manages the VoxRoute "
             "contract; owns Project Clearline.",
             ("f08", "f24", "f41")),
    # --- set_count: complete enumeration ------------------------------------
    Question("q_set_1", "set_count",
             "How many projects or campaigns depend on the Relay CRM, and which?",
             "Three: Project Clearview, Project Keystone, and the Win-back campaign.",
             ("f42", "f46", "f48")),
    Question("q_set_2", "set_count",
             "Which queues does the Switchboard IVR route?",
             "Three: NETESC, BILL, and TECH-1. The SAVE queue uses Switchboard Lite, "
             "not Switchboard.",
             ("f11", "f12", "f13", "f14")),
    # --- absent_info: never happened ----------------------------------------
    Question("q_absent_1", "absent_info",
             "What were the results of the Switchboard version 3 pilot?",
             "The documents do not describe a Switchboard version 3 pilot. Project "
             "Clearline upgrades Switchboard to version 2 only.",
             ()),
    Question("q_absent_2", "absent_info",
             "What did Telvio's 2026 customer satisfaction audit find?",
             "The documents do not describe any Telvio customer satisfaction audit.",
             ()),
)


def _index(items, kind: str) -> dict:
    index = {}
    for item in items:
        if item.id in index:
            raise ValueError(f"duplicate {kind} id: {item.id}")
        index[item.id] = item
    return index


ENTITY_BY_ID = _index(ENTITIES, "entity")
FACT_BY_ID = _index(FACTS, "fact")
DOCUMENT_BY_ID = _index(DOCUMENTS, "document")
QUESTION_BY_ID = _index(QUESTIONS, "question")

# Each fact lives in exactly one document; validate_world() enforces it.
DOC_OF_FACT = {fid: doc.id for doc in DOCUMENTS for fid in doc.fact_ids}


def required_docs(question: Question) -> list[str]:
    return sorted({DOC_OF_FACT[fid] for fid in question.fact_ids})


def validate_world() -> None:
    """Fail loudly if the answer key is inconsistent. Cheap - run it every time."""
    for fact in FACTS:
        for ref in (fact.subject, fact.object):
            if ref is not None and ref not in ENTITY_BY_ID:
                raise ValueError(f"{fact.id}: unknown entity {ref!r}")

    placements = [fid for doc in DOCUMENTS for fid in doc.fact_ids]
    unknown = sorted(set(placements) - FACT_BY_ID.keys())
    repeated = sorted({fid for fid in placements if placements.count(fid) > 1})
    unplaced = sorted(FACT_BY_ID.keys() - set(placements))
    if unknown or repeated or unplaced:
        raise ValueError(
            f"fact placement broken: unknown={unknown} repeated={repeated} "
            f"unplaced={unplaced}"
        )

    for q in QUESTIONS:
        if q.shape not in SHAPES:
            raise ValueError(f"{q.id}: unknown shape {q.shape!r}")
        missing = [fid for fid in q.fact_ids if fid not in FACT_BY_ID]
        if missing:
            raise ValueError(f"{q.id}: unknown facts {missing}")
        if q.shape == "absent_info" and q.fact_ids:
            raise ValueError(f"{q.id}: absent_info question must have no facts")
        # The Phase 1 gate: no single document answers a cross-document question.
        if q.shape in CROSS_DOCUMENT_SHAPES and len(required_docs(q)) < 2:
            raise ValueError(
                f"{q.id} ({q.shape}) is answerable from one document: {required_docs(q)}"
            )
