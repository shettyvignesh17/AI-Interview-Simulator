from flask import Blueprint, jsonify, render_template


bp = Blueprint("main", __name__)


@bp.get("/")
def index():
    return render_template("index.html")


@bp.get("/dashboard")
@bp.get("/dashboard.html")
def dashboard_page():
    return render_template("dashboard.html")


@bp.get("/aptitude")
@bp.get("/aptitude.html")
def aptitude_page():
    return render_template("aptitude.html")


@bp.get("/learning")
@bp.get("/learning.html")
def learning_page():
    return render_template("learning.html")


@bp.get("/resume-quiz")
@bp.get("/resume-quiz.html")
def resume_quiz_page():
    return render_template("resume_quiz.html")


@bp.get("/health")
def health():
    return jsonify({"status": "ok"})
