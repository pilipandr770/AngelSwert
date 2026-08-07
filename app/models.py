from datetime import datetime, timedelta

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, login_manager


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id: str):
    return User.query.get(int(user_id))


class YouTubeLink(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slot = db.Column(db.Integer, unique=True, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    url = db.Column(db.String(1024), nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AssistantInstructionSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    custom_instructions = db.Column(db.Text, default="", nullable=False)
    widget_auto_open_enabled = db.Column(db.Boolean, default=True, nullable=False)
    widget_auto_open_delay_seconds = db.Column(db.Integer, default=40, nullable=False)
    widget_greeting_text = db.Column(
        db.Text,
        default="Hallo und willkommen bei ASAI Studio. Ich kann Ihnen direkt freie Beratungstermine zeigen oder beim passenden Paket helfen.",
        nullable=False,
    )
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BlogPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(255), unique=True, nullable=False)
    excerpt = db.Column(db.Text, nullable=False)
    content = db.Column(db.Text, nullable=False)
    seo_keywords = db.Column(db.String(500), default="")
    status = db.Column(db.String(50), default="draft", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    published_at = db.Column(db.DateTime)


class BlogTopic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    topic = db.Column(db.String(255), nullable=False)
    language = db.Column(db.String(20), default="de", nullable=False)
    frequency_hours = db.Column(db.Integer, default=72, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    next_run_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_run_at = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    def schedule_next(self) -> None:
        self.last_run_at = datetime.utcnow()
        self.next_run_at = self.last_run_at + timedelta(hours=max(1, self.frequency_hours))


class BlogAutomationSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    blog_custom_instructions = db.Column(db.Text, default="", nullable=False)
    rss_sources = db.Column(db.Text, default="", nullable=False)
    auto_from_rss_enabled = db.Column(db.Boolean, default=False, nullable=False)
    max_rss_items_per_run = db.Column(db.Integer, default=2, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class BlogFeedEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    entry_key = db.Column(db.String(500), unique=True, nullable=False)
    source_url = db.Column(db.String(1024), nullable=False)
    entry_title = db.Column(db.String(500), nullable=False)
    entry_link = db.Column(db.String(1024), default="")
    processed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Lead(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(100), default="")
    stage = db.Column(db.String(100), default="new", nullable=False)
    source = db.Column(db.String(100), default="website", nullable=False)
    notes = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class LeadMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey("lead.id"), nullable=False)
    direction = db.Column(db.String(20), nullable=False)
    channel = db.Column(db.String(50), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    lead = db.relationship("Lead", backref=db.backref("messages", lazy=True, order_by="LeadMessage.created_at.desc()"))


class ServicePageSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hero_media = db.Column(db.String(1024), default="img/services_tz/image1.png", nullable=False)
    services_copy_json = db.Column(db.Text, default="", nullable=False)
    hero_title_de = db.Column(
        db.Text,
        default="Strukturierte KI-Video-, Digital-Human- und Content-Systeme für wiederkehrende Unternehmenskommunikation.",
        nullable=False,
    )
    hero_title_en = db.Column(
        db.Text,
        default="Structured AI video, digital human and content systems for recurring business communication.",
        nullable=False,
    )
    hero_lead_de = db.Column(
        db.Text,
        default="ASAI Studio verbindet Videoproduktion, Creative Direction, Digital Humans, Content-Systeme, KI-Agenten und kontrollierte Automatisierung zu einer skalierbaren Kommunikationslösung.",
        nullable=False,
    )
    hero_lead_en = db.Column(
        db.Text,
        default="ASAI Studio combines video production, creative direction, digital humans, content systems, AI agents and controlled automation into one scalable communication solution.",
        nullable=False,
    )
    digital_human_media = db.Column(db.String(1024), default="img/services_tz/image2.png", nullable=False)
    digital_human_title_de = db.Column(
        db.Text,
        default="Digital Humans für Marken, Unternehmen und Medien",
        nullable=False,
    )
    digital_human_title_en = db.Column(
        db.Text,
        default="Digital humans for brands, companies and media",
        nullable=False,
    )
    digital_human_body_de = db.Column(
        db.Text,
        default="Konsistente digitale Persönlichkeiten für wiederkehrende, mehrsprachige und skalierbare Kommunikation mit klarer Nutzungslogik.",
        nullable=False,
    )
    digital_human_body_en = db.Column(
        db.Text,
        default="Consistent digital personalities for recurring, multilingual and scalable communication with clear usage logic.",
        nullable=False,
    )
    story_poster = db.Column(db.String(1024), default="img/services_tz/image3.png", nullable=False)
    story_video_01 = db.Column(db.String(1024), default="", nullable=False)
    story_video_02 = db.Column(db.String(1024), default="", nullable=False)
    story_video_03 = db.Column(db.String(1024), default="", nullable=False)
    story_subtitles_01 = db.Column(db.String(1024), default="", nullable=False)
    story_subtitles_02 = db.Column(db.String(1024), default="", nullable=False)
    story_subtitles_03 = db.Column(db.String(1024), default="", nullable=False)
    strategy_photo = db.Column(db.String(1024), default="img/client-consultation.jpg", nullable=False)
    strategy_title_de = db.Column(
        db.Text,
        default="Starten Sie mit einer 1:1-Strategie-Session",
        nullable=False,
    )
    strategy_title_en = db.Column(
        db.Text,
        default="Start with a 1:1 strategy session",
        nullable=False,
    )
    strategy_body_de = db.Column(
        db.Text,
        default="In einer fokussierten 90-Minuten-Session analysieren wir Geschäftsmodell, Kommunikation, Zielgruppe und den Implementierungsweg.",
        nullable=False,
    )
    strategy_body_en = db.Column(
        db.Text,
        default="In a focused 90-minute session we analyze your business model, communication, audience and implementation path.",
        nullable=False,
    )
    discovery_url = db.Column(db.String(1024), default="/contact", nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class HomePageHeroSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hero_background = db.Column(db.String(1024), default="img/services_tz/image1.png", nullable=False)
    hero_image_main = db.Column(db.String(1024), default="img/services_tz/image3.png", nullable=False)
    hero_image_secondary = db.Column(db.String(1024), default="img/client-about.jpg", nullable=False)
    hero_eyebrow_de = db.Column(db.Text, default="UNSERE LEISTUNGEN", nullable=False)
    hero_eyebrow_en = db.Column(db.Text, default="OUR SERVICES", nullable=False)
    hero_title_de = db.Column(db.Text, default="Kontrollierte KI-Video- & Mediasysteme für Unternehmen", nullable=False)
    hero_title_en = db.Column(db.Text, default="Controlled AI video & media systems for business", nullable=False)
    hero_lead_de = db.Column(db.Text, default="KI-Video-Produktion, Digital Humans, Content-Systeme und Automatisierung für klare Markenpräsenz, qualifizierte Nachfrage und wiederholbares Wachstum.", nullable=False)
    hero_lead_en = db.Column(db.Text, default="AI video production, digital humans, content systems and automation designed to create clear brand presence, qualified demand and repeatable growth.", nullable=False)
    hero_point_1_de = db.Column(db.Text, default="Strategie, Creative Direction und Umsetzung bleiben abgestimmt.", nullable=False)
    hero_point_1_en = db.Column(db.Text, default="Strategy, creative direction and execution stay aligned.", nullable=False)
    hero_point_2_de = db.Column(db.Text, default="Eine Marke, ein Content-Engine, mehrere Formate.", nullable=False)
    hero_point_2_en = db.Column(db.Text, default="One brand, one content engine, multiple formats.", nullable=False)
    hero_point_3_de = db.Column(db.Text, default="Jeder Block führt zum nächsten klaren Schritt.", nullable=False)
    hero_point_3_en = db.Column(db.Text, default="Each block leads the visitor toward the next action.", nullable=False)
    hero_cta_primary_de = db.Column(db.String(255), default="AI Discovery starten", nullable=False)
    hero_cta_primary_en = db.Column(db.String(255), default="Start AI Discovery", nullable=False)
    hero_cta_secondary_de = db.Column(db.String(255), default="Leistungen ansehen", nullable=False)
    hero_cta_secondary_en = db.Column(db.String(255), default="Explore Services", nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AnalyticsEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_name = db.Column(db.String(120), nullable=False)
    page = db.Column(db.String(120), default="", nullable=False)
    lang = db.Column(db.String(10), default="de", nullable=False)
    label = db.Column(db.String(255), default="", nullable=False)
    meta_json = db.Column(db.Text, default="", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class DiscoveryAssessment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey("lead.id"), nullable=False)
    status = db.Column(db.String(20), default="yellow", nullable=False)
    score = db.Column(db.Integer, default=0, nullable=False)
    recommended_package = db.Column(db.String(50), default="", nullable=False)
    summary = db.Column(db.Text, default="", nullable=False)
    answers_json = db.Column(db.Text, default="", nullable=False)
    calendar_unlocked = db.Column(db.Boolean, default=False, nullable=False)
    reviewed_by = db.Column(db.String(255), default="", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    lead = db.relationship("Lead", backref=db.backref("discoveries", lazy=True, order_by="DiscoveryAssessment.created_at.desc()"))


class CrmGlossaryTerm(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    language = db.Column(db.String(10), default="de", nullable=False)
    term = db.Column(db.String(255), nullable=False)
    definition = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(120), default="general", nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    updated_by = db.Column(db.String(255), default="", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class InternalCalendarSlot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    starts_at = db.Column(db.DateTime, nullable=False, index=True)
    ends_at = db.Column(db.DateTime, nullable=False)
    is_available = db.Column(db.Boolean, default=True, nullable=False)
    created_by = db.Column(db.String(255), default="system", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class InternalCalendarBooking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    slot_id = db.Column(db.Integer, db.ForeignKey("internal_calendar_slot.id"), nullable=False)
    lead_id = db.Column(db.Integer, db.ForeignKey("lead.id"), nullable=False)
    client_name = db.Column(db.String(255), nullable=False)
    client_email = db.Column(db.String(255), nullable=False)
    note = db.Column(db.Text, default="", nullable=False)
    source = db.Column(db.String(120), default="chatbot", nullable=False)
    status = db.Column(db.String(50), default="booked", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    slot = db.relationship("InternalCalendarSlot", backref=db.backref("bookings", lazy=True))
    lead = db.relationship("Lead", backref=db.backref("calendar_bookings", lazy=True, order_by="InternalCalendarBooking.created_at.desc()"))


class CrmAiReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey("lead.id"), nullable=False)
    summary = db.Column(db.Text, nullable=False)
    recommended_action = db.Column(db.Text, default="", nullable=False)
    created_by = db.Column(db.String(120), default="crm_assistant", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    lead = db.relationship("Lead", backref=db.backref("ai_reports", lazy=True, order_by="CrmAiReport.created_at.desc()"))


class InternalCalendarSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    day_start_hour = db.Column(db.Integer, default=9, nullable=False)
    day_end_hour = db.Column(db.Integer, default=18, nullable=False)
    slot_duration_minutes = db.Column(db.Integer, default=90, nullable=False)
    slot_interval_minutes = db.Column(db.Integer, default=120, nullable=False)
    weekdays_csv = db.Column(db.String(32), default="0,1,2,3,4", nullable=False)
    horizon_days = db.Column(db.Integer, default=90, nullable=False)
    updated_by = db.Column(db.String(255), default="system", nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
