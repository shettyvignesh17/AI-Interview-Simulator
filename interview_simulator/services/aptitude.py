import math
import random
import uuid
from collections import defaultdict
from fractions import Fraction

from interview_simulator.utils.common import iso_now, safe_json_dumps, safe_json_loads


COMPANIES = ["NVIDIA", "Apple", "Alphabet (Google)", "Microsoft", "Amazon", "Walmart"]
CATEGORIES = [
    "Quantitative Aptitude",
    "Logical Reasoning",
    "Analytical Reasoning",
    "Verbal Ability",
    "Data Interpretation",
    "Probability",
    "Time & Work",
    "Time, Speed & Distance",
    "Profit & Loss",
    "Percentages",
    "Ratios",
    "Number Systems",
    "Coding-Decoding",
    "Blood Relations",
    "Seating Arrangement",
    "Puzzles",
    "Series Completion",
    "Syllogisms",
    "Clocks",
    "Calendars",
    "Permutation & Combination",
    "Basic Mathematics",
    "Graph Interpretation",
    "Critical Thinking",
]
DIFFICULTY_PATTERN = ["Easy", "Medium", "Easy", "Hard", "Medium"]
QUIZ_SIZE = 10
QUIZ_TIMER_SECONDS = 12 * 60
PASS_PERCENTAGE = 60.0


def _unique_options(answer, candidates):
    answer_text = str(answer)
    options = [answer_text]
    fallback_candidates = ["Cannot be determined", "None of these", "Insufficient information"]
    for candidate in [*candidates, *fallback_candidates]:
        candidate_text = str(candidate)
        if candidate_text not in options:
            options.append(candidate_text)
        if len(options) == 4:
            break
    return options


def _numeric_options(answer, step=1, suffix=""):
    values = [answer, answer + step, max(0, answer - step), answer + (2 * step), max(0, answer - (2 * step))]
    return _unique_options(f"{answer}{suffix}", [f"{value}{suffix}" for value in values[1:]])


def _shift_word(word, shift):
    return "".join(chr((ord(character) - 65 + shift) % 26 + 65) for character in word.upper())


def _fraction_text(numerator, denominator):
    value = Fraction(numerator, denominator)
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def _build_question(company, company_index, slot):
    category = CATEGORIES[slot % len(CATEGORIES)]
    variant = slot // len(CATEGORIES)
    seed = ((company_index + 1) * 10_000) + slot
    rng = random.Random(seed)
    context = f"In {company} aptitude practice set {slot + 1}"

    if category == "Quantitative Aptitude":
        start = 12 + company_index * 3 + variant * 5
        numbers = [start + offset for offset in range(5)]
        answer = start + 2
        question = f"{context}, find the average of {', '.join(map(str, numbers))}."
        options = _numeric_options(answer, 2)
        explanation = f"The sum is {sum(numbers)}; dividing by 5 gives {answer}."
    elif category == "Logical Reasoning":
        question = (
            f"{context}, consider: All secure devices are tested. Some tested devices are portable. "
            "Which conclusion must be true?"
        )
        answer = "All secure devices are tested"
        options = [answer, "All portable devices are secure", "No tested device is portable", "Some secure devices are portable"]
        explanation = "Only the first statement is guaranteed directly by the premise; the overlap with portable devices is unknown."
    elif category == "Analytical Reasoning":
        people = ["Asha", "Bina", "Charan", "Dev", "Esha"]
        shift = (company_index + variant) % len(people)
        order = people[shift:] + people[:shift]
        answer = order[2]
        question = (
            f"{context}, five candidates rank from highest to lowest as {', '.join(order)}. "
            "Who is ranked third?"
        )
        options = _unique_options(answer, order)
        explanation = f"The third name in the stated order is {answer}."
    elif category == "Verbal Ability":
        words = [
            ("concise", "brief", ["uncertain", "lengthy", "indirect"]),
            ("diligent", "hardworking", ["careless", "silent", "temporary"]),
            ("prudent", "wise", ["reckless", "noisy", "ordinary"]),
        ]
        word, answer, distractors = words[(company_index + variant) % len(words)]
        question = f"{context}, choose the word closest in meaning to '{word}'."
        options = [answer, *distractors]
        explanation = f"'{answer}' is the closest synonym of '{word}'."
    elif category == "Data Interpretation":
        first = 80 + company_index * 10 + variant * 20
        second = int(first * 1.25)
        answer = "25%"
        question = (
            f"{context}, a chart shows {first} completed tasks in Quarter 1 and {second} in Quarter 2. "
            "What is the percentage increase?"
        )
        options = [answer, "20%", "30%", "45%"]
        explanation = f"The increase is {second - first}; ({second - first}/{first}) x 100 = 25%."
    elif category == "Probability":
        red = 3 + company_index + variant
        blue = red + 2
        answer = _fraction_text(red, red + blue)
        question = (
            f"{context}, a bag contains {red} red and {blue} blue tokens. "
            "What is the probability of drawing a red token once?"
        )
        options = _unique_options(answer, [_fraction_text(blue, red + blue), "1/2", _fraction_text(red, blue)])
        explanation = f"Favourable outcomes are {red} out of {red + blue}, which simplifies to {answer}."
    elif category == "Time & Work":
        scale = 4 + company_index + variant
        a_days = 2 * scale
        b_days = 3 * scale
        answer = f"{_fraction_text(a_days * b_days, a_days + b_days)} days"
        question = (
            f"{context}, worker A completes a task in {a_days} days and worker B in {b_days} days. "
            "How long will they take together?"
        )
        options = _unique_options(answer, [f"{scale} days", f"{2 * scale} days", f"{3 * scale} days"])
        explanation = f"Their combined rate is 1/{a_days} + 1/{b_days}; its reciprocal is {answer}."
    elif category == "Time, Speed & Distance":
        speed = 40 + company_index * 5 + variant * 10
        hours = 2 + (company_index + variant) % 3
        distance = speed * hours
        answer = f"{hours} hours"
        question = f"{context}, a vehicle covers {distance} km at {speed} km/h. How much time does it take?"
        options = _unique_options(answer, [f"{hours + 1} hours", f"{max(1, hours - 1)} hours", f"{hours + 2} hours"])
        explanation = f"Time = distance / speed = {distance}/{speed} = {hours} hours."
    elif category == "Profit & Loss":
        cost = 400 + company_index * 100 + variant * 200
        rate = 20
        selling = int(cost * 1.2)
        answer = f"Rs. {selling}"
        question = f"{context}, an item costing Rs. {cost} is sold at a {rate}% profit. Find the selling price."
        options = _unique_options(answer, [f"Rs. {cost + 40}", f"Rs. {cost + 100}", f"Rs. {int(cost * 0.8)}"])
        explanation = f"Selling price = {cost} x 1.20 = Rs. {selling}."
    elif category == "Percentages":
        percent = [15, 20, 25][(company_index + variant) % 3]
        number = 200 + company_index * 40 + variant * 80
        answer = int(number * percent / 100)
        question = f"{context}, what is {percent}% of {number}?"
        options = _numeric_options(answer, max(5, number // 20))
        explanation = f"{percent}/100 x {number} = {answer}."
    elif category == "Ratios":
        left = 2 + (company_index % 3)
        right = left + 3
        unit = 10 + variant * 5
        total = (left + right) * unit
        answer = left * unit
        question = (
            f"{context}, two teams share {total} tasks in the ratio {left}:{right}. "
            "How many tasks does the first team receive?"
        )
        options = _numeric_options(answer, unit)
        explanation = f"The first share is {left}/{left + right} x {total} = {answer}."
    elif category == "Number Systems":
        divisor = 5 + company_index
        quotient = 7 + variant
        remainder = 2 + (company_index % 3)
        number = divisor * quotient + remainder
        answer = remainder
        question = f"{context}, what is the remainder when {number} is divided by {divisor}?"
        options = _unique_options(answer, [0, 1, remainder + 1, divisor - 1])
        explanation = f"{number} = {divisor} x {quotient} + {remainder}, so the remainder is {remainder}."
    elif category == "Coding-Decoding":
        words = ["LOGIC", "TRAIN", "SMART", "FOCUS", "CLEAR", "QUICK"]
        word = words[company_index]
        shift = 1 + variant
        answer = _shift_word(word, shift)
        question = (
            f"{context}, each letter is shifted {shift} place{'s' if shift > 1 else ''} forward in the alphabet. "
            f"How is {word} encoded?"
        )
        options = _unique_options(answer, [_shift_word(word, shift + 1), _shift_word(word, -shift), word[::-1]])
        explanation = f"Moving every letter forward by {shift} produces {answer}."
    elif category == "Blood Relations":
        names = [("Maya", "Ravi", "Tara"), ("Neha", "Kiran", "Isha"), ("Lina", "Arun", "Sara")]
        daughter, father, sister = names[(company_index + variant) % len(names)]
        question = (
            f"{context}, {daughter} is the daughter of {father}, and {sister} is {father}'s sister. "
            f"How is {sister} related to {daughter}?"
        )
        answer = "Aunt"
        options = [answer, "Mother", "Sister", "Cousin"]
        explanation = f"{sister} is the sister of {daughter}'s father, so she is {daughter}'s aunt."
    elif category == "Seating Arrangement":
        labels = ["P", "Q", "R", "S", "T"]
        rotation = (company_index + variant) % len(labels)
        order = labels[rotation:] + labels[:rotation]
        answer = order[2]
        question = (
            f"{context}, five people sit in a row facing north in this left-to-right order: "
            f"{', '.join(order)}. Who sits in the middle?"
        )
        options = _unique_options(answer, order)
        explanation = f"With five seats, the third position is the middle, occupied by {answer}."
    elif category == "Puzzles":
        labels = ["Red only", "Blue only", "Mixed"]
        question = (
            f"{context}, three boxes are labelled Red only, Blue only, and Mixed, but every label is wrong. "
            "From which box should one token be drawn first to identify all boxes?"
        )
        answer = "The box labelled Mixed"
        options = [answer, "The box labelled Red only", "The box labelled Blue only", "Any box gives equal information"]
        explanation = "Because every label is wrong, the box labelled Mixed contains only one colour; one draw identifies it and the other labels follow."
    elif category == "Series Completion":
        start = 3 + company_index + variant
        step = 3 + variant
        series = [start + step * index for index in range(5)]
        answer = series[-1] + step
        question = f"{context}, complete the series: {', '.join(map(str, series))}, __."
        options = _numeric_options(answer, step)
        explanation = f"Each term increases by {step}, so the next term is {answer}."
    elif category == "Syllogisms":
        question = (
            f"{context}, statements say: All analysts are readers. No reader is careless. "
            "Which conclusion necessarily follows?"
        )
        answer = "No analyst is careless"
        options = [answer, "All readers are analysts", "Some careless people are analysts", "No analyst is a reader"]
        explanation = "Analysts are a subset of readers, and readers exclude careless people; therefore analysts cannot be careless."
    elif category == "Clocks":
        hour = 2 + (company_index + variant) % 5
        minute = 30
        angle = abs((30 * hour + 0.5 * minute) - (6 * minute))
        answer = f"{int(min(angle, 360 - angle))} degrees"
        question = f"{context}, what is the smaller angle between the clock hands at {hour}:30?"
        options = _unique_options(answer, ["45 degrees", "75 degrees", "90 degrees", "105 degrees", "135 degrees"])
        explanation = f"The hour hand is at {30 * hour + 15} degrees and the minute hand at 180 degrees; the smaller angle is {answer}."
    elif category == "Calendars":
        days = 45 + company_index * 7 + variant * 3
        weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        start_index = (company_index + variant) % 7
        answer = weekdays[(start_index + days) % 7]
        question = f"{context}, if today is {weekdays[start_index]}, what day will it be after {days} days?"
        options = _unique_options(answer, [weekdays[(start_index + offset) % 7] for offset in (1, 2, 3, 4, 5, 6)])
        explanation = f"{days} leaves remainder {days % 7} when divided by 7, so the day is {answer}."
    elif category == "Permutation & Combination":
        total = 6 + company_index + variant
        chosen = 2 + (variant % 2)
        answer = math.comb(total, chosen)
        question = f"{context}, in how many ways can {chosen} people be chosen from a group of {total}?"
        options = _numeric_options(answer, max(2, total))
        explanation = f"Use combinations: C({total},{chosen}) = {answer}."
    elif category == "Basic Mathematics":
        coefficient = 3 + (company_index % 4)
        x_value = 5 + variant + company_index
        constant = 4 + company_index
        result = coefficient * x_value + constant
        answer = x_value
        question = f"{context}, solve for x: {coefficient}x + {constant} = {result}."
        options = _numeric_options(answer, 2)
        explanation = f"Subtract {constant}, then divide by {coefficient}: x = {x_value}."
    elif category == "Graph Interpretation":
        monday = 120 + company_index * 15 + variant * 20
        tuesday = monday + 35 + company_index * 5
        answer = tuesday - monday
        question = (
            f"{context}, a bar graph records {monday} requests on Monday and {tuesday} on Tuesday. "
            "How many more requests were recorded on Tuesday?"
        )
        options = _numeric_options(answer, 10)
        explanation = f"Subtract the bars: {tuesday} - {monday} = {answer}."
    else:
        question = (
            f"{context}, a team claims a new process reduces errors. Which evidence would best support the claim?"
        )
        answer = "A controlled comparison showing a consistent error reduction"
        options = [
            answer,
            "One employee's positive opinion",
            "A description of how modern the process looks",
            "The number of meetings held about the process",
        ]
        explanation = "A controlled comparison directly measures whether the process caused a repeatable reduction in errors."

    rng.shuffle(options)
    return {
        "id": company_index * 50 + slot + 1,
        "company": company,
        "category": category,
        "question": question,
        "options": options,
        "answer": str(answer),
        "difficulty": DIFFICULTY_PATTERN[slot % len(DIFFICULTY_PATTERN)],
        "explanation": explanation,
    }


def generate_aptitude_questions():
    questions = [
        _build_question(company, company_index, slot)
        for company_index, company in enumerate(COMPANIES)
        for slot in range(50)
    ]
    if len(questions) != 300 or len({item["question"] for item in questions}) != 300:
        raise RuntimeError("Aptitude generator must produce exactly 300 unique questions.")
    for item in questions:
        if len(item["options"]) != 4 or item["answer"] not in item["options"]:
            raise RuntimeError(f"Invalid options for aptitude question {item['id']}.")
    return questions


def ensure_aptitude_question_bank(database, force=False):
    current_count = database.execute("SELECT COUNT(*) FROM aptitude_questions").fetchone()[0]
    if current_count == 300 and not force:
        return current_count

    questions = generate_aptitude_questions()
    if force or current_count:
        database.execute("DELETE FROM aptitude_questions")
    database.executemany(
        """
        INSERT INTO aptitude_questions (
            id, company, category, question, options_json, answer, explanation, difficulty
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                item["id"], item["company"], item["category"], item["question"],
                safe_json_dumps(item["options"]), item["answer"], item["explanation"], item["difficulty"],
            )
            for item in questions
        ],
    )
    database.commit()
    return len(questions)


def _shuffle_question(row, randomizer):
    options = safe_json_loads(row["options_json"], [])
    randomizer.shuffle(options)
    return {
        "id": row["id"],
        "company": row["company"],
        "category": row["category"],
        "question": row["question"],
        "options": options,
        "answer": row["answer"],
        "explanation": row["explanation"],
        "difficulty": row["difficulty"],
    }


def _previous_question_ids(database, user_id):
    rows = database.execute(
        "SELECT questions_json FROM aptitude_attempts WHERE user_id = ?", (user_id,)
    ).fetchall()
    return {
        int(question["id"])
        for row in rows
        for question in safe_json_loads(row["questions_json"], [])
        if question.get("id") is not None
    }


def _select_questions(database, user_id):
    randomizer = random.SystemRandom()
    rows = database.execute("SELECT * FROM aptitude_questions").fetchall()
    seen_ids = _previous_question_ids(database, user_id)
    companies = COMPANIES[:]
    randomizer.shuffle(companies)
    company_slots = [company for company in companies for _ in range(2 if company in companies[:4] else 1)]
    randomizer.shuffle(company_slots)
    difficulty_slots = ["Easy"] * 4 + ["Medium"] * 4 + ["Hard"] * 2
    randomizer.shuffle(difficulty_slots)
    selected = []

    for company, difficulty in zip(company_slots, difficulty_slots):
        candidates = [
            row for row in rows
            if row["company"] == company
            and row["difficulty"] == difficulty
            and row["id"] not in seen_ids
            and row["id"] not in {item["id"] for item in selected}
        ]
        if not candidates:
            candidates = [
                row for row in rows
                if row["company"] == company
                and row["difficulty"] == difficulty
                and row["id"] not in {item["id"] for item in selected}
            ]
        if not candidates:
            candidates = [
                row for row in rows
                if row["company"] == company and row["id"] not in {item["id"] for item in selected}
            ]
        chosen = randomizer.choice(candidates)
        selected.append(_shuffle_question(chosen, randomizer))

    randomizer.shuffle(selected)
    return selected


def start_quiz(database, user_id):
    database.execute(
        "UPDATE aptitude_attempts SET status = 'abandoned' WHERE user_id = ? AND status = 'active'",
        (user_id,),
    )
    attempt_id = str(uuid.uuid4())
    questions = _select_questions(database, user_id)
    database.execute(
        """
        INSERT INTO aptitude_attempts (
            id, user_id, status, questions_json, responses_json, score, total_questions,
            percentage, company_performance_json, category_performance_json, created_at
        ) VALUES (?, ?, 'active', ?, '{}', 0, ?, 0, '{}', '{}', ?)
        """,
        (attempt_id, user_id, safe_json_dumps(questions), QUIZ_SIZE, iso_now()),
    )
    database.commit()
    return database.execute("SELECT * FROM aptitude_attempts WHERE id = ?", (attempt_id,)).fetchone()


def public_attempt(row):
    questions = safe_json_loads(row["questions_json"], [])
    return {
        "id": row["id"],
        "status": row["status"],
        "createdAt": row["created_at"],
        "questions": [
            {key: value for key, value in question.items() if key not in {"answer", "explanation"}}
            for question in questions
        ],
    }


def _performance_entry(performance, key, correct):
    entry = performance[key]
    entry["total"] += 1
    entry["correct"] += int(correct)


def submit_quiz(database, row, responses):
    questions = safe_json_loads(row["questions_json"], [])
    normalized = {str(key): str(value) for key, value in (responses or {}).items()}
    company_performance = defaultdict(lambda: {"correct": 0, "total": 0})
    category_performance = defaultdict(lambda: {"correct": 0, "total": 0})
    review = []
    score = 0

    for index, question in enumerate(questions, start=1):
        selected = normalized.get(str(question["id"]), "")
        correct = selected == question["answer"]
        score += int(correct)
        _performance_entry(company_performance, question["company"], correct)
        _performance_entry(category_performance, question["category"], correct)
        review.append(
            {
                "number": index,
                "id": question["id"],
                "company": question["company"],
                "category": question["category"],
                "difficulty": question["difficulty"],
                "question": question["question"],
                "options": question["options"],
                "yourAnswer": selected or "Not answered",
                "correctAnswer": question["answer"],
                "correct": correct,
                "explanation": question["explanation"],
            }
        )

    percentage = round((score / len(questions)) * 100, 1) if questions else 0.0
    completed_at = iso_now()
    database.execute(
        """
        UPDATE aptitude_attempts
        SET status = 'completed', responses_json = ?, score = ?, percentage = ?,
            company_performance_json = ?, category_performance_json = ?, completed_at = ?
        WHERE id = ?
        """,
        (
            safe_json_dumps(normalized), score, percentage,
            safe_json_dumps(company_performance), safe_json_dumps(category_performance),
            completed_at, row["id"],
        ),
    )
    database.commit()
    return {
        "attemptId": row["id"],
        "score": score,
        "totalQuestions": len(questions),
        "correctAnswers": score,
        "wrongAnswers": len(questions) - score,
        "percentage": percentage,
        "passed": percentage >= PASS_PERCENTAGE,
        "companyPerformance": dict(company_performance),
        "categoryPerformance": dict(category_performance),
        "review": review,
        "completedAt": completed_at,
    }


def summarize_history(rows):
    completed = [row for row in rows if row["status"] == "completed"]
    total_attempts = len(completed)
    total_correct = sum(row["score"] for row in completed)
    total_questions = sum(row["total_questions"] for row in completed)
    company_totals = defaultdict(lambda: {"correct": 0, "total": 0})
    category_totals = defaultdict(lambda: {"correct": 0, "total": 0})

    for row in completed:
        for company, values in safe_json_loads(row["company_performance_json"], {}).items():
            company_totals[company]["correct"] += values["correct"]
            company_totals[company]["total"] += values["total"]
        for category, values in safe_json_loads(row["category_performance_json"], {}).items():
            category_totals[category]["correct"] += values["correct"]
            category_totals[category]["total"] += values["total"]

    def with_accuracy(values):
        return {**values, "accuracy": round(values["correct"] / values["total"] * 100, 1) if values["total"] else 0.0}

    category_accuracy = {key: with_accuracy(value) for key, value in category_totals.items()}
    ranked_categories = sorted(category_accuracy.items(), key=lambda item: (-item[1]["accuracy"], item[0]))
    history = [
        {
            "id": row["id"],
            "date": row["completed_at"] or row["created_at"],
            "score": row["score"],
            "totalQuestions": row["total_questions"],
            "percentage": row["percentage"],
            "passed": row["percentage"] >= PASS_PERCENTAGE,
            "companyPerformance": safe_json_loads(row["company_performance_json"], {}),
        }
        for row in completed
    ]
    return {
        "attempts": total_attempts,
        "highestScore": max((row["score"] for row in completed), default=0),
        "averageScore": round(total_correct / total_attempts, 1) if total_attempts else 0.0,
        "accuracy": round(total_correct / total_questions * 100, 1) if total_questions else 0.0,
        "companyAccuracy": {key: with_accuracy(value) for key, value in company_totals.items()},
        "strongCategories": [key for key, _value in ranked_categories[:3]],
        "weakCategories": [key for key, _value in sorted(ranked_categories, key=lambda item: (item[1]["accuracy"], item[0]))[:3]],
        "history": history,
    }
