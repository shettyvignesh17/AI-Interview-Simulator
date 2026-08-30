# User Manual

## 1. Install and Run

Open Terminal and run each command in order:

```bash
git clone https://github.com/shreyasv045/AI-Interview-Simulator.git
cd AI-Interview-Simulator
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```

This project has no separate frontend build command. Flask serves the HTML, CSS, JavaScript, and API together.

Open `http://127.0.0.1:5000`. If `.env` uses `PORT=5050`, open `http://127.0.0.1:5050` instead.

Keep the Terminal window running while using the website. Press `Control + C` in that Terminal to stop the server.

## 2. Sign Up or Login

1. Open the main page.
2. Choose `Sign Up` for a new account or `Login` for an existing account.
3. Enter the requested name, email, and password.
4. After authentication, the interview setup and performance summary appear.

## 3. Configure an Interview

Choose all four settings:

1. `Company`: the target company style, such as NVIDIA, Google, Microsoft, Amazon, or Apple.
2. `Interview Round`: Technical Round, Manager Round, or HR Round.
3. `Domain`: choose one of the 18 technical domains.
4. `Difficulty`: Easy, Medium, or Hard.

Questions come from the 1,000-question interview bank. Resume upload is not part of the main interview.

Optionally enable `Hands-Free Voice Interview`. This makes the interviewer speak each question, open the microphone automatically, detect a completed spoken turn, and continue without requiring the normal answer buttons.

## 4. Run the System Check

1. Read the privacy notice.
2. Select `I understand and want to continue`.
3. Click `Run System Check`.
4. Allow camera and microphone permission if you want the complete monitored and spoken-answer experience.
5. Check the Webcam, Microphone, Speaker, and Browser Focus status rows.

If camera permission is denied or a browser API is unavailable, the interview still works in limited mode with typed answers and an optional question transcript.

## 5. Start and Answer

1. Click `Start Interview`.
2. Wait for the `3, 2, 1` countdown.
3. Listen while the interviewer speaks the question.
4. Use `Repeat Question` up to two times if needed.
5. Enable `Show Question Transcript` only when an accessible text alternative is needed.
6. In manual mode, choose `Type Answer` or `Speak Answer`.

### Hands-Free Voice Mode

1. Enable `Hands-Free Voice Interview` before starting.
2. Allow microphone permission when requested.
3. After the interviewer finishes, the microphone opens automatically and the live transcript appears.
4. Speak naturally. Continuing to speak cancels the pending submission; a short silence completes and submits the turn.
5. Select `Answer Now` while the interviewer is speaking if you want to interrupt and begin immediately.
6. You can still use Stop, Submit, typed answers, or Skip at any time.

### Submit an Answer

1. For typed mode, enter the response in the text area and use `Clear`, `Skip Question`, or `Submit Answer`.
2. For spoken mode, select `Start Speaking`, review the live transcript, then select `Stop` and `Submit Answer`.
3. Watch the word count, elapsed time, and optional speech pace preview.
4. Answer within two minutes. The timer starts after the interviewer finishes speaking and warns at 30 and 10 seconds remaining.

Each interview asks exactly five unique questions. Bank questions alternate with answer-aware follow-ups, then rotate to a fresh topic. Two consecutive Strong answers move the hidden level up; two consecutive Wrong, Insufficient, or Timeout outcomes move it down; a Partial answer resets both streaks. Scores, classifications, level changes, and ideal answers remain hidden until the interview ends.

When an OpenAI key is configured, follow-ups use structured model output based on the previous answer and recent conversation memory. Otherwise, the built-in contextual engine generates them locally. Provider failure never stops the interview.

## 6. Monitoring and Privacy

During an active interview, the application may record browser-supported observable events:

- interview page hidden or window focus lost
- camera disabled
- microphone disabled or interrupted
- face not visible for a sustained period, if `FaceDetector` is supported
- more than one possible face visible for a sustained period, if supported

Warnings use neutral terms such as `Focus Warning`, `Attention Warning`, and `Possible integrity event`. These signals can be imperfect and are not proof of cheating.

The normal website cannot determine which external website or application was opened. The app does not perform face recognition or infer identity, protected characteristics, personality, honesty, emotion, or mental state.

## 7. Review the Report

After the last question, the main page displays:

- overall, technical, communication, and relevance scores
- strengths and improvement suggestions
- recommended topics linked to Interview Learning
- response timing and answer-by-answer communication feedback
- starting/ending difficulty, answer classifications, and adaptive progression
- adaptive follow-up count, generation source, and the reason each follow-up was asked
- speaking pace, filler words, pauses, automatic turn completions, interruptions, and available transcript-confidence signals
- neutral integrity event counts
- each question, candidate answer, score, strengths, improvements, ideal answer, and missed concepts

Use `Practice Another Interview` to return to setup. Use `Analytics` in the navigation to review all previous interviews.

## 8. Other Modules

- `Analytics`: summary, strengths, weaknesses, improvements, and expandable history
- `Aptitude Quiz`: randomized 10-question aptitude attempts from a 300-question bank
- `Interview Learning`: a 1,200-question preparation catalog with a separate 200-problem Practical Coding section, filters, hints, four-language solutions, notes, bookmarks, progress, and study mode
- `Resume Quiz`: a separate private resume-defense assessment based only on detected resume claims

## 9. Resume Quiz

1. Select `Resume Quiz` in the navigation after logging in.
2. Drag a PDF/DOCX into the upload area or browse for the file.
3. Select `Upload & Analyze Resume`. The app displays live analysis stages rather than a blank screen.
4. Review Technical Skills, Professional Experience, Projects, and additional evidence. Missing categories remain empty and are never invented.
5. Select `Generate Resume Quiz`, review the generated category/difficulty distribution, then select `Start Resume Quiz`.
6. Answer exactly ten MCQs. Use Previous, Next, or the numbered question map; selections remain saved.
7. Complete the attempt within the single `10:00` overall timer. Navigation never restarts it. Warnings appear once at 5:00, 1:00, and 0:30.
8. On manual submission, confirm whether to submit unanswered questions. At `0:00`, the app locks changes and submits automatically.
9. Review score, attempted/correct/unanswered totals, readiness, category/skill/project/experience performance, risk areas, learning links, explanations, and why each question was asked.
10. Select `Retake Resume Quiz` for a rotated set using the same resume, or `Upload Different Resume` to analyze another document.

Removing a resume also removes Resume Quiz attempts linked to that document. This prevents orphaned personal-document data.

## 10. Troubleshooting

### `TemplateNotFound: index.html`

Run Flask from the project root, not from the `templates` folder:

```bash
cd /path/to/AI-Interview-Simulator
source .venv/bin/activate
python app.py
```

Do not open `templates/index.html` with a `file:///` URL. Always use the Flask URL.

### Flask or another package is missing

```bash
cd /path/to/AI-Interview-Simulator
source .venv/bin/activate
pip install -r requirements.txt
```

### Port is already in use

Set another port in `.env`, restart Flask, and open the matching URL:

```env
PORT=5050
```

### Camera does not start

- Allow the site in browser permissions.
- Close other applications using the camera.
- Use a Chromium-based browser on `localhost`.
- Run System Check again.
- Continue with typed-answer limited mode if the device remains unavailable.

### Spoken questions do not play

Enable `Show Question Transcript` and use the text alternative. Check the device volume and browser audio permissions before the next session.

### Spoken answers do not transcribe

Speech recognition support varies by browser. Use a current Chromium-based browser, allow microphone permission, and run System Check again. You can always switch to `Type Answer` without restarting the question.

### Hands-free mode does not start automatically

- Confirm `Hands-Free Voice Interview` was selected before starting.
- Allow microphone permission and use a current Chromium-based browser.
- If browser speech recognition is unavailable, use manual spoken mode or typed answers.
- Reloading during an active interview is not recommended because live browser voice state is temporary.

### AI follow-ups use the local engine

Open `.env`, set `AI_PROVIDER=hybrid`, add a valid `OPENAI_API_KEY`, and restart Flask. The local engine remains the expected fallback if the model request times out or returns invalid structured content.

### Question database failure

```bash
source .venv/bin/activate
python scripts/seed_interview_questions.py
python app.py
```

### Dashboard is empty

Complete all questions in at least one interview. The dashboard only summarizes completed sessions.

### Resume Quiz rejects a PDF or DOCX

- Confirm the extension is `.pdf` or `.docx` and the file is not empty.
- Use a text-based PDF. A PDF containing only scanned images has no readable text and is rejected instead of generating unrelated questions.
- Remove PDF encryption/password protection.
- Reinstall dependencies if PDF support reports that `pypdf` is missing.

### Resume Quiz shows no supported technical claims

Use clear section headings such as `Technical Skills`, `Projects`, and `Professional Experience`, and include the technologies used in project/experience descriptions. The module will not invent technologies that the parser did not detect.

### Login resets after restarting

Keep the same `SECRET_KEY` value in `.env` between runs.

## 11. Answering Tips

- Technical: state the problem, approach, reasoning, complexity or trade-off, edge cases, and production validation.
- Manager: use Situation, Task, Action, Result and make ownership, stakeholder alignment, and impact explicit.
- HR: answer directly, connect the response to role fit, and support claims with a concise example.
- Typed answers: lead with a clear headline before adding supporting details.
