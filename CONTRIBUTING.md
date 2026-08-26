# Contributing

Contributions should preserve the project's explainable, privacy-aware behavior and avoid unsupported claims about AI models or company question provenance.

## Development Workflow

1. Fork the repository and create a focused branch.
2. Create a virtual environment and install `requirements.txt`.
3. Copy `.env.example` to `.env`; never commit credentials or personal data.
4. Keep frontend behavior accessible without camera, microphone, speech recognition, or an OpenAI key.
5. Add or update tests for every behavior change.
6. Run the validation commands before opening a pull request.

```bash
python -m compileall -q app.py interview_simulator scripts tests
python -m unittest discover -s tests -v
```

## Pull Requests

- Explain the user-visible change and its trade-offs.
- Document new environment variables in `.env.example` and `README.md`.
- Do not commit `.env`, local databases, uploads, generated caches, or real resume data.
- Keep optional external-AI behavior behind a deterministic local fallback.
- Clearly label future or experimental capabilities instead of presenting them as implemented.
