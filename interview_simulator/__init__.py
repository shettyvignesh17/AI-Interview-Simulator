from datetime import timedelta
from pathlib import Path

from flask import Flask

from .utils.env import load_env_file


def create_app(test_config=None):
    base_dir = Path(__file__).resolve().parent.parent
    load_env_file(base_dir)

    app = Flask(
        __name__,
        template_folder=str(base_dir / "templates"),
        static_folder=str(base_dir / "static"),
        static_url_path="/static",
    )

    from .config import Config

    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    Path(app.config["DATA_DIR"]).mkdir(parents=True, exist_ok=True)
    Path(app.config["UPLOAD_DIR"]).mkdir(parents=True, exist_ok=True)

    app.permanent_session_lifetime = timedelta(
        days=app.config["PERMANENT_SESSION_LIFETIME_DAYS"]
    )

    from . import db

    db.init_app(app)

    from .routes.auth import bp as auth_bp
    from .routes.aptitude import bp as aptitude_bp
    from .routes.interview import bp as interview_bp
    from .routes.learning import bp as learning_bp
    from .routes.resume_quiz import bp as resume_quiz_bp
    from .routes.main import bp as main_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(interview_bp)
    app.register_blueprint(aptitude_bp)
    app.register_blueprint(learning_bp)
    app.register_blueprint(resume_quiz_bp)

    @app.context_processor
    def inject_app_config():
        return {
            "frontend_config": {
                "questionTimeLimit": app.config["QUESTION_TIME_LIMIT"],
                "maxQuestions": app.config["MAX_QUESTIONS_PER_SESSION"],
                "aiProvider": app.config["AI_PROVIDER"],
            }
        }

    @app.after_request
    def allow_local_interview_devices(response):
        response.headers.setdefault(
            "Permissions-Policy",
            "camera=(self), microphone=(self), on-device-speech-recognition=(self)",
        )
        return response

    return app
