import json
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from flask import Blueprint, current_app, jsonify, request
from flask_login import current_user

from ..extensions import db
from ..models import (
    AnalyticsEvent,
    AssistantInstructionSettings,
    CrmAiReport,
    CrmGlossaryTerm,
    InternalCalendarBooking,
    InternalCalendarSlot,
    Lead,
    LeadMessage,
)
from ..services.ai_service import extract_lead_profile_update, generate_chat_reply, generate_crm_hint


api_bp = Blueprint("api", __name__, url_prefix="/api")


def _has_analytics_consent() -> bool:
    consent = (request.cookies.get("as_cookie_consent") or "").strip().lower()
    if consent in {"all", "analytics", "accepted"}:
        return True

    header_value = (request.headers.get("X-Consent-Analytics") or "").strip().lower()
    return header_value in {"1", "true", "yes", "on"}


def _resolve_timezone(tz_name: str | None) -> ZoneInfo:
    candidate = (tz_name or "").strip()
    if not candidate:
        return ZoneInfo("UTC")
    try:
        return ZoneInfo(candidate)
    except Exception:
        return ZoneInfo("UTC")


def _to_user_time(dt_utc_naive: datetime, tz: ZoneInfo) -> datetime:
    return dt_utc_naive.replace(tzinfo=timezone.utc).astimezone(tz)


def _looks_like_time_request(text: str) -> bool:
    t = text.lower()
    markers = [
        "дата", "время", "час", "котра година", "который час", "time", "date", "uhrzeit", "datum",
    ]
    return any(m in t for m in markers)


def _looks_like_calendar_request(text: str) -> bool:
    t = text.lower()
    markers = [
        "календар", "calendar", "termin", "appointment", "slot", "слот", "встреч", "зустріч",
    ]
    return any(m in t for m in markers)


def _looks_like_booking_request(text: str) -> bool:
    t = text.lower()
    markers = [
        "запис", "запиши", "book", "booking", "термин", "appointment", "консультац", "consultation", "beratung",
    ]
    return any(m in t for m in markers)


def _looks_like_pricing_request(text: str) -> bool:
    t = text.lower()
    markers = ["цена", "стоимость", "price", "pricing", "preise", "kostet", "пакет", "package", "angebot"]
    return any(m in t for m in markers)


def _is_no_access_disclaimer(text: str) -> bool:
    t = (text or "").lower()
    markers = [
        "не имею доступа",
        "не можу отримати доступ",
        "i don't have access",
        "i do not have access",
        "kein zugriff",
        "couldn't access",
    ]
    return any(m in t for m in markers)


def _looks_like_email(value: str) -> bool:
    email = (value or "").strip()
    return bool(email and "@" in email and "." in email.split("@")[-1])


def _resolve_chat_lead(payload: dict) -> Lead | None:
    email = (payload.get("lead_email") or payload.get("email") or "").strip().lower()
    name = (payload.get("lead_name") or payload.get("name") or "").strip()
    if not _looks_like_email(email):
        return None

    lead = Lead.query.filter_by(email=email).first()
    if not lead:
        lead = Lead(
            name=name or email.split("@")[0],
            email=email,
            stage="new",
            source="chatbot-widget",
            notes="Lead created from chatbot conversation.",
        )
        db.session.add(lead)
        db.session.flush()
        return lead

    if name and (not lead.name or lead.name == lead.email):
        lead.name = name
    return lead


def _store_chat_messages(lead: Lead | None, user_message: str, bot_reply: str) -> None:
    if not lead:
        return
    incoming = (user_message or "").strip()
    outgoing = (bot_reply or "").strip()
    if incoming:
        db.session.add(
            LeadMessage(
                lead_id=lead.id,
                direction="incoming",
                channel="chatbot_widget",
                body=incoming,
            )
        )


PROFILE_FIELDS = [
    "profile_industry",
    "profile_work_scope",
    "profile_work_topic",
    "profile_desired_outcome",
    "profile_timeline",
    "profile_decision_maker",
]


def _lead_profile_dict(lead: Lead | None) -> dict:
    if not lead:
        return {}
    return {
        "profile_industry": (lead.profile_industry or "").strip(),
        "profile_work_scope": (lead.profile_work_scope or "").strip(),
        "profile_work_topic": (lead.profile_work_topic or "").strip(),
        "profile_desired_outcome": (lead.profile_desired_outcome or "").strip(),
        "profile_timeline": (lead.profile_timeline or "").strip(),
        "profile_decision_maker": (lead.profile_decision_maker or "").strip(),
    }


def _missing_profile_fields(profile: dict) -> list[str]:
    missing_map = {
        "profile_industry": "industry",
        "profile_work_scope": "work_scope",
        "profile_work_topic": "work_topic",
        "profile_desired_outcome": "desired_outcome",
        "profile_timeline": "timeline",
        "profile_decision_maker": "decision_maker",
    }
    result: list[str] = []
    for field_name, label in missing_map.items():
        if not (profile.get(field_name) or "").strip():
            result.append(label)
    return result


def _autofill_lead_profile(lead: Lead | None, message: str, api_key: str, model: str) -> None:
    if not lead:
        return
    if len((message or "").strip()) < 8:
        return

    current_profile = _lead_profile_dict(lead)
    updates = extract_lead_profile_update(
        api_key=api_key,
        model=model,
        message=message,
        current_profile=current_profile,
    )
    if not updates:
        return

    changed = False
    for field_name in PROFILE_FIELDS:
        new_value = (updates.get(field_name) or "").strip()
        if not new_value:
            continue
        old_value = (getattr(lead, field_name, "") or "").strip()
        if old_value == new_value:
            continue
        setattr(lead, field_name, new_value[:1200] if field_name == "profile_desired_outcome" else new_value[:255])
        changed = True

    if changed:
        db.session.add(lead)


def _trim_text(value: str, max_chars: int) -> str:
    text = (value or "").strip()
    if len(text) <= max_chars:
        return text
    return text[-max_chars:]


def _payload_history_block(payload: dict, max_items: int = 10) -> str:
    items = payload.get("history") or []
    if not isinstance(items, list):
        return ""

    safe_items = items[-max_items:]
    lines: list[str] = []
    for item in safe_items:
        if not isinstance(item, dict):
            continue
        role = (item.get("role") or "").strip().lower()
        text = _trim_text(str(item.get("text") or ""), 350)
        if role not in {"user", "bot"} or not text:
            continue
        lines.append(f"- {role}: {text}")
    return "\n".join(lines)


def _lead_history_block(lead: Lead | None, max_items: int = 10) -> str:
    if not lead:
        return ""
    items = (
        LeadMessage.query.filter_by(lead_id=lead.id, channel="chatbot_widget")
        .order_by(LeadMessage.created_at.desc())
        .limit(max_items)
        .all()
    )
    if not items:
        return ""

    lines: list[str] = []
    for item in reversed(items):
        role = "user" if item.direction == "incoming" else "bot"
        lines.append(f"- {role}: {_trim_text(item.body, 350)}")
    return "\n".join(lines)


def _lead_profile_block(lead: Lead | None) -> str:
    if not lead:
        return ""
    profile = _lead_profile_dict(lead)
    missing = _missing_profile_fields(profile)
    return (
        f"Lead stage: {(lead.stage or '-').strip()}\n"
        f"Lead source: {(lead.source or '-').strip()}\n"
        f"Lead notes: {_trim_text(lead.notes or '-', 1200)}\n"
        f"Client card: {json.dumps(profile, ensure_ascii=False)}\n"
        f"Missing client-card fields: {', '.join(missing) if missing else 'none'}"
    )
    if outgoing:
        db.session.add(
            LeadMessage(
                lead_id=lead.id,
                direction="outgoing",
                channel="chatbot_widget",
                body=outgoing,
            )
        )


@api_bp.post("/chat")
def chat():
    payload = request.get_json(silent=True) or {}
    message = (payload.get("message") or "").strip()
    tz_name = (payload.get("timezone") or "UTC").strip()
    tz = _resolve_timezone(tz_name)
    if not message:
        return jsonify({"error": "Message is required."}), 400

    settings = AssistantInstructionSettings.query.first()
    custom_instructions = (settings.custom_instructions if settings else "") or ""
    instruction_doc_text = (settings.instruction_doc_text if settings else "") or ""
    lead = _resolve_chat_lead(payload)
    if current_app.config.get("ENABLE_LEAD_PROFILE_AUTOFILL", False):
        _autofill_lead_profile(
            lead=lead,
            message=message,
            api_key=current_app.config["OPENAI_API_KEY"],
            model=current_app.config["OPENAI_MODEL"],
        )

    def _reply(reply_text: str):
        _store_chat_messages(lead, message, reply_text)
        if lead:
            db.session.add(lead)
        db.session.commit()
        return jsonify({"reply": reply_text})

    now_utc = datetime.utcnow()
    now_local = _to_user_time(now_utc, tz)
    now_iso = now_utc.isoformat(timespec="minutes") + "Z"
    terms = CrmGlossaryTerm.query.filter_by(is_active=True).order_by(CrmGlossaryTerm.updated_at.desc()).limit(20).all()
    terms_block = "\n".join([f"- {item.term}: {item.definition}" for item in terms])

    window_start = datetime.utcnow()
    window_end = window_start + timedelta(days=14)
    slots = (
        InternalCalendarSlot.query.filter(
            InternalCalendarSlot.is_available.is_(True),
            InternalCalendarSlot.starts_at >= window_start,
            InternalCalendarSlot.starts_at <= window_end,
        )
        .order_by(InternalCalendarSlot.starts_at.asc())
        .limit(10)
        .all()
    )
    slots_block = "\n".join(
        [
            f"- slot_id={slot.id}, starts_at_utc={slot.starts_at.isoformat()}Z, starts_at_local={_to_user_time(slot.starts_at, tz).isoformat()}"
            for slot in slots
        ]
    )

    runtime_context = (
        f"Current UTC time: {now_iso}\n"
        f"Current local time for user timezone ({tz.key}): {now_local.isoformat()}\n"
        "Use this current time reference in answers.\n"
        "Do not ask again for facts already provided in recent dialogue or lead profile.\n"
        "Acknowledge known facts and ask only for missing critical fields.\n"
        "If any client-card fields are missing, ask at most ONE concise clarification question per reply.\n"
        "If user asks about appointment, suggest booking via internal calendar slots below.\n"
        "Available slots (next 14 days):\n"
        f"{slots_block or '- no free slots currently'}\n"
        "CRM glossary terms:\n"
        f"{terms_block or '- no glossary terms yet'}"
    )

    lead_profile_block = _lead_profile_block(lead)
    lead_history_block = _lead_history_block(lead)
    payload_history_block = _payload_history_block(payload)

    history_block = "\n".join(
        item
        for item in [lead_history_block, payload_history_block]
        if item
    )

    instructions_bundle = "\n\n".join(
        item
        for item in [
            _trim_text(custom_instructions, 4000),
            f"Instruction document context:\n{_trim_text(instruction_doc_text, 9000)}" if instruction_doc_text else "",
            runtime_context,
            f"Lead profile context:\n{lead_profile_block}" if lead_profile_block else "",
            f"Recent dialogue context:\n{history_block}" if history_block else "",
        ]
        if item
    )

    if _looks_like_calendar_request(message):
        if not slots:
            return _reply(
                "Зараз немає вільних слотів у календарі на найближчі 14 днів. "
                "Спробуйте пізніше або зверніться до адміністратора."
            )
        lines = [
            "Ось найближчі вільні слоти (локальний час):"
        ]
        for slot in slots[:5]:
            local_start = _to_user_time(slot.starts_at, tz).strftime("%Y-%m-%d %H:%M")
            local_end = _to_user_time(slot.ends_at, tz).strftime("%H:%M")
            lines.append(f"- #{slot.id}: {local_start} - {local_end}")
        lines.append("Щоб забронювати, оберіть слот у чат-віджеті нижче.")
        return _reply("\n".join(lines))

    if _looks_like_time_request(message):
        return _reply(
            f"Время UTC: {now_iso}. "
            f"Локальний час ({tz.key}): {now_local.strftime('%Y-%m-%d %H:%M:%S %Z')}."
        )

    if _looks_like_booking_request(message):
        if not slots:
            return _reply(
                "Я можу записати вас на консультацію, але зараз немає вільних слотів у найближчі 14 днів. "
                "Будь ласка, спробуйте пізніше або зверніться до адміністратора."
            )
        slot = slots[0]
        local_start = _to_user_time(slot.starts_at, tz).strftime("%Y-%m-%d %H:%M")
        local_end = _to_user_time(slot.ends_at, tz).strftime("%H:%M")
        return _reply(
            "Так, я можу записати вас на термін. "
            f"Найближчий вільний слот: #{slot.id}, {local_start} - {local_end}. "
            "Оберіть слот у віджеті та вкажіть ім'я й email для підтвердження."
        )

    if _looks_like_pricing_request(message):
        return _reply(
            "Орієнтовні пакети: Starter - 999 EUR/місяць, Growth - 1.999 EUR/місяць, PRO - від 3.999 EUR/місяць (без ПДВ). "
            "Для точного розрахунку можемо забронювати персональну консультацію через календар у чаті."
        )

    reply = generate_chat_reply(
        api_key=current_app.config["OPENAI_API_KEY"],
        model=current_app.config["OPENAI_MODEL"],
        user_message=message,
        custom_instructions=instructions_bundle,
    )

    if _is_no_access_disclaimer(reply):
        if _looks_like_calendar_request(message) or _looks_like_booking_request(message):
            if slots:
                slot = slots[0]
                local_start = _to_user_time(slot.starts_at, tz).strftime("%Y-%m-%d %H:%M")
                local_end = _to_user_time(slot.ends_at, tz).strftime("%H:%M")
                reply = (
                    "Я маю доступ до внутрішнього календаря. "
                    f"Найближчий вільний слот: #{slot.id}, {local_start} - {local_end}. "
                    "Оберіть слот у віджеті нижче та надішліть ім'я й email для бронювання."
                )
            else:
                reply = "Я маю доступ до внутрішнього календаря, але наразі вільних слотів у найближчі 14 днів немає."
        elif _looks_like_time_request(message):
            reply = (
                f"Время UTC: {now_iso}. "
                f"Локальний час ({tz.key}): {now_local.strftime('%Y-%m-%d %H:%M:%S %Z')}."
            )

    return _reply(reply)


@api_bp.post("/track")
def track_event():
    if not _has_analytics_consent():
        return jsonify({"ok": True, "skipped": "consent_required"})

    payload = request.get_json(silent=True) or {}
    event_name = (payload.get("event") or "").strip()
    if not event_name:
        return jsonify({"error": "Event name is required."}), 400

    event = AnalyticsEvent(
        event_name=event_name[:120],
        page=(payload.get("page") or "")[:120],
        lang=(payload.get("lang") or "de")[:10],
        label=(payload.get("label") or "")[:255],
        meta_json=json.dumps(payload.get("meta") or {}, ensure_ascii=False),
    )
    db.session.add(event)
    db.session.commit()

    return jsonify({"ok": True})


@api_bp.get("/calendar/slots")
def calendar_slots():
    days = request.args.get("days", "90").strip()
    try:
        days_int = max(1, min(90, int(days)))
    except ValueError:
        days_int = 90

    tz_name = (request.args.get("timezone") or "UTC").strip()
    tz = _resolve_timezone(tz_name)
    start = datetime.utcnow()
    end = start + timedelta(days=days_int)
    slots = (
        InternalCalendarSlot.query.filter(
            InternalCalendarSlot.is_available.is_(True),
            InternalCalendarSlot.starts_at >= start,
            InternalCalendarSlot.starts_at <= end,
        )
        .order_by(InternalCalendarSlot.starts_at.asc())
        .all()
    )

    data = [
        {
            "id": slot.id,
            "starts_at": slot.starts_at.isoformat() + "Z",
            "ends_at": slot.ends_at.isoformat() + "Z",
            "starts_at_local": _to_user_time(slot.starts_at, tz).isoformat(),
            "ends_at_local": _to_user_time(slot.ends_at, tz).isoformat(),
        }
        for slot in slots
    ]
    return jsonify(
        {
            "now_utc": datetime.utcnow().isoformat() + "Z",
            "timezone": tz.key,
            "now_local": _to_user_time(datetime.utcnow(), tz).isoformat(),
            "slots": data,
        }
    )


@api_bp.post("/calendar/book")
def calendar_book():
    payload = request.get_json(silent=True) or {}
    tz_name = (payload.get("timezone") or "UTC").strip()
    tz = _resolve_timezone(tz_name)
    slot_id = payload.get("slot_id")
    client_name = (payload.get("name") or "").strip()
    client_email = (payload.get("email") or "").strip().lower()
    note = (payload.get("note") or "").strip()

    if not slot_id or not client_name or not client_email:
        return jsonify({"error": "slot_id, name and email are required"}), 400

    slot = InternalCalendarSlot.query.get(slot_id)
    if not slot or not slot.is_available:
        return jsonify({"error": "Slot is unavailable"}), 409

    lead = Lead.query.filter_by(email=client_email).first()
    if not lead:
        lead = Lead(name=client_name, email=client_email, stage="booked", source="chatbot-calendar", notes=note)
        db.session.add(lead)
        db.session.flush()
    else:
        lead.name = client_name
        lead.stage = "booked"
        if note:
            lead.notes = (lead.notes + "\n" + note).strip() if lead.notes else note

    booking = InternalCalendarBooking(
        slot_id=slot.id,
        lead_id=lead.id,
        client_name=client_name,
        client_email=client_email,
        note=note,
        source="chatbot",
        status="booked",
    )
    slot.is_available = False

    db.session.add(booking)
    db.session.commit()

    return jsonify(
        {
            "ok": True,
            "booking_id": booking.id,
            "slot": {
                "id": slot.id,
                "starts_at": slot.starts_at.isoformat() + "Z",
                "ends_at": slot.ends_at.isoformat() + "Z",
                "starts_at_local": _to_user_time(slot.starts_at, tz).isoformat(),
                "ends_at_local": _to_user_time(slot.ends_at, tz).isoformat(),
            },
        }
    )


@api_bp.post("/crm/report")
def crm_report():
    if not (current_user.is_authenticated and getattr(current_user, "is_admin", False)):
        return jsonify({"error": "Forbidden"}), 403

    payload = request.get_json(silent=True) or {}
    lead_id = payload.get("lead_id")
    question = (payload.get("question") or "").strip() or "Give me a concise CRM report and next action."
    if not lead_id:
        return jsonify({"error": "lead_id is required"}), 400

    lead = Lead.query.get(lead_id)
    if not lead:
        return jsonify({"error": "Lead not found"}), 404

    recent_messages = (
        LeadMessage.query.filter_by(lead_id=lead.id)
        .order_by(LeadMessage.created_at.desc())
        .limit(20)
        .all()
    )
    history_lines = [
        f"- {item.created_at.isoformat()} [{item.channel}/{item.direction}] {item.body}"
        for item in reversed(recent_messages)
    ]
    conversation_context = "\n".join(history_lines)

    ai_summary = generate_crm_hint(
        api_key=current_app.config["OPENAI_API_KEY"],
        model=current_app.config["OPENAI_MODEL"],
        lead_name=lead.name,
        lead_stage=lead.stage,
        question=question,
        conversation_context=conversation_context,
    )
    report = CrmAiReport(
        lead_id=lead.id,
        summary=ai_summary,
        recommended_action="Review summary and send follow-up within 24 hours.",
        created_by="crm_assistant",
    )
    db.session.add(report)
    db.session.commit()

    return jsonify(
        {
            "ok": True,
            "report_id": report.id,
            "summary": report.summary,
            "recommended_action": report.recommended_action,
        }
    )
