"""Rebuild and validate the 1,000-question adaptive interview bank."""

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from interview_simulator import create_app
from interview_simulator.db import get_db
from interview_simulator.services.interview_delivery import ensure_interview_question_bank


def main():
    app = create_app()
    with app.app_context():
        database = get_db()
        total = ensure_interview_question_bank(database, force=True)
        category_counts = database.execute(
            """
            SELECT bank_category, COUNT(*) AS total
            FROM interview_questions
            GROUP BY bank_category
            ORDER BY bank_category
            """
        ).fetchall()

    print(f"Seeded {total} interview questions.")
    for row in category_counts:
        print(f"- {row['bank_category']}: {row['total']}")


if __name__ == "__main__":
    main()
