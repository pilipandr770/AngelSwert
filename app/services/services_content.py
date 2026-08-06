import copy
import json
from typing import Any


DEFAULT_SERVICES_COPY: dict[str, dict[str, Any]] = {
    "de": {
        "hero": {
            "eyebrow": "UNSERE LEISTUNGEN",
            "title": "Strukturierte KI-Video-, Digital-Human- und Content-Systeme für wiederkehrende Unternehmenskommunikation.",
            "lead": "ASAI Studio verbindet Videoproduktion, Creative Direction, Digital Humans, Content-Systeme, KI-Agenten und kontrollierte Automatisierung zu einer skalierbaren Kommunikationslösung.",
            "cta_primary": "AI Discovery starten",
            "cta_secondary": "Pakete ansehen",
        },
        "five_core": {
            "title": "Fünf Hauptleistungen",
            "cards": [
                {
                    "summary": "Videoproduktion & Creative Direction",
                    "body": "Konzeption, Drehbuch, Produktion, Schnitt, Postproduktion, Motion Design, 3D und Lokalisierung.",
                },
                {
                    "summary": "Digital Humans, KI-Avatare & KI-Influencer",
                    "body": "Digitale Präsentatoren und fiktionale Medienpersönlichkeiten mit klarer Rolle, Stimme, Sprache und Human Approval.",
                },
                {
                    "summary": "Content-, Medien- & YouTube-Systeme",
                    "body": "Planbare Content-Säulen, Redaktion, Publishing-Workflows und wiederkehrende Videoformate.",
                },
                {
                    "summary": "KI-Agenten, Automatisierung & Integrationen",
                    "body": "Assistenzsysteme, Routing, Freigaben, APIs und kontrollierte Datenflüsse für skalierbare Prozesse.",
                },
                {
                    "summary": "Strategie, Beratung & Implementierung",
                    "body": "Business-Analyse, Implementierungsweg, Governance, Trainings und operative Projektkoordination.",
                },
            ],
        },
        "digital_humans": {
            "eyebrow": "Digital Humans",
            "title": "Digital Humans für Marken, Unternehmen und Medien",
            "body": "Konsistente digitale Persönlichkeiten für wiederkehrende, mehrsprachige und skalierbare Kommunikation mit klarer Nutzungslogik.",
            "features": [
                "Business Presenter für Erklärvideos und interne Kommunikation",
                "Multilingual Host für Länder und Zielgruppen",
                "Authorised Digital Twin auf Basis freigegebener Rechte",
                "Fictional AI Influencer für Storytelling und Kampagnen",
            ],
            "meta": "Transparenz: Bei sprechenden Avataren wird klar gekennzeichnet, dass es sich um einen KI-Assistenten handelt.",
            "cta_primary": "Digital Human Projekt prüfen",
            "cta_secondary": "Stronger Than Yesterday ansehen",
        },
        "story": {
            "eyebrow": "AI Influencer Storytelling",
            "title": "Stronger Than Yesterday",
            "lead": "Eine visuelle Storytelling-Serie mit fiktionalen KI-Influencern, filmischer KI-Produktion und menschlicher Creative Direction.",
            "episodes": [
                {"eyebrow": "EPISODE 01", "title": "THE ARRIVAL", "status": "In Produktion", "button": "Story ansehen"},
                {"eyebrow": "EPISODE 02", "title": "THE MISSION", "status": "In Produktion", "button": "Story ansehen"},
                {"eyebrow": "EPISODE 03", "title": "STRONGER TOGETHER", "status": "In Produktion", "button": "Story ansehen"},
            ],
            "cta_watch": "Story ansehen",
            "cta_explore": "AI Influencer Production entdecken",
            "cta_discovery": "AI Discovery starten",
            "meta": "KI-generiertes Storytelling-Projekt mit fiktionalen Digital Humans und autorisierter KI-Darstellung. Creative Direction und menschliche Kontrolle durch ASAI Studio.",
        },
        "youtube": {
            "eyebrow": "YouTube Media Ecosystem",
            "title": "Built Through Real Media Practice",
            "lead": "ASAI Studio wird durch praktische Produktion in vier Medienumgebungen geformt: Technologie, mehrsprachiger Experten-Content, Finance und Kinder-Storytelling.",
            "visit_label": "Kanal besuchen",
        },
        "packages": {
            "eyebrow": "Packages",
            "title": "Pakete und Preise",
            "items": [
                {
                    "name": "Starter",
                    "price": "Content-Basis · EUR 999 + MwSt. / Monat",
                    "features": [
                        "10 Videos pro Monat",
                        "30-60 Sekunden pro Video",
                        "1 Digital Human · 1 KI-Stimme",
                        "Untertitel inklusive · 1 Korrekturrunde",
                    ],
                    "cta": "Eignung prüfen",
                },
                {
                    "name": "Growth",
                    "price": "Mehrsprachiges Publishing-System · EUR 1.999 + MwSt. / Monat",
                    "features": [
                        "20 Videos pro Monat",
                        "Bis zu 2 Digital Humans und 2 Sprachen",
                        "Premium-Visual-System und Redaktion",
                        "Monatliche Content-Auswertung",
                    ],
                    "cta": "Eignung prüfen",
                },
                {
                    "name": "PRO",
                    "price": "Kontrolliertes Video-System · ab EUR 3.999 + MwSt. / Monat",
                    "features": [
                        "Mehrere Digital Humans, Stimmen und Sprachen",
                        "Individuelle Workflow-Architektur und Integrationen",
                        "Menschliche Kontrolle vor Veröffentlichung",
                        "Analyse, Optimierung und Team-Support",
                    ],
                    "cta": "PRO-Bedarf prüfen",
                },
            ],
            "meta": "Alle Preise sind Nettopreise. Die gesetzliche Mehrwertsteuer, Integrationen und Zusatzanforderungen werden nach der Discovery bestätigt.",
        },
        "optional_growth": {
            "eyebrow": "Optional Growth",
            "title": "Optionale Growth-, Marketing- und Markenleistungen",
            "cards": [
                {
                    "title": "Content & Growth",
                    "body": "Content-Marketing, Social-Media-Marketing, Lead-Generierungs-Content und Sales-Support-Videos.",
                },
                {
                    "title": "Paid & Search",
                    "body": "SEO, SEA, PPC, Google Ads, digitale Kampagnen und Kampagnen-Kreatives.",
                },
                {
                    "title": "Brand Partnerships",
                    "body": "Sponsoring, Affiliate- und Referral-Projekte sowie Ambassador-Kooperationen.",
                },
            ],
            "meta": "Diese Leistungen und externe Werbebudgets sind kein automatischer Bestandteil der monatlichen Video-Pakete.",
        },
        "workflow": {
            "title": "So arbeiten wir",
            "steps": [
                {
                    "label": "01 - Discovery & Strategie",
                    "body": "Business-Review, Zielgruppen- und Angebotsanalyse, erste Empfehlung.",
                },
                {
                    "label": "02 - Konzeption & Systemdesign",
                    "body": "Content-Modell, Digital Human, visuelles System, Produktionslogik.",
                },
                {
                    "label": "03 - Produktion & Launch",
                    "body": "Skripte, Produktion, Lokalisierung, Review, Auslieferung.",
                },
                {
                    "label": "04 - Stabilisierung & Automatisierung",
                    "body": "Workflow-Optimierung, Rollen, Monitoring, Integrationen.",
                },
                {
                    "label": "05 - Wachstum & Skalierung",
                    "body": "Mehr Content und Sprachen, zusätzliche Kanäle, Growth-Kampagnen.",
                },
            ],
            "meta": "Aufbauen. Produzieren. Stabilisieren. Automatisieren. Dann skalieren.",
        },
        "strategy": {
            "eyebrow": "Strategy Session",
            "title": "Starten Sie mit einer 1:1-Strategie-Session",
            "body": "In einer fokussierten 90-Minuten-Session analysieren wir Geschäftsmodell, Kommunikation, Zielgruppe und den Implementierungsweg.",
            "price": "90 Minuten · EUR 250 + MwSt.",
            "features": [
                "Business- und Kommunikations-Review",
                "Content-Ziele, Zielgruppe und Kanäle",
                "Empfohlene Paket- oder Pilot-Empfehlung",
            ],
            "cta": "AI Discovery starten",
            "meta": "Kalenderbuchung wird nach Discovery und Eignungsprüfung freigeschaltet.",
        },
    },
    "en": {
        "hero": {
            "eyebrow": "OUR SERVICES",
            "title": "Structured AI video, digital human and content systems for recurring business communication.",
            "lead": "ASAI Studio combines video production, creative direction, digital humans, content systems, AI agents and controlled automation into one scalable communication solution.",
            "cta_primary": "Start AI Discovery",
            "cta_secondary": "See packages",
        },
        "five_core": {
            "title": "Five core services",
            "cards": [
                {
                    "summary": "Video production & creative direction",
                    "body": "Concept, scripting, production, editing, post-production, motion design, 3D and localization.",
                },
                {
                    "summary": "Digital humans, AI avatars & AI influencers",
                    "body": "Digital presenters and fictional media personalities with a clear role, voice, language and human approval.",
                },
                {
                    "summary": "Content, media & YouTube systems",
                    "body": "Plannable content pillars, editorial systems, publishing workflows and recurring video formats.",
                },
                {
                    "summary": "AI agents, automation & integrations",
                    "body": "Assistant systems, routing, approvals, APIs and controlled data flows for scalable processes.",
                },
                {
                    "summary": "Strategy, consulting & implementation",
                    "body": "Business analysis, implementation path, governance, training and operational project coordination.",
                },
            ],
        },
        "digital_humans": {
            "eyebrow": "Digital Humans",
            "title": "Digital humans for brands, companies and media",
            "body": "Consistent digital personalities for recurring, multilingual and scalable communication with clear usage logic.",
            "features": [
                "Business presenter for explainers and internal communication",
                "Multilingual host for countries and audiences",
                "Authorised digital twin based on approved rights",
                "Fictional AI influencer for storytelling and campaigns",
            ],
            "meta": "Transparency: speaking avatars are clearly disclosed as AI assistants.",
            "cta_primary": "Evaluate digital human project",
            "cta_secondary": "View Stronger Than Yesterday",
        },
        "story": {
            "eyebrow": "AI Influencer Storytelling",
            "title": "Stronger Than Yesterday",
            "lead": "A visual storytelling series with fictional AI influencers, cinematic AI production and human creative direction.",
            "episodes": [
                {"eyebrow": "EPISODE 01", "title": "THE ARRIVAL", "status": "In production", "button": "Watch the story"},
                {"eyebrow": "EPISODE 02", "title": "THE MISSION", "status": "In production", "button": "Watch the story"},
                {"eyebrow": "EPISODE 03", "title": "STRONGER TOGETHER", "status": "In production", "button": "Watch the story"},
            ],
            "cta_watch": "Watch the story",
            "cta_explore": "Explore AI Influencer Production",
            "cta_discovery": "Start AI Discovery",
            "meta": "AI-generated storytelling project with fictional digital humans and authorised AI representation. Creative direction and human control by ASAI Studio.",
        },
        "youtube": {
            "eyebrow": "YouTube Media Ecosystem",
            "title": "Built Through Real Media Practice",
            "lead": "ASAI Studio is informed by hands-on production across four media environments: technology, multilingual expert content, finance and children's storytelling.",
            "visit_label": "Visit channel",
        },
        "packages": {
            "eyebrow": "Packages",
            "title": "Packages and pricing",
            "items": [
                {
                    "name": "Starter",
                    "price": "Content base · EUR 999 + VAT / month",
                    "features": [
                        "10 videos per month",
                        "30-60 seconds per video",
                        "1 digital human · 1 AI voice",
                        "Subtitles included · 1 revision round",
                    ],
                    "cta": "Check fit",
                },
                {
                    "name": "Growth",
                    "price": "Multilingual publishing system · EUR 1,999 + VAT / month",
                    "features": [
                        "20 videos per month",
                        "Up to 2 digital humans and 2 languages",
                        "Premium visual system and editorial structure",
                        "Monthly content evaluation",
                    ],
                    "cta": "Check fit",
                },
                {
                    "name": "PRO",
                    "price": "Controlled video system · from EUR 3,999 + VAT / month",
                    "features": [
                        "Multiple digital humans, voices and languages",
                        "Custom workflow architecture and integrations",
                        "Human control before publication",
                        "Analysis, optimization and team support",
                    ],
                    "cta": "Check PRO fit",
                },
            ],
            "meta": "All prices are net prices. VAT, integrations and additional requirements are confirmed after discovery.",
        },
        "optional_growth": {
            "eyebrow": "Optional Growth",
            "title": "Optional growth, marketing and brand services",
            "cards": [
                {
                    "title": "Content & Growth",
                    "body": "Content marketing, social media marketing, lead generation content and sales support videos.",
                },
                {
                    "title": "Paid & Search",
                    "body": "SEO, SEA, PPC, Google Ads, digital campaigns and campaign creatives.",
                },
                {
                    "title": "Brand Partnerships",
                    "body": "Sponsorships, affiliate and referral projects, plus ambassador collaborations.",
                },
            ],
            "meta": "These services and external ad budgets are not automatically included in monthly video packages.",
        },
        "workflow": {
            "title": "How we work",
            "steps": [
                {
                    "label": "01 - Discovery & strategy",
                    "body": "Business review, audience and offer analysis, first recommendation.",
                },
                {
                    "label": "02 - Concept & system design",
                    "body": "Content model, digital human, visual system and production logic.",
                },
                {
                    "label": "03 - Production & launch",
                    "body": "Scripts, production, localization, review and delivery.",
                },
                {
                    "label": "04 - Stabilization & automation",
                    "body": "Workflow optimization, roles, monitoring and integrations.",
                },
                {
                    "label": "05 - Growth & scaling",
                    "body": "More content and languages, additional channels, growth campaigns.",
                },
            ],
            "meta": "Build. Produce. Stabilize. Automate. Then scale.",
        },
        "strategy": {
            "eyebrow": "Strategy Session",
            "title": "Start with a 1:1 strategy session",
            "body": "In a focused 90-minute session we analyze your business model, communication, audience and implementation path.",
            "price": "90 minutes · EUR 250 + VAT",
            "features": [
                "Business and communication review",
                "Content goals, audience and channels",
                "Recommended package or pilot path",
            ],
            "cta": "Start AI Discovery",
            "meta": "Calendar booking is unlocked after discovery and qualification.",
        },
    },
}


def _merge_values(default_value: Any, incoming_value: Any) -> Any:
    if isinstance(default_value, dict):
        merged = copy.deepcopy(default_value)
        incoming = incoming_value if isinstance(incoming_value, dict) else {}
        for key, child_default in default_value.items():
            merged[key] = _merge_values(child_default, incoming.get(key))
        return merged

    if isinstance(default_value, list):
        merged_list = copy.deepcopy(default_value)
        incoming_list = incoming_value if isinstance(incoming_value, list) else []
        for index, child_default in enumerate(default_value):
            value = incoming_list[index] if index < len(incoming_list) else None
            merged_list[index] = _merge_values(child_default, value)
        return merged_list

    if isinstance(default_value, str):
        if isinstance(incoming_value, str) and incoming_value.strip():
            return incoming_value.strip()
        return default_value

    return incoming_value if incoming_value is not None else default_value


def default_services_copy() -> dict[str, dict[str, Any]]:
    return copy.deepcopy(DEFAULT_SERVICES_COPY)


def parse_services_copy(raw_json: str) -> dict[str, dict[str, Any]]:
    parsed: Any = {}
    try:
        parsed = json.loads(raw_json or "{}")
    except Exception:
        parsed = {}

    defaults = default_services_copy()
    return _merge_values(defaults, parsed)


def localized_services_copy(raw_json: str, lang: str) -> dict[str, Any]:
    all_copy = parse_services_copy(raw_json)
    lang_code = "de" if (lang or "").lower() == "de" else "en"
    return all_copy.get(lang_code, all_copy["en"])


def update_services_copy_from_form(form_data, raw_json: str) -> str:
    updated_copy = parse_services_copy(raw_json)

    def set_path(target: Any, path_parts: list[Any], value: str) -> None:
        node = target
        for part in path_parts[:-1]:
            node = node[part]
        node[path_parts[-1]] = value.strip()

    def iter_paths(node: Any, prefix: list[Any] | None = None):
        prefix = prefix or []
        if isinstance(node, dict):
            for key, value in node.items():
                yield from iter_paths(value, prefix + [key])
            return
        if isinstance(node, list):
            for index, value in enumerate(node):
                yield from iter_paths(value, prefix + [index])
            return
        yield prefix

    for lang_code in ("de", "en"):
        language_root = updated_copy[lang_code]
        for path in iter_paths(language_root):
            form_key = f"{lang_code}__" + "__".join(str(p) for p in path)
            if form_key not in form_data:
                continue
            set_path(language_root, path, (form_data.get(form_key) or ""))

    return json.dumps(updated_copy, ensure_ascii=False)
