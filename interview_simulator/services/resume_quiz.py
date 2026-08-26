"""Source-grounded Resume Quiz generation, evaluation, and analytics."""

import hashlib
import random
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from interview_simulator.utils.common import iso_now, safe_json_dumps, safe_json_loads, unique_list


QUIZ_SIZE = 10
QUIZ_TIMER_SECONDS = 10 * 60
DIFFICULTY_MIX = {"Easy": 3, "Medium": 5, "Hard": 2}
RNG = random.SystemRandom()


def _template(identifier, difficulty, stem, correct, distractors, explanation):
    return {
        "id": identifier,
        "difficulty": difficulty,
        "stem": stem,
        "correct": correct,
        "distractors": distractors,
        "explanation": explanation,
    }


UNIVERSAL_TEMPLATES = [
    _template("validate-input", "Easy", "What should happen before untrusted input is processed by {topic}?",
              "Validate its type, format, and allowed range", ["Trust it because it reached the application", "Store it before checking it", "Disable error handling"],
              "Boundary validation prevents malformed or unsafe data from reaching core logic."),
    _template("small-test", "Easy", "Which test best verifies one isolated unit of {topic}-based logic?",
              "A focused unit test with controlled inputs and outputs", ["A production deployment", "A visual color check", "A network speed test only"],
              "A unit test isolates one behavior and checks a known result with minimal dependencies."),
    _template("version-control", "Easy", "Which practice makes changes involving {topic} easiest to review and reverse?",
              "Small commits with meaningful messages", ["One large undocumented commit", "Editing production directly", "Deleting prior versions"],
              "Small, explained commits improve reviewability, traceability, and rollback safety."),
    _template("observability", "Medium", "A {topic}-based feature fails intermittently in production. What evidence is most useful first?",
              "Structured logs, metrics, traces, and a reproducible request context", ["A guess about the cause", "Only the latest source file", "The UI color palette"],
              "Correlated telemetry establishes when, where, and under which inputs a failure occurred."),
    _template("failure-handling", "Medium", "A dependency used by a {topic}-based feature becomes temporarily unavailable. What is the strongest design response?",
              "Use bounded retries, timeouts, graceful degradation, and clear errors", ["Retry forever without delay", "Ignore every failure", "Restart all users' devices"],
              "Timeouts and bounded recovery prevent cascading failures while preserving a controlled user experience."),
    _template("performance", "Medium", "Before optimizing a slow {topic}-based workflow, what should you do first?",
              "Measure the bottleneck with representative profiling data", ["Rewrite every component", "Remove validation", "Assume the database is responsible"],
              "Measurement identifies the actual constraint and provides a baseline for evaluating an optimization."),
    _template("secrets", "Medium", "How should credentials required by a {topic}-based application be managed?",
              "Keep them outside source control in a secret-management mechanism", ["Hard-code them in the repository", "Put them in a public README", "Send them in client-side logs"],
              "Secret stores and environment injection reduce accidental disclosure and enable controlled rotation."),
    _template("compatibility", "Medium", "When changing a public interface used by a {topic}-based system, what reduces consumer breakage?",
              "Use a backward-compatible contract or an explicit versioned migration", ["Change it silently", "Remove all old fields immediately", "Depend on consumers guessing the new format"],
              "Compatibility planning gives dependent clients a stable transition path."),
    _template("concurrency", "Hard", "Two requests update the same {topic}-related record concurrently. Which approach best protects correctness?",
              "Use an appropriate transaction, lock, or optimistic concurrency check", ["Accept the last write without checking", "Add a longer UI animation", "Duplicate the record on every update"],
              "Concurrency controls detect or serialize conflicting writes so valid state is not silently lost."),
    _template("architecture", "Hard", "A {topic}-based feature must scale without making failures harder to diagnose. Which decision is strongest?",
              "Separate clear responsibilities and add measurable contracts at boundaries", ["Create many services without ownership boundaries", "Share mutable global state everywhere", "Remove monitoring to reduce overhead"],
              "Clear boundaries reduce coupling, while measurable contracts preserve observability as the system grows."),
]


PACKS = {
    "python": [
        _template("py-set", "Easy", "Which Python structure is best for unique values with fast membership checks?", "set", ["list", "tuple", "str"], "A set stores unique hashable values and offers average O(1) membership checks."),
        _template("py-context", "Medium", "What is the main benefit of Python's `with` statement for a file or connection?", "It guarantees context cleanup through a context manager", ["It makes every operation asynchronous", "It converts data to JSON", "It disables exceptions"], "Context managers run cleanup logic even when the block raises an exception."),
        _template("py-generator", "Medium", "Why use a Python generator for a large stream of records?", "It yields items lazily and avoids loading the full stream into memory", ["It permanently caches every item", "It guarantees parallel execution", "It removes the need for error handling"], "Generators compute values incrementally, reducing peak memory use."),
        _template("py-mutable", "Hard", "Why can a mutable default argument cause surprising Python behavior?", "The same object is reused across function calls", ["Python deletes it after every call", "Mutable values cannot be passed to functions", "It always becomes immutable"], "Default expressions are evaluated once at function definition, so mutations persist between calls."),
    ],
    "sql": [
        _template("sql-left", "Easy", "Which SQL JOIN returns every row from the left table plus matching right-table rows?", "LEFT JOIN", ["INNER JOIN", "CROSS JOIN", "SELF JOIN"], "LEFT JOIN preserves all left-side rows and uses NULL for missing right-side matches."),
        _template("sql-index", "Medium", "When is a database index most likely to improve a query?", "When it supports frequently filtered or joined columns with useful selectivity", ["When every write must become slower", "When the table has no queries", "When it replaces all constraints"], "Indexes can avoid broad scans when their leading columns match selective access patterns."),
        _template("sql-group", "Medium", "Why is HAVING used after GROUP BY?", "It filters aggregated groups", ["It sorts individual rows", "It creates a foreign key", "It renames a table"], "WHERE filters source rows; HAVING filters the groups produced by aggregation."),
        _template("sql-transaction", "Hard", "Which isolation problem occurs when two transactions overwrite each other's updates without detection?", "Lost update", ["Phantom read", "Dirty schema", "Cartesian product"], "A lost update occurs when one concurrent write silently replaces another."),
    ],
    "machine learning": [
        _template("ml-split", "Easy", "Why keep a test set separate from model training?", "To estimate performance on unseen data", ["To increase training labels", "To guarantee zero bias", "To remove all noisy features"], "A held-out test set provides a less biased estimate of generalization."),
        _template("ml-imbalance", "Medium", "For a highly imbalanced classifier, which metric is often more informative than accuracy alone?", "Precision, recall, or F1 for the important class", ["Training file size", "Number of columns only", "Mean feature name length"], "Class-aware metrics reveal errors that overall accuracy can hide."),
        _template("ml-overfit", "Medium", "Which signal most strongly suggests overfitting?", "Training performance improves while validation performance worsens", ["Both training and validation improve similarly", "The dataset has column names", "Inference uses a function"], "A widening train-validation gap indicates that the model is fitting training-specific patterns."),
        _template("ml-leak", "Hard", "What is data leakage in a predictive pipeline?", "Training uses information that would not be available at real prediction time", ["The model has too few layers", "Rows are stored in a database", "A metric is rounded"], "Leakage creates unrealistically strong evaluation by exposing future or target-derived information."),
        _template("ml-rf", "Hard", "Why can Random Forest reduce variance compared with one decision tree?", "It aggregates many trees trained with randomized samples and features", ["It removes all training examples", "It fits one deeper tree", "It always uses linear regression"], "Bagging and feature randomness decorrelate trees; aggregation smooths individual high-variance errors."),
    ],
    "react": [
        _template("react-props", "Easy", "What is the primary role of props in React?", "Pass read-only data from a parent to a child component", ["Mutate the browser database", "Replace all component state", "Compile CSS on the server"], "Props form the explicit input contract of a component."),
        _template("react-key", "Medium", "Why should list items have stable React keys?", "They help reconciliation preserve item identity across renders", ["They encrypt component state", "They make HTTP requests", "They replace accessibility labels"], "Stable keys let React match prior and next list elements correctly."),
        _template("react-effect", "Medium", "When is `useEffect` appropriate?", "Synchronizing a component with an external system after rendering", ["Calculating every local variable", "Declaring static HTML only", "Replacing event handlers"], "Effects are for synchronization with systems outside React's pure rendering process."),
        _template("react-state", "Hard", "Why should React state updates avoid direct mutation?", "Immutable updates give React a reliable change signal and preserve prior state", ["Mutation is invalid JavaScript", "State must always be a string", "It prevents all rerenders"], "New references make state transitions predictable and avoid corrupting values used by prior renders."),
    ],
    "web api": [
        _template("api-method", "Easy", "Which HTTP method is normally used to retrieve a resource without changing it?", "GET", ["POST", "PATCH", "DELETE"], "GET is defined for safe resource retrieval."),
        _template("api-status", "Medium", "Which status code best represents successful creation of a resource?", "201 Created", ["204 Unauthorized", "404 Created", "500 Accepted"], "201 communicates that the request succeeded and a new resource was created."),
        _template("api-idempotent", "Medium", "What does it mean for an API operation to be idempotent?", "Repeating the same request has the same intended effect as sending it once", ["It never returns data", "It requires no authentication", "It always runs asynchronously"], "Idempotency makes retries safer by avoiding repeated side effects."),
        _template("api-auth", "Hard", "Where should authorization be enforced for a protected API resource?", "On the server for every relevant request and resource", ["Only by hiding the UI button", "Only in client-side JavaScript", "Only in documentation"], "The server is the trusted boundary and must verify both identity and resource-level permission."),
    ],
    "data": [
        _template("data-missing", "Easy", "Before filling missing numerical values, what should be checked first?", "Why values are missing and how the feature is distributed", ["Only the file extension", "The UI theme", "The row order alone"], "The missingness mechanism and distribution determine whether imputation is valid and which method fits."),
        _template("data-vector", "Medium", "Why prefer vectorized Pandas or NumPy operations over Python row loops when possible?", "They use optimized array operations and are usually faster", ["They guarantee perfect data", "They remove all memory use", "They make testing unnecessary"], "Vectorized operations shift work to optimized native implementations."),
        _template("data-duplicate", "Medium", "What is the safest response to duplicate records in a dataset?", "Define the business identity rule before deduplicating", ["Delete every repeated value", "Keep only random rows", "Convert all columns to text"], "Duplicate handling requires a domain-aware key so valid repeated events are not destroyed."),
        _template("data-pipeline", "Hard", "How should preprocessing be applied during model validation?", "Fit preprocessing on each training fold and apply it to that fold's validation data", ["Fit once on the entire dataset before splitting", "Skip preprocessing in validation", "Use the test labels to choose transformations"], "Fold-local fitting prevents validation information from leaking into training transformations."),
    ],
    "deep learning": [
        _template("dl-loss", "Easy", "What does a loss function provide during neural-network training?", "A differentiable measure of prediction error to optimize", ["A database index", "A deployment hostname", "A guarantee of fairness"], "The optimizer uses loss gradients to update model parameters."),
        _template("dl-dropout", "Medium", "Why is dropout used during training?", "It randomly disables activations to reduce co-adaptation and overfitting", ["It adds labels", "It increases image resolution", "It encrypts weights"], "Randomly dropping units acts as regularization and encourages more robust representations."),
        _template("dl-learning-rate", "Medium", "What can happen when the learning rate is much too high?", "Training can oscillate or diverge instead of converging", ["Every gradient becomes exact", "The dataset becomes balanced", "Inference becomes deterministic"], "Oversized update steps can repeatedly overshoot useful minima."),
        _template("dl-eval", "Hard", "Why should evaluation disable training-specific behavior such as dropout?", "Inference should use the model's deterministic evaluation behavior", ["To delete learned weights", "To increase the batch labels", "To retrain on test data"], "Evaluation mode uses the inference definitions of layers such as dropout and batch normalization."),
    ],
    "programming": [
        _template("prog-hash", "Easy", "Which structure usually gives average constant-time key lookup?", "Hash map", ["Unsorted linked list", "Call stack", "Plain text file"], "A hash map uses a hash-derived bucket to locate keys in average O(1) time."),
        _template("prog-oop", "Medium", "What does encapsulation primarily achieve?", "It hides internal state behind a controlled public contract", ["It runs every method in parallel", "It removes all dependencies", "It guarantees no defects"], "Encapsulation limits how state can be accessed and changed."),
        _template("prog-stack", "Medium", "Which situation naturally uses a stack?", "Tracking nested function calls or matching brackets", ["Finding a key by hash", "Serving items in first-in-first-out order", "Storing one immutable number"], "Stacks model last-in-first-out nesting, including calls and paired delimiters."),
        _template("prog-complexity", "Hard", "What is the time complexity of binary search on a sorted array?", "O(log n)", ["O(1)", "O(n)", "O(n squared)"], "Each comparison discards half the remaining search range."),
    ],
}


FAMILY_MAP = {
    "Python": "python",
    "SQL": "sql", "PostgreSQL": "sql", "MySQL": "sql", "SQLite": "sql", "Oracle": "sql",
    "Machine Learning": "machine learning", "Random Forest": "machine learning", "Decision Tree": "machine learning",
    "XGBoost": "machine learning", "Scikit-learn": "machine learning", "Data Science": "machine learning", "Statistics": "machine learning",
    "React": "react",
    "REST": "web api", "REST API": "web api", "Flask": "web api", "Django": "web api", "FastAPI": "web api",
    "Node.js": "web api", "Express": "web api", "GraphQL": "web api", "Microservices": "web api",
    "Pandas": "data", "NumPy": "data", "Power BI": "data", "Tableau": "data",
    "Deep Learning": "deep learning", "TensorFlow": "deep learning", "Keras": "deep learning", "PyTorch": "deep learning",
    "Java": "programming", "C++": "programming", "C#": "programming", "JavaScript": "programming", "TypeScript": "programming",
}


def _sources(analysis):
    sources = []
    mentions = analysis.get("skillMentions", {})
    for skill in analysis.get("technicalSkills", []):
        sources.append({
            "category": "Technical Skills", "section": "Technical Skills", "item": skill,
            "skill": skill, "evidence": skill, "weight": 10 + int(mentions.get(skill, 1)),
        })
    for project in analysis.get("projects", []):
        for skill in project.get("technologies", []):
            sources.append({
                "category": "Projects", "section": "Projects", "item": project.get("name") or "Project",
                "skill": skill, "evidence": project.get("description", ""), "weight": 18 + int(mentions.get(skill, 1)),
            })
    for experience in analysis.get("professionalExperience", []):
        for skill in experience.get("technologies", []):
            sources.append({
                "category": "Professional Experience", "section": "Professional Experience",
                "item": experience.get("role") or experience.get("organization") or "Professional experience",
                "skill": skill, "evidence": experience.get("description", ""), "weight": 15 + int(mentions.get(skill, 1)),
            })
    return sources


def _category_allocation(sources):
    available = {source["category"] for source in sources}
    if available == {"Technical Skills", "Projects", "Professional Experience"}:
        return {"Technical Skills": 4, "Projects": 4, "Professional Experience": 2}
    if available == {"Technical Skills", "Projects"}:
        return {"Technical Skills": 5, "Projects": 5}
    if available == {"Technical Skills", "Professional Experience"}:
        return {"Technical Skills": 6, "Professional Experience": 4}
    if available == {"Projects", "Professional Experience"}:
        return {"Projects": 6, "Professional Experience": 4}
    if len(available) == 1:
        return {next(iter(available)): QUIZ_SIZE}
    ordered = [category for category in ("Technical Skills", "Projects", "Professional Experience") if category in available]
    if not ordered:
        return {}
    allocation = {category: QUIZ_SIZE // len(ordered) for category in ordered}
    for category in ordered[: QUIZ_SIZE - sum(allocation.values())]:
        allocation[category] += 1
    return allocation


def _candidate(source, template):
    topic = source["skill"]
    if source["category"] == "Projects":
        lead = f"Your resume connects {topic} with the {source['item']} project."
    elif source["category"] == "Professional Experience":
        lead = f"Your resume associates {topic} with your {source['item']} experience."
    else:
        lead = f"Your resume lists {topic}."
    question_uid = hashlib.sha256(
        f"{source['category']}|{source['item']}|{topic}|{template['id']}".encode("utf-8")
    ).hexdigest()[:24]
    options = [template["correct"], *template["distractors"]]
    RNG.shuffle(options)
    return {
        "question_uid": question_uid,
        "category": source["category"],
        "topic": topic,
        "difficulty": template["difficulty"],
        "question": f"{lead} {template['stem'].format(topic=topic)}",
        "options": options,
        "correct_answer": template["correct"],
        "explanation": template["explanation"],
        "resume_source": {
            "section": source["section"], "item": source["item"], "skill": topic,
            "evidence": source["evidence"],
        },
        "weight": source["weight"],
    }


def generate_questions(analysis, previous_question_uids=None):
    sources = _sources(analysis)
    allocation = _category_allocation(sources)
    if not allocation:
        raise ValueError(
            "No supported technical claims were detected. Add clear technical skills to the resume and try again."
        )
    previous = set(previous_question_uids or [])
    candidates = []
    for source in sources:
        family = FAMILY_MAP.get(source["skill"])
        templates = [*(PACKS.get(family, [])), *UNIVERSAL_TEMPLATES]
        candidates.extend(_candidate(source, template) for template in templates)

    selected = []
    used_uids = set()
    used_topics = Counter()
    difficulty_slots = [difficulty for difficulty, count in DIFFICULTY_MIX.items() for _ in range(count)]
    RNG.shuffle(difficulty_slots)

    for category, count in allocation.items():
        for _ in range(count):
            target_difficulty = difficulty_slots.pop()
            pool = [
                candidate for candidate in candidates
                if candidate["category"] == category
                and candidate["difficulty"] == target_difficulty
                and candidate["question_uid"] not in used_uids
            ]
            if not pool:
                pool = [
                    candidate for candidate in candidates
                    if candidate["category"] == category and candidate["question_uid"] not in used_uids
                ]
            if not pool:
                raise ValueError("The resume did not provide enough supported concepts to build ten questions.")
            chosen = max(
                pool,
                key=lambda candidate: (
                    25 if candidate["question_uid"] not in previous else 0,
                    -8 * used_topics[candidate["topic"]],
                    candidate["weight"],
                    RNG.random() * 15,
                ),
            )
            selected.append(chosen)
            used_uids.add(chosen["question_uid"])
            used_topics[chosen["topic"]] += 1

    RNG.shuffle(selected)
    return selected


def previous_question_uids(database, user_id, resume_id):
    rows = database.execute(
        """
        SELECT q.question_uid FROM resume_quiz_questions q
        JOIN resume_quiz_sessions s ON s.id=q.session_id
        WHERE s.user_id=? AND s.resume_id=? AND s.status='completed'
        ORDER BY s.created_at DESC LIMIT 50
        """,
        (user_id, resume_id),
    ).fetchall()
    return [row["question_uid"] for row in rows]


def create_quiz(database, user_id, resume_id, analysis):
    existing = database.execute(
        "SELECT * FROM resume_quiz_sessions WHERE user_id=? AND resume_id=? "
        "AND status IN ('ready','active') ORDER BY created_at DESC LIMIT 1",
        (user_id, resume_id),
    ).fetchone()
    if existing:
        return existing
    questions = generate_questions(analysis, previous_question_uids(database, user_id, resume_id))
    session_id = str(uuid.uuid4())
    now = iso_now()
    database.execute(
        """
        INSERT INTO resume_quiz_sessions (id,user_id,resume_id,status,total_questions,time_limit_seconds,created_at)
        VALUES (?,?,?,'ready',?,?,?)
        """,
        (session_id, user_id, resume_id, QUIZ_SIZE, QUIZ_TIMER_SECONDS, now),
    )
    for position, question in enumerate(questions, 1):
        database.execute(
            """
            INSERT INTO resume_quiz_questions (
                id,session_id,question_uid,position,category,topic,difficulty,question,
                options_json,correct_answer,explanation,resume_source_json
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                str(uuid.uuid4()), session_id, question["question_uid"], position,
                question["category"], question["topic"], question["difficulty"], question["question"],
                safe_json_dumps(question["options"]), question["correct_answer"], question["explanation"],
                safe_json_dumps(question["resume_source"]),
            ),
        )
    database.commit()
    return database.execute("SELECT * FROM resume_quiz_sessions WHERE id=?", (session_id,)).fetchone()


def _parse_datetime(value):
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def remaining_seconds(session_row):
    if session_row["status"] == "ready":
        return session_row["time_limit_seconds"]
    if session_row["status"] == "completed":
        return 0
    deadline = _parse_datetime(session_row["deadline_at"])
    return max(0, int((deadline - datetime.now(timezone.utc)).total_seconds())) if deadline else 0


def start_quiz(database, session_row):
    if session_row["status"] == "completed":
        raise ValueError("This Resume Quiz is already complete.")
    if session_row["status"] == "ready":
        now = datetime.now(timezone.utc)
        database.execute(
            "UPDATE resume_quiz_sessions SET status='active',started_at=?,deadline_at=? WHERE id=? AND status='ready'",
            (now.isoformat(), (now + timedelta(seconds=QUIZ_TIMER_SECONDS)).isoformat(), session_row["id"]),
        )
        database.commit()
    return database.execute("SELECT * FROM resume_quiz_sessions WHERE id=?", (session_row["id"],)).fetchone()


def public_questions(database, session_id):
    rows = database.execute(
        "SELECT * FROM resume_quiz_questions WHERE session_id=? ORDER BY position", (session_id,)
    ).fetchall()
    return [
        {
            "id": row["id"], "position": row["position"], "category": row["category"],
            "topic": row["topic"], "difficulty": row["difficulty"], "question": row["question"],
            "options": safe_json_loads(row["options_json"], []),
        }
        for row in rows
    ]


def saved_responses(database, session_id):
    rows = database.execute(
        "SELECT question_id,selected_answer,time_spent_seconds FROM resume_quiz_answers WHERE session_id=?",
        (session_id,),
    ).fetchall()
    return {
        row["question_id"]: {
            "selectedAnswer": row["selected_answer"], "timeSpent": row["time_spent_seconds"]
        }
        for row in rows if row["selected_answer"]
    }


def save_answer(database, session_row, question_id, selected_answer, time_spent=0):
    if session_row["status"] != "active":
        raise ValueError("This quiz is not accepting answers.")
    if remaining_seconds(session_row) <= 0:
        return False
    question = database.execute(
        "SELECT options_json FROM resume_quiz_questions WHERE id=? AND session_id=?",
        (question_id, session_row["id"]),
    ).fetchone()
    if not question:
        raise ValueError("Question not found in this quiz.")
    options = safe_json_loads(question["options_json"], [])
    if selected_answer not in options:
        raise ValueError("Select one of the four available options.")
    database.execute(
        """
        INSERT INTO resume_quiz_answers (session_id,question_id,selected_answer,time_spent_seconds,updated_at)
        VALUES (?,?,?,?,?)
        ON CONFLICT(session_id,question_id) DO UPDATE SET
            selected_answer=excluded.selected_answer,
            time_spent_seconds=MAX(resume_quiz_answers.time_spent_seconds,excluded.time_spent_seconds),
            updated_at=excluded.updated_at
        """,
        (session_row["id"], question_id, selected_answer, max(0, int(time_spent or 0)), iso_now()),
    )
    database.commit()
    return True


def _performance(rows, key):
    buckets = defaultdict(lambda: {"correct": 0, "total": 0})
    for row in rows:
        label = row[key]
        buckets[label]["total"] += 1
        buckets[label]["correct"] += int(row["is_correct"] or 0)
    return {
        label: {
            **values,
            "accuracy": round(values["correct"] / values["total"] * 100, 1) if values["total"] else 0,
        }
        for label, values in buckets.items()
    }


def _build_analytics(answer_rows, time_used):
    category_performance = _performance(answer_rows, "category")
    topic_performance = _performance(answer_rows, "topic")
    project_rows = []
    experience_rows = []
    risks = []
    for row in answer_rows:
        source = safe_json_loads(row["resume_source_json"], {})
        enriched = dict(row)
        enriched["source_item"] = source.get("item", row["topic"])
        if source.get("section") == "Projects":
            project_rows.append(enriched)
        if source.get("section") == "Professional Experience":
            experience_rows.append(enriched)
        if not row["is_correct"]:
            risks.append({
                "topic": row["topic"], "source": source,
                "message": f"Your resume lists {row['topic']} in {source.get('item', source.get('section', 'a professional claim'))}, but this concept needs review.",
                "recommendation": f"Review {row['topic']} fundamentals and the explanation for this question.",
            })
    strong = [topic for topic, values in topic_performance.items() if values["accuracy"] >= 70]
    weak = [topic for topic, values in topic_performance.items() if values["accuracy"] < 70]
    return {
        "categoryPerformance": category_performance,
        "technicalSkillsPerformance": topic_performance,
        "projectKnowledge": _performance(project_rows, "source_item") if project_rows else {},
        "experienceKnowledge": _performance(experience_rows, "topic") if experience_rows else {},
        "strongAreas": strong,
        "areasToImprove": weak,
        "riskAreas": risks[:8],
        "recommendedTopics": weak[:8],
        "averageTimePerQuestion": round(time_used / QUIZ_SIZE, 1),
    }


def submit_quiz(database, session_row, responses=None, time_spent=None, force_timeout=False):
    if session_row["status"] != "active":
        raise ValueError("This Resume Quiz has already been submitted.")
    responses = responses if isinstance(responses, dict) else {}
    time_spent = time_spent if isinstance(time_spent, dict) else {}
    timed_out = force_timeout or remaining_seconds(session_row) <= 0
    questions = database.execute(
        "SELECT * FROM resume_quiz_questions WHERE session_id=? ORDER BY position", (session_row["id"],)
    ).fetchall()
    stored = saved_responses(database, session_row["id"])
    started = _parse_datetime(session_row["started_at"]) or datetime.now(timezone.utc)
    elapsed = max(0, int((datetime.now(timezone.utc) - started).total_seconds()))
    time_used_seconds = min(QUIZ_TIMER_SECONDS, elapsed)

    correct = incorrect = unanswered = 0
    for question in questions:
        selected = responses.get(question["id"])
        if selected is None:
            selected = stored.get(question["id"], {}).get("selectedAnswer")
        options = safe_json_loads(question["options_json"], [])
        if selected not in options:
            selected = None
        is_correct = int(selected == question["correct_answer"]) if selected is not None else None
        correct += int(is_correct or 0)
        incorrect += int(is_correct == 0)
        unanswered += int(is_correct is None)
        question_time = max(
            int(time_spent.get(question["id"], 0) or 0),
            int(stored.get(question["id"], {}).get("timeSpent", 0) or 0),
        )
        database.execute(
            """
            INSERT INTO resume_quiz_answers (session_id,question_id,selected_answer,is_correct,time_spent_seconds,updated_at)
            VALUES (?,?,?,?,?,?)
            ON CONFLICT(session_id,question_id) DO UPDATE SET
                selected_answer=excluded.selected_answer,is_correct=excluded.is_correct,
                time_spent_seconds=MAX(resume_quiz_answers.time_spent_seconds,excluded.time_spent_seconds),
                updated_at=excluded.updated_at
            """,
            (session_row["id"], question["id"], selected, is_correct, question_time, iso_now()),
        )
    percentage = round(correct / QUIZ_SIZE * 100, 1)
    joined_rows = database.execute(
        """
        SELECT q.*,a.selected_answer,a.is_correct,a.time_spent_seconds
        FROM resume_quiz_questions q JOIN resume_quiz_answers a ON a.question_id=q.id AND a.session_id=q.session_id
        WHERE q.session_id=? ORDER BY q.position
        """,
        (session_row["id"],),
    ).fetchall()
    analytics = _build_analytics(joined_rows, time_used_seconds)
    submitted = iso_now()
    database.execute(
        """
        UPDATE resume_quiz_sessions SET status='completed',score=?,correct_answers=?,incorrect_answers=?,
            unanswered_questions=?,percentage=?,time_used_seconds=?,timed_out=?,analytics_json=?,submitted_at=?
        WHERE id=? AND status='active'
        """,
        (
            correct, correct, incorrect, unanswered, percentage, time_used_seconds,
            int(timed_out), safe_json_dumps(analytics), submitted, session_row["id"],
        ),
    )
    database.commit()
    return database.execute("SELECT * FROM resume_quiz_sessions WHERE id=?", (session_row["id"],)).fetchone()


def result_payload(database, session_row):
    rows = database.execute(
        """
        SELECT q.*,a.selected_answer,a.is_correct,a.time_spent_seconds
        FROM resume_quiz_questions q LEFT JOIN resume_quiz_answers a
          ON a.question_id=q.id AND a.session_id=q.session_id
        WHERE q.session_id=? ORDER BY q.position
        """,
        (session_row["id"],),
    ).fetchall()
    review = []
    for row in rows:
        source = safe_json_loads(row["resume_source_json"], {})
        review.append({
            "questionId": row["id"], "position": row["position"], "category": row["category"],
            "topic": row["topic"], "difficulty": row["difficulty"], "question": row["question"],
            "options": safe_json_loads(row["options_json"], []), "correctAnswer": row["correct_answer"],
            "selectedAnswer": row["selected_answer"], "isCorrect": bool(row["is_correct"]),
            "status": "Not Answered" if row["selected_answer"] is None else ("Correct" if row["is_correct"] else "Incorrect"),
            "explanation": row["explanation"], "resumeSource": source,
            "timeSpent": row["time_spent_seconds"] or 0,
        })
    analytics = safe_json_loads(session_row["analytics_json"], {})
    readiness = session_row["percentage"]
    label = "Excellent Preparation" if readiness >= 90 else "Strong Preparation" if readiness >= 75 else "Moderate Preparation" if readiness >= 60 else "Needs More Review"
    return {
        "sessionId": session_row["id"], "resumeId": session_row["resume_id"],
        "score": session_row["score"], "totalQuestions": QUIZ_SIZE, "percentage": session_row["percentage"],
        "correctAnswers": session_row["correct_answers"], "incorrectAnswers": session_row["incorrect_answers"],
        "unansweredQuestions": session_row["unanswered_questions"],
        "questionsAttempted": QUIZ_SIZE - session_row["unanswered_questions"],
        "timeUsedSeconds": session_row["time_used_seconds"], "timeLimitSeconds": QUIZ_TIMER_SECONDS,
        "timedOut": bool(session_row["timed_out"]), "submittedAt": session_row["submitted_at"],
        "readiness": {"score": readiness, "label": label}, "analytics": analytics, "review": review,
    }


def history_summary(rows):
    completed = [row for row in rows if row["status"] == "completed"]
    history = [
        {
            "sessionId": row["id"], "resumeId": row["resume_id"], "score": row["score"],
            "percentage": row["percentage"], "timeUsedSeconds": row["time_used_seconds"],
            "timedOut": bool(row["timed_out"]), "date": row["submitted_at"] or row["created_at"],
        }
        for row in completed
    ]
    return {
        "attempts": len(completed),
        "highestScore": max((row["percentage"] for row in completed), default=0),
        "averageScore": round(sum(row["percentage"] for row in completed) / len(completed), 1) if completed else 0,
        "history": history,
        "trend": [
            {"label": f"Attempt {index + 1}", "score": row["percentage"]}
            for index, row in enumerate(reversed(completed))
        ],
    }
