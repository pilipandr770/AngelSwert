from __future__ import annotations

from html import escape
from urllib.parse import urljoin
from typing import Iterable


DEFAULT_SITE_URL = "https://www.angelswert.de"


def normalize_site_url(base_url: str | None) -> str:
    clean = (base_url or "").strip().rstrip("/")
    return clean or DEFAULT_SITE_URL


def absolute_url(base_url: str | None, path_or_url: str) -> str:
    base = normalize_site_url(base_url)
    target = (path_or_url or "").strip()
    if not target:
        return base
    if target.startswith("http://") or target.startswith("https://"):
        return target
    if not target.startswith("/"):
        target = "/" + target
    return base + target


def render_robots_txt(base_url: str | None) -> str:
    sitemap_url = absolute_url(base_url, "/sitemap.xml")
    return "\n".join(
        [
            "User-agent: *",
            "Allow: /",
            "Disallow: /admin/",
            "Disallow: /api/",
            "Disallow: /auth/",
            "Disallow: /health",
            f"Sitemap: {sitemap_url}",
            "",
        ]
    )


def render_llms_txt(base_url: str | None, brand_name: str) -> str:
    site = normalize_site_url(base_url)
    return "\n".join(
        [
            f"# {brand_name}",
            "",
            "Marketing website for AI video production, digital humans, content systems and consultation.",
            "",
            "## Core pages",
            f"- {absolute_url(site, '/')}",
            f"- {absolute_url(site, '/about')}",
            f"- {absolute_url(site, '/services')}",
            f"- {absolute_url(site, '/programs')}",
            f"- {absolute_url(site, '/contact')}",
            f"- {absolute_url(site, '/blog')}",
            "",
            "## Notes",
            "- Public content is bilingual (DE/EN).",
            "- Use the website for discovery, services, programs and contact intent.",
            "- Robots should prefer indexable public pages and avoid admin/API routes.",
            "",
        ]
    )


def render_ai_txt(base_url: str | None, brand_name: str) -> str:
    site = normalize_site_url(base_url)
    return "\n".join(
        [
            f"Brand: {brand_name}",
            f"Website: {site}",
            "Purpose: premium marketing website for AI video production and digital media services.",
            "Public priorities: brand discovery, services overview, program selection, contact conversion, SEO blog.",
            "Languages: German and English.",
            "Important URLs:",
            f"- {absolute_url(site, '/services')}",
            f"- {absolute_url(site, '/programs')}",
            f"- {absolute_url(site, '/contact')}",
            f"- {absolute_url(site, '/blog')}",
            "",
        ]
    )


def render_geo_txt(base_url: str | None, brand_name: str) -> str:
    site = normalize_site_url(base_url)
    return "\n".join(
        [
            f"Brand: {brand_name}",
            f"Website: {site}",
            "Target markets: Germany, Austria, Switzerland, broader EU/remote clients.",
            "Primary languages: de, en.",
            "Currency: EUR.",
            "Timezone: Europe/Berlin.",
            "Delivery model: remote-first with consultation-led onboarding.",
            "",
        ]
    )


def render_humans_txt(brand_name: str) -> str:
    return "\n".join(
        [
            f"Team: {brand_name}",
            "Role: AI video production, digital humans, content systems, strategy and consulting.",
            "Contact: use the public contact page.",
            "",
        ]
    )


def sitemap_xml(url_entries: Iterable[dict[str, object]]) -> str:
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">',
    ]
    for entry in url_entries:
        loc = escape(str(entry.get("loc", "")))
        parts.append("  <url>")
        parts.append(f"    <loc>{loc}</loc>")

        lastmod = entry.get("lastmod")
        if lastmod:
            parts.append(f"    <lastmod>{escape(str(lastmod))}</lastmod>")

        for alternate in entry.get("alternates", []) or []:
            href = escape(str(alternate.get("href", "")))
            hreflang = escape(str(alternate.get("hreflang", "")))
            if href and hreflang:
                parts.append(f'    <xhtml:link rel="alternate" hreflang="{hreflang}" href="{href}" />')

        parts.append("  </url>")

    parts.append("</urlset>")
    return "\n".join(parts)
