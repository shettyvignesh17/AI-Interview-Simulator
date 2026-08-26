import random
from collections import Counter
from datetime import datetime, timezone

from interview_simulator.services.learning_catalog import COMPANIES, generate_learning_catalog
from interview_simulator.utils.common import iso_now, safe_json_dumps, safe_json_loads


PAGE_SIZE = 20
DAILY_GOALS = {5, 10, 20, 30}
CONFIDENCE_LEVELS = {"", "low", "medium", "high"}
FLASHCARD_LEVELS = {"", "easy", "medium", "difficult"}


QUESTION_COLUMNS = (
    "id", "question_type", "category", "subcategory", "company", "difficulty", "question",
    "answer", "detailed_explanation", "example", "tags_json", "topic", "estimated_study_time",
    "frequency", "related_questions_json", "approach", "code", "time_complexity",
    "space_complexity", "common_mistakes", "interview_tip", "created_at",
)


def ensure_learning_catalog(database, force=False):
    current_count = database.execute("SELECT COUNT(*) FROM learning_questions").fetchone()[0]
    if current_count == 1000 and not force:
        return current_count

    aptitude_rows = database.execute("SELECT * FROM aptitude_questions ORDER BY id").fetchall()
    records = generate_learning_catalog(aptitude_rows)
    if force or current_count:
        database.execute("DELETE FROM learning_questions")

    placeholders = ", ".join("?" for _ in QUESTION_COLUMNS)
    updates = ", ".join(f"{column}=excluded.{column}" for column in QUESTION_COLUMNS if column != "id")
    database.executemany(
        f"""
        INSERT INTO learning_questions ({', '.join(QUESTION_COLUMNS)})
        VALUES ({placeholders})
        ON CONFLICT(id) DO UPDATE SET {updates}
        """,
        [tuple(record.get(column, iso_now() if column == "created_at" else "") for column in QUESTION_COLUMNS) for record in records],
    )
    database.commit()
    return len(records)


def _question_payload(row, include_answer=True):
    payload = {
        "questionId": row["id"],
        "type": row["question_type"],
        "category": row["category"],
        "subcategory": row["subcategory"],
        "company": row["company"],
        "companyLabel": f"{row['company']}-style question",
        "difficulty": row["difficulty"],
        "question": row["question"],
        "example": row["example"],
        "tags": safe_json_loads(row["tags_json"], []),
        "topic": row["topic"],
        "estimatedStudyTime": row["estimated_study_time"],
        "frequency": row["frequency"],
        "bookmarked": bool(row["bookmarked"]) if "bookmarked" in row.keys() else False,
        "studied": bool(row["studied"]) if "studied" in row.keys() else False,
        "revision": bool(row["revision"]) if "revision" in row.keys() else False,
        "viewedCount": row["viewed_count"] if "viewed_count" in row.keys() else 0,
        "confidence": row["confidence"] if "confidence" in row.keys() else "",
        "flashcardDifficulty": row["flashcard_difficulty"] if "flashcard_difficulty" in row.keys() else "",
        "notes": row["notes"] if "notes" in row.keys() else "",
        "lastViewed": row["last_viewed"] if "last_viewed" in row.keys() else None,
    }
    if include_answer:
        payload.update(
            {
                "answer": row["answer"],
                "detailedExplanation": row["detailed_explanation"],
                "approach": row["approach"],
                "code": row["code"],
                "timeComplexity": row["time_complexity"],
                "spaceComplexity": row["space_complexity"],
                "commonMistakes": row["common_mistakes"],
                "interviewTip": row["interview_tip"],
            }
        )
    return payload


def _joined_select():
    return """
        SELECT q.*, COALESCE(p.bookmarked, 0) AS bookmarked,
               COALESCE(p.studied, 0) AS studied,
               COALESCE(p.revision, 0) AS revision,
               COALESCE(p.viewed_count, 0) AS viewed_count,
               COALESCE(p.confidence, '') AS confidence,
               COALESCE(p.flashcard_difficulty, '') AS flashcard_difficulty,
               COALESCE(p.notes, '') AS notes,
               p.last_viewed AS last_viewed
        FROM learning_questions q
        LEFT JOIN learning_progress p ON p.question_id = q.id AND p.user_id = ?
    """


def _filters(params, alias="q"):
    clauses = []
    values = []
    search = (params.get("search") or "").strip()
    for term in search.split()[:8]:
        pattern = f"%{term}%"
        clauses.append(
            f"({alias}.question LIKE ? OR {alias}.topic LIKE ? OR {alias}.company LIKE ? "
            f"OR {alias}.category LIKE ? OR {alias}.subcategory LIKE ? OR {alias}.tags_json LIKE ?)"
        )
        values.extend([pattern] * 6)

    field_map = {
        "type": "question_type", "difficulty": "difficulty", "company": "company",
        "topic": "topic", "frequency": "frequency",
    }
    for parameter, column in field_map.items():
        value = (params.get(parameter) or "").strip()
        if value and value.lower() != "all":
            clauses.append(f"{alias}.{column} = ?")
            values.append(value)

    status = (params.get("status") or "").strip().lower()
    if status == "studied": clauses.append("COALESCE(p.studied, 0) = 1")
    elif status == "not-studied": clauses.append("COALESCE(p.studied, 0) = 0")
    elif status == "bookmarked": clauses.append("COALESCE(p.bookmarked, 0) = 1")
    elif status == "revision": clauses.append("COALESCE(p.revision, 0) = 1")

    return clauses, values


def list_questions(database, user_id, params):
    try:
        page = max(1, int(params.get("page", 1)))
    except (TypeError, ValueError):
        page = 1
    clauses, values = _filters(params)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sort_map = {
        "difficulty": "CASE q.difficulty WHEN 'Easy' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END, q.topic",
        "important": "CASE q.frequency WHEN 'Very Common' THEN 1 WHEN 'Common' THEN 2 WHEN 'Moderate' THEN 3 ELSE 4 END, q.topic",
        "common": "CASE q.frequency WHEN 'Very Common' THEN 1 WHEN 'Common' THEN 2 WHEN 'Moderate' THEN 3 ELSE 4 END, q.question",
        "company": "q.company, q.topic",
        "recently-added": "q.created_at DESC, q.id DESC",
        "not-studied": "COALESCE(p.studied, 0), q.topic",
        "recently-viewed": "p.last_viewed DESC, q.topic",
        "recommended": "COALESCE(p.revision, 0) DESC, CASE COALESCE(p.confidence, '') WHEN 'low' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END, q.frequency",
    }
    ordering = sort_map.get((params.get("sort") or "recommended").lower(), sort_map["recommended"])
    count_row = database.execute(
        f"SELECT COUNT(*) AS total FROM learning_questions q LEFT JOIN learning_progress p ON p.question_id=q.id AND p.user_id=? {where}",
        (user_id, *values),
    ).fetchone()
    total = count_row["total"]
    total_pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    page = min(page, total_pages)
    rows = database.execute(
        f"{_joined_select()} {where} ORDER BY {ordering} LIMIT ? OFFSET ?",
        (user_id, *values, PAGE_SIZE, (page - 1) * PAGE_SIZE),
    ).fetchall()
    return {
        "questions": [_question_payload(row) for row in rows],
        "pagination": {
            "page": page, "pageSize": PAGE_SIZE, "total": total, "totalPages": total_pages,
            "from": (page - 1) * PAGE_SIZE + 1 if total else 0,
            "to": min(page * PAGE_SIZE, total),
        },
    }


def get_question(database, user_id, question_id):
    row = database.execute(
        f"{_joined_select()} WHERE q.id = ?", (user_id, question_id)
    ).fetchone()
    if not row:
        return None
    payload = _question_payload(row)
    related = database.execute(
        """
        SELECT id, question, topic, difficulty, company FROM learning_questions
        WHERE id != ? AND (topic = ? OR category = ?) ORDER BY RANDOM() LIMIT 4
        """,
        (question_id, row["topic"], row["category"]),
    ).fetchall()
    payload["relatedQuestions"] = [
        {"questionId": item["id"], "question": item["question"], "topic": item["topic"],
         "difficulty": item["difficulty"], "company": item["company"]}
        for item in related
    ]
    return payload


def update_progress(database, user_id, question_id, payload):
    if not database.execute("SELECT id FROM learning_questions WHERE id = ?", (question_id,)).fetchone():
        return None
    existing = database.execute(
        "SELECT * FROM learning_progress WHERE user_id = ? AND question_id = ?", (user_id, question_id)
    ).fetchone()
    values = {
        "bookmarked": existing["bookmarked"] if existing else 0,
        "studied": existing["studied"] if existing else 0,
        "revision": existing["revision"] if existing else 0,
        "viewed_count": existing["viewed_count"] if existing else 0,
        "confidence": existing["confidence"] if existing else "",
        "flashcard_difficulty": existing["flashcard_difficulty"] if existing else "",
        "notes": existing["notes"] if existing else "",
        "last_viewed": existing["last_viewed"] if existing else None,
        "learned_at": existing["learned_at"] if existing else None,
    }
    now = iso_now()
    for key in ("bookmarked", "studied", "revision"):
        if key in payload:
            values[key] = int(bool(payload[key]))
    if "confidence" in payload:
        confidence = str(payload["confidence"] or "").lower()
        if confidence in CONFIDENCE_LEVELS: values["confidence"] = confidence
    if "flashcardDifficulty" in payload:
        level = str(payload["flashcardDifficulty"] or "").lower()
        if level in FLASHCARD_LEVELS: values["flashcard_difficulty"] = level
    if "notes" in payload:
        values["notes"] = str(payload["notes"] or "").strip()[:5000]
    if payload.get("viewed"):
        values["viewed_count"] += 1
        values["last_viewed"] = now
    if "studied" in payload:
        values["learned_at"] = now if values["studied"] else None

    database.execute(
        """
        INSERT INTO learning_progress (
            user_id, question_id, bookmarked, studied, revision, viewed_count, confidence,
            flashcard_difficulty, notes, last_viewed, learned_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id, question_id) DO UPDATE SET
            bookmarked=excluded.bookmarked, studied=excluded.studied, revision=excluded.revision,
            viewed_count=excluded.viewed_count, confidence=excluded.confidence,
            flashcard_difficulty=excluded.flashcard_difficulty, notes=excluded.notes,
            last_viewed=excluded.last_viewed, learned_at=excluded.learned_at, updated_at=excluded.updated_at
        """,
        (user_id, question_id, values["bookmarked"], values["studied"], values["revision"],
         values["viewed_count"], values["confidence"], values["flashcard_difficulty"], values["notes"],
         values["last_viewed"], values["learned_at"], now),
    )
    if payload.get("viewed"):
        ensure_preferences(database, user_id)
        database.execute(
            "UPDATE learning_preferences SET last_question_id=?, last_section=?, updated_at=? WHERE user_id=?",
            (question_id, payload.get("section", "overview")[:30], now, user_id),
        )
    database.commit()
    return get_question(database, user_id, question_id)


def ensure_preferences(database, user_id):
    database.execute(
        """
        INSERT INTO learning_preferences (user_id, daily_goal, target_companies_json, updated_at)
        VALUES (?, 10, '[]', ?) ON CONFLICT(user_id) DO NOTHING
        """,
        (user_id, iso_now()),
    )
    database.commit()
    return database.execute("SELECT * FROM learning_preferences WHERE user_id = ?", (user_id,)).fetchone()


def update_preferences(database, user_id, payload):
    row = ensure_preferences(database, user_id)
    daily_goal = payload.get("dailyGoal", row["daily_goal"])
    try: daily_goal = int(daily_goal)
    except (TypeError, ValueError): daily_goal = row["daily_goal"]
    if daily_goal not in DAILY_GOALS: daily_goal = row["daily_goal"]
    targets = payload.get("targetCompanies", safe_json_loads(row["target_companies_json"], []))
    if not isinstance(targets, list): targets = []
    targets = [company for company in COMPANIES if company in targets]
    database.execute(
        "UPDATE learning_preferences SET daily_goal=?, target_companies_json=?, updated_at=? WHERE user_id=?",
        (daily_goal, safe_json_dumps(targets), iso_now(), user_id),
    )
    database.commit()
    return {"dailyGoal": daily_goal, "targetCompanies": targets, "lastSection": row["last_section"], "lastQuestionId": row["last_question_id"]}


def _section_summary(database, user_id):
    rows = database.execute(
        """
        SELECT q.question_type, COUNT(*) AS total, COALESCE(SUM(p.studied), 0) AS studied,
               COALESCE(SUM(p.bookmarked), 0) AS bookmarked
        FROM learning_questions q
        LEFT JOIN learning_progress p ON p.question_id=q.id AND p.user_id=?
        GROUP BY q.question_type
        """,
        (user_id,),
    ).fetchall()
    return {
        row["question_type"]: {
            "total": row["total"], "studied": row["studied"], "bookmarked": row["bookmarked"],
            "progress": round(row["studied"] / row["total"] * 100, 1) if row["total"] else 0,
        }
        for row in rows
    }


def _topic_signals(database, user_id):
    rows = database.execute(
        """
        SELECT q.topic, SUM(CASE WHEN p.studied=1 THEN 1 ELSE 0 END) AS studied,
               SUM(CASE WHEN p.revision=1 OR p.confidence='low' OR p.flashcard_difficulty='difficult' THEN 1 ELSE 0 END) AS weak,
               SUM(CASE WHEN p.confidence='high' OR p.flashcard_difficulty='easy' THEN 1 ELSE 0 END) AS strong
        FROM learning_questions q JOIN learning_progress p ON p.question_id=q.id
        WHERE p.user_id=? GROUP BY q.topic
        """,
        (user_id,),
    ).fetchall()
    most = sorted(rows, key=lambda row: (-row["studied"], row["topic"]))[:5]
    weak = sorted((row for row in rows if row["weak"]), key=lambda row: (-row["weak"], row["topic"]))[:5]
    strong = sorted((row for row in rows if row["strong"]), key=lambda row: (-row["strong"], row["topic"]))[:5]
    return {
        "mostStudiedTopics": [row["topic"] for row in most],
        "weakTopics": [row["topic"] for row in weak],
        "strongTopics": [row["topic"] for row in strong],
    }


def learning_overview(database, user_id):
    preference_row = ensure_preferences(database, user_id)
    preferences = {
        "dailyGoal": preference_row["daily_goal"],
        "targetCompanies": safe_json_loads(preference_row["target_companies_json"], []),
        "lastSection": preference_row["last_section"],
        "lastQuestionId": preference_row["last_question_id"],
    }
    sections = _section_summary(database, user_id)
    progress = database.execute(
        """
        SELECT COUNT(*) AS tracked,
               COALESCE(SUM(CASE WHEN viewed_count > 0 THEN 1 ELSE 0 END), 0) AS viewed,
               COALESCE(SUM(studied), 0) AS learned,
               COALESCE(SUM(bookmarked), 0) AS bookmarked,
               COALESCE(SUM(revision), 0) AS revision,
               COALESCE(SUM(CASE WHEN studied=1 AND date(learned_at)=date('now') THEN 1 ELSE 0 END), 0) AS today
        FROM learning_progress WHERE user_id=?
        """,
        (user_id,),
    ).fetchone()
    ordinal = datetime.now(timezone.utc).date().toordinal()
    daily_row = database.execute(
        f"{_joined_select()} ORDER BY q.id LIMIT 1 OFFSET ?", (user_id, ordinal % 1000)
    ).fetchone()
    recent_rows = database.execute(
        f"{_joined_select()} WHERE p.last_viewed IS NOT NULL ORDER BY p.last_viewed DESC LIMIT 6", (user_id,)
    ).fetchall()
    target_companies = preferences["targetCompanies"]
    candidates = database.execute(_joined_select(), (user_id,)).fetchall()
    scored = sorted(
        candidates,
        key=lambda row: (
            -(4 if row["company"] in target_companies else 0),
            -(3 if row["revision"] else 0),
            -(2 if row["confidence"] == "low" else 0),
            row["studied"],
            row["id"],
        ),
    )[:6]
    continue_question = get_question(database, user_id, preferences["lastQuestionId"]) if preferences["lastQuestionId"] else None
    signals = _topic_signals(database, user_id)
    company_rows = database.execute(
        """
        SELECT q.company, COUNT(*) AS total, COALESCE(SUM(p.studied), 0) AS studied
        FROM learning_questions q
        LEFT JOIN learning_progress p ON p.question_id=q.id AND p.user_id=?
        GROUP BY q.company ORDER BY q.company
        """,
        (user_id,),
    ).fetchall()
    return {
        "sections": sections,
        "totals": {
            "questions": sum(section["total"] for section in sections.values()),
            "viewed": progress["viewed"], "learned": progress["learned"],
            "bookmarked": progress["bookmarked"], "revision": progress["revision"],
        },
        "dailyGoal": {"target": preferences["dailyGoal"], "completed": progress["today"]},
        "preferences": preferences,
        "questionOfDay": _question_payload(daily_row) if daily_row else None,
        "recommended": [_question_payload(row) for row in scored],
        "recentlyViewed": [_question_payload(row) for row in recent_rows],
        "continueQuestion": continue_question,
        "companyProgress": {
            row["company"]: {
                "total": row["total"], "studied": row["studied"],
                "progress": round(row["studied"] / row["total"] * 100, 1) if row["total"] else 0,
            }
            for row in company_rows
        },
        **signals,
    }


def metadata(database):
    topic_rows = database.execute("SELECT DISTINCT question_type, topic FROM learning_questions ORDER BY question_type, topic").fetchall()
    topics = sorted({row["topic"] for row in topic_rows})
    topics_by_type = {
        question_type: [row["topic"] for row in topic_rows if row["question_type"] == question_type]
        for question_type in ("aptitude", "coding", "interview")
    }
    categories = [row[0] for row in database.execute("SELECT DISTINCT category FROM learning_questions ORDER BY category")]
    return {"companies": COMPANIES, "topics": topics, "topicsByType": topics_by_type, "categories": categories, "dailyGoals": sorted(DAILY_GOALS)}


def random_question(database, user_id, params):
    clauses, values = _filters(params)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    row = database.execute(
        f"{_joined_select()} {where} ORDER BY RANDOM() LIMIT 1", (user_id, *values)
    ).fetchone()
    return _question_payload(row) if row else None
