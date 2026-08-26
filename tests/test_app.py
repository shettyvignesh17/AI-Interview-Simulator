import io
import tempfile
import unittest
import zipfile
from collections import Counter
from pathlib import Path
from unittest.mock import patch

from interview_simulator import create_app
from interview_simulator.db import get_db
from interview_simulator.services.ai_interviewer import generate_adaptive_follow_up
from interview_simulator.services.interview_delivery import _adaptive_transition
from interview_simulator.utils.common import safe_json_loads


class InterviewSimulatorFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        temp_path = Path(self.temp_dir.name)
        self.app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test-secret",
                "DATA_DIR": temp_path / "data",
                "UPLOAD_DIR": temp_path / "uploads",
                "DATABASE": temp_path / "data" / "test.db",
                "MAX_QUESTIONS_PER_SESSION": 5,
                "QUESTION_TIME_LIMIT": 120,
                "AI_PROVIDER": "offline",
                "OPENAI_API_KEY": "",
            }
        )
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    @staticmethod
    def make_docx(text):
        document = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            '<w:body>'
            + "".join(
                f"<w:p><w:r><w:t>{line}</w:t></w:r></w:p>" for line in text.splitlines()
            )
            + "</w:body></w:document>"
        )
        output = io.BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr("word/document.xml", document)
        output.seek(0)
        return output

    def test_auth_resume_interview_and_dashboard_flow(self):
        home_response = self.client.get("/")
        self.assertEqual(home_response.status_code, 200)
        self.assertIn("Interview Simulator", home_response.get_data(as_text=True))
        self.assertNotIn("Interview Length", home_response.get_data(as_text=True))
        self.assertIn("Speak Answer", home_response.get_data(as_text=True))

        dashboard_page_response = self.client.get("/dashboard")
        self.assertEqual(dashboard_page_response.status_code, 200)
        self.assertIn("Interview Analytics", dashboard_page_response.get_data(as_text=True))

        signup_response = self.client.post(
            "/api/auth/signup",
            json={
                "name": "Test User",
                "email": "test@example.com",
                "password": "secret123",
            },
        )
        self.assertEqual(signup_response.status_code, 201)

        resume_response = self.client.post(
            "/api/resume",
            data={
                "resume": (
                    io.BytesIO(
                        b"""
                        Skills
                        Python
                        Flask
                        SQL

                        Projects
                        Built an interview analytics platform using Flask and SQLite.

                        Experience
                        Led a small engineering team and improved release quality by 25 percent.
                        """
                    ),
                    "resume.txt",
                )
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(resume_response.status_code, 201)
        resume_payload = resume_response.get_json()
        self.assertIn("Python", resume_payload["resume"]["skills"])

        start_response = self.client.post(
            "/api/interview/start",
            json={
                "roundType": "technical",
                "domain": "software_engineering",
                "difficulty": "intermediate",
                "resumeId": resume_payload["resume"]["id"],
            },
        )
        self.assertEqual(start_response.status_code, 200)
        session_payload = start_response.get_json()
        session_id = session_payload["session"]["id"]
        self.assertEqual(session_payload["session"]["status"], "active")
        self.assertEqual(session_payload["session"]["currentLevel"], "intermediate")
        self.assertIsNotNone(session_payload["session"]["currentQuestionId"])
        first_question_id = session_payload["session"]["currentQuestionId"]
        first_question_text = session_payload["session"]["currentQuestion"]
        self.assertNotIn("aptitude", first_question_id)

        def strong_answer(question_text):
            return (
                f"First, for {question_text.lower()} I would define the user impact and constraints. "
                "Then I would design the API, data model, caching strategy, monitoring plan, and test layers "
                "because latency, availability, and quality matter. In my Flask and SQLite interview analytics "
                "project, I improved response time by 30 percent, added stronger logging for root cause analysis, "
                "and documented the trade-offs clearly for the team. I would also verify the architecture, schema, "
                "query indexes, consistency, authentication contract, deployment automation, observability, and "
                "rollback plan before measuring scalability in production."
            )

        first_answer = self.client.post(
            "/api/interview/answer",
            json={
                "sessionId": session_id,
                "persistentQuestionIds": [first_question_id],
                "answer": strong_answer(first_question_text),
            },
        )
        self.assertEqual(first_answer.status_code, 200)
        self.assertFalse(first_answer.get_json()["evaluation"]["complete"])
        first_answer_payload = first_answer.get_json()
        self.assertGreaterEqual(first_answer_payload["evaluation"]["overallScore"], 70)
        self.assertEqual(first_answer_payload["evaluation"]["classification"], "strong")
        self.assertEqual(first_answer_payload["evaluation"]["adaptiveChange"], "none")
        self.assertEqual(first_answer_payload["session"]["currentLevel"], "intermediate")
        self.assertNotEqual(first_answer_payload["session"]["currentQuestionId"], first_question_id)
        self.assertTrue(first_answer_payload["session"]["isFollowUp"])
        self.assertEqual(first_answer_payload["session"]["followUpSource"], "contextual-rules")
        self.assertTrue(first_answer_payload["evaluation"]["followUp"]["generated"])

        second_answer = self.client.post(
            "/api/interview/answer",
            json={
                "sessionId": session_id,
                "persistentQuestionIds": [
                    first_question_id,
                    first_answer_payload["session"]["currentQuestionId"],
                ],
                "answer": strong_answer(first_answer_payload["session"]["currentQuestion"]),
            },
        )
        self.assertEqual(second_answer.status_code, 200)
        second_payload = second_answer.get_json()
        self.assertFalse(second_payload["evaluation"]["complete"])
        self.assertEqual(second_payload["evaluation"]["classification"], "strong")
        self.assertEqual(second_payload["evaluation"]["adaptiveChange"], "increased")
        self.assertFalse(second_payload["session"]["isFollowUp"])

        asked_ids = {first_question_id, first_answer_payload["session"]["currentQuestionId"]}
        final_payload = None
        current_session = second_payload["session"]
        for question_number in range(3, 6):
            asked_ids.add(current_session["currentQuestionId"])
            response = self.client.post(
                "/api/interview/answer",
                json={
                    "sessionId": session_id,
                    "persistentQuestionIds": list(asked_ids),
                    "answer": strong_answer(current_session["currentQuestion"]),
                    "durationSeconds": 50,
                },
            )
            self.assertEqual(response.status_code, 200)
            final_payload = response.get_json()
            self.assertEqual(final_payload["evaluation"]["questionNumber"], question_number)
            current_session = final_payload["session"]

        self.assertTrue(final_payload["evaluation"]["complete"])
        self.assertEqual(len(final_payload["report"]["answers"]), 5)
        self.assertEqual(len({answer["questionId"] for answer in final_payload["report"]["answers"]}), 5)
        self.assertEqual(final_payload["report"]["adaptive"]["startingDifficulty"], "medium")
        self.assertEqual(final_payload["report"]["adaptive"]["endingDifficulty"], "hard")

        dashboard_response = self.client.get("/api/dashboard")
        self.assertEqual(dashboard_response.status_code, 200)
        dashboard_payload = dashboard_response.get_json()
        self.assertEqual(dashboard_payload["summary"]["completedSessions"], 1)
        self.assertGreaterEqual(dashboard_payload["summary"]["overallAverage"], 1)

        history_response = self.client.get("/api/history")
        self.assertEqual(history_response.status_code, 200)
        history_payload = history_response.get_json()
        self.assertEqual(len(history_payload["sessions"]), 1)
        self.assertEqual(history_payload["sessions"][0]["status"], "completed")

        second_start_response = self.client.post(
            "/api/interview/start",
            json={
                "roundType": "technical",
                "domain": "software_engineering",
                "difficulty": "intermediate",
                "resumeId": resume_payload["resume"]["id"],
                "persistentQuestionIds": [first_question_id],
            },
        )
        self.assertEqual(second_start_response.status_code, 200)
        second_start_payload = second_start_response.get_json()
        self.assertNotEqual(
            second_start_payload["session"]["currentQuestionId"],
            first_question_id,
        )

    def test_aptitude_quiz_flow_and_rotation(self):
        page_response = self.client.get("/aptitude")
        self.assertEqual(page_response.status_code, 200)
        self.assertIn("Aptitude Quiz", page_response.get_data(as_text=True))
        self.assertEqual(self.client.get("/api/aptitude/summary").status_code, 401)

        signup_response = self.client.post(
            "/api/auth/signup",
            json={
                "name": "Aptitude User",
                "email": "aptitude@example.com",
                "password": "secret123",
            },
        )
        self.assertEqual(signup_response.status_code, 201)

        summary = self.client.get("/api/aptitude/summary").get_json()
        self.assertEqual(summary["questionBank"]["totalQuestions"], 300)
        self.assertEqual(set(summary["questionBank"]["companyCounts"].values()), {50})

        first_start = self.client.post("/api/aptitude/start", json={})
        self.assertEqual(first_start.status_code, 200)
        first_payload = first_start.get_json()
        first_questions = first_payload["attempt"]["questions"]
        first_ids = {question["id"] for question in first_questions}
        company_counts = Counter(question["company"] for question in first_questions)
        difficulty_counts = Counter(question["difficulty"] for question in first_questions)

        self.assertEqual(len(first_questions), 10)
        self.assertEqual(len(first_ids), 10)
        self.assertEqual(len(company_counts), 6)
        self.assertEqual(sorted(company_counts.values()), [1, 1, 2, 2, 2, 2])
        self.assertEqual(difficulty_counts, {"Easy": 4, "Medium": 4, "Hard": 2})
        self.assertTrue(all(len(question["options"]) == 4 for question in first_questions))
        self.assertTrue(all("answer" not in question for question in first_questions))
        self.assertTrue(all("explanation" not in question for question in first_questions))

        submit_response = self.client.post(
            "/api/aptitude/submit",
            json={"attemptId": first_payload["attempt"]["id"], "responses": {}},
        )
        self.assertEqual(submit_response.status_code, 200)
        result_payload = submit_response.get_json()
        self.assertEqual(result_payload["result"]["score"], 0)
        self.assertEqual(len(result_payload["result"]["review"]), 10)
        self.assertEqual(result_payload["stats"]["attempts"], 1)

        duplicate_submit = self.client.post(
            "/api/aptitude/submit",
            json={"attemptId": first_payload["attempt"]["id"], "responses": {}},
        )
        self.assertEqual(duplicate_submit.status_code, 400)

        second_payload = self.client.post("/api/aptitude/start", json={}).get_json()
        second_ids = {question["id"] for question in second_payload["attempt"]["questions"]}
        self.assertEqual(first_ids & second_ids, set())

    def test_active_session_exit_endpoints_discard_without_results(self):
        signup = self.client.post(
            "/api/auth/signup",
            json={"name": "Exit User", "email": "exit@example.com", "password": "secret123"},
        )
        self.assertEqual(signup.status_code, 201)

        interview = self.client.post(
            "/api/interview/start",
            json={
                "company": "General",
                "roundType": "technical",
                "domain": "software_engineering",
                "difficulty": "easy",
            },
        ).get_json()["session"]
        abandoned_interview = self.client.post(
            "/api/interview/abandon", json={"sessionId": interview["id"]}
        )
        self.assertEqual(abandoned_interview.status_code, 200)
        self.assertTrue(abandoned_interview.get_json()["abandoned"])
        late_answer = self.client.post(
            "/api/interview/answer",
            json={"sessionId": interview["id"], "answer": "A late answer must be ignored."},
        )
        self.assertEqual(late_answer.status_code, 400)
        self.assertEqual(self.client.get("/api/dashboard").get_json()["summary"]["completedSessions"], 0)

        aptitude = self.client.post("/api/aptitude/start", json={}).get_json()["attempt"]
        abandoned_aptitude = self.client.post(
            "/api/aptitude/abandon", json={"attemptId": aptitude["id"]}
        )
        self.assertEqual(abandoned_aptitude.status_code, 200)
        self.assertEqual(
            self.client.post(
                "/api/aptitude/submit",
                json={"attemptId": aptitude["id"], "responses": {}},
            ).status_code,
            400,
        )
        self.assertEqual(self.client.get("/api/aptitude/summary").get_json()["stats"]["attempts"], 0)

        resume_text = """TECHNICAL SKILLS
Python SQL Machine Learning React Pandas Docker Git
PROJECTS
Interview Simulator | Built with Python, React, SQL, and Machine Learning.
Analytics Platform | Built dashboards with Pandas and SQL.
PROFESSIONAL EXPERIENCE
Software Intern at Example Labs | Used Python and SQL to improve reporting.
"""
        upload = self.client.post(
            "/api/resume-quiz/resume",
            data={"resume": (self.make_docx(resume_text), "Exit_Resume.docx")},
            content_type="multipart/form-data",
        )
        self.assertEqual(upload.status_code, 201)
        resume_id = upload.get_json()["resume"]["id"]
        generated = self.client.post("/api/resume-quiz/generate", json={"resumeId": resume_id})
        self.assertEqual(generated.status_code, 201)
        resume_session_id = generated.get_json()["session"]["id"]
        started = self.client.post(
            "/api/resume-quiz/start", json={"sessionId": resume_session_id}
        )
        self.assertEqual(started.status_code, 200)
        discarded = self.client.delete(f"/api/resume-quiz/session/{resume_session_id}")
        self.assertEqual(discarded.status_code, 200)
        self.assertTrue(discarded.get_json()["discarded"])
        self.assertEqual(self.client.get(f"/api/resume-quiz/session/{resume_session_id}").status_code, 404)
        resume_summary = self.client.get("/api/resume-quiz/summary").get_json()
        self.assertEqual(resume_summary["latestResume"]["resume"]["id"], resume_id)
        self.assertIsNone(resume_summary["openSession"])
        self.assertEqual(resume_summary["stats"]["attempts"], 0)

        with self.app.app_context():
            database = get_db()
            interview_status = database.execute(
                "SELECT status FROM interview_sessions WHERE id=?", (interview["id"],)
            ).fetchone()["status"]
            aptitude_status = database.execute(
                "SELECT status FROM aptitude_attempts WHERE id=?", (aptitude["id"],)
            ).fetchone()["status"]
            resume_exists = database.execute(
                "SELECT COUNT(*) FROM resumes WHERE id=?", (resume_id,)
            ).fetchone()[0]
            self.assertEqual((interview_status, aptitude_status, resume_exists), ("abandoned", "abandoned", 1))

    def test_interview_learning_catalog_and_progress(self):
        learning_page = self.client.get("/learning")
        self.assertEqual(learning_page.status_code, 200)
        self.assertIn("Interview Learning", learning_page.get_data(as_text=True))
        self.assertEqual(self.client.get("/api/learning/overview").status_code, 401)

        signup_response = self.client.post(
            "/api/auth/signup",
            json={"name": "Learning User", "email": "learning@example.com", "password": "secret123"},
        )
        self.assertEqual(signup_response.status_code, 201)

        overview_response = self.client.get("/api/learning/overview")
        self.assertEqual(overview_response.status_code, 200)
        overview_payload = overview_response.get_json()
        overview = overview_payload["overview"]
        self.assertEqual(overview["totals"]["questions"], 1000)
        self.assertEqual(
            {key: value["total"] for key, value in overview["sections"].items()},
            {"aptitude": 300, "coding": 400, "interview": 300},
        )
        self.assertGreaterEqual(len(overview_payload["metadata"]["companies"]), 40)

        first_page = self.client.get("/api/learning/questions?type=coding&page=1").get_json()
        second_page = self.client.get("/api/learning/questions?type=coding&page=2").get_json()
        first_ids = {item["questionId"] for item in first_page["questions"]}
        second_ids = {item["questionId"] for item in second_page["questions"]}
        self.assertEqual(len(first_page["questions"]), 20)
        self.assertEqual(first_page["pagination"]["total"], 400)
        self.assertEqual(first_page["pagination"]["pageSize"], 20)
        self.assertEqual(first_ids & second_ids, set())

        question = first_page["questions"][0]
        self.assertTrue(question["answer"])
        self.assertTrue(question["detailedExplanation"])
        self.assertTrue(question["commonMistakes"])
        progress_response = self.client.patch(
            f"/api/learning/questions/{question['questionId']}/progress",
            json={
                "bookmarked": True,
                "studied": True,
                "revision": True,
                "confidence": "low",
                "notes": "Review the invariant and edge cases.",
                "viewed": True,
                "section": "coding",
            },
        )
        self.assertEqual(progress_response.status_code, 200)
        updated = progress_response.get_json()["question"]
        self.assertTrue(updated["bookmarked"])
        self.assertTrue(updated["studied"])
        self.assertTrue(updated["revision"])
        self.assertEqual(updated["confidence"], "low")
        self.assertEqual(updated["viewedCount"], 1)
        self.assertIn("edge cases", updated["notes"])

        bookmark_page = self.client.get("/api/learning/questions?status=bookmarked").get_json()
        self.assertEqual(bookmark_page["pagination"]["total"], 1)
        self.assertEqual(bookmark_page["questions"][0]["questionId"], question["questionId"])

        preference_response = self.client.patch(
            "/api/learning/preferences",
            json={"dailyGoal": 20, "targetCompanies": ["NVIDIA", "Microsoft"]},
        )
        self.assertEqual(preference_response.status_code, 200)
        self.assertEqual(preference_response.get_json()["preferences"]["dailyGoal"], 20)
        self.assertEqual(
            preference_response.get_json()["preferences"]["targetCompanies"],
            ["Microsoft", "NVIDIA"],
        )

        random_response = self.client.get("/api/learning/random?type=interview&difficulty=Hard")
        self.assertEqual(random_response.status_code, 200)
        random_question = random_response.get_json()["question"]
        self.assertEqual(random_question["type"], "interview")
        self.assertEqual(random_question["difficulty"], "Hard")

        with self.app.app_context():
            database = get_db()
            total = database.execute("SELECT COUNT(*) FROM learning_questions").fetchone()[0]
            unique_ids = database.execute("SELECT COUNT(DISTINCT id) FROM learning_questions").fetchone()[0]
            unique_text = database.execute("SELECT COUNT(DISTINCT question) FROM learning_questions").fetchone()[0]
            self.assertEqual((total, unique_ids, unique_text), (1000, 1000, 1000))

    def test_voice_first_interview_bank_integrity_and_report(self):
        options = self.client.get("/api/interview/options")
        self.assertEqual(options.status_code, 200)
        option_payload = options.get_json()
        self.assertEqual(option_payload["questionBankSize"], 1000)
        self.assertEqual(
            {item["value"] for item in option_payload["rounds"]},
            {"technical", "managerial", "hr"},
        )
        self.assertGreaterEqual(len(option_payload["domains"]), 18)

        self.client.post(
            "/api/auth/signup",
            json={"name": "Voice User", "email": "voice@example.com", "password": "secret123"},
        )
        start = self.client.post(
            "/api/interview/start",
            json={
                "company": "NVIDIA",
                "roundType": "technical",
                "domain": "artificial_intelligence",
                "difficulty": "hard",
                "durationMinutes": 30,
            },
        )
        self.assertEqual(start.status_code, 200)
        start_payload = start.get_json()
        interview = start_payload["session"]
        self.assertEqual(interview["company"], "NVIDIA")
        self.assertEqual(interview["questionLimit"], 5)
        self.assertEqual(start_payload["meta"]["timerSeconds"], 120)
        self.assertIn("NVIDIA-style", interview["companyLabel"])
        self.assertEqual(self.client.get(f"/api/interview/{interview['id']}/report").status_code, 409)

        event = self.client.post(
            "/api/interview/integrity",
            json={
                "sessionId": interview["id"],
                "eventType": "TAB_SWITCH",
                "duration": 4.5,
                "questionNumber": 1,
                "severity": 1,
            },
        )
        self.assertEqual(event.status_code, 200)
        self.assertEqual(event.get_json()["integrity"]["tabSwitchCount"], 1)

        answer_one = self.client.post(
            "/api/interview/answer",
            json={
                "sessionId": interview["id"],
                "answerType": "spoken",
                "durationSeconds": 52,
                "voiceMetrics": {
                    "wordsPerMinute": 126,
                    "fillerWords": 1,
                    "longPauses": 1,
                    "transcriptionConfidence": 92,
                    "turnDetection": "automatic-silence",
                    "autoSubmitted": True,
                    "silenceStops": 1,
                    "interviewerInterruptions": 1,
                },
                "answer": (
                    "First I would establish a baseline and evaluation rubric for accuracy, latency, cost, "
                    "safety, and model quality. Then I would compare the architecture and model trade-offs, "
                    "test failure cases, monitor drift, and use a rollback plan before production deployment."
                ),
            },
        )
        self.assertEqual(answer_one.status_code, 200)
        self.assertFalse(answer_one.get_json()["evaluation"]["complete"])
        self.assertNotEqual(
            answer_one.get_json()["session"]["currentQuestionId"], interview["currentQuestionId"]
        )

        answer_two = self.client.post(
            "/api/interview/answer",
            json={
                "sessionId": interview["id"],
                "answerType": "typed",
                "durationSeconds": 120,
                "timedOut": True,
                "answer": "",
            },
        )
        self.assertEqual(answer_two.status_code, 200)
        self.assertEqual(answer_two.get_json()["evaluation"]["classification"], "timeout")

        final_payload = answer_two.get_json()
        for _question_number in range(3, 6):
            next_answer = self.client.post(
                "/api/interview/answer",
                json={
                    "sessionId": interview["id"],
                    "answerType": "typed",
                    "durationSeconds": 45,
                    "answer": (
                        "First I would define the constraints, compare alternatives, explain the technical "
                        "trade-off, validate edge cases, and measure accuracy, latency, cost, reliability, "
                        "and safety with production monitoring, alerts, tests, and a rollback plan."
                    ),
                },
            )
            self.assertEqual(next_answer.status_code, 200)
            final_payload = next_answer.get_json()

        self.assertTrue(final_payload["evaluation"]["complete"])
        report = final_payload["report"]
        self.assertEqual(len(report["answers"]), 5)
        self.assertEqual(report["integrity"]["tabSwitches"], 1)
        self.assertEqual(report["adaptive"]["classificationCounts"]["timeout"], 1)
        self.assertEqual(len(report["adaptive"]["progression"]), 5)
        self.assertTrue(report["answers"][1]["timedOut"])
        self.assertTrue(report["answers"][0]["idealAnswer"])
        self.assertIn("wordsPerMinute", report["voice"])
        self.assertEqual(report["voice"]["automaticTurnCompletions"], 1)
        self.assertEqual(report["voice"]["interviewerInterruptions"], 1)
        self.assertEqual(report["voice"]["averageTranscriptionConfidence"], 92)
        self.assertGreaterEqual(report["adaptive"]["generatedFollowUps"], 1)

        with self.app.app_context():
            database = get_db()
            total = database.execute("SELECT COUNT(*) FROM interview_questions").fetchone()[0]
            answer_count = database.execute("SELECT COUNT(*) FROM candidate_answers").fetchone()[0]
            event_count = database.execute("SELECT COUNT(*) FROM integrity_events").fetchone()[0]
            self.assertEqual((total, answer_count, event_count), (1000, 5, 1))

    def test_adaptive_streak_boundaries_and_partial_reset(self):
        first_strong = _adaptive_transition("strong", "medium", 0, 0)
        self.assertEqual(first_strong, ("medium", 1, 0, "none"))
        self.assertEqual(_adaptive_transition("partial", "medium", 1, 0), ("medium", 0, 0, "none"))
        second_strong = _adaptive_transition("strong", "medium", first_strong[1], first_strong[2])
        self.assertEqual(second_strong, ("hard", 0, 0, "increased"))

        first_weak = _adaptive_transition("timeout", "hard", 0, 0)
        self.assertEqual(first_weak, ("hard", 0, 1, "none"))
        second_weak = _adaptive_transition("insufficient", "hard", first_weak[1], first_weak[2])
        self.assertEqual(second_weak, ("medium", 0, 0, "decreased"))
        self.assertEqual(_adaptive_transition("strong", "hard", 1, 0)[0], "hard")
        self.assertEqual(_adaptive_transition("wrong", "easy", 0, 1)[0], "easy")

    @patch("interview_simulator.services.ai_interviewer._openai_follow_up")
    def test_structured_ai_follow_up_and_local_fallback(self, mocked_openai):
        current = {
            "id": "question-1",
            "base_id": "base-1",
            "text": "How would you design a reliable API?",
            "topic": "API design",
            "difficulty": "medium",
            "bank_category": "Technical / Computer Science",
            "expected_keywords": ["contract", "versioning", "authentication", "monitoring"],
            "ideal_answer": "Define a stable contract, version changes, secure access, and monitor failures.",
            "tags": ["api", "reliability"],
            "source_company": "NVIDIA",
        }
        evaluation = {
            "classification": "partial",
            "matchedKeywords": ["contract"],
            "missedConcepts": ["versioning", "monitoring"],
        }
        local = generate_adaptive_follow_up(
            current=current,
            answer="I would define a clear contract.",
            evaluation=evaluation,
            round_type="technical",
            domain="software_engineering",
            company="NVIDIA",
            target_difficulty="medium",
            transcript=[],
            asked_questions=[current],
            settings={"provider": "offline"},
        )
        self.assertTrue(local["is_follow_up"])
        self.assertEqual(local["generation_source"], "contextual-rules")
        self.assertEqual(local["parent_question_id"], current["id"])
        self.assertNotEqual(local["text"], current["text"])
        self.assertGreaterEqual(len(local["expected_keywords"]), 3)

        mocked_openai.return_value = {
            "question": "How would you version that API without breaking existing clients?",
            "ideal_answer": "Use an explicit compatibility policy, additive changes, contract tests, and a measured migration plan.",
            "explanation": "This probes whether the candidate can evolve a public contract safely.",
            "expected_keywords": ["versioning", "compatibility", "contract tests", "migration"],
            "reason": "The previous answer covered contracts but did not explain compatibility during change.",
        }
        generated = generate_adaptive_follow_up(
            current=current,
            answer="I would define a clear contract.",
            evaluation=evaluation,
            round_type="technical",
            domain="software_engineering",
            company="NVIDIA",
            target_difficulty="hard",
            transcript=[{"speaker": "candidate", "text": "I would define a clear contract."}],
            asked_questions=[current],
            settings={"provider": "openai", "api_key": "test-key", "model": "test-model"},
        )
        self.assertEqual(generated["generation_source"], "openai")
        self.assertEqual(generated["generation_model"], "test-model")
        self.assertEqual(generated["difficulty"], "hard")
        self.assertIn("version", generated["text"].lower())

    def test_resume_quiz_upload_generation_evaluation_timeout_rotation_and_privacy(self):
        page = self.client.get("/resume-quiz")
        self.assertEqual(page.status_code, 200)
        self.assertIn("Resume-Based Quiz", page.get_data(as_text=True))
        self.assertEqual(self.client.get("/api/resume-quiz/summary").status_code, 401)

        signup = self.client.post(
            "/api/auth/signup",
            json={"name": "Resume User", "email": "resume@example.com", "password": "secret123"},
        )
        self.assertEqual(signup.status_code, 201)
        unsupported = self.client.post(
            "/api/resume-quiz/resume",
            data={"resume": (io.BytesIO(b"plain resume text"), "resume.txt")},
            content_type="multipart/form-data",
        )
        self.assertEqual(unsupported.status_code, 400)
        invalid_docx = self.client.post(
            "/api/resume-quiz/resume",
            data={"resume": (io.BytesIO(b"not a zip archive"), "resume.docx")},
            content_type="multipart/form-data",
        )
        self.assertEqual(invalid_docx.status_code, 400)

        resume_text = """TECHNICAL SKILLS
Python SQL Machine Learning React Pandas Docker Git
PROJECTS
AI Interview Simulator | Built with Python React Machine Learning and SQL for interview analysis.
Customer Churn | Trained Random Forest with Pandas and Scikit-learn.
PROFESSIONAL EXPERIENCE
AI Intern at Example Labs | Used Python Pandas and Machine Learning for data preprocessing and classification.
EDUCATION
B.Tech Computer Science 2025
CERTIFICATIONS
AWS Cloud Fundamentals
resume.user@example.com
+91 9876543210
"""
        upload = self.client.post(
            "/api/resume-quiz/resume",
            data={"resume": (self.make_docx(resume_text), "Resume_User.docx")},
            content_type="multipart/form-data",
        )
        self.assertEqual(upload.status_code, 201)
        upload_payload = upload.get_json()
        resume_id = upload_payload["resume"]["id"]
        self.assertGreaterEqual(upload_payload["counts"]["technicalSkills"], 7)
        self.assertEqual(upload_payload["counts"]["professionalExperience"], 1)
        self.assertEqual(upload_payload["counts"]["projects"], 2)
        analysis_text = str(upload_payload["analysis"])
        self.assertNotIn("resume.user@example.com", analysis_text)
        self.assertNotIn("9876543210", analysis_text)

        generated = self.client.post("/api/resume-quiz/generate", json={"resumeId": resume_id})
        self.assertEqual(generated.status_code, 201)
        generated_payload = generated.get_json()
        session_id = generated_payload["session"]["id"]
        self.assertEqual(
            generated_payload["distribution"]["categories"],
            {"Technical Skills": 4, "Projects": 4, "Professional Experience": 2},
        )
        self.assertEqual(
            generated_payload["distribution"]["difficulties"],
            {"Easy": 3, "Medium": 5, "Hard": 2},
        )

        started = self.client.post("/api/resume-quiz/start", json={"sessionId": session_id})
        self.assertEqual(started.status_code, 200)
        attempt = started.get_json()["session"]
        questions = attempt["questions"]
        self.assertEqual(len(questions), 10)
        self.assertEqual(len({question["id"] for question in questions}), 10)
        self.assertTrue(all(len(question["options"]) == 4 for question in questions))
        self.assertTrue(all("correctAnswer" not in question for question in questions))
        self.assertLessEqual(attempt["remainingSeconds"], 600)
        self.assertGreater(attempt["remainingSeconds"], 590)

        invalid_answer = self.client.patch(
            "/api/resume-quiz/answer",
            json={
                "sessionId": session_id,
                "questionId": questions[0]["id"],
                "selectedAnswer": "An option not present in the question",
            },
        )
        self.assertEqual(invalid_answer.status_code, 400)

        with self.app.app_context():
            database = get_db()
            question_rows = database.execute(
                "SELECT * FROM resume_quiz_questions WHERE session_id=? ORDER BY position",
                (session_id,),
            ).fetchall()
            correct_answers = {row["id"]: row["correct_answer"] for row in question_rows[:9]}
            first_uids = {row["question_uid"] for row in question_rows}
            sources = [safe_json_loads(row["resume_source_json"], {}) for row in question_rows]
            detected = set(upload_payload["analysis"]["technicalSkills"])
            self.assertTrue(all(source["skill"] in detected for source in sources))

        submitted = self.client.post(
            "/api/resume-quiz/submit",
            json={
                "sessionId": session_id,
                "responses": correct_answers,
                "timeSpent": {question["id"]: 30 for question in questions},
            },
        )
        self.assertEqual(submitted.status_code, 200)
        result = submitted.get_json()["result"]
        self.assertEqual((result["score"], result["unansweredQuestions"]), (9, 1))
        self.assertEqual(len(result["review"]), 10)
        self.assertEqual(result["review"][-1]["status"], "Not Answered")
        self.assertTrue(all(item["explanation"] for item in result["review"]))
        self.assertTrue(all(item["resumeSource"]["skill"] in detected for item in result["review"]))
        self.assertIn("categoryPerformance", result["analytics"])
        self.assertIn("technicalSkillsPerformance", result["analytics"])
        self.assertEqual(
            self.client.post("/api/resume-quiz/submit", json={"sessionId": session_id}).status_code,
            409,
        )

        retake = self.client.post("/api/resume-quiz/generate", json={"resumeId": resume_id})
        self.assertEqual(retake.status_code, 201)
        retake_id = retake.get_json()["session"]["id"]
        self.client.post("/api/resume-quiz/start", json={"sessionId": retake_id})
        with self.app.app_context():
            database = get_db()
            second_uids = {
                row["question_uid"]
                for row in database.execute(
                    "SELECT question_uid FROM resume_quiz_questions WHERE session_id=?", (retake_id,)
                ).fetchall()
            }
            self.assertNotEqual(first_uids, second_uids)
            database.execute(
                "UPDATE resume_quiz_sessions SET deadline_at='2000-01-01T00:00:00+00:00' WHERE id=?",
                (retake_id,),
            )
            database.commit()
        timed_out = self.client.get(f"/api/resume-quiz/session/{retake_id}")
        self.assertEqual(timed_out.status_code, 200)
        self.assertTrue(timed_out.get_json()["result"]["timedOut"])
        self.assertEqual(timed_out.get_json()["result"]["unansweredQuestions"], 10)
        self.assertEqual(self.client.get("/api/resume-quiz/history").get_json()["stats"]["attempts"], 2)

        self.client.post("/api/auth/logout", json={})
        self.client.post(
            "/api/auth/signup",
            json={"name": "Other User", "email": "other@example.com", "password": "secret123"},
        )
        self.assertEqual(self.client.get(f"/api/resume-quiz/result/{session_id}").status_code, 404)
        self.assertIsNone(self.client.get("/api/resume-quiz/summary").get_json()["latestResume"])


if __name__ == "__main__":
    unittest.main()
