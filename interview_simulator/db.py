import sqlite3

from flask import current_app, g


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS resumes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    filename TEXT NOT NULL,
    content_type TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    skills_json TEXT NOT NULL DEFAULT '[]',
    projects_json TEXT NOT NULL DEFAULT '[]',
    experience_json TEXT NOT NULL DEFAULT '[]',
    summary TEXT NOT NULL DEFAULT '',
    file_size INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS interview_sessions (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    round_type TEXT NOT NULL,
    domain TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    resume_id INTEGER,
    current_question TEXT NOT NULL,
    asked_questions_json TEXT NOT NULL DEFAULT '[]',
    transcript_json TEXT NOT NULL DEFAULT '[]',
    score REAL NOT NULL DEFAULT 0,
    confidence_score REAL NOT NULL DEFAULT 0,
    clarity_score REAL NOT NULL DEFAULT 0,
    depth_score REAL NOT NULL DEFAULT 0,
    strengths_json TEXT NOT NULL DEFAULT '[]',
    weaknesses_json TEXT NOT NULL DEFAULT '[]',
    suggestions_json TEXT NOT NULL DEFAULT '[]',
    interviewer_notes TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'active',
    question_index INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    completed_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (resume_id) REFERENCES resumes(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS interview_questions (
    id TEXT PRIMARY KEY,
    base_question_id TEXT NOT NULL,
    company TEXT NOT NULL,
    interview_round TEXT NOT NULL CHECK (interview_round IN ('technical', 'managerial', 'hr')),
    domain TEXT NOT NULL,
    bank_category TEXT NOT NULL,
    topic TEXT NOT NULL,
    difficulty TEXT NOT NULL CHECK (difficulty IN ('easy', 'medium', 'hard')),
    question TEXT NOT NULL UNIQUE,
    ideal_answer TEXT NOT NULL,
    answer_explanation TEXT NOT NULL,
    keywords_json TEXT NOT NULL DEFAULT '[]',
    expected_points_json TEXT NOT NULL DEFAULT '[]',
    follow_ups_json TEXT NOT NULL DEFAULT '[]',
    estimated_answer_time INTEGER NOT NULL DEFAULT 120,
    frequency TEXT NOT NULL,
    tags_json TEXT NOT NULL DEFAULT '[]',
    provenance TEXT NOT NULL DEFAULT 'style_reference'
);

CREATE TABLE IF NOT EXISTS candidate_answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    question_number INTEGER NOT NULL,
    question_text TEXT NOT NULL,
    topic TEXT NOT NULL,
    difficulty TEXT NOT NULL,
    company TEXT NOT NULL DEFAULT 'General',
    round_type TEXT NOT NULL DEFAULT 'technical',
    domain TEXT NOT NULL DEFAULT 'software_engineering',
    answer_type TEXT NOT NULL CHECK (answer_type IN ('typed', 'spoken', 'skipped')),
    answer_text TEXT NOT NULL,
    duration_seconds INTEGER NOT NULL DEFAULT 0,
    answer_classification TEXT NOT NULL DEFAULT 'insufficient',
    timed_out INTEGER NOT NULL DEFAULT 0,
    adaptive_change TEXT NOT NULL DEFAULT 'none',
    voice_metrics_json TEXT NOT NULL DEFAULT '{}',
    evaluation_json TEXT NOT NULL DEFAULT '{}',
    ideal_answer TEXT NOT NULL DEFAULT '',
    answer_explanation TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES interview_sessions(id) ON DELETE CASCADE,
    UNIQUE (session_id, question_number)
);

CREATE TABLE IF NOT EXISTS integrity_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    duration_seconds REAL NOT NULL DEFAULT 0,
    question_number INTEGER NOT NULL DEFAULT 0,
    severity INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES interview_sessions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_interview_questions_selection
ON interview_questions (interview_round, company, domain, difficulty);

CREATE INDEX IF NOT EXISTS idx_candidate_answers_session
ON candidate_answers (session_id, question_number);

CREATE INDEX IF NOT EXISTS idx_integrity_events_session
ON integrity_events (session_id, created_at);

CREATE TABLE IF NOT EXISTS aptitude_questions (
    id INTEGER PRIMARY KEY,
    company TEXT NOT NULL,
    category TEXT NOT NULL,
    question TEXT NOT NULL UNIQUE,
    options_json TEXT NOT NULL,
    answer TEXT NOT NULL,
    explanation TEXT NOT NULL,
    difficulty TEXT NOT NULL CHECK (difficulty IN ('Easy', 'Medium', 'Hard'))
);

CREATE TABLE IF NOT EXISTS aptitude_attempts (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    questions_json TEXT NOT NULL,
    responses_json TEXT NOT NULL DEFAULT '{}',
    score INTEGER NOT NULL DEFAULT 0,
    total_questions INTEGER NOT NULL DEFAULT 10,
    percentage REAL NOT NULL DEFAULT 0,
    company_performance_json TEXT NOT NULL DEFAULT '{}',
    category_performance_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    completed_at TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_aptitude_questions_company_difficulty
ON aptitude_questions (company, difficulty);

CREATE INDEX IF NOT EXISTS idx_aptitude_attempts_user_created
ON aptitude_attempts (user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS learning_questions (
    id TEXT PRIMARY KEY,
    question_type TEXT NOT NULL CHECK (question_type IN ('aptitude', 'coding', 'interview')),
    category TEXT NOT NULL,
    subcategory TEXT NOT NULL,
    company TEXT NOT NULL,
    difficulty TEXT NOT NULL CHECK (difficulty IN ('Easy', 'Medium', 'Hard')),
    question TEXT NOT NULL UNIQUE,
    answer TEXT NOT NULL,
    detailed_explanation TEXT NOT NULL,
    example TEXT NOT NULL DEFAULT '',
    tags_json TEXT NOT NULL DEFAULT '[]',
    topic TEXT NOT NULL,
    estimated_study_time INTEGER NOT NULL DEFAULT 5,
    frequency TEXT NOT NULL,
    related_questions_json TEXT NOT NULL DEFAULT '[]',
    approach TEXT NOT NULL DEFAULT '',
    code TEXT NOT NULL DEFAULT '',
    time_complexity TEXT NOT NULL DEFAULT '',
    space_complexity TEXT NOT NULL DEFAULT '',
    common_mistakes TEXT NOT NULL DEFAULT '',
    interview_tip TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS learning_progress (
    user_id INTEGER NOT NULL,
    question_id TEXT NOT NULL,
    bookmarked INTEGER NOT NULL DEFAULT 0,
    studied INTEGER NOT NULL DEFAULT 0,
    revision INTEGER NOT NULL DEFAULT 0,
    viewed_count INTEGER NOT NULL DEFAULT 0,
    confidence TEXT NOT NULL DEFAULT '',
    flashcard_difficulty TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    last_viewed TEXT,
    learned_at TEXT,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (user_id, question_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES learning_questions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS learning_preferences (
    user_id INTEGER PRIMARY KEY,
    daily_goal INTEGER NOT NULL DEFAULT 10,
    target_companies_json TEXT NOT NULL DEFAULT '[]',
    last_section TEXT NOT NULL DEFAULT 'overview',
    last_question_id TEXT,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (last_question_id) REFERENCES learning_questions(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_learning_questions_type_topic
ON learning_questions (question_type, topic);

CREATE INDEX IF NOT EXISTS idx_learning_questions_company_difficulty
ON learning_questions (company, difficulty);

CREATE INDEX IF NOT EXISTS idx_learning_progress_user_status
ON learning_progress (user_id, studied, bookmarked, revision);

CREATE TABLE IF NOT EXISTS resume_analyses (
    resume_id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    analysis_json TEXT NOT NULL,
    technical_skill_count INTEGER NOT NULL DEFAULT 0,
    experience_count INTEGER NOT NULL DEFAULT 0,
    project_count INTEGER NOT NULL DEFAULT 0,
    certification_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY (resume_id) REFERENCES resumes(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS resume_quiz_sessions (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    resume_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'ready' CHECK (status IN ('ready', 'active', 'completed')),
    total_questions INTEGER NOT NULL DEFAULT 10,
    time_limit_seconds INTEGER NOT NULL DEFAULT 600,
    score INTEGER NOT NULL DEFAULT 0,
    correct_answers INTEGER NOT NULL DEFAULT 0,
    incorrect_answers INTEGER NOT NULL DEFAULT 0,
    unanswered_questions INTEGER NOT NULL DEFAULT 10,
    percentage REAL NOT NULL DEFAULT 0,
    time_used_seconds INTEGER NOT NULL DEFAULT 0,
    timed_out INTEGER NOT NULL DEFAULT 0,
    analytics_json TEXT NOT NULL DEFAULT '{}',
    started_at TEXT,
    deadline_at TEXT,
    submitted_at TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (resume_id) REFERENCES resumes(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS resume_quiz_questions (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    question_uid TEXT NOT NULL,
    position INTEGER NOT NULL,
    category TEXT NOT NULL,
    topic TEXT NOT NULL,
    difficulty TEXT NOT NULL CHECK (difficulty IN ('Easy', 'Medium', 'Hard')),
    question TEXT NOT NULL,
    options_json TEXT NOT NULL,
    correct_answer TEXT NOT NULL,
    explanation TEXT NOT NULL,
    resume_source_json TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES resume_quiz_sessions(id) ON DELETE CASCADE,
    UNIQUE (session_id, position),
    UNIQUE (session_id, question_uid)
);

CREATE TABLE IF NOT EXISTS resume_quiz_answers (
    session_id TEXT NOT NULL,
    question_id TEXT NOT NULL,
    selected_answer TEXT,
    is_correct INTEGER,
    time_spent_seconds INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (session_id, question_id),
    FOREIGN KEY (session_id) REFERENCES resume_quiz_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES resume_quiz_questions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_resume_analyses_user
ON resume_analyses (user_id, created_at);

CREATE INDEX IF NOT EXISTS idx_resume_quiz_sessions_user
ON resume_quiz_sessions (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_resume_quiz_questions_session
ON resume_quiz_questions (session_id, position);
"""


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(
            current_app.config["DATABASE"], detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_error=None):
    database = g.pop("db", None)
    if database is not None:
        database.close()


def init_database():
    database = get_db()
    database.executescript(SCHEMA)
    _migrate_resumes(database)
    _migrate_interview_sessions(database)
    _migrate_candidate_answers(database)
    from interview_simulator.services.aptitude import ensure_aptitude_question_bank
    from interview_simulator.services.interview_delivery import ensure_interview_question_bank
    from interview_simulator.services.learning import ensure_learning_catalog

    ensure_aptitude_question_bank(database)
    ensure_learning_catalog(database)
    ensure_interview_question_bank(database)


def _migrate_interview_sessions(database):
    """Add simulator v2 fields to databases created by older project versions."""
    existing = {
        row["name"] for row in database.execute("PRAGMA table_info(interview_sessions)").fetchall()
    }
    columns = {
        "company": "TEXT NOT NULL DEFAULT 'General'",
        "duration_minutes": "INTEGER NOT NULL DEFAULT 30",
        "question_limit": "INTEGER NOT NULL DEFAULT 5",
        "technical_score": "REAL NOT NULL DEFAULT 0",
        "communication_score": "REAL NOT NULL DEFAULT 0",
        "relevance_score": "REAL NOT NULL DEFAULT 0",
        "completeness_score": "REAL NOT NULL DEFAULT 0",
        "integrity_status": "TEXT NOT NULL DEFAULT 'Normal'",
        "tab_switch_count": "INTEGER NOT NULL DEFAULT 0",
        "total_time_away": "REAL NOT NULL DEFAULT 0",
        "longest_time_away": "REAL NOT NULL DEFAULT 0",
        "started_at": "TEXT",
        "starting_difficulty": "TEXT NOT NULL DEFAULT 'easy'",
        "strong_streak": "INTEGER NOT NULL DEFAULT 0",
        "weak_streak": "INTEGER NOT NULL DEFAULT 0",
        "adaptive_history_json": "TEXT NOT NULL DEFAULT '[]'",
        "timeout_count": "INTEGER NOT NULL DEFAULT 0",
        "window_blur_count": "INTEGER NOT NULL DEFAULT 0",
        "attention_warning_count": "INTEGER NOT NULL DEFAULT 0",
        "multiple_face_count": "INTEGER NOT NULL DEFAULT 0",
        "face_absence_count": "INTEGER NOT NULL DEFAULT 0",
        "camera_interruption_count": "INTEGER NOT NULL DEFAULT 0",
        "microphone_interruption_count": "INTEGER NOT NULL DEFAULT 0",
    }
    for name, definition in columns.items():
        if name not in existing:
            database.execute(f"ALTER TABLE interview_sessions ADD COLUMN {name} {definition}")
    database.commit()


def _migrate_resumes(database):
    existing = {row["name"] for row in database.execute("PRAGMA table_info(resumes)").fetchall()}
    if "file_size" not in existing:
        database.execute("ALTER TABLE resumes ADD COLUMN file_size INTEGER NOT NULL DEFAULT 0")
    database.commit()


def _migrate_candidate_answers(database):
    """Persist the context and adaptive outcome for every main question."""
    existing = {
        row["name"] for row in database.execute("PRAGMA table_info(candidate_answers)").fetchall()
    }
    columns = {
        "company": "TEXT NOT NULL DEFAULT 'General'",
        "round_type": "TEXT NOT NULL DEFAULT 'technical'",
        "domain": "TEXT NOT NULL DEFAULT 'software_engineering'",
        "answer_classification": "TEXT NOT NULL DEFAULT 'insufficient'",
        "timed_out": "INTEGER NOT NULL DEFAULT 0",
        "adaptive_change": "TEXT NOT NULL DEFAULT 'none'",
    }
    for name, definition in columns.items():
        if name not in existing:
            database.execute(f"ALTER TABLE candidate_answers ADD COLUMN {name} {definition}")
    database.commit()


def init_app(app):
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_database()
