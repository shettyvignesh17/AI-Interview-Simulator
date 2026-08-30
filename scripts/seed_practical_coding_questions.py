"""Reseed and validate the Practical Coding portion of Interview Learning."""

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from interview_simulator import create_app
from interview_simulator.db import get_db
from interview_simulator.services.learning import ensure_learning_catalog
from interview_simulator.utils.common import safe_json_loads


def main():
    app = create_app()
    with app.app_context():
        database = get_db()
        ensure_learning_catalog(database, force=True)
        rows = database.execute(
            "SELECT id, difficulty, solutions_json FROM learning_questions "
            "WHERE category='Practical Coding' ORDER BY id"
        ).fetchall()
        difficulty = {
            level: sum(row["difficulty"] == level for row in rows)
            for level in ("Easy", "Medium", "Hard")
        }
        required_languages = {"python", "java", "cpp", "javascript"}
        incomplete = [
            row["id"] for row in rows
            if set(safe_json_loads(row["solutions_json"], {})) != required_languages
        ]
        if len(rows) != 200 or difficulty != {"Easy": 70, "Medium": 90, "Hard": 40} or incomplete:
            raise RuntimeError(
                f"Practical catalog validation failed: total={len(rows)}, "
                f"difficulty={difficulty}, incomplete={incomplete[:5]}"
            )
        print("Practical Coding catalog ready: 200 questions (70 Easy, 90 Medium, 40 Hard).")


if __name__ == "__main__":
    main()
