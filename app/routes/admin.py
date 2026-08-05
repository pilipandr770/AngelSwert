from datetime import datetime

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from slugify import slugify

from ..extensions import db
from ..models import BlogPost, BlogTopic, Lead, LeadMessage, YouTubeLink
from ..services.ai_service import generate_blog_post, generate_crm_hint


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def _admin_required():
    return current_user.is_authenticated and current_user.is_admin


@admin_bp.before_request
def check_admin_access():
    if request.endpoint in {"auth.login", "auth.login_post"}:
        return None
    if not _admin_required() and request.endpoint and request.endpoint.startswith("admin."):
        return redirect(url_for("auth.login"))
    return None


@admin_bp.get("/")
@login_required
def dashboard():
    if not current_user.is_admin:
        return redirect(url_for("auth.login"))

    stats = {
        "leads": Lead.query.count(),
        "published_posts": BlogPost.query.filter_by(status="published").count(),
        "draft_posts": BlogPost.query.filter_by(status="draft").count(),
        "topics": BlogTopic.query.filter_by(is_active=True).count(),
    }
    latest_leads = Lead.query.order_by(Lead.created_at.desc()).limit(5).all()
    return render_template("admin/dashboard.html", stats=stats, latest_leads=latest_leads)


@admin_bp.get("/youtube")
@login_required
def youtube_settings():
    links = YouTubeLink.query.order_by(YouTubeLink.slot.asc()).all()
    return render_template("admin/youtube_links.html", links=links)


@admin_bp.post("/youtube")
@login_required
def youtube_settings_save():
    for slot in range(1, 5):
        title = (request.form.get(f"title_{slot}") or "").strip()
        url = (request.form.get(f"url_{slot}") or "").strip()
        link = YouTubeLink.query.filter_by(slot=slot).first()
        if link and title and url:
            link.title = title
            link.url = url
    db.session.commit()
    flash("YouTube-посилання оновлено.", "success")
    return redirect(url_for("admin.youtube_settings"))


@admin_bp.get("/blog")
@login_required
def blog_admin_list():
    posts = BlogPost.query.order_by(BlogPost.created_at.desc()).all()
    topics = BlogTopic.query.order_by(BlogTopic.created_at.desc()).all()
    return render_template("admin/blog_posts.html", posts=posts, topics=topics)


@admin_bp.post("/blog/create")
@login_required
def blog_create_manual():
    title = (request.form.get("title") or "").strip()
    excerpt = (request.form.get("excerpt") or "").strip()
    content = (request.form.get("content") or "").strip()
    status = (request.form.get("status") or "draft").strip()

    if not title or not content:
        flash("Потрібно заповнити заголовок і контент.", "error")
        return redirect(url_for("admin.blog_admin_list"))

    base_slug = slugify(title)
    slug = base_slug
    idx = 1
    while BlogPost.query.filter_by(slug=slug).first():
        idx += 1
        slug = f"{base_slug}-{idx}"

    post = BlogPost(
        title=title,
        slug=slug,
        excerpt=excerpt or content[:180],
        content=content,
        status=status,
        published_at=datetime.utcnow() if status == "published" else None,
    )
    db.session.add(post)
    db.session.commit()
    flash("Статтю збережено.", "success")
    return redirect(url_for("admin.blog_admin_list"))


@admin_bp.post("/blog/generate")
@login_required
def blog_generate_ai():
    topic = (request.form.get("topic") or "").strip()
    language = (request.form.get("language") or "de").strip()
    status = (request.form.get("status") or "draft").strip()

    if not topic:
        flash("Для AI-генерації потрібно вказати тему.", "error")
        return redirect(url_for("admin.blog_admin_list"))

    post_data = generate_blog_post(
        api_key=current_app.config["OPENAI_API_KEY"],
        model=current_app.config["OPENAI_MODEL"],
        topic=topic,
        language=language,
    )

    base_slug = slugify(post_data["title"])
    slug = base_slug
    idx = 1
    while BlogPost.query.filter_by(slug=slug).first():
        idx += 1
        slug = f"{base_slug}-{idx}"

    post = BlogPost(
        title=post_data["title"],
        slug=slug,
        excerpt=post_data["excerpt"][:500] if post_data["excerpt"] else topic,
        content=post_data["content"],
        seo_keywords=post_data["seo_keywords"][:500],
        status=status,
        published_at=datetime.utcnow() if status == "published" else None,
    )
    db.session.add(post)
    db.session.commit()
    flash("AI-статтю згенеровано.", "success")
    return redirect(url_for("admin.blog_admin_list"))


@admin_bp.post("/blog/topic")
@login_required
def add_blog_topic():
    topic = (request.form.get("topic") or "").strip()
    language = (request.form.get("language") or "de").strip()
    frequency_hours = int(request.form.get("frequency_hours") or 72)

    if not topic:
        flash("Потрібно вказати тему.", "error")
        return redirect(url_for("admin.blog_admin_list"))

    schedule = BlogTopic(
        topic=topic,
        language=language,
        frequency_hours=max(1, frequency_hours),
        next_run_at=datetime.utcnow(),
        is_active=True,
    )
    db.session.add(schedule)
    db.session.commit()
    flash("Тему та розклад додано.", "success")
    return redirect(url_for("admin.blog_admin_list"))


@admin_bp.get("/crm")
@login_required
def crm_list():
    leads = Lead.query.order_by(Lead.created_at.desc()).all()
    return render_template("admin/clients.html", leads=leads)


@admin_bp.post("/crm/create")
@login_required
def crm_create():
    lead = Lead(
        name=(request.form.get("name") or "").strip(),
        email=(request.form.get("email") or "").strip(),
        phone=(request.form.get("phone") or "").strip(),
        source=(request.form.get("source") or "website").strip(),
        stage=(request.form.get("stage") or "new").strip(),
        notes=(request.form.get("notes") or "").strip(),
    )
    if not lead.name or not lead.email:
        flash("Ім'я та email є обов'язковими.", "error")
        return redirect(url_for("admin.crm_list"))

    db.session.add(lead)
    db.session.commit()
    flash("Ліда створено.", "success")
    return redirect(url_for("admin.crm_detail", lead_id=lead.id))


@admin_bp.get("/crm/<int:lead_id>")
@login_required
def crm_detail(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    return render_template("admin/client_detail.html", lead=lead, ai_hint=None)


@admin_bp.post("/crm/<int:lead_id>/message")
@login_required
def crm_add_message(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    message = LeadMessage(
        lead_id=lead.id,
        direction=(request.form.get("direction") or "outgoing").strip(),
        channel=(request.form.get("channel") or "email").strip(),
        body=(request.form.get("body") or "").strip(),
    )
    if not message.body:
        flash("Потрібно заповнити текст повідомлення.", "error")
        return redirect(url_for("admin.crm_detail", lead_id=lead.id))

    db.session.add(message)
    db.session.commit()
    flash("Повідомлення збережено.", "success")
    return redirect(url_for("admin.crm_detail", lead_id=lead.id))


@admin_bp.post("/crm/<int:lead_id>/ai")
@login_required
def crm_ai_hint(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    question = (request.form.get("question") or "").strip()
    if not question:
        flash("Потрібно вказати запитання.", "error")
        return redirect(url_for("admin.crm_detail", lead_id=lead.id))

    ai_hint = generate_crm_hint(
        api_key=current_app.config["OPENAI_API_KEY"],
        model=current_app.config["OPENAI_MODEL"],
        lead_name=lead.name,
        lead_stage=lead.stage,
        question=question,
    )
    return render_template("admin/client_detail.html", lead=lead, ai_hint=ai_hint)
