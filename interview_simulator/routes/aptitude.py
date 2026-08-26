from flask import Blueprint, jsonify, request

from interview_simulator.db import get_db
from interview_simulator.services.aptitude import (
    COMPANIES,
    QUIZ_SIZE,
    QUIZ_TIMER_SECONDS,
    public_attempt,
    start_quiz,
    submit_quiz,
    summarize_history,
)
from interview_simulator.utils.auth import get_current_user, login_required
from interview_simulator.utils.common import iso_now


bp = Blueprint("aptitude", __name__, url_prefix="/api/aptitude")


@bp.get("/summary")
@login_required
def aptitude_summary():
    database = get_db()
    user = get_current_user()
    rows = database.execute(
        "SELECT * FROM aptitude_attempts WHERE user_id = ? ORDER BY created_at DESC",
        (user["id"],),
    ).fetchall()
    company_rows = database.execute(
        "SELECT company, COUNT(*) AS total FROM aptitude_questions GROUP BY company ORDER BY company"
    ).fetchall()
    return jsonify(
        {
            "stats": summarize_history(rows),
            "questionBank": {
                "totalQuestions": sum(row["total"] for row in company_rows),
                "companyCounts": {row["company"]: row["total"] for row in company_rows},
            },
        }
    )


@bp.post("/start")
@login_required
def start_aptitude_quiz():
    database = get_db()
    user = get_current_user()
    row = start_quiz(database, user["id"])
    return jsonify(
        {
            "attempt": public_attempt(row),
            "meta": {
                "quizSize": QUIZ_SIZE,
                "timerSeconds": QUIZ_TIMER_SECONDS,
                "companies": COMPANIES,
                "difficultyMix": {"Easy": 4, "Medium": 4, "Hard": 2},
            },
        }
    )


@bp.post("/submit")
@login_required
def submit_aptitude_quiz():
    payload = request.get_json(silent=True) or {}
    attempt_id = payload.get("attemptId")
    responses = payload.get("responses") or {}
    if not attempt_id or not isinstance(responses, dict):
        return jsonify({"error": "A valid attempt and response map are required."}), 400

    database = get_db()
    user = get_current_user()
    row = database.execute(
        "SELECT * FROM aptitude_attempts WHERE id = ? AND user_id = ?",
        (attempt_id, user["id"]),
    ).fetchone()
    if not row:
        return jsonify({"error": "Quiz attempt not found."}), 404
    if row["status"] != "active":
        return jsonify({"error": "This quiz has already been submitted."}), 400

    result = submit_quiz(database, row, responses)
    history_rows = database.execute(
        "SELECT * FROM aptitude_attempts WHERE user_id = ? ORDER BY created_at DESC",
        (user["id"],),
    ).fetchall()
    return jsonify({"result": result, "stats": summarize_history(history_rows)})


@bp.post("/abandon")
@login_required
def abandon_aptitude_quiz():
    payload = request.get_json(silent=True) or {}
    attempt_id = str(payload.get("attemptId") or "").strip()
    if not attempt_id:
        return jsonify({"error": "A valid quiz attempt is required."}), 400

    database = get_db()
    user = get_current_user()
    row = database.execute(
        "SELECT status FROM aptitude_attempts WHERE id=? AND user_id=?",
        (attempt_id, user["id"]),
    ).fetchone()
    if not row:
        return jsonify({"error": "Quiz attempt not found."}), 404
    if row["status"] == "completed":
        return jsonify({"error": "A completed quiz cannot be abandoned."}), 409
    if row["status"] == "abandoned":
        return jsonify({"abandoned": True})

    database.execute(
        """
        UPDATE aptitude_attempts
        SET status='abandoned', responses_json='{}', completed_at=?
        WHERE id=? AND user_id=? AND status='active'
        """,
        (iso_now(), attempt_id, user["id"]),
    )
    database.commit()
    return jsonify({"abandoned": True})
