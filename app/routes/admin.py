import json
from datetime import datetime
from datetime import timedelta
from pathlib import Path
import uuid

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from slugify import slugify
from werkzeug.utils import secure_filename

from ..extensions import db
from ..models import (
    AnalyticsEvent,
    AssistantInstructionSettings,
    BlogAutomationSettings,
    BlogPost,
    BlogTopic,
    CrmAiReport,
    CrmGlossaryTerm,
    DiscoveryAssessment,
    HomePageHeroSettings,
    InternalCalendarSettings,
    InternalCalendarSlot,
    Lead,
    LeadMessage,
    ServicePageSettings,
    YouTubeLink,
)
from ..services.ai_service import (
    BLOG_AI_ACT_POLICY,
    EU_AI_ACT_PRIORITY_POLICY,
    generate_blog_post,
    generate_crm_hint,
    normalize_blog_language,
)
from ..services.blog_scheduler import import_from_rss_sources
from ..services.services_content import default_services_copy, parse_services_copy, update_services_copy_from_form
from ..services.storage import s3_enabled, upload_bytes_to_s3


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")
SERVICES_CMS_TABS = {"tab-media", "tab-de", "tab-en", "tab-flow"}
HOME_HERO_TABS = {"tab-media", "tab-de", "tab-en"}


def _save_uploaded_static_file(file_storage, folder: str, allowed_ext: set[str]) -> str:
    if not file_storage or not getattr(file_storage, "filename", ""):
        return ""

    raw_name = secure_filename(file_storage.filename)
    ext = Path(raw_name).suffix.lower()
    if not ext or ext not in allowed_ext:
        return ""

    unique_name = f"{Path(raw_name).stem}-{uuid.uuid4().hex[:10]}{ext}"
    payload = file_storage.read()
    if not payload:
        return ""

    relative_key = f"{folder.strip('/')}/{unique_name}".replace("\\", "/")

    if s3_enabled():
        try:
            return upload_bytes_to_s3(payload, relative_key=relative_key, content_type=file_storage.mimetype)
        except Exception as exc:
            current_app.logger.exception("S3 upload failed, falling back to local storage: %s", exc)

    static_root = Path(current_app.root_path) / "static"
    target_dir = static_root / folder
    target_dir.mkdir(parents=True, exist_ok=True)
    save_path = target_dir / unique_name
    save_path.write_bytes(payload)

    return relative_key


def _admin_required():
    return current_user.is_authenticated and current_user.is_admin


def _lead_crm_context(lead: Lead, message_limit: int = 25) -> str:
    recent_messages = (
        LeadMessage.query.filter_by(lead_id=lead.id)
        .order_by(LeadMessage.created_at.desc())
        .limit(max(5, min(100, message_limit)))
        .all()
    )
    ordered_messages = list(reversed(recent_messages))
    message_lines = [
        f"- {item.created_at.strftime('%Y-%m-%d %H:%M')} [{item.channel}/{item.direction}] {item.body}"
        for item in ordered_messages
    ]

    latest_discovery = (
        DiscoveryAssessment.query.filter_by(lead_id=lead.id)
        .order_by(DiscoveryAssessment.created_at.desc())
        .first()
    )
    if latest_discovery:
        discovery_line = (
            "Discovery: "
            f"status={latest_discovery.status}, "
            f"score={latest_discovery.score}, "
            f"package={latest_discovery.recommended_package or '-'}, "
            f"summary={latest_discovery.summary or '-'}"
        )
    else:
        discovery_line = "Discovery: -"

    return "\n".join([discovery_line, "Messages:", *message_lines])


def _calendar_weekdays_from_csv(csv_value: str) -> set[int]:
    values = {int(x.strip()) for x in (csv_value or "").split(",") if x.strip().isdigit()}
    return values or {0, 1, 2, 3, 4}


def _regenerate_future_calendar_slots(settings: InternalCalendarSettings, actor: str) -> int:
    now = datetime.utcnow()

    # Remove only future slots that are still free; keep already booked slots.
    free_slots = InternalCalendarSlot.query.filter(
        InternalCalendarSlot.starts_at >= now,
        InternalCalendarSlot.is_available.is_(True),
    ).all()
    for slot in free_slots:
        if not slot.bookings:
            db.session.delete(slot)

    weekdays = _calendar_weekdays_from_csv(settings.weekdays_csv)
    start_hour = max(0, min(23, settings.day_start_hour))
    end_hour = max(start_hour + 1, min(24, settings.day_end_hour))
    duration = max(15, settings.slot_duration_minutes)
    interval = max(duration, settings.slot_interval_minutes)
    horizon = max(1, min(180, settings.horizon_days))

    generated = 0
    day = now.date()
    end_date = (now + timedelta(days=horizon)).date()
    while day <= end_date:
        if day.weekday() in weekdays:
            minute_cursor = start_hour * 60
            day_end_minutes = end_hour * 60
            while minute_cursor + duration <= day_end_minutes:
                starts_at = datetime(day.year, day.month, day.day, minute_cursor // 60, minute_cursor % 60, 0)
                if starts_at > now:
                    exists = InternalCalendarSlot.query.filter_by(starts_at=starts_at).first()
                    if not exists:
                        db.session.add(
                            InternalCalendarSlot(
                                starts_at=starts_at,
                                ends_at=starts_at + timedelta(minutes=duration),
                                is_available=True,
                                created_by=actor or "admin",
                            )
                        )
                        generated += 1
                minute_cursor += interval
        day += timedelta(days=1)

    return generated


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
        "events": AnalyticsEvent.query.count(),
        "discoveries": DiscoveryAssessment.query.count(),
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


@admin_bp.get("/services-content")
@login_required
def services_content_settings():
    settings = ServicePageSettings.query.first()
    if not settings:
        settings = ServicePageSettings()
        db.session.add(settings)
        db.session.commit()
    services_copy = parse_services_copy(settings.services_copy_json)
    requested_tab = (request.args.get("tab") or "").strip()
    initial_tab = requested_tab if requested_tab in SERVICES_CMS_TABS else "tab-media"
    return render_template(
        "admin/services_content.html",
        settings=settings,
        services_copy=services_copy,
        initial_tab=initial_tab,
    )


@admin_bp.post("/services-content")
@login_required
def services_content_settings_save():
    settings = ServicePageSettings.query.first()
    if not settings:
        settings = ServicePageSettings()
        db.session.add(settings)

    settings.hero_media = (request.form.get("hero_media") or "").strip() or settings.hero_media
    settings.digital_human_media = (request.form.get("digital_human_media") or "").strip() or settings.digital_human_media
    settings.story_poster = (request.form.get("story_poster") or "").strip() or settings.story_poster
    settings.story_video_01 = (request.form.get("story_video_01") or "").strip()
    settings.story_video_02 = (request.form.get("story_video_02") or "").strip()
    settings.story_video_03 = (request.form.get("story_video_03") or "").strip()
    settings.strategy_photo = (request.form.get("strategy_photo") or "").strip() or settings.strategy_photo
    settings.discovery_url = (request.form.get("discovery_url") or "").strip() or "/contact"
    settings.services_copy_json = update_services_copy_from_form(request.form, settings.services_copy_json)
    active_tab = (request.form.get("active_tab") or "").strip()
    safe_tab = active_tab if active_tab in SERVICES_CMS_TABS else "tab-media"

    image_ext = {".jpg", ".jpeg", ".png", ".webp", ".avif", ".gif"}
    video_ext = {".mp4", ".webm"}

    hero_uploaded = _save_uploaded_static_file(request.files.get("hero_media_file"), "uploads/services", image_ext)
    if hero_uploaded:
        settings.hero_media = hero_uploaded

    digital_uploaded = _save_uploaded_static_file(request.files.get("digital_human_media_file"), "uploads/services", image_ext)
    if digital_uploaded:
        settings.digital_human_media = digital_uploaded

    poster_uploaded = _save_uploaded_static_file(request.files.get("story_poster_file"), "uploads/services", image_ext)
    if poster_uploaded:
        settings.story_poster = poster_uploaded

    strategy_uploaded = _save_uploaded_static_file(request.files.get("strategy_photo_file"), "uploads/services", image_ext)
    if strategy_uploaded:
        settings.strategy_photo = strategy_uploaded

    video_01_uploaded = _save_uploaded_static_file(request.files.get("story_video_01_file"), "uploads/services", video_ext)
    if video_01_uploaded:
        settings.story_video_01 = video_01_uploaded
    video_02_uploaded = _save_uploaded_static_file(request.files.get("story_video_02_file"), "uploads/services", video_ext)
    if video_02_uploaded:
        settings.story_video_02 = video_02_uploaded
    video_03_uploaded = _save_uploaded_static_file(request.files.get("story_video_03_file"), "uploads/services", video_ext)
    if video_03_uploaded:
        settings.story_video_03 = video_03_uploaded

    db.session.commit()
    flash("Налаштування сторінки Services збережено.", "success")
    return redirect(url_for("admin.services_content_settings", tab=safe_tab))


@admin_bp.post("/services-content/reset-copy")
@login_required
def services_content_reset_copy():
    settings = ServicePageSettings.query.first()
    if not settings:
        settings = ServicePageSettings()
        db.session.add(settings)

    settings.services_copy_json = json.dumps(default_services_copy(), ensure_ascii=False)
    active_tab = (request.form.get("active_tab") or "").strip()
    safe_tab = active_tab if active_tab in SERVICES_CMS_TABS else "tab-media"
    db.session.commit()
    flash("Тексти сторінки Services скинуто до значень за замовчуванням.", "success")
    return redirect(url_for("admin.services_content_settings", tab=safe_tab))


@admin_bp.get("/home-hero")
@login_required
def home_hero_settings():
    settings = HomePageHeroSettings.query.first()
    if not settings:
        settings = HomePageHeroSettings()
        db.session.add(settings)
        db.session.commit()

    requested_tab = (request.args.get("tab") or "").strip()
    initial_tab = requested_tab if requested_tab in HOME_HERO_TABS else "tab-media"
    return render_template("admin/home_hero.html", settings=settings, initial_tab=initial_tab)


@admin_bp.post("/home-hero")
@login_required
def home_hero_settings_save():
    settings = HomePageHeroSettings.query.first()
    if not settings:
        settings = HomePageHeroSettings()
        db.session.add(settings)

    for field_name in [
        "hero_background",
        "hero_image_main",
        "hero_image_secondary",
        "hero_eyebrow_de",
        "hero_eyebrow_en",
        "hero_title_de",
        "hero_title_en",
        "hero_lead_de",
        "hero_lead_en",
        "hero_point_1_de",
        "hero_point_1_en",
        "hero_point_2_de",
        "hero_point_2_en",
        "hero_point_3_de",
        "hero_point_3_en",
        "hero_cta_primary_de",
        "hero_cta_primary_en",
        "hero_cta_secondary_de",
        "hero_cta_secondary_en",
    ]:
        value = (request.form.get(field_name) or "").strip()
        if value:
            setattr(settings, field_name, value)

    image_ext = {".jpg", ".jpeg", ".png", ".webp", ".avif", ".gif"}
    video_ext = {".mp4", ".webm"}
    bg_uploaded = _save_uploaded_static_file(request.files.get("hero_background_file"), "uploads/home", image_ext)
    if bg_uploaded:
        settings.hero_background = bg_uploaded

    main_uploaded = _save_uploaded_static_file(request.files.get("hero_image_main_file"), "uploads/home", image_ext | video_ext)
    if main_uploaded:
        settings.hero_image_main = main_uploaded

    secondary_uploaded = _save_uploaded_static_file(request.files.get("hero_image_secondary_file"), "uploads/home", image_ext)
    if secondary_uploaded:
        settings.hero_image_secondary = secondary_uploaded

    active_tab = (request.form.get("active_tab") or "").strip()
    safe_tab = active_tab if active_tab in HOME_HERO_TABS else "tab-media"
    db.session.commit()
    flash("Налаштування верхнього блоку головної сторінки збережено.", "success")
    return redirect(url_for("admin.home_hero_settings", tab=safe_tab))


@admin_bp.get("/analytics")
@login_required
def analytics_events():
    events = AnalyticsEvent.query.order_by(AnalyticsEvent.created_at.desc()).limit(200).all()
    return render_template("admin/analytics.html", events=events)


@admin_bp.get("/calendar-settings")
@login_required
def calendar_settings():
    settings = InternalCalendarSettings.query.first()
    if not settings:
        settings = InternalCalendarSettings(updated_by=current_user.email)
        db.session.add(settings)
        db.session.commit()
    return render_template("admin/calendar_settings.html", settings=settings)


@admin_bp.post("/calendar-settings")
@login_required
def calendar_settings_save():
    settings = InternalCalendarSettings.query.first()
    if not settings:
        settings = InternalCalendarSettings()
        db.session.add(settings)

    def _int_field(name: str, default: int) -> int:
        try:
            return int((request.form.get(name) or str(default)).strip())
        except ValueError:
            return default

    settings.day_start_hour = max(0, min(23, _int_field("day_start_hour", 9)))
    settings.day_end_hour = max(settings.day_start_hour + 1, min(24, _int_field("day_end_hour", 18)))
    settings.slot_duration_minutes = max(15, min(180, _int_field("slot_duration_minutes", 90)))
    settings.slot_interval_minutes = max(settings.slot_duration_minutes, min(240, _int_field("slot_interval_minutes", 120)))
    settings.horizon_days = max(1, min(180, _int_field("horizon_days", 90)))
    settings.weekdays_csv = (request.form.get("weekdays_csv") or "0,1,2,3,4").strip()
    settings.updated_by = current_user.email

    generated = _regenerate_future_calendar_slots(settings, actor=current_user.email)
    db.session.commit()
    flash(f"Налаштування календаря збережено. Згенеровано нових слотів: {generated}.", "success")
    return redirect(url_for("admin.calendar_settings"))


@admin_bp.get("/blog")
@login_required
def blog_admin_list():
    posts = BlogPost.query.order_by(BlogPost.created_at.desc()).all()
    topics = BlogTopic.query.order_by(BlogTopic.created_at.desc()).all()
    settings = BlogAutomationSettings.query.first()
    if not settings:
        settings = BlogAutomationSettings(
            blog_custom_instructions="",
            rss_sources="",
            auto_from_rss_enabled=False,
            max_rss_items_per_run=2,
        )
        db.session.add(settings)
        db.session.commit()

    return render_template(
        "admin/blog_posts.html",
        posts=posts,
        topics=topics,
        blog_settings=settings,
        blog_policy_text=BLOG_AI_ACT_POLICY,
    )


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


@admin_bp.get("/blog/<int:post_id>/edit")
@login_required
def blog_edit(post_id):
    post = BlogPost.query.get_or_404(post_id)
    return render_template("admin/blog_edit.html", post=post)


@admin_bp.post("/blog/<int:post_id>/edit")
@login_required
def blog_edit_save(post_id):
    post = BlogPost.query.get_or_404(post_id)

    title = (request.form.get("title") or "").strip()
    excerpt = (request.form.get("excerpt") or "").strip()
    content = (request.form.get("content") or "").strip()
    seo_keywords = (request.form.get("seo_keywords") or "").strip()
    status = (request.form.get("status") or "draft").strip()
    slug_input = (request.form.get("slug") or "").strip()

    if not title or not content:
        flash("Потрібно заповнити заголовок і контент.", "error")
        return redirect(url_for("admin.blog_edit", post_id=post.id))

    base_slug = slugify(slug_input or title)
    slug = base_slug
    idx = 1
    while BlogPost.query.filter(BlogPost.slug == slug, BlogPost.id != post.id).first():
        idx += 1
        slug = f"{base_slug}-{idx}"

    post.title = title
    post.slug = slug
    post.excerpt = excerpt or content[:180]
    post.content = content
    post.seo_keywords = seo_keywords[:500]
    post.status = status

    if status == "published":
        post.published_at = post.published_at or datetime.utcnow()
    else:
        post.published_at = None

    db.session.commit()
    flash("Статтю оновлено.", "success")
    return redirect(url_for("admin.blog_admin_list"))


@admin_bp.post("/blog/<int:post_id>/delete")
@login_required
def blog_delete(post_id):
    post = BlogPost.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    flash("Статтю видалено.", "success")
    return redirect(url_for("admin.blog_admin_list"))


@admin_bp.post("/blog/generate")
@login_required
def blog_generate_ai():
    topic = (request.form.get("topic") or "").strip()
    language = normalize_blog_language(request.form.get("language") or "de")
    status = (request.form.get("status") or "draft").strip()

    if not topic:
        flash("Для AI-генерації потрібно вказати тему.", "error")
        return redirect(url_for("admin.blog_admin_list"))

    settings = BlogAutomationSettings.query.first()
    custom_instructions = settings.blog_custom_instructions if settings else ""

    post_data = generate_blog_post(
        api_key=current_app.config["OPENAI_API_KEY"],
        model=current_app.config.get("BLOG_AI_MODEL") or current_app.config["OPENAI_MODEL"],
        topic=topic,
        language=language,
        custom_instructions=custom_instructions,
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


@admin_bp.get("/assistant")
@login_required
def assistant_settings():
    settings = AssistantInstructionSettings.query.first()
    if not settings:
        settings = AssistantInstructionSettings(
            custom_instructions="",
            widget_auto_open_enabled=True,
            widget_auto_open_delay_seconds=40,
            widget_greeting_text="Hallo und willkommen bei ASAI Studio. Ich kann Ihnen direkt freie Beratungstermine zeigen oder beim passenden Paket helfen.",
        )
        db.session.add(settings)
        db.session.commit()

    return render_template(
        "admin/assistant_settings.html",
        settings=settings,
        policy_text=EU_AI_ACT_PRIORITY_POLICY,
    )


@admin_bp.post("/assistant")
@login_required
def assistant_settings_save():
    raw_text = (request.form.get("custom_instructions") or "").strip()
    widget_auto_open_enabled = (request.form.get("widget_auto_open_enabled") or "").strip().lower() in {"1", "on", "true", "yes"}
    widget_greeting_text = (request.form.get("widget_greeting_text") or "").strip()
    delay_raw = (request.form.get("widget_auto_open_delay_seconds") or "40").strip()

    try:
        widget_auto_open_delay_seconds = int(delay_raw)
    except ValueError:
        widget_auto_open_delay_seconds = 40

    widget_auto_open_delay_seconds = max(5, min(300, widget_auto_open_delay_seconds))

    if len(widget_greeting_text) > 1200:
        flash("Привітання занадто довге. Максимум 1200 символів.", "error")
        return redirect(url_for("admin.assistant_settings"))

    if not widget_greeting_text:
        widget_greeting_text = (
            "Hallo und willkommen bei ASAI Studio. "
            "Ich kann Ihnen direkt freie Beratungstermine zeigen oder beim passenden Paket helfen."
        )
    lowered = raw_text.lower()
    blocked_phrases = [
        "ignore previous instructions",
        "ignore all safety",
        "bypass safety",
        "disable safety",
        "umgehe sicherheit",
        "ignoriere die anweisungen",
    ]
    if any(phrase in lowered for phrase in blocked_phrases):
        flash("Інструкції містять спробу обійти правила безпеки. Збереження заблоковано.", "error")
        return redirect(url_for("admin.assistant_settings"))

    if len(raw_text) > 4000:
        flash("Інструкції занадто довгі. Максимум 4000 символів.", "error")
        return redirect(url_for("admin.assistant_settings"))

    settings = AssistantInstructionSettings.query.first()
    if not settings:
        settings = AssistantInstructionSettings(
            custom_instructions=raw_text,
            widget_auto_open_enabled=widget_auto_open_enabled,
            widget_auto_open_delay_seconds=widget_auto_open_delay_seconds,
            widget_greeting_text=widget_greeting_text,
        )
        db.session.add(settings)
    else:
        settings.custom_instructions = raw_text
        settings.widget_auto_open_enabled = widget_auto_open_enabled
        settings.widget_auto_open_delay_seconds = widget_auto_open_delay_seconds
        settings.widget_greeting_text = widget_greeting_text

    db.session.commit()
    flash("Налаштування AI-асистента збережено.", "success")
    return redirect(url_for("admin.assistant_settings"))


@admin_bp.post("/blog/topic")
@login_required
def add_blog_topic():
    topic = (request.form.get("topic") or "").strip()
    language = normalize_blog_language(request.form.get("language") or "de")
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


@admin_bp.post("/blog/settings")
@login_required
def blog_settings_save():
    settings = BlogAutomationSettings.query.first()
    if not settings:
        settings = BlogAutomationSettings()
        db.session.add(settings)

    instructions = (request.form.get("blog_custom_instructions") or "").strip()
    rss_sources = (request.form.get("rss_sources") or "").strip()
    auto_from_rss_enabled = (request.form.get("auto_from_rss_enabled") or "") == "on"
    max_items = int(request.form.get("max_rss_items_per_run") or 2)

    blocked_phrases = [
        "ignore previous instructions",
        "ignore all safety",
        "bypass safety",
        "disable safety",
        "umgehe sicherheit",
        "ignoriere die anweisungen",
    ]
    lowered = instructions.lower()
    if any(phrase in lowered for phrase in blocked_phrases):
        flash("Інструкції блогу містять спробу обійти правила безпеки.", "error")
        return redirect(url_for("admin.blog_admin_list"))

    settings.blog_custom_instructions = instructions[:4000]
    settings.rss_sources = rss_sources
    settings.auto_from_rss_enabled = auto_from_rss_enabled
    settings.max_rss_items_per_run = max(1, min(10, max_items))
    db.session.commit()

    flash("Налаштування блогу збережено.", "success")
    return redirect(url_for("admin.blog_admin_list"))


@admin_bp.post("/blog/rss/import")
@login_required
def blog_rss_import_now():
    created_count = import_from_rss_sources(current_app)
    flash(f"Імпорт з RSS завершено. Нових статей: {created_count}.", "success")
    return redirect(url_for("admin.blog_admin_list"))


@admin_bp.get("/crm")
@login_required
def crm_list():
    leads = Lead.query.order_by(Lead.created_at.desc()).all()
    return render_template("admin/clients.html", leads=leads)


@admin_bp.get("/crm/discovery")
@login_required
def crm_discovery_list():
    assessments = DiscoveryAssessment.query.order_by(DiscoveryAssessment.created_at.desc()).all()
    return render_template("admin/discovery_list.html", assessments=assessments)


@admin_bp.post("/crm/discovery/<int:assessment_id>/status")
@login_required
def crm_discovery_update_status(assessment_id):
    assessment = DiscoveryAssessment.query.get_or_404(assessment_id)
    status = (request.form.get("status") or "yellow").strip().lower()
    if status not in {"green", "yellow", "red"}:
        flash("Невірний статус Discovery.", "error")
        return redirect(url_for("admin.crm_discovery_list"))

    assessment.status = status
    assessment.calendar_unlocked = status == "green"
    assessment.reviewed_by = current_user.email
    db.session.commit()
    flash("Статус Discovery оновлено.", "success")
    return redirect(url_for("admin.crm_discovery_list"))


@admin_bp.get("/crm/terms")
@login_required
def crm_terms_list():
    terms = CrmGlossaryTerm.query.order_by(CrmGlossaryTerm.updated_at.desc()).all()
    return render_template("admin/crm_terms.html", terms=terms)


@admin_bp.post("/crm/terms")
@login_required
def crm_terms_create():
    term = (request.form.get("term") or "").strip()
    definition = (request.form.get("definition") or "").strip()
    language = (request.form.get("language") or "de").strip().lower()
    category = (request.form.get("category") or "general").strip()

    if not term or not definition:
        flash("Термін і визначення є обов'язковими.", "error")
        return redirect(url_for("admin.crm_terms_list"))

    if language not in {"de", "en"}:
        language = "de"

    item = CrmGlossaryTerm(
        language=language,
        term=term,
        definition=definition,
        category=category,
        is_active=True,
        updated_by=current_user.email,
    )
    db.session.add(item)
    db.session.commit()
    flash("Термін CRM додано.", "success")
    return redirect(url_for("admin.crm_terms_list"))


@admin_bp.post("/crm/terms/<int:term_id>/toggle")
@login_required
def crm_terms_toggle(term_id):
    item = CrmGlossaryTerm.query.get_or_404(term_id)
    item.is_active = not item.is_active
    item.updated_by = current_user.email
    db.session.commit()
    flash("Статус терміна оновлено.", "success")
    return redirect(url_for("admin.crm_terms_list"))


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
    chatbot_messages = (
        LeadMessage.query.filter_by(lead_id=lead.id, channel="chatbot_widget")
        .order_by(LeadMessage.created_at.asc())
        .all()
    )
    return render_template("admin/client_detail.html", lead=lead, ai_hint=None, chatbot_messages=chatbot_messages)


@admin_bp.post("/crm/<int:lead_id>/discovery")
@login_required
def crm_add_discovery(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    status = (request.form.get("status") or "yellow").strip().lower()
    if status not in {"green", "yellow", "red"}:
        status = "yellow"

    score_raw = (request.form.get("score") or "0").strip()
    try:
        score = max(0, min(100, int(score_raw)))
    except ValueError:
        score = 0

    assessment = DiscoveryAssessment(
        lead_id=lead.id,
        status=status,
        score=score,
        recommended_package=(request.form.get("recommended_package") or "").strip(),
        summary=(request.form.get("summary") or "").strip(),
        answers_json=(request.form.get("answers_json") or "").strip(),
        calendar_unlocked=status == "green",
        reviewed_by=current_user.email,
    )
    db.session.add(assessment)
    db.session.commit()
    flash("Оцінку дискавері додано.", "success")
    return redirect(url_for("admin.crm_detail", lead_id=lead.id))


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
    action = (request.form.get("action") or "hint").strip().lower()
    question = (request.form.get("question") or "").strip()
    if not question and action == "summary":
        question = "Сделай краткое саммари переписки клиента: ключевой запрос, возражения, риск, следующий шаг."

    if not question:
        flash("Потрібно вказати запитання.", "error")
        return redirect(url_for("admin.crm_detail", lead_id=lead.id))

    crm_context = _lead_crm_context(lead)

    ai_hint = generate_crm_hint(
        api_key=current_app.config["OPENAI_API_KEY"],
        model=current_app.config["OPENAI_MODEL"],
        lead_name=lead.name,
        lead_stage=lead.stage,
        question=question,
        conversation_context=crm_context,
    )
    chatbot_messages = (
        LeadMessage.query.filter_by(lead_id=lead.id, channel="chatbot_widget")
        .order_by(LeadMessage.created_at.asc())
        .all()
    )
    return render_template("admin/client_detail.html", lead=lead, ai_hint=ai_hint, chatbot_messages=chatbot_messages)


@admin_bp.post("/crm/<int:lead_id>/report")
@login_required
def crm_generate_report(lead_id):
    lead = Lead.query.get_or_404(lead_id)
    question = (request.form.get("question") or "").strip() or "Create concise CRM report and next action."
    crm_context = _lead_crm_context(lead)

    summary = generate_crm_hint(
        api_key=current_app.config["OPENAI_API_KEY"],
        model=current_app.config["OPENAI_MODEL"],
        lead_name=lead.name,
        lead_stage=lead.stage,
        question=question,
        conversation_context=crm_context,
    )
    report = CrmAiReport(
        lead_id=lead.id,
        summary=summary,
        recommended_action="Зв'яжіться з клієнтом протягом 24 годин та підтвердіть наступний крок.",
        created_by="crm_assistant",
    )
    db.session.add(report)
    db.session.commit()

    flash("AI-звіт для CRM згенеровано та збережено.", "success")
    return redirect(url_for("admin.crm_detail", lead_id=lead.id))
