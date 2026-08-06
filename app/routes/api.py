import json

from flask import Blueprint, current_app, jsonify, request

from ..extensions import db
from ..models import AnalyticsEvent, AssistantInstructionSettings
from ..services.ai_service import generate_chat_reply


api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.post("/chat")
def chat():
    payload = request.get_json(silent=True) or {}
    message = (payload.get("message") or "").strip()
    if not message:
        return jsonify({"error": "Message is required."}), 400

    settings = AssistantInstructionSettings.query.first()
    custom_instructions = settings.custom_instructions if settings else ""

    reply = generate_chat_reply(
        api_key=current_app.config["OPENAI_API_KEY"],
        model=current_app.config["OPENAI_MODEL"],
        user_message=message,
        custom_instructions=custom_instructions,
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
