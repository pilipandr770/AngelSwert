import json
from datetime import datetime, timedelta
from flask import Flask
from sqlalchemy import inspect, text
from urllib.parse import urlparse

from .config import Config
from .extensions import db, login_manager
from .models import (
    AssistantInstructionSettings,
    BlogAutomationSettings,
    HomePageHeroSettings,
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
from .services.services_content import DEFAULT_SERVICES_COPY, parse_services_copy


SERVICE_TEXT_DEFAULTS = {
    "hero_title_de": "Strukturierte KI-Video-, Digital-Human- und Content-Systeme für wiederkehrende Unternehmenskommunikation.",
    "hero_title_en": "Structured AI video, digital human and content systems for recurring business communication.",
    "hero_lead_de": "ASAI Studio verbindet Videoproduktion, Creative Direction, Digital Humans, Content-Systeme, KI-Agenten und kontrollierte Automatisierung zu einer skalierbaren Kommunikationslösung.",
    "hero_lead_en": "ASAI Studio combines video production, creative direction, digital humans, content systems, AI agents and controlled automation into one scalable communication solution.",
    "digital_human_title_de": "Digital Humans für Marken, Unternehmen und Medien",
    "digital_human_title_en": "Digital humans for brands, companies and media",
    "digital_human_body_de": "Konsistente digitale Persönlichkeiten für wiederkehrende, mehrsprachige und skalierbare Kommunikation mit klarer Nutzungslogik.",
    "digital_human_body_en": "Consistent digital personalities for recurring, multilingual and scalable communication with clear usage logic.",
    "strategy_title_de": "Starten Sie mit einer 1:1-Strategie-Session",
    "strategy_title_en": "Start with a 1:1 strategy session",
    "strategy_body_de": "In einer fokussierten 90-Minuten-Session analysieren wir Geschäftsmodell, Kommunikation, Zielgruppe und den Implementierungsweg.",
    "strategy_body_en": "In a focused 90-minute session we analyze your business model, communication, audience and implementation path.",
}

SERVICE_COPY_JSON_DEFAULT = json.dumps(DEFAULT_SERVICES_COPY, ensure_ascii=False)


def _ensure_service_settings_columns() -> None:
    required_columns = {
        "services_copy_json": "TEXT NOT NULL DEFAULT ''",
        "hero_title_de": "TEXT NOT NULL DEFAULT ''",
        "hero_title_en": "TEXT NOT NULL DEFAULT ''",
        "hero_lead_de": "TEXT NOT NULL DEFAULT ''",
        "hero_lead_en": "TEXT NOT NULL DEFAULT ''",
        "digital_human_title_de": "TEXT NOT NULL DEFAULT ''",
        "digital_human_title_en": "TEXT NOT NULL DEFAULT ''",
        "digital_human_body_de": "TEXT NOT NULL DEFAULT ''",
        "digital_human_body_en": "TEXT NOT NULL DEFAULT ''",
        "strategy_title_de": "TEXT NOT NULL DEFAULT ''",
        "strategy_title_en": "TEXT NOT NULL DEFAULT ''",
        "strategy_body_de": "TEXT NOT NULL DEFAULT ''",
        "strategy_body_en": "TEXT NOT NULL DEFAULT ''",
    }

    inspector = inspect(db.engine)
    try:
        existing = {col["name"] for col in inspector.get_columns("service_page_settings")}
    except Exception:
        return

    changed = False
    for column, ddl in required_columns.items():
        if column in existing:
            continue
        db.session.execute(text(f"ALTER TABLE service_page_settings ADD COLUMN {column} {ddl}"))
        changed = True

    if changed:
        db.session.commit()


def _ensure_assistant_settings_columns() -> None:
    required_columns = {
        "widget_auto_open_enabled": "BOOLEAN NOT NULL DEFAULT TRUE",
        "widget_auto_open_delay_seconds": "INTEGER NOT NULL DEFAULT 40",
        "widget_greeting_text": "TEXT NOT NULL DEFAULT ''",
        "instruction_doc_text": "TEXT NOT NULL DEFAULT ''",
        "instruction_doc_name": "VARCHAR(255) NOT NULL DEFAULT ''",
    }

    inspector = inspect(db.engine)
    try:
        existing = {col["name"] for col in inspector.get_columns("assistant_instruction_settings")}
    except Exception:
        return

    changed = False
    for column, ddl in required_columns.items():
        if column in existing:
            continue
        db.session.execute(text(f"ALTER TABLE assistant_instruction_settings ADD COLUMN {column} {ddl}"))
        changed = True

    if changed:
        db.session.commit()


def _ensure_lead_profile_columns() -> None:
    required_columns = {
        "profile_industry": "VARCHAR(255) NOT NULL DEFAULT ''",
        "profile_work_scope": "VARCHAR(255) NOT NULL DEFAULT ''",
        "profile_work_topic": "VARCHAR(255) NOT NULL DEFAULT ''",
        "profile_desired_outcome": "TEXT NOT NULL DEFAULT ''",
        "profile_timeline": "VARCHAR(120) NOT NULL DEFAULT ''",
        "profile_decision_maker": "VARCHAR(255) NOT NULL DEFAULT ''",
        "profile_updated_at": "TIMESTAMP",
    }

    inspector = inspect(db.engine)
    try:
        existing = {col["name"] for col in inspector.get_columns("lead")}
    except Exception:
        return

    changed = False
    for column, ddl in required_columns.items():
        if column in existing:
            continue
        db.session.execute(text(f"ALTER TABLE lead ADD COLUMN {column} {ddl}"))
        changed = True

    if changed:
        db.session.commit()


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
        db.session.add(
            AssistantInstructionSettings(
                custom_instructions="",
                widget_auto_open_enabled=True,
                widget_auto_open_delay_seconds=40,
                widget_greeting_text="Hallo und willkommen bei ASAI Studio. Ich kann Ihnen direkt freie Beratungstermine zeigen oder beim passenden Paket helfen.",
                instruction_doc_text="",
                instruction_doc_name="",
            )
        )
    else:
        assistant_settings = AssistantInstructionSettings.query.first()
        if assistant_settings:
            if not (assistant_settings.widget_greeting_text or "").strip():
                assistant_settings.widget_greeting_text = (
                    "Hallo und willkommen bei ASAI Studio. "
                    "Ich kann Ihnen direkt freie Beratungstermine zeigen oder beim passenden Paket helfen."
                )
            if assistant_settings.widget_auto_open_delay_seconds <= 0:
                assistant_settings.widget_auto_open_delay_seconds = 40
            db.session.add(assistant_settings)

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
                services_copy_json=SERVICE_COPY_JSON_DEFAULT,
                hero_title_de=SERVICE_TEXT_DEFAULTS["hero_title_de"],
                hero_title_en=SERVICE_TEXT_DEFAULTS["hero_title_en"],
                hero_lead_de=SERVICE_TEXT_DEFAULTS["hero_lead_de"],
                hero_lead_en=SERVICE_TEXT_DEFAULTS["hero_lead_en"],
                digital_human_media="img/services_tz/image2.png",
                digital_human_title_de=SERVICE_TEXT_DEFAULTS["digital_human_title_de"],
                digital_human_title_en=SERVICE_TEXT_DEFAULTS["digital_human_title_en"],
                digital_human_body_de=SERVICE_TEXT_DEFAULTS["digital_human_body_de"],
                digital_human_body_en=SERVICE_TEXT_DEFAULTS["digital_human_body_en"],
                story_poster="img/services_tz/image3.png",
                strategy_photo="img/client-consultation.jpg",
                strategy_title_de=SERVICE_TEXT_DEFAULTS["strategy_title_de"],
                strategy_title_en=SERVICE_TEXT_DEFAULTS["strategy_title_en"],
                strategy_body_de=SERVICE_TEXT_DEFAULTS["strategy_body_de"],
                strategy_body_en=SERVICE_TEXT_DEFAULTS["strategy_body_en"],
                discovery_url=discovery_endpoint,
            )
        )
    else:
        settings = ServicePageSettings.query.first()
        changed = False

        merged_copy = parse_services_copy(settings.services_copy_json)
        merged_copy_json = json.dumps(merged_copy, ensure_ascii=False)
        if (settings.services_copy_json or "") != merged_copy_json:
            settings.services_copy_json = merged_copy_json
            changed = True

        for field_name, fallback_value in SERVICE_TEXT_DEFAULTS.items():
            current_value = (getattr(settings, field_name, "") or "").strip()
            if current_value:
                continue
            setattr(settings, field_name, fallback_value)
            changed = True
        if changed:
            db.session.add(settings)

    if not HomePageHeroSettings.query.first():
        db.session.add(HomePageHeroSettings())

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
        _ensure_assistant_settings_columns()
        _ensure_lead_profile_columns()
        _ensure_service_settings_columns()
        _seed_defaults(app)

    init_scheduler(app)
    return app
