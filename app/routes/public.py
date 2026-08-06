from urllib.parse import parse_qs, urlparse
from urllib.request import urlopen
import json
import re

from flask import Blueprint, current_app, flash, g, redirect, render_template, request, url_for
from markdown import markdown
from werkzeug.routing import BuildError

from ..extensions import db
from ..i18n import translate
from ..models import BlogPost, Lead, LeadMessage, ServicePageSettings, YouTubeLink


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

    def youtube_latest_video_id_from_channel(url: str) -> str:
        parsed = urlparse(url or "")
        if "youtube.com" not in parsed.netloc:
            return ""

        path = (parsed.path or "").strip("/")
        if not path:
            return ""

        # For channel-like URLs, probe the videos page and grab the first videoId.
        if path.startswith("@") or path.startswith("channel/") or path.startswith("c/") or path.startswith("user/"):
            channel_videos_url = f"https://www.youtube.com/{path}/videos"
            try:
                with urlopen(channel_videos_url, timeout=3.5) as response:
                    html = response.read().decode("utf-8", errors="ignore")
                match = re.search(r'"videoId":"([A-Za-z0-9_-]{11})"', html)
                if match:
                    return match.group(1)
            except Exception:
                return ""

        return ""

    def youtube_thumbnail(url: str) -> str:
        video_id = youtube_video_id(url)
        if video_id:
            return f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg"

        # Fallback for valid YouTube links where a direct video ID is not parsed.
        # oEmbed returns a thumbnail URL for many watch/shorts links.
        try:
            endpoint = f"https://www.youtube.com/oembed?url={url}&format=json"
            with urlopen(endpoint, timeout=2.5) as response:
                data = json.loads(response.read().decode("utf-8"))
                thumb = (data.get("thumbnail_url") or "").strip()
                if thumb:
                    return thumb
        except Exception:
            pass

        return ""

    def youtube_thumbnail_candidates(url: str) -> list[str]:
        candidates: list[str] = []
        video_id = youtube_video_id(url)
        if not video_id:
            video_id = youtube_latest_video_id_from_channel(url)
        if video_id:
            candidates.extend(
                [
                    f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg",
                    f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
                    f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg",
                    f"https://i.ytimg.com/vi/{video_id}/sddefault.jpg",
                    f"https://i.ytimg.com/vi_webp/{video_id}/maxresdefault.webp",
                    f"https://i.ytimg.com/vi_webp/{video_id}/hqdefault.webp",
                ]
            )

        oembed_thumb = youtube_thumbnail(url)
        if oembed_thumb:
            candidates.append(oembed_thumb)

        # Keep order but remove duplicates.
        unique_candidates: list[str] = []
        seen: set[str] = set()
        for item in candidates:
            if item and item not in seen:
                unique_candidates.append(item)
                seen.add(item)

        return unique_candidates

    featured_videos = []
    for link in links[:4]:
        thumbnail_candidates = youtube_thumbnail_candidates(link.url)
        featured_videos.append(
            {
                "title": link.title,
                "url": link.url,
                "slot": link.slot,
                "thumbnail": thumbnail_candidates[0] if thumbnail_candidates else "",
                "thumbnail_candidates": thumbnail_candidates,
            }
        )

    return render_template("public/home.html", links=links, featured_videos=featured_videos)


@public_bp.get("/about")
def about():
    return render_template("public/about.html")


@public_bp.get("/services")
def services():
    settings = ServicePageSettings.query.first()
    if not settings:
        settings = ServicePageSettings()
        db.session.add(settings)
        db.session.commit()

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

    featured_channels = []

    def youtube_latest_video_id_from_channel(url: str) -> str:
        parsed = urlparse(url or "")
        if "youtube.com" not in parsed.netloc:
            return ""

        path = (parsed.path or "").strip("/")
        if not path:
            return ""

        if path.startswith("@") or path.startswith("channel/") or path.startswith("c/") or path.startswith("user/"):
            channel_videos_url = f"https://www.youtube.com/{path}/videos"
            try:
                with urlopen(channel_videos_url, timeout=3.5) as response:
                    html = response.read().decode("utf-8", errors="ignore")
                match = re.search(r'"videoId":"([A-Za-z0-9_-]{11})"', html)
                if match:
                    return match.group(1)
            except Exception:
                return ""

        return ""

    def youtube_thumbnail_candidates(url: str) -> list[str]:
        candidates: list[str] = []
        video_id = youtube_video_id(url)
        if not video_id:
            video_id = youtube_latest_video_id_from_channel(url)
        if video_id:
            candidates.extend(
                [
                    f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg",
                    f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
                    f"https://i.ytimg.com/vi/{video_id}/mqdefault.jpg",
                    f"https://i.ytimg.com/vi/{video_id}/sddefault.jpg",
                ]
            )
        return candidates

    for link in links[:4]:
        video_id = youtube_video_id(link.url)
        candidates = youtube_thumbnail_candidates(link.url)
        featured_channels.append(
            {
                "title": link.title,
                "url": link.url,
                "slot": link.slot,
                "thumbnail": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg" if video_id else "",
                "thumbnail_candidates": candidates,
            }
        )

    def media_url(value: str) -> str:
        clean = (value or "").strip()
        if not clean:
            return ""
        if clean.startswith("http://") or clean.startswith("https://"):
            return clean
        return url_for("static", filename=clean.lstrip("/"))

    discovery_url = (settings.discovery_url or "").strip() or "/contact"
    if discovery_url.startswith("http://") or discovery_url.startswith("https://"):
        discovery_href = discovery_url
    elif discovery_url == "/contact":
        discovery_href = url_for("public.contact", lang=getattr(g, "lang", "de"))
    else:
        separator = "&" if "?" in discovery_url else "?"
        discovery_href = f"{discovery_url}{separator}lang={getattr(g, 'lang', 'de')}"

    return render_template(
        "public/services.html",
        services_settings=settings,
        featured_channels=featured_channels,
        discovery_href=discovery_href,
        hero_media_url=media_url(settings.hero_media),
        digital_human_media_url=media_url(settings.digital_human_media),
        story_poster_url=media_url(settings.story_poster),
        story_video_01_url=media_url(settings.story_video_01),
        story_video_02_url=media_url(settings.story_video_02),
        story_video_03_url=media_url(settings.story_video_03),
        story_subtitles_01_url=media_url(settings.story_subtitles_01),
        story_subtitles_02_url=media_url(settings.story_subtitles_02),
        story_subtitles_03_url=media_url(settings.story_subtitles_03),
        strategy_photo_url=media_url(settings.strategy_photo),
    )


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
    privacy_consent = (request.form.get("privacy_consent") or "").strip().lower()
    lang = getattr(g, "lang", "de")

    if not name or not email or not message:
        flash(translate(lang, "contact.form_error"), "error")
        return redirect(url_for("public.contact", lang=lang))

    if privacy_consent not in {"1", "on", "true", "yes"}:
        if lang == "de":
            flash("Bitte stimmen Sie der Datenschutzerklarung zu.", "error")
        else:
            flash("Please agree to the privacy policy.", "error")
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
        f"Privacy consent: yes",
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
@public_bp.get("/impressum/")
def impressum():
    return render_template("public/impressum.html")


@public_bp.get("/privacy")
@public_bp.get("/datenschutzerklaerung")
@public_bp.get("/datenschutzerklaerung/")
def privacy():
    return render_template("public/privacy.html")


@public_bp.get("/terms")
@public_bp.get("/allgemeine-geschaeftsbedingungen")
@public_bp.get("/allgemeine-geschaeftsbedingungen/")
def terms():
    return render_template("public/terms.html")


@public_bp.get("/widerrufsbelehrung")
@public_bp.get("/widerrufsbelehrung/")
@public_bp.get("/withdrawal")
def withdrawal():
    return render_template("public/withdrawal.html")


@public_bp.get("/cookie-policy")
@public_bp.get("/cookie-policy/")
@public_bp.get("/cookie-richtlinie")
@public_bp.get("/cookie-richtlinie/")
def cookie_policy():
    return render_template("public/cookies.html")


@public_bp.get("/health")
def health():
    return {"status": "ok"}
