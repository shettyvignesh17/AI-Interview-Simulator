import re

from flask import Blueprint, jsonify, request, session
from werkzeug.security import check_password_hash, generate_password_hash

from interview_simulator.db import get_db
from interview_simulator.utils.auth import get_current_user
from interview_simulator.utils.common import iso_now


bp = Blueprint("auth", __name__, url_prefix="/api/auth")

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _serialize_user(user_row):
    return {
        "id": user_row["id"],
        "name": user_row["name"],
        "email": user_row["email"],
        "createdAt": user_row["created_at"],
    }


@bp.get("/session")
def auth_session():
    user = get_current_user()
    return jsonify(
        {
            "authenticated": bool(user),
            "user": _serialize_user(user) if user else None,
        }
    )


@bp.post("/signup")
def signup():
    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""

    if len(name) < 2:
        return jsonify({"error": "Name must be at least 2 characters."}), 400
    if not EMAIL_PATTERN.match(email):
        return jsonify({"error": "Enter a valid email address."}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400

    database = get_db()
    existing = database.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if existing:
        return jsonify({"error": "An account with that email already exists."}), 409

    database.execute(
        """
        INSERT INTO users (name, email, password_hash, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (name, email, generate_password_hash(password), iso_now()),
    )
    database.commit()

    user = database.execute(
        "SELECT id, name, email, created_at FROM users WHERE email = ?", (email,)
    ).fetchone()

    session.clear()
    session.permanent = True
    session["user_id"] = user["id"]

    return jsonify({"message": "Account created.", "user": _serialize_user(user)}), 201


@bp.post("/login")
def login():
    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip().lower()
    password = payload.get("password") or ""

    database = get_db()
    user = database.execute(
        "SELECT id, name, email, password_hash, created_at FROM users WHERE email = ?",
        (email,),
    ).fetchone()

    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid email or password."}), 401

    session.clear()
    session.permanent = True
    session["user_id"] = user["id"]

    return jsonify({"message": "Welcome back.", "user": _serialize_user(user)})


@bp.post("/logout")
def logout():
    session.clear()
    return jsonify({"message": "Signed out."})
