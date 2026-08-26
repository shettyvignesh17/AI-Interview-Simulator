import random
import uuid
from collections import Counter

from interview_simulator.utils.common import (
    clamp,
    extract_significant_terms,
    iso_now,
    tokenize,
    unique_list,
)


DIFFICULTY_LADDER = ["beginner", "intermediate", "advanced"]

ROUND_PROFILES = {
    "managerial": {
        "label": "Managerial Round",
        "opening": "We'll focus on leadership judgment, stakeholder alignment, and ownership.",
        "strong_reaction": "That shows mature leadership thinking.",
        "neutral_reaction": "There is a useful idea there. Tighten the structure a bit more.",
        "struggle_reaction": "I need a clearer and more concrete leadership example from you.",
    },
    "technical": {
        "label": "Technical Interview",
        "opening": "Let's evaluate how you reason through technical trade-offs, debugging, and execution.",
        "strong_reaction": "Solid. Your reasoning feels structured and practical.",
        "neutral_reaction": "You are on the right track. Go one layer deeper next time.",
        "struggle_reaction": "Let's slow it down and make the answer more concrete.",
    },
    "hr": {
        "label": "HR Interview",
        "opening": "This round is about clarity, role fit, motivation, and professional self-awareness.",
        "strong_reaction": "That answer feels grounded and authentic.",
        "neutral_reaction": "The intent is good. Make the message sharper and more role-aligned.",
        "struggle_reaction": "I need a more specific and confident answer here.",
    },
}

DOMAIN_PROFILES = {
    "software_engineering": {
        "label": "Software Engineering",
        "keywords": ["api", "backend", "frontend", "scalability", "testing", "deployment"],
        "topics": [
            {
                "name": "system design",
                "keywords": ["architecture", "latency", "cache", "availability", "service"],
                "scenario": "designing a product that must stay responsive during traffic spikes",
                "managerial_focus": "guiding a team through a risky architecture change",
                "hr_focus": "balancing speed, quality, and ownership",
                "easy_anchor": "the first two components you would design and why",
                "deep_anchor": "the trade-offs around caching, consistency, and failure isolation",
            },
            {
                "name": "apis and integrations",
                "keywords": ["api", "contract", "versioning", "authentication", "integration"],
                "scenario": "building and evolving an external API used by multiple clients",
                "managerial_focus": "coordinating backend, frontend, and external partners around an API change",
                "hr_focus": "communicating clearly across technical and non-technical teams",
                "easy_anchor": "how you would keep the API simple and predictable",
                "deep_anchor": "how you would version, observe, and secure the integration",
            },
            {
                "name": "reliability and debugging",
                "keywords": ["logs", "incident", "monitoring", "debugging", "root cause"],
                "scenario": "investigating a production issue that users are actively feeling",
                "managerial_focus": "leading incident response without creating panic in the team",
                "hr_focus": "staying calm and accountable when production breaks",
                "easy_anchor": "the first signals you would inspect to narrow the issue",
                "deep_anchor": "how you would separate mitigation, root cause analysis, and prevention",
            },
            {
                "name": "testing and quality",
                "keywords": ["testing", "qa", "automation", "coverage", "quality"],
                "scenario": "raising confidence in a feature that ships frequently",
                "managerial_focus": "building a quality culture when release pressure is high",
                "hr_focus": "taking ownership of quality even when deadlines are tight",
                "easy_anchor": "the minimum test layers you would add first",
                "deep_anchor": "how you would balance confidence, speed, and maintainability",
            },
            {
                "name": "data modeling",
                "keywords": ["schema", "query", "index", "normalization", "consistency"],
                "scenario": "designing a data model that supports growth and reporting needs",
                "managerial_focus": "driving alignment when teams disagree on data definitions",
                "hr_focus": "working carefully with ambiguity and long-term maintainability",
                "easy_anchor": "the core entities you would model first",
                "deep_anchor": "how you would reason about schema evolution and query performance",
            },
        ],
    },
    "data_science": {
        "label": "Data Science",
        "keywords": ["data", "experiment", "model", "feature", "analysis"],
        "topics": [
            {
                "name": "experimentation",
                "keywords": ["hypothesis", "ab test", "metric", "uplift", "bias"],
                "scenario": "designing an experiment to validate whether a product change works",
                "managerial_focus": "aligning stakeholders on metrics when teams want different outcomes",
                "hr_focus": "translating analytical work into business impact",
                "easy_anchor": "the main metric and guardrail metric you would choose",
                "deep_anchor": "how you would handle bias, statistical power, and noisy data",
            },
            {
                "name": "feature engineering",
                "keywords": ["feature", "signal", "encoding", "drift", "pipeline"],
                "scenario": "creating features for a predictive model with messy input data",
                "managerial_focus": "prioritizing data quality work under delivery pressure",
                "hr_focus": "being disciplined when the data is incomplete or imperfect",
                "easy_anchor": "the first transformations you would trust enough to ship",
                "deep_anchor": "how you would guard against leakage and drifting features",
            },
            {
                "name": "model evaluation",
                "keywords": ["precision", "recall", "roc", "baseline", "validation"],
                "scenario": "deciding whether a model is good enough for production",
                "managerial_focus": "communicating model trade-offs to cross-functional leaders",
                "hr_focus": "making balanced decisions instead of chasing vanity metrics",
                "easy_anchor": "the baseline you would compare against first",
                "deep_anchor": "how you would select metrics when different mistakes have different costs",
            },
            {
                "name": "storytelling",
                "keywords": ["insight", "dashboard", "visualization", "decision", "stakeholder"],
                "scenario": "presenting an analysis that should influence a product decision",
                "managerial_focus": "driving alignment with data when opinions are strong",
                "hr_focus": "communicating clearly and persuasively without overselling",
                "easy_anchor": "the one message you would lead with",
                "deep_anchor": "how you would explain uncertainty while still recommending action",
            },
            {
                "name": "deployment and monitoring",
                "keywords": ["serving", "monitoring", "latency", "drift", "retraining"],
                "scenario": "shipping a model that needs to stay useful after release",
                "managerial_focus": "working with engineering to make data products reliable",
                "hr_focus": "owning outcomes after a model has launched",
                "easy_anchor": "the first production metric you would watch",
                "deep_anchor": "how you would respond when drift and latency conflict with each other",
            },
        ],
    },
    "ai_ml": {
        "label": "AI/ML",
        "keywords": ["model", "prompt", "evaluation", "embedding", "pipeline"],
        "topics": [
            {
                "name": "model selection",
                "keywords": ["latency", "cost", "accuracy", "fine-tuning", "trade-off"],
                "scenario": "choosing the right model for a user-facing AI feature",
                "managerial_focus": "leading trade-off discussions between speed, cost, and model quality",
                "hr_focus": "taking responsible ownership in fast-moving AI work",
                "easy_anchor": "the first selection criteria you would write down",
                "deep_anchor": "how you would compare quality, latency, and cost before launch",
            },
            {
                "name": "prompt and evaluation design",
                "keywords": ["prompt", "eval", "hallucination", "rubric", "benchmark"],
                "scenario": "improving an AI assistant that sometimes gives weak or risky answers",
                "managerial_focus": "setting quality bars for an AI product before wider rollout",
                "hr_focus": "staying honest about uncertainty and model limitations",
                "easy_anchor": "the evaluation signals you would start measuring first",
                "deep_anchor": "how you would reduce hallucinations without hurting usefulness",
            },
            {
                "name": "mlops",
                "keywords": ["deployment", "versioning", "observability", "rollback", "pipeline"],
                "scenario": "operationalizing an ML workflow for repeated releases",
                "managerial_focus": "bringing engineering discipline to a research-heavy team",
                "hr_focus": "working effectively between experimentation and production rigor",
                "easy_anchor": "the minimum release controls you would put in place",
                "deep_anchor": "how you would version models, prompts, and evaluations together",
            },
            {
                "name": "responsible ai",
                "keywords": ["bias", "privacy", "safety", "fairness", "risk"],
                "scenario": "reducing risk in an AI feature that affects user decisions",
                "managerial_focus": "escalating ethical risk while keeping the team aligned",
                "hr_focus": "showing judgment when performance and safety pull in different directions",
                "easy_anchor": "the user risks you would identify first",
                "deep_anchor": "how you would design monitoring and human review for sensitive cases",
            },
            {
                "name": "retrieval systems",
                "keywords": ["retrieval", "embedding", "ranking", "context", "grounding"],
                "scenario": "building a retrieval-augmented system that must stay accurate and fast",
                "managerial_focus": "coordinating product and platform teams on AI system quality",
                "hr_focus": "bringing systems thinking to modern AI application design",
                "easy_anchor": "how you would keep context relevant without overloading the model",
                "deep_anchor": "how you would evaluate retrieval quality separately from generation quality",
            },
        ],
    },
    "core_engineering": {
        "label": "Core Engineering",
        "keywords": ["design", "safety", "process", "quality", "efficiency"],
        "topics": [
            {
                "name": "design calculations",
                "keywords": ["load", "material", "factor", "stress", "tolerance"],
                "scenario": "validating a design before it moves toward production",
                "managerial_focus": "ensuring technical rigor while teams push for speed",
                "hr_focus": "bringing discipline and accountability to engineering decisions",
                "easy_anchor": "the first assumptions and constraints you would document",
                "deep_anchor": "how you would validate safety factors and design margins",
            },
            {
                "name": "manufacturing and process",
                "keywords": ["throughput", "yield", "process", "bottleneck", "cycle time"],
                "scenario": "improving a process that is slowing delivery or quality",
                "managerial_focus": "leading process change without losing team buy-in",
                "hr_focus": "staying pragmatic while improving real-world operations",
                "easy_anchor": "the first bottleneck you would investigate",
                "deep_anchor": "how you would separate process variation from operator error",
            },
            {
                "name": "safety and compliance",
                "keywords": ["standard", "compliance", "audit", "risk", "mitigation"],
                "scenario": "making sure a design or process meets strict safety expectations",
                "managerial_focus": "raising compliance concerns when a deadline is at risk",
                "hr_focus": "showing judgment when safety and pressure collide",
                "easy_anchor": "the critical standards or checks you would review first",
                "deep_anchor": "how you would document decisions and mitigation for auditability",
            },
            {
                "name": "root cause analysis",
                "keywords": ["failure", "fault", "investigation", "corrective", "preventive"],
                "scenario": "investigating a recurring failure and preventing it from returning",
                "managerial_focus": "running a calm and effective post-incident review",
                "hr_focus": "taking ownership after a technical issue affects delivery",
                "easy_anchor": "the evidence you would collect before making conclusions",
                "deep_anchor": "how you would turn findings into preventive action, not just a quick fix",
            },
            {
                "name": "optimization",
                "keywords": ["cost", "efficiency", "trade-off", "quality", "constraint"],
                "scenario": "improving efficiency without harming safety or quality",
                "managerial_focus": "making trade-off decisions when every option has downsides",
                "hr_focus": "showing balanced judgment in constrained environments",
                "easy_anchor": "the one metric you would optimize first",
                "deep_anchor": "how you would justify a trade-off between cost and performance",
            },
        ],
    },
}

FILLER_PHRASES = ["maybe", "kind of", "sort of", "i guess", "not sure", "um", "uh"]
STRUCTURE_WORDS = ["first", "second", "then", "because", "therefore", "result", "impact"]
IMPACT_WORDS = ["improved", "reduced", "increased", "saved", "delivered", "launched", "led", "owned"]
STAR_WORDS = ["situation", "task", "action", "result", "challenge", "outcome"]
RNG = random.SystemRandom()

def start_session(round_type, domain, difficulty, resume_profile, max_questions, persistent_asked_ids=None):
    round_profile = ROUND_PROFILES[round_type]
    opening = round_profile["opening"]
    # The selected difficulty controls the starting point, then the interview adapts from there.
    current_level = difficulty if difficulty in DIFFICULTY_LADDER else "beginner"
    question_bank = _build_question_bank(round_type, domain, resume_profile)
    first_question, pool_recycled = _select_question_for_level(
        target_level=current_level,
        question_bank=question_bank,
        session_asked_ids=set(),
        persistent_asked_ids=set(persistent_asked_ids or []),
        recent_topic=None,
    )

    transcript = [
        {
            "speaker": "interviewer",
            "kind": "intro",
            "text": f"{opening} {first_question['text']}",
            "timestamp": iso_now(),
        }
    ]

    return {
        "id": str(uuid.uuid4()),
        "current_question": first_question["text"],
        "current_question_id": first_question["id"],
        "current_level": first_question["difficulty"],
        "asked_questions": [first_question],
        "transcript": transcript,
        "score": 0,
        "confidence_score": 0,
        "clarity_score": 0,
        "depth_score": 0,
        "strengths": [],
        "weaknesses": [],
        "suggestions": [],
        "interviewer_notes": opening,
        "status": "active",
        "question_index": 1,
        "max_questions": max_questions,
        "pool_recycled": pool_recycled,
        "created_at": iso_now(),
    }


def evaluate_answer(session_state, answer, round_type, domain, base_difficulty, resume_profile, persistent_asked_ids=None):
    last_question = session_state["asked_questions"][-1]
    domain_profile = DOMAIN_PROFILES[domain]
    round_profile = ROUND_PROFILES[round_type]
    answer_tokens = tokenize(answer)
    word_count = len(answer_tokens)
    sentence_count = max(answer.count("."), answer.count("?"), answer.count("!"), 1)
    avg_sentence_len = word_count / sentence_count

    filler_hits = sum(answer.lower().count(phrase) for phrase in FILLER_PHRASES)
    structure_hits = sum(answer.lower().count(word) for word in STRUCTURE_WORDS)
    impact_hits = sum(answer.lower().count(word) for word in IMPACT_WORDS)
    star_hits = sum(answer.lower().count(word) for word in STAR_WORDS)
    numeric_hits = sum(character.isdigit() for character in answer)
    relevance_hits = _keyword_overlap(answer_tokens, last_question["expected_keywords"] + domain_profile["keywords"])

    confidence_score = clamp(
        30 + min(word_count, 160) * 0.22 + structure_hits * 4 - filler_hits * 6 + min(numeric_hits, 8) * 1.5
    )
    clarity_score = clamp(
        28
        + structure_hits * 10
        + min(sentence_count, 6) * 4
        + max(0, 25 - abs(avg_sentence_len - 18))
        - filler_hits * 4
    )
    depth_score = clamp(
        18 + relevance_hits * 10 + impact_hits * 7 + min(numeric_hits, 10) * 2 + star_hits * 5
    )
    relevance_score = clamp(22 + relevance_hits * 12 + impact_hits * 5)

    if round_type == "technical":
        overall_score = (
            confidence_score * 0.2
            + clarity_score * 0.25
            + depth_score * 0.35
            + relevance_score * 0.2
        )
    elif round_type == "managerial":
        overall_score = (
            confidence_score * 0.2
            + clarity_score * 0.25
            + depth_score * 0.2
            + relevance_score * 0.15
            + clamp(25 + impact_hits * 10 + star_hits * 7) * 0.2
        )
    else:
        overall_score = (
            confidence_score * 0.25
            + clarity_score * 0.35
            + depth_score * 0.15
            + relevance_score * 0.25
        )

    performance_band = _performance_band(overall_score)
    reaction = _reaction_for_band(round_profile, performance_band)
    interruption = _build_interruption(answer, clarity_score, performance_band)

    strengths, weaknesses, suggestions = _build_feedback(
        round_type,
        word_count,
        confidence_score,
        clarity_score,
        depth_score,
        relevance_score,
        impact_hits,
        filler_hits,
    )

    updated_strengths = unique_list(session_state["strengths"] + strengths)
    updated_weaknesses = unique_list(session_state["weaknesses"] + weaknesses)
    updated_suggestions = unique_list(session_state["suggestions"] + suggestions)

    transcript = list(session_state["transcript"])
    transcript.append(
        {
            "speaker": "candidate",
            "kind": "answer",
            "text": answer.strip(),
            "timestamp": iso_now(),
        }
    )

    session_complete = session_state["question_index"] >= session_state["max_questions"]
    current_level = session_state.get("current_level") or last_question.get("difficulty") or "beginner"
    next_question = None
    pool_recycled = False

    if not session_complete:
        question_bank = _build_question_bank(round_type, domain, resume_profile)
        session_asked_ids = {
            question["id"] for question in session_state["asked_questions"] if question.get("id")
        }
        next_question, pool_recycled = get_next_question(
            user_score=overall_score,
            current_level=current_level,
            question_bank=question_bank,
            session_asked_ids=session_asked_ids,
            persistent_asked_ids=set(persistent_asked_ids or []),
            recent_topic=last_question.get("topic"),
        )
        transcript.append(
            {
                "speaker": "interviewer",
                "kind": "question",
                "text": f"{reaction} {next_question['text']}",
                "timestamp": iso_now(),
            }
        )
    else:
        transcript.append(
            {
                "speaker": "interviewer",
                "kind": "summary",
                "text": _final_summary(updated_strengths, updated_weaknesses, updated_suggestions),
                "timestamp": iso_now(),
            }
        )

    completed_at = iso_now() if session_complete else None
    answered_questions = session_state["question_index"]
    rolling_divisor = max(answered_questions, 1)
    next_level = next_question["difficulty"] if next_question else current_level

    updated_state = {
        "current_question": next_question["text"] if next_question else session_state["current_question"],
        "current_question_id": next_question["id"] if next_question else last_question["id"],
        "current_level": next_level,
        "asked_questions": session_state["asked_questions"] + ([next_question] if next_question else []),
        "transcript": transcript,
        "score": round(((session_state["score"] * (rolling_divisor - 1)) + overall_score) / rolling_divisor, 2),
        "confidence_score": round(
            ((session_state["confidence_score"] * (rolling_divisor - 1)) + confidence_score) / rolling_divisor, 2
        ),
        "clarity_score": round(
            ((session_state["clarity_score"] * (rolling_divisor - 1)) + clarity_score) / rolling_divisor, 2
        ),
        "depth_score": round(
            ((session_state["depth_score"] * (rolling_divisor - 1)) + depth_score) / rolling_divisor, 2
        ),
        "strengths": updated_strengths[:6],
        "weaknesses": updated_weaknesses[:6],
        "suggestions": updated_suggestions[:6],
        "interviewer_notes": reaction,
        "status": "completed" if session_complete else "active",
        "question_index": session_state["question_index"] + (0 if session_complete else 1),
        "pool_recycled": pool_recycled,
        "completed_at": completed_at,
    }

    return {
        "state": updated_state,
        "evaluation": {
            "overallScore": round(overall_score, 1),
            "confidenceScore": round(confidence_score, 1),
            "clarityScore": round(clarity_score, 1),
            "depthScore": round(depth_score, 1),
            "performanceBand": performance_band,
            "currentLevel": next_level,
            "strengths": strengths[:3],
            "weaknesses": weaknesses[:3],
            "suggestions": suggestions[:3],
            "reaction": reaction,
            "interruption": interruption,
            "complete": session_complete,
            "progressPercent": round((answered_questions / session_state["max_questions"]) * 100),
            "poolRecycled": pool_recycled,
            "questionNumber": answered_questions,
        },
    }


def _build_question_bank(round_type, domain, resume_profile):
    domain_profile = DOMAIN_PROFILES[domain]
    bank = {level: [] for level in DIFFICULTY_LADDER}

    for index, topic in enumerate(domain_profile["topics"], start=1):
        for level in DIFFICULTY_LADDER:
            question = _topic_question(round_type, domain, domain_profile["label"], topic, level, index)
            bank[level].append(question)

    resume_bank = _build_resume_question_bank(round_type, domain, domain_profile, resume_profile)
    for level in DIFFICULTY_LADDER:
        bank[level].extend(resume_bank[level])

    return bank


def _build_resume_question_bank(round_type, domain, domain_profile, resume_profile):
    bank = {level: [] for level in DIFFICULTY_LADDER}
    if not resume_profile:
        return bank

    projects = resume_profile.get("projects", [])
    experience = resume_profile.get("experience", [])
    skills = resume_profile.get("skills", [])

    if round_type == "technical" and projects:
        project = projects[0]
        project_slug = _slugify(project)
        bank["beginner"].append(
            _question_object(
                question_id=f"{round_type}:{domain}:beginner:resume-project:{project_slug}",
                text=f"Your resume mentions '{project}'. Give me a simple overview of the problem and the solution you built.",
                topic="resume-project",
                difficulty="beginner",
                expected_keywords=extract_significant_terms(project) + domain_profile["keywords"],
                source="resume",
            )
        )
        bank["intermediate"].append(
            _question_object(
                question_id=f"{round_type}:{domain}:intermediate:resume-project:{project_slug}",
                text=f"Tell me about the toughest implementation challenge in '{project}' and how you worked through it.",
                topic="resume-project",
                difficulty="intermediate",
                expected_keywords=extract_significant_terms(project) + domain_profile["keywords"],
                source="resume",
            )
        )
        bank["advanced"].append(
            _question_object(
                question_id=f"{round_type}:{domain}:advanced:resume-project:{project_slug}",
                text=f"If '{project}' had to support 10x more scale, what design trade-offs would you revisit first?",
                topic="resume-project",
                difficulty="advanced",
                expected_keywords=extract_significant_terms(project) + domain_profile["keywords"],
                source="resume",
            )
        )

    if round_type == "managerial" and experience:
        role_line = experience[0]
        role_slug = _slugify(role_line)
        bank["beginner"].append(
            _question_object(
                question_id=f"{round_type}:{domain}:beginner:resume-experience:{role_slug}",
                text=f"In the experience you listed as '{role_line}', tell me about one moment where you had to coordinate people to get work done.",
                topic="resume-experience",
                difficulty="beginner",
                expected_keywords=extract_significant_terms(role_line) + ["team", "stakeholder", "delivery"],
                source="resume",
            )
        )
        bank["intermediate"].append(
            _question_object(
                question_id=f"{round_type}:{domain}:intermediate:resume-experience:{role_slug}",
                text=f"Describe a leadership challenge from '{role_line}' where different stakeholders wanted different outcomes. How did you align them?",
                topic="resume-experience",
                difficulty="intermediate",
                expected_keywords=extract_significant_terms(role_line) + ["team", "stakeholder", "alignment"],
                source="resume",
            )
        )
        bank["advanced"].append(
            _question_object(
                question_id=f"{round_type}:{domain}:advanced:resume-experience:{role_slug}",
                text=f"Looking back at '{role_line}', what high-risk decision required the strongest leadership judgment from you, and why?",
                topic="resume-experience",
                difficulty="advanced",
                expected_keywords=extract_significant_terms(role_line) + ["risk", "leadership", "decision"],
                source="resume",
            )
        )

    if round_type == "hr" and skills:
        skill = skills[0]
        skill_slug = _slugify(skill)
        bank["beginner"].append(
            _question_object(
                question_id=f"{round_type}:{domain}:beginner:resume-skill:{skill_slug}",
                text=f"You highlight '{skill}' on your resume. Why is that a meaningful strength for this role?",
                topic="resume-skill",
                difficulty="beginner",
                expected_keywords=extract_significant_terms(skill) + domain_profile["keywords"],
                source="resume",
            )
        )
        bank["intermediate"].append(
            _question_object(
                question_id=f"{round_type}:{domain}:intermediate:resume-skill:{skill_slug}",
                text=f"How have you turned '{skill}' into real value on a team, and where are you still improving?",
                topic="resume-skill",
                difficulty="intermediate",
                expected_keywords=extract_significant_terms(skill) + domain_profile["keywords"],
                source="resume",
            )
        )
        bank["advanced"].append(
            _question_object(
                question_id=f"{round_type}:{domain}:advanced:resume-skill:{skill_slug}",
                text=f"If you joined a new team tomorrow, how would you use '{skill}' to create early impact while still learning the environment?",
                topic="resume-skill",
                difficulty="advanced",
                expected_keywords=extract_significant_terms(skill) + domain_profile["keywords"],
                source="resume",
            )
        )

    return bank


def _question_object(question_id, text, topic, difficulty, expected_keywords, source, topic_data=None):
    return {
        "id": question_id,
        "question": text,
        "text": text,
        "topic": topic,
        "difficulty": difficulty,
        "level": difficulty,
        "expected_keywords": expected_keywords,
        "source": source,
        "topic_data": topic_data,
    }


def _topic_question(round_type, domain, domain_label, topic, difficulty, index):
    if round_type == "technical":
        if difficulty == "beginner":
            text = f"In a {domain_label} role, how would you approach {topic['scenario']}? Keep it practical and high level."
        elif difficulty == "advanced":
            text = (
                f"Describe how you would handle {topic['scenario']} in a production setting, "
                f"and defend the trade-offs you would make."
            )
        else:
            text = f"Walk me through how you would handle {topic['scenario']}. Explain your reasoning clearly."
    elif round_type == "managerial":
        if difficulty == "beginner":
            text = f"Tell me about a time you had to handle {topic['managerial_focus']}. What was your approach?"
        elif difficulty == "advanced":
            text = (
                f"Imagine you're responsible for {topic['managerial_focus']} in a high-pressure environment. "
                f"How would you align stakeholders, decide quickly, and manage risk?"
            )
        else:
            text = f"How would you lead a team through {topic['managerial_focus']} while keeping execution on track?"
    else:
        if difficulty == "beginner":
            text = f"Why does working on {topic['hr_focus']} appeal to you in a {domain_label} role?"
        elif difficulty == "advanced":
            text = (
                f"What makes you a strong fit for work centered on {topic['hr_focus']}, "
                f"and what skill are you intentionally developing next?"
            )
        else:
            text = f"How does your background prepare you for {topic['hr_focus']} in a {domain_label} team?"

    return _question_object(
        question_id=f"{round_type}:{domain}:{difficulty}:{index}:{_slugify(topic['name'])}",
        text=text,
        topic=topic["name"],
        difficulty=difficulty,
        expected_keywords=topic["keywords"],
        source="bank",
        topic_data=topic,
    )


def get_random_question(level, question_bank, excluded_ids=None, recent_topic=None):
    excluded_ids = excluded_ids or set()
    candidates = [question for question in question_bank.get(level, []) if question["id"] not in excluded_ids]

    if recent_topic:
        rotated_candidates = [question for question in candidates if question["topic"] != recent_topic]
        if rotated_candidates:
            candidates = rotated_candidates

    if not candidates:
        return None

    return RNG.choice(candidates)


def _select_question_for_level(target_level, question_bank, session_asked_ids, persistent_asked_ids, recent_topic=None):
    strict_exclusions = set(session_asked_ids) | set(persistent_asked_ids)
    search_order = _level_search_order(target_level)

    for level in search_order:
        question = get_random_question(level, question_bank, strict_exclusions, recent_topic=recent_topic)
        if question:
            return question, False

    for level in search_order:
        question = get_random_question(level, question_bank, set(session_asked_ids), recent_topic=recent_topic)
        if question:
            return question, True

    for level in search_order:
        question = get_random_question(level, question_bank, set(), recent_topic=None)
        if question:
            return question, True

    fallback_level = target_level if target_level in DIFFICULTY_LADDER else "beginner"
    return question_bank[fallback_level][0], True


def get_next_question(user_score, current_level, question_bank, session_asked_ids, persistent_asked_ids, recent_topic=None):
    target_level = _get_next_level(user_score, current_level)
    return _select_question_for_level(
        target_level=target_level,
        question_bank=question_bank,
        session_asked_ids=session_asked_ids,
        persistent_asked_ids=persistent_asked_ids,
        recent_topic=recent_topic,
    )


def _get_next_level(user_score, current_level):
    index = DIFFICULTY_LADDER.index(current_level)
    if user_score >= 70:
        index = min(index + 1, len(DIFFICULTY_LADDER) - 1)
    elif user_score < 40:
        index = max(index - 1, 0)
    return DIFFICULTY_LADDER[index]


def _level_search_order(target_level):
    target_index = DIFFICULTY_LADDER.index(target_level)
    return sorted(
        DIFFICULTY_LADDER,
        key=lambda level: (abs(DIFFICULTY_LADDER.index(level) - target_index), DIFFICULTY_LADDER.index(level)),
    )


def _slugify(value):
    parts = tokenize(value)
    return "-".join(parts[:8]) or "question"


def _performance_band(score):
    if score >= 70:
        return "strong"
    if score >= 40:
        return "steady"
    return "struggling"


def _reaction_for_band(round_profile, performance_band):
    if performance_band == "strong":
        return round_profile["strong_reaction"]
    if performance_band == "steady":
        return round_profile["neutral_reaction"]
    return round_profile["struggle_reaction"]


def _build_interruption(answer, clarity_score, performance_band):
    if len(answer.split()) > 160:
        return "Let me pause you there. Lead with the conclusion first, then support it."
    if performance_band == "struggling" and clarity_score < 55:
        return "Pause for a second and structure it in three parts: context, action, result."
    return ""


def _keyword_overlap(answer_tokens, keywords):
    keyword_set = {keyword.lower() for keyword in keywords}
    hits = 0
    for token in answer_tokens:
        if token.lower() in keyword_set:
            hits += 1
    return hits


def _build_feedback(
    round_type,
    word_count,
    confidence_score,
    clarity_score,
    depth_score,
    relevance_score,
    impact_hits,
    filler_hits,
):
    strengths = []
    weaknesses = []
    suggestions = []

    if clarity_score >= 72:
        strengths.append("Clear answer structure")
    if confidence_score >= 72:
        strengths.append("Confident delivery under pressure")
    if depth_score >= 68:
        strengths.append("Good specificity and depth")
    if relevance_score >= 65:
        strengths.append("Answer stayed aligned to the role")
    if impact_hits >= 2:
        strengths.append("Connected actions to measurable outcomes")

    if word_count < 25:
        weaknesses.append("Answers were too brief")
        suggestions.append("Use a simple structure: context, action, result.")
    if word_count > 180:
        weaknesses.append("Answers became too long")
        suggestions.append("Lead with the headline, then add only the strongest supporting detail.")
    if confidence_score < 55:
        weaknesses.append("Confidence dipped in delivery")
        suggestions.append("Pause before answering and avoid hedging phrases.")
    if clarity_score < 55:
        weaknesses.append("Structure was hard to follow")
        suggestions.append("Use signposts such as first, then, and result.")
    if depth_score < 55:
        weaknesses.append("Examples needed more depth")
        suggestions.append("Add trade-offs, technical detail, or decision criteria.")
    if filler_hits >= 2:
        weaknesses.append("Filler language weakened the answer")
        suggestions.append("Replace hesitation with short pauses and direct statements.")

    if round_type == "managerial" and impact_hits == 0:
        suggestions.append("Highlight stakeholder impact and the result you achieved.")
    if round_type == "technical" and depth_score < 65:
        suggestions.append("Explain not only what you did, but why that approach was chosen.")
    if round_type == "hr" and relevance_score < 60:
        suggestions.append("Tie your answer back to role fit and motivation.")

    return unique_list(strengths)[:4], unique_list(weaknesses)[:4], unique_list(suggestions)[:4]


def _final_summary(strengths, weaknesses, suggestions):
    strength_text = strengths[0] if strengths else "steady communication"
    weakness_text = weaknesses[0] if weaknesses else "adding a bit more depth"
    suggestion_text = suggestions[0] if suggestions else "keep your answers structured and specific"
    return (
        f"Round complete. Your strongest signal was {strength_text.lower()}. "
        f"The main growth area is {weakness_text.lower()}. Next session, {suggestion_text.lower()}"
    )


def summarize_history(rows):
    round_scores = {"managerial": 0, "technical": 0, "hr": 0}
    round_counts = {"managerial": 0, "technical": 0, "hr": 0}
    strengths = Counter()
    weaknesses = Counter()
    suggestions = Counter()
    history = []

    for row in rows:
        round_scores[row["round_type"]] += row["score"]
        round_counts[row["round_type"]] += 1
        for item in row.get("strengths", []):
            strengths[item] += 1
        for item in row.get("weaknesses", []):
            weaknesses[item] += 1
        for item in row.get("suggestions", []):
            suggestions[item] += 1

        history.append(
            {
                "id": row["id"],
                "roundType": row["round_type"],
                "domain": row["domain"],
                "difficulty": row["difficulty"],
                "score": row["score"],
                "createdAt": row["created_at"],
                "completedAt": row.get("completed_at"),
            }
        )

    averaged = {}
    for round_type, total in round_scores.items():
        count = round_counts[round_type]
        averaged[round_type] = round(total / count, 1) if count else 0

    completed_scores = [row["score"] for row in rows if row.get("completed_at")]
    overall_average = round(sum(completed_scores) / len(completed_scores), 1) if completed_scores else 0

    trend_data = [
        {
            "label": item["createdAt"][:10],
            "score": item["score"],
        }
        for item in history[-6:]
    ]

    return {
        "roundScores": averaged,
        "overallAverage": overall_average,
        "completedSessions": len(completed_scores),
        "strengths": [item for item, _count in strengths.most_common(5)],
        "weaknesses": [item for item, _count in weaknesses.most_common(5)],
        "suggestions": [item for item, _count in suggestions.most_common(5)],
        "history": list(reversed(history[-10:])),
        "charts": {
            "roundBars": [
                {"label": ROUND_PROFILES[key]["label"], "value": value}
                for key, value in averaged.items()
            ],
            "trend": trend_data,
        },
    }
