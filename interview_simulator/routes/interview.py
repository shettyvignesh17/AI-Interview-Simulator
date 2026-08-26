from collections import defaultdict

from flask import Blueprint, current_app, jsonify, request

from interview_simulator.db import get_db
from interview_simulator.services.engine import summarize_history
from interview_simulator.services.interview_delivery import (
    COMPANIES,
    DOMAINS,
    LEGACY_DIFFICULTIES,
    ROUNDS,
    build_report,
    evaluate_delivery_answer,
    interview_options,
    normalize_difficulty,
    start_delivery_session,
)
from interview_simulator.services.resume_parser import parse_resume
from interview_simulator.utils.auth import get_current_user, login_required
from interview_simulator.utils.common import iso_now, safe_json_dumps, safe_json_loads


bp = Blueprint("interview", __name__, url_prefix="/api")
STANDARD_QUESTION_LIMIT = 5
QUESTION_TIME_LIMIT_SECONDS = 120


@bp.get("/interview/options")
def interview_setup_options():
    options = interview_options()
    ai_enabled = bool(current_app.config.get("OPENAI_API_KEY")) and current_app.config.get("AI_PROVIDER") in {"openai", "hybrid"}
    options["adaptiveFollowUps"] = {
        "enabled": True,
        "provider": "OpenAI + local fallback" if ai_enabled else "Local contextual engine",
        "aiEnabled": ai_enabled,
    }
    options["advancedVoice"] = {
        "enabled": True,
        "turnDetection": "Browser speech-end and silence detection",
    }
    return jsonify(options)


def _resume_payload(row):
    return {
        "id": row["id"],
        "filename": row["filename"],
        "skills": safe_json_loads(row["skills_json"], []),
        "projects": safe_json_loads(row["projects_json"], []),
        "experience": safe_json_loads(row["experience_json"], []),
        "summary": row["summary"],
        "createdAt": row["created_at"],
    }


def _session_payload(row):
    asked_questions = safe_json_loads(row["asked_questions_json"], [])
    current_question_payload = asked_questions[-1] if asked_questions and isinstance(asked_questions[-1], dict) else {}

    public_questions = [
        {
            "id": item.get("id"),
            "topic": item.get("topic"),
            "difficulty": item.get("difficulty"),
            "companyLabel": item.get("company_label"),
            "isFollowUp": bool(item.get("is_follow_up")),
            "generationSource": item.get("generation_source", "question-bank"),
        }
        for item in asked_questions
        if isinstance(item, dict)
    ]

    return {
        "id": row["id"],
        "company": row["company"],
        "roundType": row["round_type"],
        "domain": row["domain"],
        "difficulty": row["starting_difficulty"],
        "currentLevel": row["starting_difficulty"],
        "startingDifficulty": row["starting_difficulty"],
        "currentQuestion": row["current_question"],
        "currentQuestionId": current_question_payload.get("id"),
        "questionIndex": row["question_index"],
        "questionNumber": row["question_index"],
        "status": row["status"],
        "score": row["score"],
        "technicalScore": row["technical_score"],
        "communicationScore": row["communication_score"],
        "relevanceScore": row["relevance_score"],
        "completenessScore": row["completeness_score"],
        "confidenceScore": row["confidence_score"],
        "clarityScore": row["clarity_score"],
        "depthScore": row["depth_score"],
        "strengths": safe_json_loads(row["strengths_json"], []),
        "weaknesses": safe_json_loads(row["weaknesses_json"], []),
        "suggestions": safe_json_loads(row["suggestions_json"], []),
        "chat": safe_json_loads(row["transcript_json"], []),
        "askedQuestions": public_questions,
        "questionLimit": row["question_limit"],
        "durationMinutes": row["duration_minutes"],
        "integrityStatus": row["integrity_status"],
        "tabSwitchCount": row["tab_switch_count"],
        "totalTimeAway": row["total_time_away"],
        "longestTimeAway": row["longest_time_away"],
        "windowBlurCount": row["window_blur_count"],
        "attentionWarningCount": row["attention_warning_count"],
        "multipleFaceCount": row["multiple_face_count"],
        "cameraInterruptionCount": row["camera_interruption_count"],
        "microphoneInterruptionCount": row["microphone_interruption_count"],
        "currentTopic": current_question_payload.get("topic"),
        "companyLabel": current_question_payload.get("company_label"),
        "isFollowUp": bool(current_question_payload.get("is_follow_up")),
        "followUpSource": current_question_payload.get("generation_source", "question-bank"),
        "followUpReason": current_question_payload.get("follow_up_reason", ""),
        "followUpModel": current_question_payload.get("generation_model"),
        "poolRecycled": bool(current_question_payload.get("pool_recycled", False)),
        "createdAt": row["created_at"],
        "completedAt": row["completed_at"],
    }


def _performance_summary(database, user_id):
    rows = database.execute(
        """
        SELECT domain, score, technical_score, communication_score, created_at
        FROM interview_sessions
        WHERE user_id=? AND status='completed'
        ORDER BY created_at
        """,
        (user_id,),
    ).fetchall()
    if not rows:
        return {
            "interviewsCompleted": 0, "averageScore": 0, "technicalScore": 0,
            "communicationScore": 0, "strongestDomain": "Not available",
            "weakestDomain": "Not available", "recentTrend": [],
        }
    domains = defaultdict(list)
    for row in rows:
        domains[row["domain"]].append(row["score"])
    domain_averages = {
        domain: round(sum(scores) / len(scores), 1) for domain, scores in domains.items()
    }
    return {
        "interviewsCompleted": len(rows),
        "averageScore": round(sum(row["score"] for row in rows) / len(rows), 1),
        "technicalScore": round(sum(row["technical_score"] for row in rows) / len(rows), 1),
        "communicationScore": round(sum(row["communication_score"] for row in rows) / len(rows), 1),
        "strongestDomain": DOMAINS.get(max(domain_averages, key=domain_averages.get), max(domain_averages, key=domain_averages.get)),
        "weakestDomain": DOMAINS.get(min(domain_averages, key=domain_averages.get), min(domain_averages, key=domain_averages.get)),
        "recentTrend": [round(row["score"], 1) for row in rows[-6:]],
    }


@bp.post("/resume")
@login_required
def upload_resume():
    user = get_current_user()
    uploaded_file = request.files.get("resume")

    if not uploaded_file or not uploaded_file.filename:
        return jsonify({"error": "Choose a resume file to upload."}), 400

    try:
        parsed = parse_resume(uploaded_file)
    except (ValueError, RuntimeError) as exc:
        return jsonify({"error": str(exc)}), 400

    database = get_db()
    database.execute(
        """
        INSERT INTO resumes (
            user_id, filename, content_type, raw_text, skills_json, projects_json,
            experience_json, summary, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user["id"],
            parsed["filename"],
            parsed["content_type"],
            parsed["text"],
            safe_json_dumps(parsed["profile"]["skills"]),
            safe_json_dumps(parsed["profile"]["projects"]),
            safe_json_dumps(parsed["profile"]["experience"]),
            parsed["profile"]["summary"],
            iso_now(),
        ),
    )
    database.commit()

    resume = database.execute(
        "SELECT * FROM resumes WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user["id"],)
    ).fetchone()

    return jsonify({"message": "Resume uploaded.", "resume": _resume_payload(resume)}), 201


@bp.post("/interview/start")
@login_required
def start_interview():
    payload = request.get_json(silent=True) or {}
    round_type = (payload.get("roundType") or "").strip().lower()
    domain = (payload.get("domain") or "").strip().lower()
    difficulty = (payload.get("difficulty") or "easy").strip().lower()
    company = (payload.get("company") or "General").strip()
    persistent_question_ids = payload.get("persistentQuestionIds") or []
    if not isinstance(persistent_question_ids, list):
        persistent_question_ids = []

    if round_type not in ROUNDS:
        return jsonify({"error": "Select a valid interview round."}), 400
    if domain not in DOMAINS:
        return jsonify({"error": "Select a valid domain."}), 400
    if difficulty not in {*LEGACY_DIFFICULTIES, "easy", "medium", "hard"}:
        return jsonify({"error": "Select Easy, Medium, or Hard difficulty."}), 400
    if company != "General" and company not in COMPANIES:
        return jsonify({"error": "Select a valid target company."}), 400
    try:
        duration_minutes = int(payload.get("durationMinutes") or 30)
    except (TypeError, ValueError):
        duration_minutes = 30
    if duration_minutes not in {15, 30, 45, 60}:
        return jsonify({"error": "Select a 15, 30, 45, or 60 minute interview."}), 400

    database = get_db()
    user = get_current_user()
    database.execute(
        """
        UPDATE interview_sessions
        SET status='abandoned', completed_at=?, interviewer_notes=?
        WHERE user_id=? AND status='active'
        """,
        (iso_now(), "Interview replaced by a new session.", user["id"]),
    )
    question_limit = STANDARD_QUESTION_LIMIT
    session_state = start_delivery_session(
        database=database,
        company=company,
        round_type=round_type,
        domain=domain,
        difficulty=difficulty,
        max_questions=question_limit,
        duration_minutes=duration_minutes,
        persistent_asked_ids=persistent_question_ids,
    )

    if session_state["asked_questions"]:
        session_state["asked_questions"][-1]["pool_recycled"] = session_state["pool_recycled"]

    database.execute(
        """
        INSERT INTO interview_sessions (
            id, user_id, company, round_type, domain, difficulty, resume_id, current_question,
            asked_questions_json, transcript_json, score, confidence_score,
            clarity_score, depth_score, strengths_json, weaknesses_json,
            suggestions_json, interviewer_notes, status, question_index, created_at,
            duration_minutes, question_limit, technical_score, communication_score,
            relevance_score, completeness_score, started_at
            , starting_difficulty, strong_streak, weak_streak, adaptive_history_json,
            timeout_count
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_state["id"],
            user["id"],
            company,
            round_type,
            domain,
            session_state["current_level"],
            None,
            session_state["current_question"],
            safe_json_dumps(session_state["asked_questions"]),
            safe_json_dumps(session_state["transcript"]),
            session_state["score"],
            session_state["confidence_score"],
            session_state["clarity_score"],
            session_state["depth_score"],
            safe_json_dumps(session_state["strengths"]),
            safe_json_dumps(session_state["weaknesses"]),
            safe_json_dumps(session_state["suggestions"]),
            session_state["interviewer_notes"],
            session_state["status"],
            session_state["question_index"],
            session_state["created_at"],
            duration_minutes,
            question_limit,
            session_state["technical_score"],
            session_state["communication_score"],
            session_state["relevance_score"],
            session_state["completeness_score"],
            session_state["started_at"],
            session_state["starting_difficulty"],
            session_state["strong_streak"],
            session_state["weak_streak"],
            safe_json_dumps(session_state["adaptive_history"]),
            session_state["timeout_count"],
        ),
    )
    database.commit()

    row = database.execute(
        "SELECT * FROM interview_sessions WHERE id = ?", (session_state["id"],)
    ).fetchone()

    return jsonify(
        {
            "session": _session_payload(row),
            "meta": {
                "companyLabel": f"{company}-style interview" if company != "General" else "General interview",
                "roundLabel": ROUNDS[round_type],
                "domainLabel": DOMAINS[domain],
                "timerSeconds": QUESTION_TIME_LIMIT_SECONDS,
                "maxQuestions": question_limit,
                "durationMinutes": duration_minutes,
                "startLevel": session_state["current_level"],
                "poolRecycled": session_state["pool_recycled"],
            },
        }
    )


@bp.post("/interview/answer")
@login_required
def answer_question():
    payload = request.get_json(silent=True) or {}
    session_id = payload.get("sessionId")
    answer = (payload.get("answer") or "").strip()
    answer_type = (payload.get("answerType") or "typed").strip().lower()
    timed_out = bool(payload.get("timedOut"))
    voice_metrics = payload.get("voiceMetrics") or {}
    if not isinstance(voice_metrics, dict):
        voice_metrics = {}
    try:
        duration_seconds = max(0, int(payload.get("durationSeconds") or 0))
    except (TypeError, ValueError):
        duration_seconds = 0
    persistent_question_ids = payload.get("persistentQuestionIds") or []
    if not isinstance(persistent_question_ids, list):
        persistent_question_ids = []

    if answer_type not in {"typed", "spoken", "skipped"}:
        answer_type = "typed"
    if answer_type == "skipped" and not answer:
        answer = "Question skipped by candidate."
    if timed_out and not answer:
        answer = "Response timed out before the candidate submitted an answer."
    if not session_id or not answer:
        return jsonify({"error": "Session and answer are required."}), 400

    database = get_db()
    user = get_current_user()
    row = database.execute(
        "SELECT * FROM interview_sessions WHERE id = ? AND user_id = ?",
        (session_id, user["id"]),
    ).fetchone()

    if not row:
        return jsonify({"error": "Interview session not found."}), 404
    if row["status"] != "active":
        return jsonify({"error": "This interview session is already complete."}), 400

    state = {
        "current_question": row["current_question"],
        "asked_questions": safe_json_loads(row["asked_questions_json"], []),
        "transcript": safe_json_loads(row["transcript_json"], []),
        "score": row["score"],
        "technical_score": row["technical_score"],
        "communication_score": row["communication_score"],
        "relevance_score": row["relevance_score"],
        "completeness_score": row["completeness_score"],
        "confidence_score": row["confidence_score"],
        "clarity_score": row["clarity_score"],
        "depth_score": row["depth_score"],
        "strengths": safe_json_loads(row["strengths_json"], []),
        "weaknesses": safe_json_loads(row["weaknesses_json"], []),
        "suggestions": safe_json_loads(row["suggestions_json"], []),
        "question_index": row["question_index"],
        "status": row["status"],
        "max_questions": row["question_limit"],
        "current_level": row["difficulty"],
        "strong_streak": row["strong_streak"],
        "weak_streak": row["weak_streak"],
        "adaptive_history": safe_json_loads(row["adaptive_history_json"], []),
        "timeout_count": row["timeout_count"],
    }

    result = evaluate_delivery_answer(
        database=database,
        session_state=state,
        answer=answer,
        round_type=row["round_type"],
        domain=row["domain"],
        company=row["company"],
        persistent_asked_ids=persistent_question_ids,
        answer_type=answer_type,
        duration_seconds=duration_seconds,
        voice_metrics=voice_metrics,
        timed_out=timed_out,
        ai_settings={
            "provider": current_app.config.get("AI_PROVIDER", "hybrid"),
            "api_key": current_app.config.get("OPENAI_API_KEY", ""),
            "model": current_app.config.get("OPENAI_FOLLOWUP_MODEL", "gpt-5-mini"),
            "timeout_seconds": current_app.config.get("OPENAI_TIMEOUT_SECONDS", 8),
        },
    )
    updated_state = result["state"]

    if updated_state["asked_questions"]:
        updated_state["asked_questions"][-1]["pool_recycled"] = updated_state["pool_recycled"]

    answer_record = result["answer_record"]
    database.execute(
        """
        INSERT INTO candidate_answers (
            session_id, question_id, question_number, question_text, topic, difficulty,
            company, round_type, domain,
            answer_type, answer_text, duration_seconds, voice_metrics_json, evaluation_json,
            answer_classification, timed_out, adaptive_change,
            ideal_answer, answer_explanation, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            session_id, answer_record["question_id"], row["question_index"],
            answer_record["question_text"], answer_record["topic"], answer_record["difficulty"],
            answer_record["company"], answer_record["round_type"], answer_record["domain"],
            answer_record["answer_type"], answer_record["answer_text"],
            answer_record["duration_seconds"], answer_record["voice_metrics_json"],
            answer_record["evaluation_json"], answer_record["answer_classification"],
            answer_record["timed_out"], answer_record["adaptive_change"], answer_record["ideal_answer"],
            answer_record["answer_explanation"], iso_now(),
        ),
    )

    database.execute(
        """
        UPDATE interview_sessions
        SET current_question = ?, difficulty = ?, asked_questions_json = ?, transcript_json = ?,
            score = ?, confidence_score = ?, clarity_score = ?, depth_score = ?,
            technical_score = ?, communication_score = ?, relevance_score = ?, completeness_score = ?,
            strengths_json = ?, weaknesses_json = ?, suggestions_json = ?,
            interviewer_notes = ?, status = ?, question_index = ?, completed_at = ?
            , strong_streak = ?, weak_streak = ?, adaptive_history_json = ?, timeout_count = ?
        WHERE id = ?
        """,
        (
            updated_state["current_question"],
            updated_state["current_level"],
            safe_json_dumps(updated_state["asked_questions"]),
            safe_json_dumps(updated_state["transcript"]),
            updated_state["score"],
            updated_state["confidence_score"],
            updated_state["clarity_score"],
            updated_state["depth_score"],
            updated_state["technical_score"],
            updated_state["communication_score"],
            updated_state["relevance_score"],
            updated_state["completeness_score"],
            safe_json_dumps(updated_state["strengths"]),
            safe_json_dumps(updated_state["weaknesses"]),
            safe_json_dumps(updated_state["suggestions"]),
            updated_state["interviewer_notes"],
            updated_state["status"],
            updated_state["question_index"],
            updated_state["completed_at"],
            updated_state["strong_streak"],
            updated_state["weak_streak"],
            safe_json_dumps(updated_state["adaptive_history"]),
            updated_state["timeout_count"],
            session_id,
        ),
    )
    database.commit()

    refreshed = database.execute(
        "SELECT * FROM interview_sessions WHERE id = ?", (session_id,)
    ).fetchone()

    response = {"session": _session_payload(refreshed), "evaluation": result["evaluation"]}
    if refreshed["status"] == "completed":
        response["report"] = build_report(database, session_id, user["id"])
    return jsonify(response)


@bp.post("/interview/abandon")
@login_required
def abandon_interview():
    payload = request.get_json(silent=True) or {}
    session_id = str(payload.get("sessionId") or "").strip()
    if not session_id:
        return jsonify({"error": "A valid interview session is required."}), 400

    database = get_db()
    user = get_current_user()
    row = database.execute(
        "SELECT status FROM interview_sessions WHERE id=? AND user_id=?",
        (session_id, user["id"]),
    ).fetchone()
    if not row:
        return jsonify({"error": "Interview session not found."}), 404
    if row["status"] == "completed":
        return jsonify({"error": "A completed interview cannot be abandoned."}), 409
    if row["status"] == "abandoned":
        return jsonify({"abandoned": True})

    database.execute(
        """
        UPDATE interview_sessions
        SET status='abandoned', completed_at=?, interviewer_notes=?
        WHERE id=? AND user_id=? AND status='active'
        """,
        (iso_now(), "Interview abandoned by the candidate.", session_id, user["id"]),
    )
    database.commit()
    return jsonify({"abandoned": True})


@bp.get("/dashboard")
@login_required
def dashboard():
    database = get_db()
    user = get_current_user()
    rows = database.execute(
        """
        SELECT *
        FROM interview_sessions
        WHERE user_id = ? AND status = 'completed'
        ORDER BY created_at ASC
        """,
        (user["id"],),
    ).fetchall()

    history_rows = []
    for row in rows:
        history_rows.append(
            {
                "id": row["id"],
                "round_type": row["round_type"],
                "domain": row["domain"],
                "difficulty": row["difficulty"],
                "score": row["score"],
                "strengths": safe_json_loads(row["strengths_json"], []),
                "weaknesses": safe_json_loads(row["weaknesses_json"], []),
                "suggestions": safe_json_loads(row["suggestions_json"], []),
                "created_at": row["created_at"],
                "completed_at": row["completed_at"],
            }
        )

    latest_resume = database.execute(
        "SELECT * FROM resumes WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user["id"],)
    ).fetchone()

    return jsonify(
        {
            "summary": summarize_history(history_rows),
            "performance": _performance_summary(database, user["id"]),
            "latestResume": _resume_payload(latest_resume) if latest_resume else None,
        }
    )


@bp.get("/interview/<session_id>/report")
@login_required
def interview_report(session_id):
    database = get_db()
    user = get_current_user()
    interview = database.execute(
        "SELECT status FROM interview_sessions WHERE id=? AND user_id=?", (session_id, user["id"])
    ).fetchone()
    if interview and interview["status"] != "completed":
        return jsonify({"error": "The report is available after the interview is complete."}), 409
    report = build_report(database, session_id, user["id"])
    if not report:
        return jsonify({"error": "Interview session not found."}), 404
    return jsonify({"report": report})


@bp.post("/interview/integrity")
@login_required
def record_integrity_event():
    payload = request.get_json(silent=True) or {}
    session_id = str(payload.get("sessionId") or "").strip()
    event_type = str(payload.get("eventType") or "").strip().upper()
    allowed_events = {
        "TAB_SWITCH", "WINDOW_BLUR", "FACE_NOT_VISIBLE", "MULTIPLE_FACES",
        "MULTIPLE_FACE_DETECTED", "CAMERA_DISABLED", "CAMERA_INTERRUPTED",
        "REPEATED_LOOK_AWAY", "MICROPHONE_DISABLED", "MICROPHONE_INTERRUPTED",
    }
    if not session_id or event_type not in allowed_events:
        return jsonify({"error": "A valid session and integrity event are required."}), 400
    try:
        duration = max(0, float(payload.get("duration") or 0))
        severity = min(3, max(1, int(payload.get("severity") or 1)))
        question_number = max(0, int(payload.get("questionNumber") or 0))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid integrity event values."}), 400

    database = get_db()
    user = get_current_user()
    interview = database.execute(
        "SELECT * FROM interview_sessions WHERE id=? AND user_id=?", (session_id, user["id"])
    ).fetchone()
    if not interview:
        return jsonify({"error": "Interview session not found."}), 404
    database.execute(
        """
        INSERT INTO integrity_events (
            session_id, event_type, duration_seconds, question_number, severity, created_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (session_id, event_type, duration, question_number, severity, iso_now()),
    )
    status = "Focus Warning" if event_type in {"TAB_SWITCH", "WINDOW_BLUR"} else "Attention Warning"
    database.execute(
        "UPDATE interview_sessions SET integrity_status=?, "
        "attention_warning_count=attention_warning_count+1 WHERE id=?",
        (status, session_id),
    )
    if event_type == "TAB_SWITCH":
        database.execute(
            """
            UPDATE interview_sessions
            SET tab_switch_count=tab_switch_count+1,
                total_time_away=total_time_away+?,
                longest_time_away=MAX(longest_time_away, ?),
                integrity_status=?
            WHERE id=?
            """,
            (duration, duration, status, session_id),
        )
    elif event_type == "WINDOW_BLUR":
        database.execute(
            """
            UPDATE interview_sessions
            SET window_blur_count=window_blur_count+1,
                total_time_away=total_time_away+?,
                longest_time_away=MAX(longest_time_away, ?)
            WHERE id=?
            """,
            (duration, duration, session_id),
        )
    counter_columns = {
        "FACE_NOT_VISIBLE": "face_absence_count",
        "MULTIPLE_FACES": "multiple_face_count",
        "MULTIPLE_FACE_DETECTED": "multiple_face_count",
        "CAMERA_DISABLED": "camera_interruption_count",
        "CAMERA_INTERRUPTED": "camera_interruption_count",
        "MICROPHONE_DISABLED": "microphone_interruption_count",
        "MICROPHONE_INTERRUPTED": "microphone_interruption_count",
    }
    counter_column = counter_columns.get(event_type)
    if counter_column:
        database.execute(
            f"UPDATE interview_sessions SET {counter_column}={counter_column}+1 WHERE id=?",
            (session_id,),
        )
    database.commit()
    refreshed = database.execute(
        "SELECT integrity_status, tab_switch_count, total_time_away, longest_time_away, "
        "window_blur_count, attention_warning_count, multiple_face_count, "
        "camera_interruption_count, microphone_interruption_count "
        "FROM interview_sessions WHERE id=?", (session_id,)
    ).fetchone()
    return jsonify(
        {
            "integrity": {
                "status": refreshed["integrity_status"],
                "tabSwitchCount": refreshed["tab_switch_count"],
                "totalTimeAway": refreshed["total_time_away"],
                "longestTimeAway": refreshed["longest_time_away"],
                "windowBlurCount": refreshed["window_blur_count"],
                "attentionWarningCount": refreshed["attention_warning_count"],
                "multipleFaceCount": refreshed["multiple_face_count"],
                "cameraInterruptionCount": refreshed["camera_interruption_count"],
                "microphoneInterruptionCount": refreshed["microphone_interruption_count"],
            }
        }
    )


@bp.get("/history")
@login_required
def history():
    database = get_db()
    user = get_current_user()
    rows = database.execute(
        """
        SELECT *
        FROM interview_sessions
        WHERE user_id = ?
        ORDER BY created_at DESC
        """,
        (user["id"],),
    ).fetchall()
    return jsonify({"sessions": [_session_payload(row) for row in rows]})
