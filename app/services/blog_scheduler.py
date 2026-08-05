from datetime import datetime

import feedparser
from apscheduler.schedulers.background import BackgroundScheduler
from slugify import slugify

from ..extensions import db
from ..models import BlogAutomationSettings, BlogFeedEntry, BlogPost, BlogTopic
from .ai_service import generate_blog_post, normalize_blog_language, summarize_source_text


scheduler = BackgroundScheduler()


def _safe_slug(value: str, fallback: str) -> str:
    return slugify(value) or slugify(fallback) or f"post-{int(datetime.utcnow().timestamp())}"


def _build_unique_slug(base_value: str, fallback: str) -> str:
    base_slug = _safe_slug(base_value, fallback)
    slug = base_slug
    idx = 1
    while BlogPost.query.filter_by(slug=slug).first():
        idx += 1
        slug = f"{base_slug}-{idx}"
    return slug


def _create_post_from_generated(topic: str, post_data: dict, status: str = "published") -> None:
    slug = _build_unique_slug(post_data.get("title", topic), topic)
    post = BlogPost(
        title=post_data.get("title", topic),
        slug=slug,
        excerpt=(post_data.get("excerpt") or topic)[:500],
        content=post_data.get("content") or "",
        seo_keywords=(post_data.get("seo_keywords") or topic)[:500],
        status=status,
        published_at=datetime.utcnow() if status == "published" else None,
    )
    db.session.add(post)


def _iter_rss_sources(raw_text: str) -> list[str]:
    return [line.strip() for line in (raw_text or "").splitlines() if line.strip()]


def _entry_to_source_text(entry) -> str:
    title = (getattr(entry, "title", "") or "").strip()
    summary = (getattr(entry, "summary", "") or "").strip()
    content_parts = []
    for part in getattr(entry, "content", []) or []:
        value = (part.get("value") or "").strip() if isinstance(part, dict) else ""
        if value:
            content_parts.append(value)

    composed = "\n\n".join([title, summary, "\n".join(content_parts)]).strip()
    return composed


def import_from_rss_sources(app) -> int:
    with app.app_context():
        settings = BlogAutomationSettings.query.first()
        if not settings:
            return 0

        urls = _iter_rss_sources(settings.rss_sources)
        if not urls:
            return 0

        language = "de"
        max_items = max(1, min(10, settings.max_rss_items_per_run or 2))
        created_count = 0

        for feed_url in urls:
            if created_count >= max_items:
                break

            parsed = feedparser.parse(feed_url)
            entries = parsed.entries[: max_items * 2]
            for entry in entries:
                if created_count >= max_items:
                    break

                entry_id = (getattr(entry, "id", "") or getattr(entry, "link", "") or getattr(entry, "title", "")).strip()
                if not entry_id:
                    continue

                entry_key = f"{feed_url}|{entry_id}"[:500]
                if BlogFeedEntry.query.filter_by(entry_key=entry_key).first():
                    continue

                topic = (getattr(entry, "title", "") or "AI marketing news").strip()
                link = (getattr(entry, "link", "") or "").strip()
                source_text = _entry_to_source_text(entry)
                source_summary = summarize_source_text(source_text)
                source_hint = (
                    f"Feed source: {feed_url}. Source URL: {link}. Source summary: {source_summary}"
                    if link
                    else f"Feed source: {feed_url}. Source summary: {source_summary}"
                )

                post_data = generate_blog_post(
                    api_key=app.config["OPENAI_API_KEY"],
                    model=app.config.get("BLOG_AI_MODEL") or app.config["OPENAI_MODEL"],
                    topic=topic,
                    language=normalize_blog_language(language),
                    custom_instructions=settings.blog_custom_instructions,
                    source_hint=source_hint,
                )

                _create_post_from_generated(topic, post_data, status="published")
                db.session.add(
                    BlogFeedEntry(
                        entry_key=entry_key,
                        source_url=feed_url,
                        entry_title=topic[:500],
                        entry_link=link[:1024],
                    )
                )
                created_count += 1

        if created_count:
            db.session.commit()

        return created_count


def run_scheduled_blog_generation(app):
    with app.app_context():
        topics = BlogTopic.query.filter(
            BlogTopic.is_active.is_(True),
            BlogTopic.next_run_at <= datetime.utcnow(),
        ).all()
        settings = BlogAutomationSettings.query.first()
        custom_instructions = settings.blog_custom_instructions if settings else ""

        for topic in topics:
            post_data = generate_blog_post(
                api_key=app.config["OPENAI_API_KEY"],
                model=app.config.get("BLOG_AI_MODEL") or app.config["OPENAI_MODEL"],
                topic=topic.topic,
                language=normalize_blog_language(topic.language),
                custom_instructions=custom_instructions,
            )

            _create_post_from_generated(topic.topic, post_data, status="published")
            topic.schedule_next()

        if topics:
            db.session.commit()

        if settings and settings.auto_from_rss_enabled:
            import_from_rss_sources(app)


def init_scheduler(app):
    if not app.config.get("ENABLE_BLOG_SCHEDULER", True):
        return
    if scheduler.running:
        return

    scheduler.add_job(
        func=lambda: run_scheduled_blog_generation(app),
        trigger="interval",
        minutes=30,
        id="blog_generation",
        replace_existing=True,
    )
    scheduler.start()
