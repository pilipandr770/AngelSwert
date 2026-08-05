from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from slugify import slugify

from ..extensions import db
from ..models import BlogPost, BlogTopic
from .ai_service import generate_blog_post


scheduler = BackgroundScheduler()


def run_scheduled_blog_generation(app):
    with app.app_context():
        topics = BlogTopic.query.filter(
            BlogTopic.is_active.is_(True),
            BlogTopic.next_run_at <= datetime.utcnow(),
        ).all()

        for topic in topics:
            post_data = generate_blog_post(
                api_key=app.config["OPENAI_API_KEY"],
                model=app.config["OPENAI_MODEL"],
                topic=topic.topic,
                language=topic.language,
            )

            base_slug = slugify(post_data["title"]) or slugify(topic.topic)
            slug = base_slug
            idx = 1
            while BlogPost.query.filter_by(slug=slug).first():
                idx += 1
                slug = f"{base_slug}-{idx}"

            post = BlogPost(
                title=post_data["title"],
                slug=slug,
                excerpt=post_data["excerpt"][:500],
                content=post_data["content"],
                seo_keywords=post_data["seo_keywords"][:500],
                status="published",
                published_at=datetime.utcnow(),
            )
            db.session.add(post)
            topic.schedule_next()

        if topics:
            db.session.commit()


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
