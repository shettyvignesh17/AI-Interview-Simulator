from collections import Counter

from flask import Blueprint, jsonify, request

from interview_simulator.db import get_db
from interview_simulator.services.resume_parser import parse_resume
from interview_simulator.services.resume_quiz import (
    DIFFICULTY_MIX,
    QUIZ_SIZE,
    QUIZ_TIMER_SECONDS,
    create_quiz,
    history_summary,
    public_questions,
    remaining_seconds,
    result_payload,
    save_answer,
    saved_responses,
    start_quiz,
    submit_quiz,
)
from interview_simulator.utils.auth import get_current_user, login_required
from interview_simulator.utils.common import iso_now, safe_json_dumps, safe_json_loads


bp = Blueprint("resume_quiz", __name__, url_prefix="/api/resume-quiz")


def _analysis_payload(resume, analysis_row):
    analysis = safe_json_loads(analysis_row["analysis_json"], {})
    return {
        "resume": {
            "id": resume["id"], "filename": resume["filename"],
            "contentType": resume["content_type"], "fileSize": resume["file_size"],
            "uploadedAt": resume["created_at"], "status": "Analysis Complete",
        },
        "analysis": analysis,
        "counts": {
            "technicalSkills": analysis_row["technical_skill_count"],
            "professionalExperience": analysis_row["experience_count"],
            "projects": analysis_row["project_count"],
            "certifications": analysis_row["certification_count"],
        },
    }


def _owned_analysis(database, user_id, resume_id):
    return database.execute(
        """
        SELECT r.*,a.analysis_json,a.technical_skill_count,a.experience_count,
               a.project_count,a.certification_count,a.created_at AS analyzed_at
        FROM resumes r JOIN resume_analyses a ON a.resume_id=r.id
        WHERE r.id=? AND r.user_id=? AND a.user_id=?
        """,
        (resume_id, user_id, user_id),
    ).fetchone()


def _owned_session(database, user_id, session_id):
    return database.execute(
        "SELECT * FROM resume_quiz_sessions WHERE id=? AND user_id=?", (session_id, user_id)
    ).fetchone()


def _session_payload(database, session_row, include_questions=False):
    payload = {
        "id": session_row["id"], "resumeId": session_row["resume_id"],
        "status": session_row["status"], "totalQuestions": session_row["total_questions"],
        "timeLimitSeconds": session_row["time_limit_seconds"],
        "remainingSeconds": remaining_seconds(session_row),
        "startedAt": session_row["started_at"], "deadlineAt": session_row["deadline_at"],
    }
    if include_questions:
        payload["questions"] = public_questions(database, session_row["id"])
        payload["responses"] = saved_responses(database, session_row["id"])
    return payload


@bp.get("/summary")
@login_required
def resume_quiz_summary():
    database = get_db()
    user = get_current_user()
    latest = database.execute(
        """
        SELECT r.*,a.analysis_json,a.technical_skill_count,a.experience_count,
               a.project_count,a.certification_count,a.created_at AS analyzed_at
        FROM resumes r JOIN resume_analyses a ON a.resume_id=r.id
        WHERE r.user_id=? ORDER BY a.created_at DESC LIMIT 1
        """,
        (user["id"],),
    ).fetchone()
    rows = database.execute(
        "SELECT * FROM resume_quiz_sessions WHERE user_id=? ORDER BY created_at DESC",
        (user["id"],),
    ).fetchall()
    open_session = next((row for row in rows if row["status"] in {"ready", "active"}), None)
    return jsonify(
        {
            "latestResume": _analysis_payload(latest, latest) if latest else None,
            "openSession": _session_payload(database, open_session) if open_session else None,
            "stats": history_summary(rows),
            "meta": {
                "quizSize": QUIZ_SIZE, "timerSeconds": QUIZ_TIMER_SECONDS,
                "difficultyMix": DIFFICULTY_MIX, "supportedFormats": ["PDF", "DOCX"],
            },
        }
    )


@bp.post("/resume")
@login_required
def upload_resume_for_quiz():
    uploaded = request.files.get("resume")
    if not uploaded or not uploaded.filename:
        return jsonify({"error": "Choose a PDF or DOCX resume to upload."}), 400
    try:
        parsed = parse_resume(uploaded, allowed_extensions={".pdf", ".docx"})
    except (ValueError, RuntimeError) as exc:
        return jsonify({"error": str(exc)}), 400

    database = get_db()
    user = get_current_user()
    profile = parsed["profile"]
    analysis = parsed["analysis"]
    cursor = database.execute(
        """
        INSERT INTO resumes (
            user_id,filename,content_type,raw_text,skills_json,projects_json,
            experience_json,summary,file_size,created_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?)
        """,
        (
            user["id"], parsed["filename"], parsed["content_type"], parsed["text"],
            safe_json_dumps(profile["skills"]), safe_json_dumps(profile["projects"]),
            safe_json_dumps(profile["experience"]), profile["summary"], parsed["file_size"], iso_now(),
        ),
    )
    resume_id = cursor.lastrowid
    database.execute(
        """
        INSERT INTO resume_analyses (
            resume_id,user_id,analysis_json,technical_skill_count,experience_count,
            project_count,certification_count,created_at
        ) VALUES (?,?,?,?,?,?,?,?)
        """,
        (
            resume_id, user["id"], safe_json_dumps(analysis),
            len(analysis.get("technicalSkills", [])),
            len(analysis.get("professionalExperience", [])),
            len(analysis.get("projects", [])), len(analysis.get("certifications", [])), iso_now(),
        ),
    )
    database.commit()
    row = _owned_analysis(database, user["id"], resume_id)
    return jsonify({"message": "Resume analyzed successfully.", **_analysis_payload(row, row)}), 201


@bp.delete("/resume/<int:resume_id>")
@login_required
def remove_resume(resume_id):
    database = get_db()
    user = get_current_user()
    row = database.execute(
        "SELECT id FROM resumes WHERE id=? AND user_id=?", (resume_id, user["id"])
    ).fetchone()
    if not row:
        return jsonify({"error": "Resume not found."}), 404
    database.execute("DELETE FROM resumes WHERE id=? AND user_id=?", (resume_id, user["id"]))
    database.commit()
    return jsonify({"message": "Resume and its quiz data were removed."})


@bp.post("/generate")
@login_required
def generate_resume_quiz():
    payload = request.get_json(silent=True) or {}
    try:
        resume_id = int(payload.get("resumeId"))
    except (TypeError, ValueError):
        return jsonify({"error": "Choose an analyzed resume first."}), 400
    database = get_db()
    user = get_current_user()
    row = _owned_analysis(database, user["id"], resume_id)
    if not row:
        return jsonify({"error": "Analyzed resume not found."}), 404
    try:
        session_row = create_quiz(
            database, user["id"], resume_id, safe_json_loads(row["analysis_json"], {})
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 422
    category_rows = database.execute(
        "SELECT category FROM resume_quiz_questions WHERE session_id=?", (session_row["id"],)
    ).fetchall()
    difficulty_rows = database.execute(
        "SELECT difficulty FROM resume_quiz_questions WHERE session_id=?", (session_row["id"],)
    ).fetchall()
    return jsonify(
        {
            "message": "Your source-grounded Resume Quiz is ready.",
            "session": _session_payload(database, session_row),
            "distribution": {
                "categories": dict(Counter(row["category"] for row in category_rows)),
                "difficulties": dict(Counter(row["difficulty"] for row in difficulty_rows)),
            },
        }
    ), 201


@bp.post("/start")
@login_required
def start_resume_quiz():
    payload = request.get_json(silent=True) or {}
    session_id = str(payload.get("sessionId") or "").strip()
    database = get_db()
    user = get_current_user()
    row = _owned_session(database, user["id"], session_id)
    if not row:
        return jsonify({"error": "Resume Quiz session not found."}), 404
    try:
        row = start_quiz(database, row)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    return jsonify({"session": _session_payload(database, row, include_questions=True)})


@bp.get("/session/<session_id>")
@login_required
def get_resume_quiz_session(session_id):
    database = get_db()
    user = get_current_user()
    row = _owned_session(database, user["id"], session_id)
    if not row:
        return jsonify({"error": "Resume Quiz session not found."}), 404
    if row["status"] == "active" and remaining_seconds(row) <= 0:
        row = submit_quiz(database, row, force_timeout=True)
    if row["status"] == "completed":
        return jsonify({"session": _session_payload(database, row), "result": result_payload(database, row)})
    return jsonify({"session": _session_payload(database, row, include_questions=row["status"] == "active")})


@bp.delete("/session/<session_id>")
@login_required
def discard_resume_quiz_session(session_id):
    database = get_db()
    user = get_current_user()
    row = _owned_session(database, user["id"], session_id)
    if not row:
        return jsonify({"error": "Resume Quiz session not found."}), 404
    if row["status"] == "completed":
        return jsonify({"error": "A completed Resume Quiz cannot be discarded."}), 409

    database.execute(
        "DELETE FROM resume_quiz_sessions WHERE id=? AND user_id=?",
        (session_id, user["id"]),
    )
    database.commit()
    return jsonify({"discarded": True})


@bp.patch("/answer")
@login_required
def save_resume_quiz_answer():
    payload = request.get_json(silent=True) or {}
    session_id = str(payload.get("sessionId") or "").strip()
    question_id = str(payload.get("questionId") or "").strip()
    database = get_db()
    user = get_current_user()
    row = _owned_session(database, user["id"], session_id)
    if not row:
        return jsonify({"error": "Resume Quiz session not found."}), 404
    try:
        saved = save_answer(
            database, row, question_id, payload.get("selectedAnswer"), payload.get("timeSpent", 0)
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    if not saved:
        completed = submit_quiz(database, row, force_timeout=True)
        return jsonify({"timedOut": True, "result": result_payload(database, completed)})
    refreshed = _owned_session(database, user["id"], session_id)
    return jsonify({"saved": True, "remainingSeconds": remaining_seconds(refreshed)})


@bp.post("/submit")
@login_required
def submit_resume_quiz():
    payload = request.get_json(silent=True) or {}
    session_id = str(payload.get("sessionId") or "").strip()
    responses = payload.get("responses") or {}
    time_spent = payload.get("timeSpent") or {}
    if not isinstance(responses, dict) or not isinstance(time_spent, dict):
        return jsonify({"error": "Responses must be submitted as question maps."}), 400
    database = get_db()
    user = get_current_user()
    row = _owned_session(database, user["id"], session_id)
    if not row:
        return jsonify({"error": "Resume Quiz session not found."}), 404
    if row["status"] != "active":
        return jsonify({"error": "This Resume Quiz has already been submitted."}), 409
    completed = submit_quiz(database, row, responses, time_spent)
    rows = database.execute(
        "SELECT * FROM resume_quiz_sessions WHERE user_id=? ORDER BY created_at DESC", (user["id"],)
    ).fetchall()
    return jsonify({"result": result_payload(database, completed), "stats": history_summary(rows)})


@bp.get("/result/<session_id>")
@login_required
def resume_quiz_result(session_id):
    database = get_db()
    user = get_current_user()
    row = _owned_session(database, user["id"], session_id)
    if not row:
        return jsonify({"error": "Resume Quiz session not found."}), 404
    if row["status"] != "completed":
        return jsonify({"error": "Results are available after submission."}), 409
    return jsonify({"result": result_payload(database, row)})


@bp.get("/history")
@login_required
def resume_quiz_history():
    database = get_db()
    user = get_current_user()
    rows = database.execute(
        "SELECT * FROM resume_quiz_sessions WHERE user_id=? ORDER BY created_at DESC", (user["id"],)
    ).fetchall()
    return jsonify({"stats": history_summary(rows)})
