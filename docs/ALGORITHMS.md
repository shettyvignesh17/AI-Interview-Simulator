# Algorithms and AI Techniques

This document separates deterministic algorithms from optional generative-AI behavior. The project does not include a trained custom machine-learning model, embeddings, BERT, transformers, spaCy, NLTK, TensorFlow, or PyTorch.

## 1. Interview Question Selection

The main selector filters out question IDs already used in the active session and recent browser history. It retrieves a candidate set for the selected round, then ranks each candidate with these implemented signals:

```text
rank = company_match
     + domain_match
     + difficulty_proximity
     + weak_topic_reinforcement
     - immediate_topic_repetition
     + secure_random_jitter
```

Current weights in `interview_delivery.py` are:

- company match: `+8`
- exact domain match: `+26`; all-domain fallback: `+8`
- difficulty: `10 - 4 * level_distance`
- weak-topic reinforcement: `+7`
- same topic as the immediately previous question: `-30`
- `SystemRandom` jitter: `[0, 3)`

This produces controlled variation while prioritizing relevance and non-repetition.

## 2. Local Answer Evaluation

The evaluator tokenizes the answer and derives observable features:

- expected-keyword coverage
- answer length and sentence count
- topic mention and example signals
- structure markers such as problem, approach, result, and trade-off
- STAR/impact markers for managerial and HR answers
- numeric evidence
- filler words, reported speaking pace, and long pauses for spoken answers

For Technical rounds:

```text
overall = 0.40 * technical
        + 0.25 * relevance
        + 0.15 * communication
        + 0.20 * completeness
```

For Manager and HR rounds:

```text
overall = 0.20 * technical_or_behavioral_depth
        + 0.25 * relevance
        + 0.30 * communication
        + 0.25 * completeness
```

A structured, evidence-backed answer can receive an eight-point bonus. All component scores are clamped to `0-100`. This is a transparent heuristic assessment, not a validated employment prediction.

## 3. Classification and Adaptive Difficulty

Answers are classified in this order:

1. `timeout` when the question timer expires.
2. `insufficient` when the answer has fewer than eight tokens.
3. `strong` when overall score is at least 70.
4. `partial` when overall score is from 40 through 69.9.
5. `wrong` below 40.

Difficulty uses a bounded finite-state progression:

```text
Easy <-> Medium <-> Hard
```

- Two consecutive Strong answers move up one level.
- Two consecutive Wrong, Insufficient, or Timeout answers move down one level.
- Partial resets both streaks.
- The level never moves below Easy or above Hard.

## 4. Adaptive Follow-Up Generation

The generator builds a bounded context from the current question, candidate answer, classification, matched/missed concepts, target difficulty, recent transcript turns, and recent question texts.

When `AI_PROVIDER` permits OpenAI and a key is configured, the Responses API must return strict JSON matching a local schema: one question, ideal answer, explanation, expected keywords, and generation reason. Candidate text is explicitly treated as untrusted content. Output length, metadata completeness, and duplicate questions are validated.

Any missing key, timeout, network failure, invalid schema, or repeated question activates the local fallback. The fallback uses performance-specific templates:

- Strong: probe scale, failure modes, or trade-offs.
- Partial: connect a covered concept to a missed concept.
- Weak/timeout: narrow to a foundational diagnostic question.

## 5. Aptitude Randomization

Each attempt creates randomized company slots with a `2,2,2,2,1,1` distribution across six companies and a fixed `4 Easy, 4 Medium, 2 Hard` mix. A cryptographically backed `SystemRandom` instance selects unused questions, shuffles question order, shuffles each option list, and preserves the correct-answer mapping. Completed-question history is used for pool rotation across attempts.

## 6. Resume Analysis and Quiz Generation

The parser validates extension, size, and extractable text. PDF text is read with `pypdf`; DOCX text is read from its XML package. Rule-based section detection and normalized technology dictionaries identify technical skills, projects, professional experience, tools, education, certifications, research, and achievements. Contact-like data is filtered from quiz evidence.

Resume Quiz templates are activated only for detected technologies. Selection uses category and difficulty targets, source-evidence links, prior question UIDs, and secure random jitter. Each generated option set has one correct answer and three shuffled distractors. No resume content is sent to OpenAI.

## 7. Quiz Scoring and Analytics

For ten-question MCQ quizzes:

```text
score = count(selected_answer == correct_answer)
percentage = 100 * score / total_questions
accuracy(group) = 100 * correct_in_group / attempted_in_group
```

Aggregations are calculated by company/category for Aptitude Quiz and by category/skill/project/experience for Resume Quiz. Historical average, highest score, trends, strong groups, and weak groups are computed from completed attempts only. Back/Quit actions mark or remove temporary attempts and never create results.

## 8. Monitoring Signals

Page visibility, focus changes, track interruptions, and browser-supported face counts are timestamped event counters. Sustained absence/multiple-face checks use time thresholds and event cooldowns. These signals are deliberately described as neutral integrity/practice events and are not classified by a machine-learning model.
