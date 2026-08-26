"""Rebuild the SQLite aptitude question bank with 300 validated MCQs."""

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from interview_simulator import create_app
from interview_simulator.db import get_db
from interview_simulator.services.aptitude import ensure_aptitude_question_bank


def main():
    app = create_app()
    with app.app_context():
        database = get_db()
        total = ensure_aptitude_question_bank(database, force=True)
        company_counts = database.execute(
            "SELECT company, COUNT(*) AS total FROM aptitude_questions GROUP BY company ORDER BY company"
        ).fetchall()

    print(f"Seeded {total} aptitude questions.")
    for row in company_counts:
        print(f"- {row['company']}: {row['total']}")


if __name__ == "__main__":
    main()
