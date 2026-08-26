from flask import Blueprint, jsonify, request

from interview_simulator.db import get_db
from interview_simulator.services.learning import (
    get_question,
    learning_overview,
    list_questions,
    metadata,
    random_question,
    update_preferences,
    update_progress,
)
from interview_simulator.utils.auth import get_current_user, login_required


bp = Blueprint("learning", __name__, url_prefix="/api/learning")


@bp.get("/overview")
@login_required
def overview():
    database = get_db()
    user = get_current_user()
    return jsonify(
        {
            "overview": learning_overview(database, user["id"]),
            "metadata": metadata(database),
        }
    )


@bp.get("/questions")
@login_required
def questions():
    database = get_db()
    user = get_current_user()
    return jsonify(list_questions(database, user["id"], request.args))


@bp.get("/questions/<question_id>")
@login_required
def question_detail(question_id):
    database = get_db()
    user = get_current_user()
    question = get_question(database, user["id"], question_id)
    if not question:
        return jsonify({"error": "Learning question not found."}), 404
    return jsonify({"question": question})


@bp.patch("/questions/<question_id>/progress")
@login_required
def question_progress(question_id):
    payload = request.get_json(silent=True) or {}
    database = get_db()
    user = get_current_user()
    question = update_progress(database, user["id"], question_id, payload)
    if not question:
        return jsonify({"error": "Learning question not found."}), 404
    return jsonify({"question": question, "overview": learning_overview(database, user["id"])})


@bp.patch("/preferences")
@login_required
def preferences():
    payload = request.get_json(silent=True) or {}
    database = get_db()
    user = get_current_user()
    return jsonify({"preferences": update_preferences(database, user["id"], payload)})


@bp.get("/random")
@login_required
def random_learning_question():
    database = get_db()
    user = get_current_user()
    question = random_question(database, user["id"], request.args)
    if not question:
        return jsonify({"error": "No question matches the selected filters."}), 404
    return jsonify({"question": question})
