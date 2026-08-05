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
