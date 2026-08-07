HOME_HERO_TEXT_DEFAULTS = {
    "de": {
        "eyebrow": "UNSERE LEISTUNGEN",
        "title": "Kontrollierte KI-Video- & Mediasysteme für Unternehmen",
        "lead": "KI-Video-Produktion, Digital Humans, Content-Systeme und Automatisierung für klare Markenpräsenz, qualifizierte Nachfrage und wiederholbares Wachstum.",
        "point_1": "Strategie, Creative Direction und Umsetzung bleiben abgestimmt.",
        "point_2": "Eine Marke, ein Content-Engine, mehrere Formate.",
        "point_3": "Jeder Block führt zum nächsten klaren Schritt.",
        "cta_primary": "AI Discovery starten",
        "cta_secondary": "Leistungen ansehen",
    },
    "en": {
        "eyebrow": "OUR SERVICES",
        "title": "Controlled AI video & media systems for business",
        "lead": "AI video production, digital humans, content systems and automation designed to create clear brand presence, qualified demand and repeatable growth.",
        "point_1": "Strategy, creative direction and execution stay aligned.",
        "point_2": "One brand, one content engine, multiple formats.",
        "point_3": "Each block leads the visitor toward the next action.",
        "cta_primary": "Start AI Discovery",
        "cta_secondary": "Explore Services",
    },
}

HOME_HERO_MEDIA_DEFAULTS = {
    "hero_bg_media": "img/services_tz/image1.png",
    "hero_main_media": "img/client-about.jpg",
    "hero_secondary_media": "img/client-accent.jpg",
}


def resolve_home_hero_media_url(path_or_url: str) -> str:
    value = (path_or_url or "").strip()
    if not value:
        return ""
    if value.startswith(("http://", "https://", "/")):
        return value
    from flask import url_for

    return url_for("static", filename=value)


def home_hero_lang_code(lang: str) -> str:
    return "de" if (lang or "de").lower() == "de" else "en"


def resolve_home_hero_content(settings, lang: str) -> dict:
    lang_code = home_hero_lang_code(lang)
    defaults = HOME_HERO_TEXT_DEFAULTS[lang_code]

    return {
        "eyebrow": (getattr(settings, f"hero_eyebrow_{lang_code}", "") or "").strip() or defaults["eyebrow"],
        "title": (getattr(settings, f"hero_title_{lang_code}", "") or "").strip() or defaults["title"],
        "lead": (getattr(settings, f"hero_lead_{lang_code}", "") or "").strip() or defaults["lead"],
        "point_1": (getattr(settings, f"hero_point_1_{lang_code}", "") or "").strip() or defaults["point_1"],
        "point_2": (getattr(settings, f"hero_point_2_{lang_code}", "") or "").strip() or defaults["point_2"],
        "point_3": (getattr(settings, f"hero_point_3_{lang_code}", "") or "").strip() or defaults["point_3"],
        "cta_primary": (getattr(settings, f"hero_cta_primary_{lang_code}", "") or "").strip() or defaults["cta_primary"],
        "cta_secondary": (getattr(settings, f"hero_cta_secondary_{lang_code}", "") or "").strip() or defaults["cta_secondary"],
        "bg_media": resolve_home_hero_media_url((getattr(settings, "hero_background", "") or "").strip() or HOME_HERO_MEDIA_DEFAULTS["hero_bg_media"]),
        "main_media": resolve_home_hero_media_url((getattr(settings, "hero_image_main", "") or "").strip() or HOME_HERO_MEDIA_DEFAULTS["hero_main_media"]),
        "secondary_media": resolve_home_hero_media_url((getattr(settings, "hero_image_secondary", "") or "").strip() or HOME_HERO_MEDIA_DEFAULTS["hero_secondary_media"]),
    }
