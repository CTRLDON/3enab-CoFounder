"""Scripted demo scenarios (offline demo mode).

These are hand-written agent responses used ONLY when a venture is created in demo mode. They pass
through exactly the same schema validation, policy redaction, gates, approvals and logging as live
model output. Every demo venture, message and log entry is labelled as scripted.

All figures inside are ASSUMPTIONS written for the demonstration — none are market data.

Scenarios:
  main — a CS student's "ChatGPT competitor" is challenged, narrowed to a student planner (rejected
         by the founder), then to a tool for tutoring centres (approved); runs all six phases.
  weak — the founder insists on a general-purpose free AI chat app; the Discover gate says STOP.
"""

from __future__ import annotations

from typing import Any

# --- Founder profiles ------------------------------------------------------------------------

_BASE_PROFILE: dict[str, Any] = {
    "background": {
        "education": "BSc Computer Science, third year (Cairo)",
        "skills": ["Python", "Basic web development (HTML, CSS, JavaScript)", "SQL basics"],
        "experience": "Volunteer teaching assistant for first-year programming labs. No full-time commercial experience.",
        "entrepreneurial_experience": "None",
        "industries": ["Education (as a student)"],
        "interests": ["AI", "Education", "Productivity tools"],
    },
    "resources": {
        "budget_amount": 10000,
        "budget_currency": "EGP",
        "weekly_hours": 15,
        "technical_resources": "Personal laptop; free-tier developer tools",
        "business_contacts": "Classmates; two teachers at a local tutoring centre",
        "customer_access": "University student groups on WhatsApp and Telegram; one tutoring centre through teacher contacts",
        "team": "Solo",
        "existing_assets": "None",
    },
    "preferences": {
        "has_idea": True,
        "starting_idea": "Build an AI application that competes with ChatGPT.",
        "problems_of_interest": ["Studying and exam preparation"],
        "target_country": "Egypt",
        "preferred_audience": "Students",
        "business_type": "either",
        "risk_tolerance": "medium",
        "short_term_goal": "Earn first revenue within six months while studying",
        "long_term_goal": "Build a sustainable software company",
        "values_and_constraints": "No misleading marketing. Must fit around the university schedule.",
    },
}

DEMO_FOUNDERS: dict[str, dict[str, Any]] = {
    "main": {"display_name": "Demo founder (CS student)", "profile": _BASE_PROFILE},
    "weak": {
        "display_name": "Demo founder (general AI chat idea)",
        "profile": {
            **_BASE_PROFILE,
            "resources": {**_BASE_PROFILE["resources"], "business_contacts": "Classmates", "customer_access": "None in particular"},
            "preferences": {
                **_BASE_PROFILE["preferences"],
                "starting_idea": "A general-purpose AI chat app for everyone in Egypt, like ChatGPT but free.",
                "preferred_audience": "Everyone",
            },
        },
    },
}

# Lines the demo founder "types". The UI offers them as suggestions in demo mode.
FOUNDER_SCRIPT: dict[str, dict[str, Any]] = {
    "main": {
        "debate": [
            "I want to build an AI app that competes with ChatGPT. It will be cheaper and better for Egyptian users.",
            "Fair. The problem I actually see: students at my university juggle six or seven courses with overlapping exam dates and plan revision in notebooks or WhatsApp. Most give up after a week.",
            "Students rarely pay for apps here, but let's start with the student revision planner and keep it free at first. I can monetise later.",
            "Let's focus on small tutoring centres instead. They already organise revision sessions for exam season, and I know two teachers at one centre.",
        ],
        "reject_reason": "Students rarely pay for apps here. I want a customer who already spends money on revision: tutoring centres.",
        "negotiation_node": "revenue",
        "negotiation": [
            "I want to replace the subscription model with a one-time purchase. Centre owners hate monthly bills.",
            "Yes — centres collect fees from students per term, so paying per term matches how they budget.",
        ],
        "experiment_results": [{"observed": 6, "note": "MOCKED demo input: 6 owners requested a pilot (scripted, not real)."}],
        "support_ticket": {
            "subject": "How do I add a second teacher?",
            "body": "We started the pilot today. How do I add sessions for a second teacher in the same room?",
        },
    },
    "weak": {
        "debate": [
            "I want to build a general AI chat app for everyone in Egypt, like ChatGPT but free.",
            "I don't want a niche. Everyone uses AI chat — if mine is free and in Arabic, people will switch.",
        ],
        "reject_reason": "",
        "negotiation_node": None,
        "negotiation": [],
        "experiment_results": [],
        "support_ticket": None,
    },
}

# --- Shared fixtures -------------------------------------------------------------------------

_INSIGHTS = {
    "summary": "A technically capable student with a small budget and limited weekly time, close to the education "
    "space as a user, with no commercial or sales experience.",
    "strengths": [
        "Can build simple web software alone (Python, basic web development).",
        "First-hand knowledge of exam-season pressure as a student.",
        "Direct access to student groups and two teachers at a tutoring centre.",
    ],
    "limitations": [
        "No sales or B2B experience.",
        "EGP 10,000 cannot fund model training or large-scale model hosting.",
        "15 hours a week limits support and sales capacity.",
    ],
    "constraints": ["Must fit around university schedule", "No misleading marketing"],
    "advantage_areas": ["Tools for students and the people who teach them"],
    "open_questions": [
        "Which specific problem has the founder seen people fail to solve?",
        "Who would pay — students, families or institutions?",
    ],
}


def _scores(values: dict[str, tuple[int, str]]) -> list[dict[str, Any]]:
    return [{"criterion": k, "score": s, "rationale": r, "evidence": "ASSUMPTION"} for k, (s, r) in values.items()]


def _gate_commentary(text: str, steps: list[str]) -> dict[str, Any]:
    return {"commentary": text, "suggested_next_steps": steps}


_CHALLENGE_CHATGPT = {
    "message": "Competing with ChatGPT head-on means matching a product people can already use for free, backed by very large "
    "model budgets and global distribution. With EGP 10,000 and 15 hours a week you could not train or serve a comparable "
    "model, and 'cheaper' is hard to win when the basic alternative costs nothing. 'Better for Egyptian users' could be a "
    "real angle, but right now it is an assumption: we don't know which task Egyptian users struggle with today.\n\n"
    "So the most useful question first: what specific problem have you personally seen people fail to solve with the tools "
    "they already have?",
    "stance": "CHALLENGE",
    "key_question": "What specific problem have you seen people fail to solve with existing tools?",
    "assumptions": [
        {"statement": "Egyptian users are poorly served by existing general AI assistants.", "classification": "ASSUMPTION",
         "why_it_matters": "The whole differentiation rests on it."},
        {"statement": "Users would switch to a new general assistant if it were cheaper.", "classification": "ASSUMPTION",
         "why_it_matters": "Free tiers of existing assistants make price a weak lever."},
        {"statement": "A solo founder can serve a competitive general-purpose model within EGP 10,000.", "classification": "ASSUMPTION",
         "why_it_matters": "Model usage costs grow with every user and could exceed the budget quickly."},
    ],
    "concerns": ["No specific customer or problem yet.", "Resources are far below what a general assistant needs."],
    "alternatives": [],
    "readiness": {"problem_defined": False, "customer_defined": False, "founder_fit_assessed": False,
                  "differentiation_identified": False, "feasible_with_resources": False, "first_experiment_identified": False,
                  "missing": ["A specific customer problem", "A specific customer group", "Why this founder can win"]},
    "recommend_proposal": False,
    "working_title": None,
}

# --- Main scenario fixtures ----------------------------------------------------------------------

_MAIN_PROPOSAL_1 = {
    "business_name": "Revisa",
    "one_liner": "A free web planner that turns a student's exam dates and course load into a revision schedule.",
    "product_category": "Study planning web app for university students",
    "problem": "University students with six or seven courses and overlapping exam dates plan revision in notebooks or chat "
    "groups and often abandon the plan within a week. (ASSUMPTION based on the founder's own observation; not yet confirmed by interviews.)",
    "target_customer": "Undergraduate students at the founder's university during exam season.",
    "solution": "A browser-based planner where a student enters courses and exam dates and gets a day-by-day revision plan they can tick off.",
    "founder_fit": "The founder is a student in this situation, can build the web app, and can reach classmates directly. Gap: no clear payer.",
    "founder_fit_score": 4,
    "value_proposition": "A realistic revision plan in five minutes instead of an abandoned notebook schedule.",
    "business_model": "Free at launch; a paid premium tier later (price and willingness to pay untested).",
    "revenue_streams": ["Optional premium plan for students (untested)"],
    "main_expenses": [
        {"item": "Domain and basic hosting", "estimate": {"amount": 1200, "currency": "EGP", "period": "per year",
                                                         "classification": "ASSUMPTION", "basis": "Rough assumption; prices not retrieved."}},
        {"item": "Campus outreach materials", "estimate": {"amount": 1500, "currency": "EGP", "period": "one-time",
                                                          "classification": "ASSUMPTION", "basis": "Leaflets for student areas; rough assumption."}},
    ],
    "estimated_startup_capital": {"amount": 3000, "currency": "EGP", "period": "first 3 months", "classification": "ASSUMPTION",
                                  "basis": "Sum of assumed expenses plus a small contingency."},
    "competitive_alternatives": [
        {"name": "Google Calendar", "note": "Free calendar some students already use for deadlines."},
        {"name": "Notion", "note": "Free templates for study planning."},
        {"name": "Paper planners and WhatsApp groups", "note": "The current status quo."},
    ],
    "major_risks": ["Students may not pay for any tier.", "Free alternatives already exist.",
                    "Abandoning plans may be a motivation problem, not a tooling problem."],
    "missing_evidence": ["Whether students would pay at all", "How many students abandon plans and why",
                         "Which features would change that behaviour"],
    "first_experiment": {"name": "Student waitlist test", "method": "Share a one-page landing page in three course groups and count sign-ups.",
                         "metric": "waitlist sign-ups", "target": 100, "window_days": 14,
                         "threshold_rationale": "About 100 sign-ups in two weeks from three large course groups would show interest beyond friends."},
    "reasons_for": ["Founder is the target user and can reach users today.", "Cheap and quick to build."],
    "reasons_against": ["No identified payer.", "Many free substitutes.", "'Monetise later' often means never."],
    "recommendation": "VALIDATE_CAREFULLY",
    "recommended_next_action": "Run the waitlist test and ask every sign-up one question about paying, before building.",
}

_MAIN_PROPOSAL_2 = {
    "business_name": "Revisa for Centres",
    "one_liner": "A simple revision-session schedule and attendance tracker for small tutoring centres in Egypt.",
    "product_category": "B2B scheduling software for small tutoring centres",
    "problem": "Small tutoring centres plan exam-season revision sessions across teachers, subjects and student groups on paper "
    "sheets and WhatsApp messages; clashes and missed sessions are discovered late. (ASSUMPTION from the founder's contacts at one "
    "centre; not yet confirmed by interviews.)",
    "target_customer": "Owners and coordinators of small tutoring centres (roughly 3–15 teachers) in Greater Cairo preparing students for exams.",
    "solution": "A browser-based tool to schedule revision sessions by subject, teacher and group, mark attendance, and export the week's "
    "plan — no installation and no student accounts in the first version.",
    "founder_fit": "Can build a records-style web tool with current skills, knows exam-season pressure first-hand, and has two teacher "
    "contacts at one centre. Gap: no experience selling to businesses.",
    "founder_fit_score": 4,
    "value_proposition": "See the whole exam-season revision plan and attendance in one place instead of across paper sheets and chat groups.",
    "business_model": "Subscription paid by the centre (B2B); price to be tested; free pilot for the first centres.",
    "revenue_streams": ["Monthly subscription per centre (price untested)"],
    "main_expenses": [
        {"item": "Domain and basic hosting", "estimate": {"amount": 1200, "currency": "EGP", "period": "per year",
                                                         "classification": "ASSUMPTION", "basis": "Rough assumption; prices not retrieved."}},
        {"item": "Leaflets for centre visits", "estimate": {"amount": 800, "currency": "EGP", "period": "one-time",
                                                           "classification": "ASSUMPTION", "basis": "Rough assumption."}},
        {"item": "Transport for centre visits", "estimate": {"amount": 1500, "currency": "EGP", "period": "first 3 months",
                                                            "classification": "ASSUMPTION", "basis": "Rough assumption for about 15 visits."}},
    ],
    "estimated_startup_capital": {"amount": 4000, "currency": "EGP", "period": "first 3 months", "classification": "ASSUMPTION",
                                  "basis": "Sum of the assumed expenses plus a contingency of about EGP 500."},
    "competitive_alternatives": [
        {"name": "WhatsApp", "note": "Groups used to announce sessions (status quo)."},
        {"name": "Google Sheets", "note": "Free spreadsheets some centres may already use."},
        {"name": "Paper schedules", "note": "Printed weekly plans on the centre wall."},
    ],
    "major_risks": ["Owners may not see clashes as a problem worth paying for.",
                    "Selling to businesses may take more than 15 hours a week.",
                    "Coordinators may not keep attendance up to date.",
                    "Only one centre is reachable through current contacts."],
    "missing_evidence": ["How many small tutoring centres exist in the target area (UNKNOWN)",
                         "Whether owners already pay for any software", "What price owners would accept",
                         "How often scheduling clashes actually happen"],
    "first_experiment": {"name": "Owner interest test",
                         "method": "Show a one-page landing page and a 10-minute walkthrough to centre owners; count owners who request a free pilot.",
                         "metric": "pilot requests from centre owners", "target": 5, "window_days": 21,
                         "threshold_rationale": "Five owner requests in three weeks would show interest beyond the founder's personal contacts."},
    "reasons_for": ["The payer already spends money on revision.", "Small, buildable scope.", "Founder has a warm introduction to one centre."],
    "reasons_against": ["B2B sales are slow.", "Status quo (paper and WhatsApp) is free and familiar.", "Evidence so far is one centre."],
    "recommendation": "VALIDATE_CAREFULLY",
    "recommended_next_action": "Interview 5–8 centre owners using the Mom Test and run the owner interest test before writing product code.",
}

_MAIN_COMPARISON = {
    "summary": "Heuristic comparison of three directions raised in the discussion. All scores are assumptions until interviews "
    "and experiments produce evidence.",
    "opportunities": [
        {
            "key": "student-planner", "title": "Exam revision planner for students",
            "description": "Free web planner that turns exam dates and course load into a revision schedule.",
            "target_customer": "University students at the founder's university",
            "estimated_startup_cost": {"amount": 3000, "currency": "EGP", "period": "first 3 months", "classification": "ASSUMPTION", "basis": "Hosting and outreach."},
            "scores": _scores({
                "founder_fit": (5, "Founder is the user and can build it."),
                "problem_severity": (3, "Painful in exam season, but students tolerate it."),
                "demand_evidence": (2, "Only the founder's observation."),
                "customer_reach": (5, "Direct access to course groups."),
                "differentiation": (2, "Many free planners exist."),
                "capital_requirements": (5, "Fits the budget."),
                "time_to_mvp": (5, "A few weeks."),
                "commercial_viability": (2, "No clear payer."),
                "technical_complexity": (5, "Simple web app."),
                "regulatory_constraints": (5, "Minimal personal data."),
                "risk": (3, "Low cost, but likely no revenue."),
                "operational_complexity": (5, "Self-serve."),
            }),
            "main_uncertainty": "Whether anyone pays.", "next_experiment": "Waitlist test with a payment question.",
        },
        {
            "key": "notes-summariser", "title": "AI notes summariser (Arabic/English)",
            "description": "Summarise lecture notes into revision sheets using a language model.",
            "target_customer": "University students",
            "estimated_startup_cost": {"amount": 15000, "currency": "EGP", "period": "first 3 months", "classification": "ASSUMPTION", "basis": "Per-use model costs grow with users."},
            "scores": _scores({
                "founder_fit": (3, "Matches the AI interest; harder to build well."),
                "problem_severity": (3, "Useful but not urgent."),
                "demand_evidence": (2, "No evidence."),
                "customer_reach": (5, "Same student access."),
                "differentiation": (1, "General assistants already summarise notes."),
                "capital_requirements": (2, "Usage costs could exceed the budget."),
                "time_to_mvp": (4, "Quick prototype."),
                "commercial_viability": (2, "Students compare with free assistants."),
                "technical_complexity": (3, "Quality in Arabic is hard."),
                "regulatory_constraints": (4, "Uploaded notes may include copyrighted material."),
                "risk": (2, "Cost and differentiation risk."),
                "operational_complexity": (4, "Self-serve."),
            }),
            "main_uncertainty": "Why a student would not just use a free assistant.", "next_experiment": "Side-by-side test against a free assistant with 10 students.",
        },
        {
            "key": "tutoring-centres", "title": "Revision and attendance tracker for tutoring centres",
            "description": "Help small centres plan revision sessions and track attendance in one place.",
            "target_customer": "Owners and coordinators of small tutoring centres",
            "estimated_startup_cost": {"amount": 4000, "currency": "EGP", "period": "first 3 months", "classification": "ASSUMPTION", "basis": "Hosting, leaflets, transport."},
            "scores": _scores({
                "founder_fit": (4, "Can build it; knows the context; no sales experience."),
                "problem_severity": (3, "Plausible pain in exam season; unconfirmed."),
                "demand_evidence": (2, "Two teacher contacts at one centre."),
                "customer_reach": (3, "One warm introduction; others need visits."),
                "differentiation": (3, "Specific to revision sessions, unlike general tools."),
                "capital_requirements": (5, "Fits the budget."),
                "time_to_mvp": (4, "A records tool is quick to build."),
                "commercial_viability": (4, "Centres already spend money on revision."),
                "technical_complexity": (5, "Simple records tool."),
                "regulatory_constraints": (3, "Student names are personal data."),
                "risk": (3, "Slow sales; cheap to test."),
                "operational_complexity": (3, "Onboarding visits needed."),
            }),
            "main_uncertainty": "Whether owners will pay.", "next_experiment": "Owner interest test with a free-pilot offer.",
        },
    ],
}

MAIN: dict[tuple[str, str], list[dict[str, Any]]] = {
    ("founder_discovery", "interpret_founder_profile"): [_INSIGHTS],
    ("skeptical_cofounder", "debate_turn"): [
        _CHALLENGE_CHATGPT,
        {
            "message": "That is a much more concrete problem, and you are close to it: you are a student and you can reach student groups. "
            "Before we get excited, two cautions. A plan abandoned after a week is often a motivation problem rather than a tooling "
            "problem, and free planners and calendars already exist. So the tool alone may not change the behaviour.\n\n"
            "Three directions are worth comparing — I've listed them. The deciding question is who pays: individual students, or an "
            "organisation that already manages students' revision?",
            "stance": "PROBE",
            "key_question": "Who would pay: students themselves, or an organisation that already manages their revision?",
            "assumptions": [
                {"statement": "Students abandon revision plans mainly because planning is hard.", "classification": "ASSUMPTION",
                 "why_it_matters": "If the cause is motivation, a planner will not fix it."},
                {"statement": "Students at the founder's university would try a new planner.", "classification": "ASSUMPTION",
                 "why_it_matters": "Reach is the founder's main advantage."},
            ],
            "concerns": ["Free substitutes", "No payer identified"],
            "alternatives": [
                {"title": "Exam revision planner for students", "one_liner": "Turn exam dates and course load into a revision schedule.",
                 "why_better_fit": "You are the user and can reach users today; cheap to build."},
                {"title": "AI notes summariser", "one_liner": "Summarise lecture notes into revision sheets.",
                 "why_better_fit": "Uses your AI interest, but competes with free assistants and costs money per use."},
                {"title": "Revision tracker for tutoring centres", "one_liner": "Help centres plan revision sessions and track attendance.",
                 "why_better_fit": "Centres already spend money on revision, and you know two teachers at one."},
            ],
            "readiness": {"problem_defined": True, "customer_defined": False, "founder_fit_assessed": True,
                          "differentiation_identified": False, "feasible_with_resources": True, "first_experiment_identified": False,
                          "missing": ["Who pays", "Why this beats free alternatives", "First experiment"]},
            "recommend_proposal": False,
            "working_title": None,
        },
        {
            "message": "A free planner is the fastest thing you can test with your classmates, so I'll draft it as a proposal. I'll be explicit "
            "about its weakness, though: 'monetise later' without a payer is a common way student products stall. The proposal includes "
            "a waitlist test with a payment question from day one, so we learn about willingness to pay before you build.",
            "stance": "AGREE_WITH_CAVEATS",
            "key_question": None,
            "assumptions": [{"statement": "Some students would pay for a premium tier.", "classification": "ASSUMPTION",
                             "why_it_matters": "Without it there is no business, only a project."}],
            "concerns": ["No payer", "Free substitutes"],
            "alternatives": [],
            "readiness": {"problem_defined": True, "customer_defined": True, "founder_fit_assessed": True,
                          "differentiation_identified": True, "feasible_with_resources": True, "first_experiment_identified": True,
                          "missing": ["Who pays and how much"]},
            "recommend_proposal": True,
            "working_title": "Revisa",
        },
        {
            "message": "Moving the payer to tutoring centres fixes the biggest weakness of the student version: centres already spend money "
            "on revision. It also brings new risks. Selling to businesses is slower, owners may be comfortable with WhatsApp and paper, and "
            "two teacher contacts are not the same as an owner who decides on spending. I'd keep the product deliberately small — a "
            "revision-session schedule and attendance tracker a coordinator can use without training — and test with owners, not students.\n\n"
            "Can you get a 20-minute conversation with the owner of the centre where your contacts teach?",
            "stance": "AGREE_WITH_CAVEATS",
            "key_question": "Can you get a 20-minute conversation with the centre's owner?",
            "assumptions": [
                {"statement": "Centre owners experience scheduling clashes often enough to care.", "classification": "ASSUMPTION",
                 "why_it_matters": "It is the problem the product solves."},
                {"statement": "Owners would pay a small recurring fee.", "classification": "ASSUMPTION",
                 "why_it_matters": "It is the business model."},
            ],
            "concerns": ["Slow B2B sales", "Evidence so far is one centre"],
            "alternatives": [],
            "readiness": {"problem_defined": True, "customer_defined": True, "founder_fit_assessed": True,
                          "differentiation_identified": True, "feasible_with_resources": True, "first_experiment_identified": True,
                          "missing": ["Owner willingness to pay"]},
            "recommend_proposal": True,
            "working_title": "Revisa for Centres",
        },
    ],
    ("skeptical_cofounder", "draft_proposal"): [_MAIN_PROPOSAL_1, _MAIN_PROPOSAL_2],
    ("opportunity_evaluation", "compare_opportunities"): [_MAIN_COMPARISON],
    ("skeptical_cofounder", "negotiate_node_edit"): [
        {
            "message": "I understand the objection, but a one-time price works against you here. Your costs repeat every term (hosting, "
            "support during each exam season), and a centre that pays once has no reason to stay in touch or renew. A one-time price high "
            "enough to cover two years of support would look expensive to a small centre and be harder to approve.\n\n"
            "What I'd consider instead is billing per academic term, because centres plan and collect fees by term. Is that closer to how "
            "owners budget?",
            "position": "DISAGREE",
            "ready_to_propose": False,
            "revision": None,
        },
        {
            "message": "Then per-term billing fits both sides: it matches how centres collect fees and it keeps revenue recurring for "
            "your recurring costs. I'd keep the first term free as a pilot. Here is the revision for you to approve or reject.",
            "position": "COUNTER_PROPOSAL",
            "ready_to_propose": True,
            "revision": {
                "current_plan": "Monthly subscription per centre (price untested).",
                "proposed_plan": "Per-term subscription per centre, billed once per academic term (about four months), first term free as a pilot. Price still untested.",
                "reasons": ["Centres collect student fees per term, so a per-term bill matches their budgeting.",
                            "Costs recur every term; revenue should too.",
                            "A one-time price would have to be high enough to deter small centres."],
                "consequences": ["Revenue arrives in larger, less frequent amounts; cash planning must cover gaps between terms.",
                                 "Churn becomes visible only at term boundaries.",
                                 "The pricing question in interviews must ask about a per-term price."],
                "affected_nodes": ["revenue", "revenue-stream-1"],
                "remaining_risks": ["Willingness to pay per term is untested.", "Centres may skip the low season."],
                "changes": [
                    {"node_id": "revenue", "field": "summary", "value": "Per-term subscription per centre (billed each academic term, about four months); first term free as a pilot."},
                    {"node_id": "revenue", "field": "strategy", "value": "Bill the way centres collect fees: once per term. Test the per-term price with owners before Phase 4."},
                    {"node_id": "revenue", "field": "risks", "value": ["Revenue is uneven between terms.", "Willingness to pay per term is untested."]},
                    {"node_id": "revenue-stream-1", "field": "title", "value": "Per-term subscription per centre"},
                    {"node_id": "revenue-stream-1", "field": "summary", "value": "Billed once per academic term; price untested (ASSUMPTION)."},
                ],
            },
        },
    ],
    ("market_research", "plan_research"): [
        {
            "questions": [
                {"question": "What share of people in Egypt use the internet?", "why_it_matters": "Bounds how many centre staff can use a browser-based tool.",
                 "related_node_id": "market-context", "indicator_hint": "internet_users"},
                {"question": "How has consumer-price inflation in Egypt moved recently?", "why_it_matters": "A price set in EGP may need regular review.",
                 "related_node_id": "costs", "indicator_hint": "inflation"},
                {"question": "How many small tutoring centres operate in Greater Cairo?", "why_it_matters": "Sizes the reachable market; no free source is known.",
                 "related_node_id": "primary-customer", "indicator_hint": "none"},
                {"question": "Do centre owners currently pay for any scheduling or admin software?", "why_it_matters": "Tests willingness to pay.",
                 "related_node_id": "revenue", "indicator_hint": "none"},
            ],
            "competitor_candidates": ["WhatsApp", "Google Sheets"],
            "customer_problem_hypotheses": [
                "Centre coordinators discover session clashes only after students complain.",
                "Attendance for revision sessions is recorded on paper and rarely reviewed.",
            ],
        }
    ],
    ("validation", "design_interviews"): [
        {
            "target_profile": "Owner or coordinator of a small tutoring centre (3–15 teachers) who planned last exam season's revision sessions.",
            "recruiting_channels": ["Introduction through the founder's two teacher contacts", "Walk-in visits to centres near the university",
                                    "Local teachers' groups, with the admin's permission"],
            "questions": [
                "Walk me through how you planned revision sessions for the last exam season.",
                "Tell me about the last time two sessions clashed or one was missed. What happened?",
                "How did you find out, and what did you do about it?",
                "What do you use today to keep the schedule and attendance?",
                "How much time did you or your coordinator spend on the schedule last week?",
                "Have you ever paid for software for the centre? What made you decide?",
                "Who else would need to agree before you changed how scheduling works?",
            ],
            "avoid": ["Asking 'Would you use an app that…?'", "Pitching before listening", "Counting compliments as evidence"],
        }
    ],
    ("validation", "design_validation"): [
        {
            "lean_canvas": {
                "problem": ["Revision sessions clash or are missed during exam season", "Attendance is on paper and not reviewed", "Plans live across paper and chat groups"],
                "customer_segments": ["Owners and coordinators of small tutoring centres in Greater Cairo"],
                "unique_value_proposition": "The whole exam-season revision plan and attendance on one page.",
                "solution": ["Session schedule by subject, teacher and group", "One-tap attendance", "Weekly plan export"],
                "channels": ["Teacher introductions", "Centre visits", "Teachers' groups (with permission)"],
                "revenue_streams": ["Per-term subscription per centre (price untested)"],
                "cost_structure": ["Hosting and domain", "Transport for visits", "Founder time"],
                "key_metrics": ["Pilot requests from owners", "Weeks with attendance recorded", "Renewals at term end"],
                "unfair_advantage": "None yet — a warm introduction to one centre is an advantage, not a moat.",
            },
            "riskiest_assumptions": [
                {"statement": "Owners see scheduling clashes as a problem worth paying to solve.", "risk": "high", "node_id": "core-problem",
                 "how_to_test": "Mom Test interviews and the owner interest test."},
                {"statement": "Owners will pay per term after a free pilot.", "risk": "high", "node_id": "revenue",
                 "how_to_test": "Ask pilot centres for a written intent to continue at the proposed price."},
                {"statement": "Coordinators will keep attendance up to date in a tool.", "risk": "medium", "node_id": "product",
                 "how_to_test": "Track pilot usage for two weeks."},
            ],
            "landing_page": {
                "headline": "Plan exam-season revision sessions in one place",
                "subheadline": "A simple schedule and attendance tracker for small tutoring centres. Free pilot for the first centres.",
                "benefits": ["See every teacher's sessions for the week on one page", "Mark attendance in seconds", "Export the week's plan to share with students"],
                "call_to_action": "Request a free pilot",
                "waitlist_question": "How many teachers work at your centre?",
            },
            "extra_experiments": [],
        }
    ],
    ("product_architect", "specify_mvp"): [
        {
            "product_name": "Revisa for Centres",
            "problem_statement": "Coordinators of small tutoring centres need one place to plan revision sessions and record attendance.",
            "primary_user": "Centre coordinator or owner, on a laptop at the centre",
            "user_journeys": [
                {"name": "Plan the week", "steps": ["Open the tool", "Add each revision session with subject, group, teacher, date and time", "Review the list for the week", "Export the plan as CSV"]},
                {"name": "Record attendance", "steps": ["Find today's session", "Enter the number of students present", "Move the session to Held"]},
            ],
            "must_have_features": [
                {"name": "Add a revision session", "capability": "create_records", "user_value": "Capture the plan in one place."},
                {"name": "Edit a session", "capability": "edit_records", "user_value": "Fix times and rooms quickly."},
                {"name": "Delete a session", "capability": "delete_records", "user_value": "Remove mistakes."},
                {"name": "Search by subject, teacher or group", "capability": "search", "user_value": "Answer 'when is X teaching?' instantly."},
                {"name": "Filter by status", "capability": "filter_by_status", "user_value": "See only planned or held sessions."},
                {"name": "Move a session forward", "capability": "status_workflow", "user_value": "Track planned → confirmed → held."},
                {"name": "Upcoming sessions count", "capability": "due_dates", "user_value": "See how many sessions are in the next 7 days."},
                {"name": "Summary counts", "capability": "summary_stats", "user_value": "Sessions by status at a glance."},
                {"name": "Export the week's plan", "capability": "csv_export", "user_value": "Share with teachers and students."},
                {"name": "Keep data between visits", "capability": "local_persistence", "user_value": "No account needed for the pilot."},
            ],
            "out_of_scope": ["Automatic clash detection between sessions", "Student accounts and notifications",
                             "Shared backend and multi-device sync", "Arabic interface (planned after pilot feedback)",
                             "Payments (MOCKED in this build)"],
            "entity": {
                "name_singular": "Revision session",
                "name_plural": "Revision sessions",
                "fields": [
                    {"key": "subject", "label": "Subject", "type": "text", "options": [], "required": True},
                    {"key": "group_name", "label": "Student group", "type": "text", "options": [], "required": True},
                    {"key": "teacher", "label": "Teacher", "type": "text", "options": [], "required": True},
                    {"key": "session_date", "label": "Date", "type": "date", "options": [], "required": True},
                    {"key": "start_time", "label": "Start time", "type": "select", "options": ["09:00", "11:00", "13:00", "15:00", "17:00", "19:00"], "required": True},
                    {"key": "room", "label": "Room", "type": "text", "options": [], "required": False},
                    {"key": "students_present", "label": "Students present", "type": "number", "options": [], "required": False},
                    {"key": "notes", "label": "Notes", "type": "longtext", "options": [], "required": False},
                ],
                "status_options": ["Planned", "Confirmed", "Held", "Cancelled"],
            },
            "acceptance_criteria": [
                "A coordinator can add a session with subject, group, teacher, date and time.",
                "Sessions persist after closing and reopening the browser.",
                "Searching for a teacher returns only that teacher's sessions.",
                "The plan exports as CSV that opens in a spreadsheet.",
                "Attendance can be recorded for a held session.",
            ],
            "tech_choices": ["Static HTML, CSS and JavaScript (no backend)", "Browser localStorage for the pilot", "Node's built-in test runner"],
        }
    ],
    ("mvp_builder", "write_mvp_copy"): [
        {
            "app_title": "Revisa for Centres",
            "tagline": "Plan revision sessions and record attendance on one page.",
            "empty_state": "No sessions yet. Add this week's first revision session with the form.",
            "getting_started": ["Add each revision session for this week.", "Use search to check a teacher's sessions.",
                                "After a session, enter the number of students present and move it to Held.",
                                "Export the plan as CSV to share it."],
            "privacy_note": "Your data stays in this browser on this computer. Nothing is uploaded. Clearing browser data deletes it, so export a CSV regularly.",
        }
    ],
    ("commercial", "propose_commercial_setup"): [
        {
            "pricing_model": "Per-term subscription per centre (agreed in the plan revision); first term free as a pilot.",
            "tiers": [
                {"name": "Pilot", "price": 0, "currency": "EGP", "period": "per_term_4_months", "includes": ["All features for one term", "Setup help from the founder"]},
                {"name": "Centre", "price": 1500, "currency": "EGP", "period": "per_term_4_months", "includes": ["Unlimited sessions and teachers", "CSV export", "Support during working hours"]},
            ],
            "price_rationale": "EGP 1,500 per term is an ASSUMPTION to test in owner interviews: low enough for a small centre's owner to decide alone, "
            "and enough that a handful of paying centres would cover the assumed monthly costs. It must be validated before any real sale.",
            "cost_assumptions": [
                {"item": "Hosting and domain", "amount": 100, "currency": "EGP", "kind": "fixed_monthly", "classification": "ASSUMPTION", "basis": "Annual cost spread monthly; prices not retrieved."},
                {"item": "Mobile data and transport for support", "amount": 400, "currency": "EGP", "kind": "fixed_monthly", "classification": "ASSUMPTION", "basis": "Rough assumption."},
                {"item": "Onboarding visit per new centre", "amount": 150, "currency": "EGP", "kind": "variable_per_sale", "classification": "ASSUMPTION", "basis": "Transport for one visit."},
                {"item": "Leaflets and setup", "amount": 800, "currency": "EGP", "kind": "one_time", "classification": "ASSUMPTION", "basis": "Rough assumption."},
            ],
            "policy_specifics": {"refund_window_days": 14,
                                 "data_collected": ["Centre name and contact details (for support)", "Session records entered by the centre (kept in the centre's own browser in the MVP)"],
                                 "governing_region": "Egypt", "support_channel": "the support contact on the product page [placeholder]"},
            "compliance_checklist": [
                {"item": "Ask a lawyer whether Egypt's personal data protection law applies to the data handled", "why": "Session records can include student names."},
                {"item": "Register the business activity before taking any real payment", "why": "Required before invoicing customers."},
                {"item": "Have a lawyer review the draft terms, privacy and refund policies", "why": "They are drafts, not legal advice."},
                {"item": "Avoid storing student names during the pilot where possible", "why": "Reduces personal-data risk."},
                {"item": "Choose a payment method only after legal review", "why": "No payment method is connected in Mate."},
            ],
            "operational_requirements": ["Founder answers support within one working day during exam season", "Remind pilot centres to export a CSV backup weekly"],
        }
    ],
    ("launch", "prepare_launch_package"): [
        {
            "store_headline": "Revisa for Centres — revision sessions and attendance on one page",
            "product_description": "Revisa for Centres helps small tutoring centres plan exam-season revision sessions by subject, teacher and group, "
            "record attendance, and export the week's plan. It runs in the browser with no installation. It is an early product built "
            "by a student founder; the first term is a free pilot and feedback shapes what comes next.",
            "feature_bullets": ["Schedule sessions by subject, teacher, group and time", "Record attendance after each session",
                                "Search and filter the week's plan", "Export the plan as CSV"],
            "announcements": [
                {"channel": "WhatsApp message to teacher contacts", "text": "Hi — I'm a CS student building a simple tool for tutoring centres to plan revision sessions and record attendance. "
                 "I'm looking for two centres to try it free for one term and tell me honestly what's missing. Could you introduce me to your centre's owner?"},
                {"channel": "Post in a local teachers' group (with admin permission)", "text": "I'm building a free-pilot tool for small tutoring centres to plan revision sessions and attendance in one place. "
                 "If you coordinate sessions and are willing to try it for a term and give feedback, message me."},
            ],
            "launch_checklist": [
                {"item": "Founder approves the store page and announcements", "owner": "founder"},
                {"item": "Founder posts the announcements personally (Mate never posts)", "owner": "founder"},
                {"item": "Run the MOCKED purchase, delivery, replay and refund test", "owner": "system"},
                {"item": "Lawyer reviews the draft policies before any real sale", "owner": "founder"},
                {"item": "Set up a support inbox", "owner": "founder"},
            ],
            "delivery_message": "Thanks for joining the Revisa for Centres pilot. Your access key is below. Open the tool, add this week's sessions, "
            "and reply to this message if anything is unclear.",
        }
    ],
    ("operations", "triage_support_ticket"): [
        {"category": "Setup help", "priority": "normal",
         "draft_reply": "Thanks for starting the pilot. Add a separate session for the second teacher with the same date, time and room — "
         "each row is one teacher's session. Clash detection is not in this version yet; I've noted that you need it.",
         "needs_founder": True}
    ],
    ("operations", "review_operations"): [
        {
            "support_workflow": ["Ticket arrives by the support contact", "Mate categorises it and drafts a reply",
                                 "Founder edits and sends the reply personally", "Feature requests are logged against plan nodes"],
            "support_categories": ["Setup help", "Bug report", "Feature request", "Billing question (MOCKED billing)"],
            "memo": {
                "recommendation": "CONTINUE",
                "summary": "In this demo run the owner interest test met its target, but that result is a MOCKED scripted input, and every order, refund "
                "and ticket is synthetic. Nothing here is evidence about real centres. The rules say continue; the honest next step is a real pilot "
                "with one centre and real interviews before any further building.",
                "what_we_learned": ["The MOCKED purchase → delivery → refund → revocation cycle works and reconciles.",
                                    "The first support question asked for clash detection, which is out of scope today."],
                "evidence_gaps": ["Real owner interviews", "Real willingness to pay per term", "Real usage by a coordinator"],
                "next_experiments": ["Two-week pilot with one real centre", "Ask pilot owners for written intent to pay EGP 1,500 per term"],
            },
        }
    ],
    ("gatekeeper", "explain_phase1_gate_go"): [_gate_commentary(
        "The proposal fits the founder's skills and budget and declares a measurable first experiment, so the gate allows validation. "
        "Nothing has been validated yet: research could not retrieve live sources in this run, and the key questions remain UNKNOWN.",
        ["Interview 5–8 centre owners with the Mom Test questions", "Run the owner interest test with the declared target"])],
    ("gatekeeper", "explain_phase2_gate_go"): [_gate_commentary(
        "The recorded result met the target that was declared before the experiment started. In this demo the result is a MOCKED scripted input.",
        ["Replace demo inputs with real pilot requests before relying on this result"])],
    ("gatekeeper", "explain_phase3_gate_go"): [_gate_commentary(
        "The MVP was generated from the template, all generated tests passed and every must-have feature maps to a supported capability.",
        ["Open the MVP and walk through both user journeys with a coordinator"])],
    ("gatekeeper", "explain_phase4_gate_go"): [_gate_commentary(
        "Pricing covers variable cost per sale, the draft policies are labelled as drafts, and the founder approved the commercial setup.",
        ["Have a lawyer review the policies before any real sale"])],
    ("gatekeeper", "explain_phase5_gate_go"): [_gate_commentary(
        "The launch package is approved and the MOCKED purchase, delivery, replay and refund cycle behaved correctly and reconciles.",
        ["Post the approved announcements yourself", "Keep checkout MOCKED until legal and payment decisions are made"])],
    ("gatekeeper", "explain_phase6_gate_go"): [_gate_commentary(
        "The rules say continue, but the basis is MOCKED demo data. Treat this as a demonstration of the decision rule, not a market result.",
        ["Run a real pilot", "Record real results and re-run this gate"])],
}

# --- Weak scenario fixtures ----------------------------------------------------------------------

WEAK: dict[tuple[str, str], list[dict[str, Any]]] = {
    ("founder_discovery", "interpret_founder_profile"): [_INSIGHTS],
    ("skeptical_cofounder", "debate_turn"): [
        {**_CHALLENGE_CHATGPT},
        {
            "message": "I'll be direct: on the evidence we have, this is a direction I'd recommend stopping rather than refining. 'Free' is not an "
            "advantage when established assistants already offer free tiers, and a free product at your budget means paying for every user's "
            "model usage out of EGP 10,000 with no revenue to replace it. Arabic support alone is unlikely to be a lasting difference.\n\n"
            "If you still want a proposal for this exact idea, I'll write it honestly — including the reasons against.",
            "stance": "RECOMMEND_STOP",
            "key_question": None,
            "assumptions": [
                {"statement": "People will switch from existing assistants to a new free one with Arabic support.", "classification": "ASSUMPTION",
                 "why_it_matters": "Without switching there are no users."},
                {"statement": "Serving a free general assistant costs far more than EGP 10,000 per year at any meaningful scale.", "classification": "ASSUMPTION",
                 "why_it_matters": "It decides whether the idea is fundable at all."},
            ],
            "concerns": ["No differentiation", "Costs scale with users while revenue is zero", "No customer access"],
            "alternatives": [{"title": "A narrow tool for a group you can reach", "one_liner": "Solve one specific task for people you already know.",
                              "why_better_fit": "Fits your budget and lets you test demand cheaply."}],
            "readiness": {"problem_defined": False, "customer_defined": False, "founder_fit_assessed": True,
                          "differentiation_identified": False, "feasible_with_resources": False, "first_experiment_identified": True,
                          "missing": ["A specific problem", "Any differentiation", "A cost model that fits the budget"]},
            "recommend_proposal": False,
            "working_title": "General AI chat app",
        },
    ],
    ("skeptical_cofounder", "draft_proposal"): [
        {
            "business_name": "General AI chat app (working title)",
            "one_liner": "A free, Arabic-first general-purpose AI chat app for everyone in Egypt.",
            "product_category": "General-purpose AI assistant (consumer app)",
            "problem": "The founder believes Egyptian users want a free assistant in Arabic. No specific problem has been identified (UNKNOWN).",
            "target_customer": "Everyone in Egypt who uses AI chat (undefined segment).",
            "solution": "A chat app on top of an open-weight language model, free to use.",
            "founder_fit": "Technical interest is real, but the founder has no customer access, no differentiation and a budget far below the cost of serving a general assistant.",
            "founder_fit_score": 2,
            "value_proposition": "Free and in Arabic — both already available from established assistants (ASSUMPTION).",
            "business_model": "None identified: free to users, no payer.",
            "revenue_streams": ["None identified"],
            "main_expenses": [{"item": "Model inference and hosting for a free user base",
                               "estimate": {"amount": 1500000, "currency": "EGP", "period": "first year", "classification": "ASSUMPTION",
                                            "basis": "Order-of-magnitude assumption for serving a free assistant to a growing user base; not sourced. The true figure is UNKNOWN."}}],
            "estimated_startup_capital": {"amount": 1500000, "currency": "EGP", "period": "first year", "classification": "ASSUMPTION",
                                          "basis": "Order-of-magnitude assumption, not sourced. Even if wrong by a factor of ten it exceeds the budget."},
            "competitive_alternatives": [{"name": "ChatGPT", "note": "Established general assistant with a free tier."},
                                         {"name": "Google Gemini", "note": "Established general assistant with a free tier."}],
            "major_risks": ["Costs grow with every user while revenue is zero.", "No reason for users to switch.", "No customer access."],
            "missing_evidence": ["Any specific problem", "Any evidence users would switch", "A cost model at this budget"],
            "first_experiment": {"name": "Switching-intent test", "method": "Landing page offering a free Arabic assistant; count sign-ups.",
                                 "metric": "waitlist sign-ups", "target": 100, "window_days": 14, "threshold_rationale": "Founder's chosen target."},
            "reasons_for": ["Founder is motivated by AI."],
            "reasons_against": ["Capital needed is far beyond the budget.", "No differentiation.", "No payer.", "No customer access."],
            "recommendation": "DO_NOT_PROCEED",
            "recommended_next_action": "Stop this direction. Return to discovery and pick a narrow problem for a group you can reach.",
        }
    ],
    ("market_research", "plan_research"): [
        {
            "questions": [
                {"question": "What share of people in Egypt use the internet?", "why_it_matters": "Upper bound on reachable users.",
                 "related_node_id": "market-context", "indicator_hint": "internet_users"},
                {"question": "Why would users switch from existing free assistants?", "why_it_matters": "Core differentiation question.",
                 "related_node_id": "competitors", "indicator_hint": "none"},
            ],
            "competitor_candidates": ["ChatGPT", "Google Gemini"],
            "customer_problem_hypotheses": ["Arabic speakers find existing assistants hard to use."],
        }
    ],
    ("validation", "design_interviews"): [
        {
            "target_profile": "Adults in Egypt who used an AI assistant in the last month.",
            "recruiting_channels": ["Classmates", "University groups"],
            "questions": ["Tell me about the last time you used an AI assistant. What for?", "What went wrong, if anything?",
                          "What did you do when it did not help?", "Have you paid for any AI tool? Why or why not?"],
            "avoid": ["Asking whether they would use a free Arabic assistant"],
        }
    ],
    ("gatekeeper", "explain_phase1_gate_stop"): [_gate_commentary(
        "The required capital (an ASSUMPTION of about 150× the budget) is far beyond what the founder has, the heuristic founder fit is 2/5, "
        "and Mate's own proposal advised against proceeding. Under the gate rules this is a STOP, not a pivot.",
        ["Reopen the discussion to look for a narrow problem for a group the founder can reach",
         "Do not spend money testing this direction"])],
}

SCENARIOS: dict[str, dict[tuple[str, str], list[dict[str, Any]]]] = {"main": MAIN, "weak": WEAK}

END_OF_SCRIPT_DEBATE = {
    "message": "This is the end of the scripted demo conversation. Scripted mode cannot respond to new messages. Request a proposal, "
    "or start a live venture to continue the discussion with the live model.",
    "stance": "PROBE",
    "key_question": None,
    "assumptions": [],
    "concerns": [],
    "alternatives": [],
    "readiness": {"missing": ["Scripted demo has ended"]},
    "recommend_proposal": False,
    "working_title": None,
}


def scripted_response(scenario: str, agent: str, task: str, turn: int) -> dict[str, Any] | None:
    fixtures = SCENARIOS.get(scenario, {}).get((agent, task))
    if not fixtures:
        return None
    if turn < len(fixtures):
        return fixtures[turn]
    if task == "debate_turn":
        return END_OF_SCRIPT_DEBATE
    return fixtures[-1]


# Gate commentary is scripted per outcome. If a demo run reaches an outcome the script did not
# anticipate, no commentary is returned (the UI says so) rather than text that contradicts the gate.
