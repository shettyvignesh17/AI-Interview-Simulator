"""Question delivery, adaptive scoring, reports, and interview-bank population."""

import random
import uuid
from collections import Counter

from interview_simulator.services.ai_interviewer import generate_adaptive_follow_up
from interview_simulator.utils.common import (
    clamp,
    extract_significant_terms,
    iso_now,
    safe_json_dumps,
    safe_json_loads,
    tokenize,
    unique_list,
)


COMPANIES = [
    "Alphabet (Google)", "Microsoft", "Amazon", "NVIDIA", "Apple", "Meta", "Netflix",
    "Adobe", "Salesforce", "Oracle", "IBM", "Intel", "AMD", "Cisco", "Qualcomm",
    "Samsung", "Uber", "Airbnb", "LinkedIn", "PayPal", "Walmart", "JPMorgan Chase",
    "Goldman Sachs", "Deloitte", "Accenture", "TCS", "Infosys", "Wipro", "Cognizant",
    "Capgemini", "Flipkart", "PhonePe", "Razorpay", "Swiggy", "Zomato", "Atlassian",
]

DOMAINS = {
    "software_engineering": "Software Engineering",
    "artificial_intelligence": "Artificial Intelligence",
    "machine_learning": "Machine Learning",
    "deep_learning": "Deep Learning",
    "data_science": "Data Science",
    "generative_ai": "Generative AI",
    "nlp": "Natural Language Processing",
    "computer_vision": "Computer Vision",
    "web_development": "Web Development",
    "backend_development": "Backend Development",
    "frontend_development": "Frontend Development",
    "full_stack_development": "Full Stack Development",
    "cloud_computing": "Cloud Computing",
    "devops": "DevOps",
    "cybersecurity": "Cybersecurity",
    "data_engineering": "Data Engineering",
    "database_sql": "Database / SQL",
    "computer_science_fundamentals": "Computer Science Fundamentals",
    # Legacy options remain valid for saved sessions and older API clients.
    "ai_ml": "AI / Machine Learning",
    "core_engineering": "Core Engineering",
}

ROUNDS = {
    "technical": "Technical Round",
    "managerial": "Manager Round",
    "hr": "HR Round",
}

DIFFICULTY_ORDER = ["easy", "medium", "hard"]
ANSWER_CLASSIFICATIONS = ("strong", "partial", "wrong", "insufficient", "timeout")
WEAK_CLASSIFICATIONS = {"wrong", "insufficient", "timeout"}
LEGACY_DIFFICULTIES = {
    "beginner": "easy",
    "intermediate": "medium",
    "advanced": "hard",
}
LEGACY_DIFFICULTIES_REVERSED = {value: key for key, value in LEGACY_DIFFICULTIES.items()}
FILLERS = ("um", "uh", "like", "basically", "actually", "you know", "kind of", "sort of")
STRUCTURE_MARKERS = ("first", "second", "then", "because", "therefore", "for example", "result")
STAR_MARKERS = ("situation", "task", "action", "result", "outcome", "challenge")
IMPACT_MARKERS = ("improved", "reduced", "increased", "saved", "delivered", "launched", "led", "owned")
RNG = random.SystemRandom()


def normalize_difficulty(value):
    normalized = str(value or "easy").strip().lower()
    return LEGACY_DIFFICULTIES.get(normalized, normalized if normalized in DIFFICULTY_ORDER else "easy")


def outward_difficulty(value, legacy=False):
    normalized = normalize_difficulty(value)
    return LEGACY_DIFFICULTIES_REVERSED[normalized] if legacy else normalized


def _domain_for(row):
    text = f"{row['category']} {row['topic']} {row['subcategory']}".lower()
    rules = (
        (("transformer", "large language", "rag", "prompt", "generative"), "generative_ai"),
        (("computer vision", "cnn", "image"), "computer_vision"),
        (("deep learning", "neural", "backprop", "lstm", "rnn"), "deep_learning"),
        (("machine learning", "model", "feature", "classification", "mlops"), "machine_learning"),
        (("ai/ml", "artificial intelligence", "embedding", "responsible ai"), "artificial_intelligence"),
        (("data science", "experiment", "pandas", "analysis"), "data_science"),
        (("sql", "database", "dbms", "acid", "normalization", "index"), "database_sql"),
        (("cloud", "availability zone"), "cloud_computing"),
        (("cyber", "security", "authentication", "authorization", "injection"), "cybersecurity"),
        (("frontend", "javascript", "web"), "frontend_development"),
        (("api", "backend", "rest", "message queue"), "backend_development"),
        (("pipeline", "data engineering"), "data_engineering"),
        (("deployment", "git", "testing", "devops"), "devops"),
        (("array", "linked list", "tree", "graph", "algorithm", "operating system", "network", "oop"),
         "computer_science_fundamentals"),
    )
    for terms, domain in rules:
        if any(term in text for term in terms):
            return domain
    return "software_engineering"


def _expected_keywords(row):
    tags = safe_json_loads(row["tags_json"], [])
    terms = extract_significant_terms(f"{row['answer']} {row['question']}")
    ignored = {"question", "answer", "explain", "would", "using", "interview", "approach"}
    return unique_list(
        [str(item).lower() for item in tags + terms if str(item).lower() not in ignored]
    )[:18]


def _follow_ups(bank_category, topic):
    if bank_category == "Coding":
        return [
            f"What are the time and space complexity trade-offs in your {topic} approach?",
            "Which edge cases would you test before you considered this solution production-ready?",
            "How would you improve the solution if the input were ten times larger?",
        ]
    if bank_category == "AI / Machine Learning":
        return [
            "Which baseline and evaluation metrics would you use, and why?",
            "How would you monitor this approach for drift, latency, and failure after deployment?",
            "What alternative would you compare against before making this decision?",
        ]
    if bank_category == "HR / Behavioral":
        return [
            "What was your specific contribution, and what measurable result followed?",
            "What would you do differently if the same situation happened again?",
            "How did you keep the other people involved aligned?",
        ]
    return [
        f"What is the most important trade-off to understand in {topic}?",
        "How would this change under production-scale constraints?",
        "What common mistake would you actively avoid here?",
    ]


def _variant_question(question, bank_category, variant):
    if variant == 0:
        return question
    additions = {
        "Coding": " Also explain the invariant, complexity, and edge cases you would validate before production.",
        "AI / Machine Learning": " Compare your preferred approach with one realistic alternative and define a production evaluation plan.",
        "HR / Behavioral": " Use a concrete situation, action, measurable result, and lesson learned in your response.",
    }
    return f"{question.rstrip()} {additions.get(bank_category, ' Defend the key trade-off with a practical example.').strip()}"


def _expand_rows(rows, target, bank_category, round_type=None):
    records = []
    for index in range(target):
        row = rows[index % len(rows)]
        variant = index // len(rows)
        question_id = f"iq-{bank_category.lower().replace(' ', '-').replace('/', '-')}-{row['id']}-{variant}"
        difficulty = str(row["difficulty"]).lower()
        keywords = _expected_keywords(row)
        records.append(
            {
                "id": question_id,
                "base_question_id": row["id"],
                "company": row["company"],
                "interview_round": round_type or "technical",
                "domain": "all_domains" if round_type in {"managerial", "hr"} else _domain_for(row),
                "bank_category": bank_category,
                "topic": row["topic"],
                "difficulty": difficulty,
                "question": _variant_question(row["question"], bank_category, variant),
                "ideal_answer": row["answer"],
                "answer_explanation": row["detailed_explanation"],
                "keywords_json": safe_json_dumps(keywords),
                "expected_points_json": safe_json_dumps(keywords[:8]),
                "follow_ups_json": safe_json_dumps(_follow_ups(bank_category, row["topic"])),
                "estimated_answer_time": {"easy": 90, "medium": 120, "hard": 180}.get(difficulty, 120),
                "frequency": row["frequency"],
                "tags_json": row["tags_json"],
                "provenance": "style_reference",
            }
        )
    return records


def ensure_interview_question_bank(database, force=False):
    current_count = database.execute("SELECT COUNT(*) FROM interview_questions").fetchone()[0]
    stale_ai_mapping = database.execute(
        "SELECT COUNT(*) FROM interview_questions "
        "WHERE bank_category='AI / Machine Learning' AND domain='software_engineering'"
    ).fetchone()[0]
    if current_count == 1000 and not force and not stale_ai_mapping:
        return current_count

    coding = database.execute(
        "SELECT * FROM learning_questions WHERE question_type='coding' AND category='Coding' ORDER BY id"
    ).fetchall()
    technical = database.execute(
        "SELECT * FROM learning_questions WHERE question_type='coding' AND category='Computer Science' ORDER BY id"
    ).fetchall()
    ai_categories = (
        "AI/ML", "Computer Vision", "Deep Learning", "Generative AI", "Large Language Models",
        "MLOps", "Machine Learning", "Python for AI", "RAG", "Transformers",
    )
    placeholders = ",".join("?" for _ in ai_categories)
    ai_rows = database.execute(
        f"SELECT * FROM learning_questions WHERE question_type='interview' AND category IN ({placeholders}) ORDER BY id",
        ai_categories,
    ).fetchall()
    hr_rows = database.execute(
        "SELECT * FROM learning_questions WHERE question_type='interview' AND category='HR' ORDER BY id"
    ).fetchall()
    manager_rows = database.execute(
        "SELECT * FROM learning_questions WHERE question_type='interview' "
        "AND category IN ('Behavioral','Situational','Project') ORDER BY id"
    ).fetchall()
    aptitude = database.execute(
        "SELECT * FROM learning_questions WHERE question_type='aptitude' ORDER BY id LIMIT 100"
    ).fetchall()

    records = []
    records.extend(_expand_rows(coding, 350, "Coding"))
    records.extend(_expand_rows(technical, 200, "Technical / Computer Science"))
    records.extend(_expand_rows(ai_rows, 200, "AI / Machine Learning"))
    records.extend(_expand_rows(hr_rows, 60, "HR / Behavioral", "hr"))
    records.extend(_expand_rows(manager_rows, 90, "HR / Behavioral", "managerial"))
    records.extend(_expand_rows(aptitude, 100, "Aptitude / Logical"))

    if force or current_count:
        database.execute("DELETE FROM interview_questions")
    columns = tuple(records[0].keys())
    values = ", ".join("?" for _ in columns)
    database.executemany(
        f"INSERT INTO interview_questions ({', '.join(columns)}) VALUES ({values})",
        [tuple(record[column] for column in columns) for record in records],
    )
    database.commit()
    return len(records)


def _question_payload(row, selected_company):
    return {
        "id": row["id"],
        "base_id": row["base_question_id"],
        "text": row["question"],
        "question": row["question"],
        "company": selected_company,
        "company_label": f"{selected_company}-style interview question",
        "round": row["interview_round"],
        "domain": row["domain"],
        "topic": row["topic"],
        "difficulty": row["difficulty"],
        "bank_category": row["bank_category"],
        "expected_keywords": safe_json_loads(row["keywords_json"], []),
        "expected_points": safe_json_loads(row["expected_points_json"], []),
        "follow_ups": safe_json_loads(row["follow_ups_json"], []),
        "ideal_answer": row["ideal_answer"],
        "answer_explanation": row["answer_explanation"],
        "estimated_answer_time": row["estimated_answer_time"],
        "frequency": row["frequency"],
        "tags": safe_json_loads(row["tags_json"], []),
        "source_company": row["company"],
        "provenance": row["provenance"],
        "is_follow_up": False,
        "follow_up_depth": 0,
        "generation_source": "question-bank",
        "generation_model": None,
        "follow_up_reason": "",
    }


def select_question(database, company, round_type, domain, difficulty, excluded_ids=None, weak_topics=None,
                    recent_topic=None):
    excluded_ids = {str(item) for item in (excluded_ids or [])}
    weak_topics = {str(item).lower() for item in (weak_topics or [])}
    normalized_difficulty = normalize_difficulty(difficulty)
    clauses = ["interview_round = ?"]
    values = [round_type]
    if round_type == "technical":
        clauses.append("bank_category <> 'Aptitude / Logical'")
    if excluded_ids:
        placeholders = ",".join("?" for _ in excluded_ids)
        clauses.append(f"id NOT IN ({placeholders})")
        values.extend(sorted(excluded_ids))
    rows = database.execute(
        f"SELECT * FROM interview_questions WHERE {' AND '.join(clauses)} "
        "ORDER BY CASE WHEN company=? THEN 0 ELSE 1 END, "
        "CASE WHEN domain=? THEN 0 WHEN domain='all_domains' THEN 1 ELSE 2 END, "
        "CASE WHEN difficulty=? THEN 0 ELSE 1 END, RANDOM() LIMIT 120",
        (*values, company, domain, normalized_difficulty),
    ).fetchall()
    if not rows:
        fallback_filter = " AND bank_category <> 'Aptitude / Logical'" if round_type == "technical" else ""
        rows = database.execute(
            f"SELECT * FROM interview_questions WHERE interview_round=?{fallback_filter} ORDER BY RANDOM() LIMIT 120",
            (round_type,),
        ).fetchall()
    if not rows:
        raise RuntimeError("The interview question bank is unavailable. Please restart the server.")

    target_index = DIFFICULTY_ORDER.index(normalized_difficulty)

    def rank(row):
        row_difficulty = str(row["difficulty"]).lower()
        difficulty_distance = abs(DIFFICULTY_ORDER.index(row_difficulty) - target_index)
        return (
            8 if row["company"] == company else 0,
            26 if row["domain"] == domain else (8 if row["domain"] == "all_domains" else 0),
            10 - difficulty_distance * 4,
            7 if row["topic"].lower() in weak_topics else 0,
            -30 if recent_topic and row["topic"] == recent_topic else 0,
            RNG.random() * 3,
        )

    chosen = max(rows, key=lambda row: sum(rank(row)))
    return _question_payload(chosen, company)


def start_delivery_session(database, company, round_type, domain, difficulty, max_questions,
                           duration_minutes, persistent_asked_ids=None):
    starting_difficulty = normalize_difficulty(difficulty)
    first = select_question(
        database, company, round_type, domain, starting_difficulty, excluded_ids=persistent_asked_ids
    )
    opening = {
        "technical": "We will begin with a technical question. Explain your reasoning clearly.",
        "managerial": "We will focus on judgment, ownership, and team leadership.",
        "hr": "We will focus on motivation, role fit, and professional self-awareness.",
    }[round_type]
    now = iso_now()
    return {
        "id": str(uuid.uuid4()),
        "current_question": first["text"],
        "current_level": outward_difficulty(starting_difficulty, difficulty in LEGACY_DIFFICULTIES),
        "starting_difficulty": outward_difficulty(starting_difficulty, difficulty in LEGACY_DIFFICULTIES),
        "strong_streak": 0,
        "weak_streak": 0,
        "adaptive_history": [],
        "timeout_count": 0,
        "asked_questions": [first],
        "transcript": [{"speaker": "interviewer", "kind": "intro", "text": opening, "timestamp": now}],
        "score": 0,
        "technical_score": 0,
        "communication_score": 0,
        "relevance_score": 0,
        "completeness_score": 0,
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
        "pool_recycled": False,
        "created_at": now,
        "started_at": now,
        "duration_minutes": duration_minutes,
    }


def _count_phrase(text, phrase):
    return text.lower().count(phrase)


def _evaluate_text(question, answer, round_type, voice_metrics=None):
    answer_lower = answer.lower()
    tokens = tokenize(answer)
    token_set = set(tokens)
    word_count = len(tokens)
    sentence_count = max(sum(answer.count(mark) for mark in ".?!"), 1)
    keywords = [str(item).lower() for item in question.get("expected_keywords", [])]
    matched = [term for term in keywords if term in token_set or term in answer_lower]
    coverage = len(matched) / max(min(len(keywords), 10), 1)
    filler_count = sum(_count_phrase(answer_lower, filler) for filler in FILLERS)
    structure_count = sum(_count_phrase(answer_lower, marker) for marker in STRUCTURE_MARKERS)
    star_count = sum(_count_phrase(answer_lower, marker) for marker in STAR_MARKERS)
    impact_count = sum(_count_phrase(answer_lower, marker) for marker in IMPACT_MARKERS)
    numeric_count = sum(character.isdigit() for character in answer)
    example_signal = any(marker in answer_lower for marker in ("for example", "in my", "when i", "such as"))

    technical = clamp(35 + coverage * 58 + min(word_count, 120) * 0.18 + min(numeric_count, 8) * 1.5)
    relevance = clamp(
        40 + coverage * 50 + min(word_count, 120) * 0.12
        + (8 if question["topic"].lower() in answer_lower else 0)
    )
    communication = clamp(
        42 + min(word_count, 100) * 0.16 + min(structure_count, 5) * 7
        + min(sentence_count, 6) * 2 - filler_count * 5
    )
    completeness = clamp(38 + coverage * 45 + min(word_count, 140) * 0.2 + (8 if example_signal else 0))
    if round_type in {"managerial", "hr"}:
        technical = clamp(35 + star_count * 10 + impact_count * 8 + (10 if example_signal else 0))
        completeness = clamp(completeness + star_count * 5 + impact_count * 4)

    voice_metrics = voice_metrics or {}
    reported_fillers = int(voice_metrics.get("fillerWords") or filler_count)
    long_pauses = int(voice_metrics.get("longPauses") or 0)
    wpm = float(voice_metrics.get("wordsPerMinute") or 0)
    if reported_fillers > 5:
        communication = clamp(communication - min(15, reported_fillers))
    if wpm and (wpm < 75 or wpm > 190):
        communication = clamp(communication - 6)
    if long_pauses > 3:
        communication = clamp(communication - min(10, long_pauses * 2))

    if round_type == "technical":
        overall = technical * 0.4 + relevance * 0.25 + communication * 0.15 + completeness * 0.2
    else:
        overall = technical * 0.2 + relevance * 0.25 + communication * 0.3 + completeness * 0.25
    if word_count >= 90 and structure_count >= 3 and (numeric_count or example_signal):
        overall = clamp(overall + 8)

    strengths = []
    improvements = []
    if technical >= 70:
        strengths.append("Covered the important concepts with useful technical depth.")
    if relevance >= 70:
        strengths.append("Stayed focused on the question and role context.")
    if communication >= 70:
        strengths.append("Used a clear, structured explanation.")
    if example_signal or impact_count:
        strengths.append("Supported the answer with concrete evidence or impact.")
    if coverage < 0.45:
        improvements.append("Cover more of the core concepts before moving to supporting detail.")
    if word_count < 25:
        improvements.append("Develop the answer with reasoning, trade-offs, and one concrete example.")
    if structure_count < 2:
        improvements.append("Use signposts such as problem, approach, result, and trade-off.")
    if filler_count >= 3:
        improvements.append("Replace filler words with short, deliberate pauses.")
    if round_type in {"managerial", "hr"} and star_count < 3:
        improvements.append("Use the STAR structure and make your personal contribution explicit.")
    if not strengths:
        strengths.append("Attempted the question and established a starting point for improvement.")
    if not improvements:
        improvements.append("Add one more trade-off or measurable outcome to make the answer stronger.")

    missed = [term for term in keywords if term not in matched][:6]
    return {
        "overallScore": round(overall, 1),
        "technicalScore": round(technical, 1),
        "relevanceScore": round(relevance, 1),
        "communicationScore": round(communication, 1),
        "completenessScore": round(completeness, 1),
        "confidenceScore": round(communication, 1),
        "clarityScore": round(communication, 1),
        "depthScore": round((technical + completeness) / 2, 1),
        "strengths": strengths[:3],
        "weaknesses": improvements[:3],
        "suggestions": improvements[:3],
        "missedConcepts": missed,
        "matchedKeywords": matched[:8],
        "wordCount": word_count,
        "fillerWords": reported_fillers,
        "performanceBand": "strong" if overall >= 70 else ("steady" if overall >= 40 else "struggling"),
    }


def _answer_classification(evaluation, timed_out=False):
    if timed_out:
        return "timeout"
    if evaluation["wordCount"] < 8:
        return "insufficient"
    if evaluation["overallScore"] >= 70:
        return "strong"
    if evaluation["overallScore"] >= 40:
        return "partial"
    return "wrong"


def _adaptive_transition(classification, current, strong_streak=0, weak_streak=0):
    """Change level only after two consecutive strong or weak classifications."""
    current_level = normalize_difficulty(current)
    index = DIFFICULTY_ORDER.index(current_level)
    change = "none"

    if classification == "strong":
        strong_streak += 1
        weak_streak = 0
        if strong_streak >= 2:
            next_index = min(index + 1, len(DIFFICULTY_ORDER) - 1)
            change = "increased" if next_index != index else "none"
            index = next_index
            strong_streak = 0
    elif classification in WEAK_CLASSIFICATIONS:
        weak_streak += 1
        strong_streak = 0
        if weak_streak >= 2:
            next_index = max(index - 1, 0)
            change = "decreased" if next_index != index else "none"
            index = next_index
            weak_streak = 0
    else:
        strong_streak = 0
        weak_streak = 0

    return DIFFICULTY_ORDER[index], strong_streak, weak_streak, change


def evaluate_delivery_answer(database, session_state, answer, round_type, domain, company,
                             persistent_asked_ids=None, answer_type="typed", duration_seconds=0,
                             voice_metrics=None, timed_out=False, ai_settings=None):
    current = session_state["asked_questions"][-1]
    evaluation = _evaluate_text(current, answer, round_type, voice_metrics)
    classification = _answer_classification(evaluation, timed_out)
    answered_number = session_state["question_index"]
    complete = answered_number >= session_state["max_questions"]
    legacy = str(session_state["current_level"]).lower() in LEGACY_DIFFICULTIES
    previous_difficulty = normalize_difficulty(session_state["current_level"])
    target_difficulty, strong_streak, weak_streak, adaptive_change = _adaptive_transition(
        classification,
        session_state["current_level"],
        session_state.get("strong_streak", 0),
        session_state.get("weak_streak", 0),
    )
    next_question = None
    pool_recycled = False

    if not complete:
        asked_ids = {item.get("id") for item in session_state["asked_questions"]}
        exclusions = asked_ids | {str(item) for item in (persistent_asked_ids or [])}
        # Alternate contextual probing with fresh topics so a short interview has both depth and breadth.
        if int(current.get("follow_up_depth") or 0) < 1:
            follow_up_evaluation = dict(evaluation)
            follow_up_evaluation["classification"] = classification
            next_question = generate_adaptive_follow_up(
                current=current,
                answer=answer,
                evaluation=follow_up_evaluation,
                round_type=round_type,
                domain=domain,
                company=company,
                target_difficulty=target_difficulty,
                transcript=session_state["transcript"],
                asked_questions=session_state["asked_questions"],
                settings=ai_settings,
            )
        else:
            weak_topics = [current["topic"]] if classification in WEAK_CLASSIFICATIONS else []
            next_question = select_question(
                database, company, round_type, domain, target_difficulty,
                excluded_ids=exclusions, weak_topics=weak_topics, recent_topic=current.get("topic"),
            )

    previous_count = answered_number - 1
    divisor = max(answered_number, 1)

    def rolling(previous, current_value):
        return round((previous * previous_count + current_value) / divisor, 2)

    transcript = list(session_state["transcript"])
    transcript.append(
        {"speaker": "candidate", "kind": "answer", "text": answer, "timestamp": iso_now(), "answerType": answer_type}
    )
    if next_question:
        transition = (
            "I want to follow up on that answer."
            if next_question.get("is_follow_up")
            else "Let's move to a different area."
        )
        transcript.append(
            {"speaker": "interviewer", "kind": "transition", "text": transition, "timestamp": iso_now()}
        )
    else:
        transcript.append(
            {"speaker": "interviewer", "kind": "summary", "text": "Thank you. The interview is complete.", "timestamp": iso_now()}
        )

    strengths = unique_list(session_state["strengths"] + evaluation["strengths"])
    weaknesses = unique_list(session_state["weaknesses"] + evaluation["weaknesses"])
    suggestions = unique_list(session_state["suggestions"] + evaluation["suggestions"])
    adaptive_history = list(session_state.get("adaptive_history", []))
    adaptive_history.append(
        {
            "questionNumber": answered_number,
            "classification": classification,
            "fromDifficulty": previous_difficulty,
            "toDifficulty": target_difficulty,
            "change": adaptive_change,
            "responseTime": max(0, int(duration_seconds or 0)),
            "timedOut": bool(timed_out),
            "nextQuestionType": "follow-up" if next_question and next_question.get("is_follow_up") else ("new-topic" if next_question else "complete"),
            "followUpSource": next_question.get("generation_source") if next_question and next_question.get("is_follow_up") else None,
        }
    )
    updated = {
        "current_question": next_question["text"] if next_question else session_state["current_question"],
        "current_level": outward_difficulty(target_difficulty, legacy),
        "asked_questions": session_state["asked_questions"] + ([next_question] if next_question else []),
        "transcript": transcript,
        "score": rolling(session_state["score"], evaluation["overallScore"]),
        "technical_score": rolling(session_state["technical_score"], evaluation["technicalScore"]),
        "communication_score": rolling(session_state["communication_score"], evaluation["communicationScore"]),
        "relevance_score": rolling(session_state["relevance_score"], evaluation["relevanceScore"]),
        "completeness_score": rolling(session_state["completeness_score"], evaluation["completenessScore"]),
        "confidence_score": rolling(session_state["confidence_score"], evaluation["confidenceScore"]),
        "clarity_score": rolling(session_state["clarity_score"], evaluation["clarityScore"]),
        "depth_score": rolling(session_state["depth_score"], evaluation["depthScore"]),
        "strengths": strengths[:8],
        "weaknesses": weaknesses[:8],
        "suggestions": suggestions[:8],
        "interviewer_notes": "Interview complete." if complete else "Question processed; detailed scoring is hidden until completion.",
        "status": "completed" if complete else "active",
        "question_index": answered_number if complete else answered_number + 1,
        "strong_streak": strong_streak,
        "weak_streak": weak_streak,
        "adaptive_history": adaptive_history,
        "timeout_count": session_state.get("timeout_count", 0) + (1 if timed_out else 0),
        "pool_recycled": pool_recycled,
        "completed_at": iso_now() if complete else None,
    }
    evaluation.update(
        {
            "complete": complete,
            "currentLevel": updated["current_level"],
            "questionNumber": answered_number,
            "progressPercent": round(answered_number / session_state["max_questions"] * 100),
            "reaction": "Thank you. Let's continue." if not complete else "Thank you. The interview is complete.",
            "interruption": "",
            "poolRecycled": False,
            "classification": classification,
            "timedOut": bool(timed_out),
            "adaptiveChange": adaptive_change,
            "responseTime": max(0, int(duration_seconds or 0)),
            "followUp": {
                "generated": bool(next_question and next_question.get("is_follow_up")),
                "source": next_question.get("generation_source") if next_question else None,
                "model": next_question.get("generation_model") if next_question else None,
            },
            "questionContext": {
                "isFollowUp": bool(current.get("is_follow_up")),
                "generationSource": current.get("generation_source", "question-bank"),
                "generationModel": current.get("generation_model"),
                "followUpReason": current.get("follow_up_reason", ""),
                "parentQuestionId": current.get("parent_question_id"),
            },
        }
    )
    return {
        "state": updated,
        "evaluation": evaluation,
        "answer_record": {
            "question_id": current["id"],
            "question_text": current["text"],
            "topic": current["topic"],
            "difficulty": current["difficulty"],
            "company": company,
            "round_type": round_type,
            "domain": domain,
            "answer_type": answer_type,
            "answer_text": answer,
            "duration_seconds": max(0, int(duration_seconds or 0)),
            "answer_classification": classification,
            "timed_out": 1 if timed_out else 0,
            "adaptive_change": adaptive_change,
            "voice_metrics_json": safe_json_dumps(voice_metrics or {}),
            "evaluation_json": safe_json_dumps(evaluation),
            "ideal_answer": current.get("ideal_answer", ""),
            "answer_explanation": current.get("answer_explanation", ""),
        },
    }


def build_report(database, session_id, user_id):
    interview = database.execute(
        "SELECT * FROM interview_sessions WHERE id=? AND user_id=?", (session_id, user_id)
    ).fetchone()
    if not interview:
        return None
    answers = database.execute(
        "SELECT * FROM candidate_answers WHERE session_id=? ORDER BY question_number", (session_id,)
    ).fetchall()
    events = database.execute(
        "SELECT * FROM integrity_events WHERE session_id=? ORDER BY created_at", (session_id,)
    ).fetchall()
    answer_payloads = []
    total_words = spoken_duration = response_duration = total_fillers = total_pauses = 0
    automatic_turn_completions = interviewer_interruptions = 0
    confidence_total = confidence_samples = 0
    repeated_phrases = Counter()
    attention_warnings = 0
    face_absence_events = 0
    classification_counts = Counter()
    for row in answers:
        evaluation = safe_json_loads(row["evaluation_json"], {})
        voice = safe_json_loads(row["voice_metrics_json"], {})
        classification = row["answer_classification"] or evaluation.get("classification", "insufficient")
        classification_counts[classification] += 1
        response_duration += row["duration_seconds"]
        if row["answer_type"] == "spoken":
            total_words += evaluation.get("wordCount", 0)
            spoken_duration += row["duration_seconds"]
            total_fillers += evaluation.get("fillerWords", 0)
            total_pauses += int(voice.get("longPauses") or 0)
            automatic_turn_completions += 1 if voice.get("autoSubmitted") else 0
            interviewer_interruptions += int(voice.get("interviewerInterruptions") or 0)
            try:
                confidence = float(voice.get("transcriptionConfidence") or 0)
            except (TypeError, ValueError):
                confidence = 0
            if confidence > 0:
                confidence_total += confidence
                confidence_samples += 1
            for phrase in voice.get("repeatedPhrases", []) or []:
                repeated_phrases[str(phrase)] += 1
        question_context = evaluation.get("questionContext", {})
        answer_payloads.append(
            {
                "questionNumber": row["question_number"],
                "questionId": row["question_id"],
                "question": row["question_text"],
                "topic": row["topic"],
                "difficulty": row["difficulty"],
                "company": row["company"],
                "roundType": row["round_type"],
                "domain": row["domain"],
                "answerType": row["answer_type"],
                "answer": row["answer_text"],
                "durationSeconds": row["duration_seconds"],
                "responseTime": row["duration_seconds"],
                "classification": classification,
                "timedOut": bool(row["timed_out"]),
                "adaptiveChange": row["adaptive_change"],
                "score": evaluation.get("overallScore", 0),
                "whatWentWell": evaluation.get("strengths", []),
                "couldImprove": evaluation.get("suggestions", []),
                "missedConcepts": evaluation.get("missedConcepts", []),
                "idealAnswer": row["ideal_answer"],
                "explanation": row["answer_explanation"],
                "isFollowUp": bool(question_context.get("isFollowUp")),
                "followUpSource": question_context.get("generationSource"),
                "followUpModel": question_context.get("generationModel"),
                "followUpReason": question_context.get("followUpReason", ""),
                "parentQuestionId": question_context.get("parentQuestionId"),
            }
        )
    event_payloads = []
    for row in events:
        if row["severity"] >= 1:
            attention_warnings += 1
        if row["event_type"] == "FACE_NOT_VISIBLE":
            face_absence_events += 1
        event_payloads.append(
            {
                "eventType": row["event_type"], "timestamp": row["created_at"],
                "duration": row["duration_seconds"], "questionNumber": row["question_number"],
                "severity": row["severity"],
            }
        )
    average_response = round(response_duration / len(answers), 1) if answers else 0
    speaking_wpm = round(total_words / (spoken_duration / 60), 1) if spoken_duration else 0
    adaptive_history = safe_json_loads(interview["adaptive_history_json"], [])
    generated_follow_ups = sum(1 for step in adaptive_history if step.get("nextQuestionType") == "follow-up")
    ai_generated_follow_ups = sum(1 for step in adaptive_history if step.get("followUpSource") == "openai")
    starting_difficulty = normalize_difficulty(interview["starting_difficulty"])
    ending_difficulty = normalize_difficulty(interview["difficulty"])
    return {
        "sessionId": interview["id"],
        "company": interview["company"],
        "roundType": interview["round_type"],
        "domain": interview["domain"],
        "difficulty": starting_difficulty,
        "startingDifficulty": starting_difficulty,
        "endingDifficulty": ending_difficulty,
        "completedAt": interview["completed_at"],
        "overallScore": interview["score"],
        "technicalScore": interview["technical_score"],
        "communicationScore": interview["communication_score"],
        "relevanceScore": interview["relevance_score"],
        "completenessScore": interview["completeness_score"],
        "strengths": safe_json_loads(interview["strengths_json"], []),
        "weaknesses": safe_json_loads(interview["weaknesses_json"], []),
        "suggestions": safe_json_loads(interview["suggestions_json"], []),
        "answers": answer_payloads,
        "adaptive": {
            "startingDifficulty": starting_difficulty,
            "endingDifficulty": ending_difficulty,
            "progression": adaptive_history,
            "classificationCounts": {
                classification: classification_counts.get(classification, 0)
                for classification in ANSWER_CLASSIFICATIONS
            },
            "strongAnswers": classification_counts.get("strong", 0),
            "partialAnswers": classification_counts.get("partial", 0),
            "wrongAnswers": classification_counts.get("wrong", 0),
            "insufficientAnswers": classification_counts.get("insufficient", 0),
            "timeouts": classification_counts.get("timeout", 0),
            "generatedFollowUps": generated_follow_ups,
            "aiGeneratedFollowUps": ai_generated_follow_ups,
            "fallbackFollowUps": max(0, generated_follow_ups - ai_generated_follow_ups),
        },
        "integrity": {
            "status": interview["integrity_status"],
            "tabSwitches": interview["tab_switch_count"],
            "totalTimeAway": interview["total_time_away"],
            "longestTimeAway": interview["longest_time_away"],
            "attentionWarnings": attention_warnings,
            "faceAbsenceEvents": face_absence_events,
            "windowBlurs": interview["window_blur_count"],
            "multiplePeopleEvents": interview["multiple_face_count"],
            "cameraInterruptions": interview["camera_interruption_count"],
            "microphoneInterruptions": interview["microphone_interruption_count"],
            "events": event_payloads,
        },
        "voice": {
            "totalSpeakingTime": spoken_duration,
            "averageResponseTime": average_response,
            "wordsPerMinute": speaking_wpm,
            "fillerWords": total_fillers,
            "longPauses": total_pauses,
            "repeatedPhrases": [item for item, _ in repeated_phrases.most_common(5)],
            "automaticTurnCompletions": automatic_turn_completions,
            "interviewerInterruptions": interviewer_interruptions,
            "averageTranscriptionConfidence": round(confidence_total / confidence_samples, 1) if confidence_samples else 0,
        },
        "recommendedTopics": unique_list(
            [answer["topic"] for answer in answer_payloads if answer["score"] < 65]
        )[:6],
    }


def interview_options():
    return {
        "companies": COMPANIES,
        "rounds": [{"value": key, "label": value} for key, value in ROUNDS.items()],
        "domains": [{"value": key, "label": value} for key, value in DOMAINS.items() if key not in {"ai_ml", "core_engineering"}],
        "difficulties": [
            {"value": "easy", "label": "Easy"},
            {"value": "medium", "label": "Medium"},
            {"value": "hard", "label": "Hard"},
        ],
        "durations": [15, 30, 45, 60],
        "questionBankSize": 1000,
    }
