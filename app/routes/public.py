from urllib.parse import parse_qs, urlparse

from flask import Blueprint, current_app, flash, g, redirect, render_template, request, url_for
from markdown import markdown
from werkzeug.routing import BuildError

from ..extensions import db
from ..i18n import translate
from ..models import BlogPost, Lead, LeadMessage, YouTubeLink


public_bp = Blueprint("public", __name__)

SUPPORTED_LANGS = {"de", "en"}


@public_bp.before_app_request
def resolve_language():
    selected = (request.args.get("lang") or request.cookies.get("lang") or "de").lower()
    g.lang = selected if selected in SUPPORTED_LANGS else "de"


@public_bp.after_app_request
def store_language(response):
    lang_from_query = (request.args.get("lang") or "").lower()
    if lang_from_query in SUPPORTED_LANGS:
        response.set_cookie("lang", lang_from_query, max_age=60 * 60 * 24 * 365)
    return response


@public_bp.app_template_filter("markdown")
def markdown_filter(text):
    return markdown(text or "")


@public_bp.context_processor
def inject_brand():
    def t(key: str) -> str:
        return translate(getattr(g, "lang", "de"), key)

    def lang_url(target_lang: str) -> str:
        target_lang = (target_lang or "de").lower()
        if target_lang not in SUPPORTED_LANGS:
            target_lang = "de"

        endpoint = request.endpoint
        if not endpoint:
            return f"{request.path}?lang={target_lang}"

        values = dict(request.view_args or {})
        for key, value in request.args.items():
            if key != "lang":
                values[key] = value
        values["lang"] = target_lang

        try:
            return url_for(endpoint, **values)
        except BuildError:
            return f"{request.path}?lang={target_lang}"

    return {
        "brand_name": current_app.config["PUBLIC_BRAND_NAME"],
        "lang": getattr(g, "lang", "de"),
        "t": t,
        "lang_url": lang_url,
    }


@public_bp.get("/")
def home():
    links = YouTubeLink.query.order_by(YouTubeLink.slot.asc()).all()

    def youtube_video_id(url: str) -> str:
        parsed = urlparse(url or "")
        if "youtu.be" in parsed.netloc:
            return parsed.path.strip("/").split("/")[0]
        if "youtube.com" in parsed.netloc:
            query = parse_qs(parsed.query)
            if query.get("v"):
                return query["v"][0]
            path_parts = [part for part in parsed.path.split("/") if part]
            if len(path_parts) >= 2 and path_parts[0] in {"shorts", "embed"}:
                return path_parts[1]
        return ""

    featured_videos = []
    for link in links[:4]:
        video_id = youtube_video_id(link.url)
        featured_videos.append(
            {
                "title": link.title,
                "url": link.url,
                "slot": link.slot,
                "thumbnail": f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg" if video_id else "",
            }
        )

    return render_template("public/home.html", links=links, featured_videos=featured_videos)


@public_bp.get("/about")
def about():
    return render_template("public/about.html")


@public_bp.get("/services")
def services():
    return render_template("public/services.html")


@public_bp.get("/programs")
def programs():
    return render_template("public/programs.html")


@public_bp.get("/contact")
def contact():
    return render_template("public/contact.html")


@public_bp.post("/contact")
def contact_submit():
    name = (request.form.get("name") or "").strip()
    company = (request.form.get("company") or "").strip()
    email = (request.form.get("email") or "").strip()
    phone = (request.form.get("phone") or "").strip()
    service_interest = (request.form.get("service_interest") or "").strip()
    preferred_language = (request.form.get("preferred_language") or "").strip()
    timeline = (request.form.get("timeline") or "").strip()
    message = (request.form.get("message") or "").strip()
    lang = getattr(g, "lang", "de")

    if not name or not email or not message:
        flash(translate(lang, "contact.form_error"), "error")
        return redirect(url_for("public.contact", lang=lang))

    structured_lines = [
        f"Website inquiry ({lang})",
        f"Name: {name}",
        f"Company: {company or '-'}",
        f"Email: {email}",
        f"Phone: {phone or '-'}",
        f"Service interest: {service_interest or '-'}",
        f"Preferred language: {preferred_language or '-'}",
        f"Timeline: {timeline or '-'}",
        "",
        "Message:",
        message,
    ]
    structured_message = "\n".join(structured_lines)

    lead = Lead(
        name=name,
        email=email,
        phone=phone,
        source=f"website-contact-form-{lang}",
        stage="new",
        notes=structured_message,
    )
    db.session.add(lead)
    db.session.flush()

    db.session.add(
        LeadMessage(
            lead_id=lead.id,
            direction="incoming",
            channel="website_form",
            body=structured_message,
        )
    )
    db.session.commit()

    flash(translate(lang, "contact.form_success"), "success")
    return redirect(url_for("public.contact", lang=lang))


@public_bp.get("/blog")
def blog_list():
    posts = (
        BlogPost.query.filter_by(status="published")
        .order_by(BlogPost.published_at.desc().nullslast(), BlogPost.created_at.desc())
        .all()
    )
    return render_template("public/blog_list.html", posts=posts)


@public_bp.get("/blog/<slug>")
def blog_post(slug):
    post = BlogPost.query.filter_by(slug=slug, status="published").first_or_404()
    return render_template("public/blog_post.html", post=post)


@public_bp.get("/impressum")
def impressum():
    return render_template("public/impressum.html")


@public_bp.get("/privacy")
def privacy():
    return render_template("public/privacy.html")


@public_bp.get("/terms")
def terms():
    return render_template("public/terms.html")


@public_bp.get("/health")
def health():
    return {"status": "ok"}
