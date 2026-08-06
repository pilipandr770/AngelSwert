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
)
from ..services.ai_service import generate_chat_reply, generate_crm_hint


api_bp = Blueprint("api", __name__, url_prefix="/api")


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


@api_bp.post("/chat")
def chat():
    payload = request.get_json(silent=True) or {}
    message = (payload.get("message") or "").strip()
    tz_name = (payload.get("timezone") or "UTC").strip()
    tz = _resolve_timezone(tz_name)
    if not message:
        return jsonify({"error": "Message is required."}), 400

    settings = AssistantInstructionSettings.query.first()
    custom_instructions = settings.custom_instructions if settings else ""

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
        "If user asks about appointment, suggest booking via internal calendar slots below.\n"
        "Available slots (next 14 days):\n"
        f"{slots_block or '- no free slots currently'}\n"
        "CRM glossary terms:\n"
        f"{terms_block or '- no glossary terms yet'}"
    )

    reply = generate_chat_reply(
        api_key=current_app.config["OPENAI_API_KEY"],
        model=current_app.config["OPENAI_MODEL"],
        user_message=message,
        custom_instructions=f"{custom_instructions}\n\n{runtime_context}",
    )
    return jsonify({"reply": reply})


@api_bp.post("/track")
def track_event():
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

    ai_summary = generate_crm_hint(
        api_key=current_app.config["OPENAI_API_KEY"],
        model=current_app.config["OPENAI_MODEL"],
        lead_name=lead.name,
        lead_stage=lead.stage,
        question=question,
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
