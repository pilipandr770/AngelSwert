from datetime import datetime, timedelta
from flask import Flask
from sqlalchemy import text
from urllib.parse import urlparse

from .config import Config
from .extensions import db, login_manager
from .models import (
    AssistantInstructionSettings,
    BlogAutomationSettings,
    InternalCalendarSettings,
    InternalCalendarSlot,
    ServicePageSettings,
    User,
    YouTubeLink,
)
from .routes.admin import admin_bp
from .routes.api import api_bp
from .routes.auth import auth_bp
from .routes.public import public_bp
from .services.blog_scheduler import init_scheduler


def _seed_defaults(app: Flask) -> None:
    admin_email = app.config["ADMIN_EMAIL"]
    admin_password = app.config["ADMIN_PASSWORD"]

    if not User.query.filter_by(email=admin_email).first():
        user = User(email=admin_email, is_admin=True)
        user.set_password(admin_password)
        db.session.add(user)

    defaults = [
        (1, "YouTube Channel 1", "https://www.youtube.com/"),
        (2, "YouTube Channel 2", "https://www.youtube.com/"),
        (3, "YouTube Channel 3", "https://www.youtube.com/"),
        (4, "YouTube Channel 4", "https://www.youtube.com/"),
    ]
    for slot, title, url in defaults:
        if not YouTubeLink.query.filter_by(slot=slot).first():
            db.session.add(YouTubeLink(slot=slot, title=title, url=url))

    if not AssistantInstructionSettings.query.first():
        db.session.add(AssistantInstructionSettings(custom_instructions=""))

    if not BlogAutomationSettings.query.first():
        db.session.add(
            BlogAutomationSettings(
                blog_custom_instructions="",
                rss_sources=(
                    "https://openai.com/news/rss.xml\n"
                    "https://blog.google/technology/ai/rss/\n"
                    "https://www.searchenginejournal.com/feed/"
                ),
                auto_from_rss_enabled=False,
                max_rss_items_per_run=2,
            )
        )

    if not ServicePageSettings.query.first():
        discovery_endpoint = urlparse(app.config.get("PUBLIC_DISCOVERY_URL") or "").path or "/contact"
        db.session.add(
            ServicePageSettings(
                hero_media="img/services_tz/image1.png",
                digital_human_media="img/services_tz/image2.png",
                story_poster="img/services_tz/image3.png",
                strategy_photo="img/client-consultation.jpg",
                discovery_url=discovery_endpoint,
            )
        )

    settings = InternalCalendarSettings.query.first()
    if not settings:
        settings = InternalCalendarSettings(
            day_start_hour=9,
            day_end_hour=18,
            slot_duration_minutes=90,
            slot_interval_minutes=120,
            weekdays_csv="0,1,2,3,4",
            horizon_days=90,
            updated_by="system",
        )
        db.session.add(settings)
        db.session.flush()

    if InternalCalendarSlot.query.count() == 0:
        now = datetime.utcnow()
        start_date = now.date()
        end_date = (now + timedelta(days=max(1, settings.horizon_days))).date()
        weekdays = {int(x.strip()) for x in settings.weekdays_csv.split(",") if x.strip().isdigit()}
        if not weekdays:
            weekdays = {0, 1, 2, 3, 4}

        start_hour = max(0, min(23, settings.day_start_hour))
        end_hour = max(start_hour + 1, min(24, settings.day_end_hour))
        duration = max(15, settings.slot_duration_minutes)
        interval = max(duration, settings.slot_interval_minutes)

        day = start_date
        while day <= end_date:
            if day.weekday() in weekdays:
                minute_cursor = start_hour * 60
                end_minutes = end_hour * 60
                while minute_cursor + duration <= end_minutes:
                    starts_at = datetime(day.year, day.month, day.day, minute_cursor // 60, minute_cursor % 60, 0)
                    ends_at = starts_at + timedelta(minutes=90)
                    if starts_at > now:
                        db.session.add(
                            InternalCalendarSlot(
                                starts_at=starts_at,
                                ends_at=starts_at + timedelta(minutes=duration),
                                is_available=True,
                                created_by="system",
                            )
                        )
                    minute_cursor += interval
            day += timedelta(days=1)

    db.session.commit()


def _ensure_db_schema(app: Flask) -> None:
    schema = (app.config.get("DB_SCHEMA") or "public").strip()
    if schema == "public":
        return
    # Schema name is validated in config.py.
    db.session.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema}"'))
    db.session.commit()


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

    app.register_blueprint(public_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)

    with app.app_context():
        _ensure_db_schema(app)
        db.create_all()
        _seed_defaults(app)

    init_scheduler(app)
    return app
