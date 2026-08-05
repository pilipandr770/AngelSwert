from flask import Blueprint, current_app, jsonify, request

from ..services.ai_service import generate_chat_reply


api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.post("/chat")
def chat():
    payload = request.get_json(silent=True) or {}
    message = (payload.get("message") or "").strip()
    if not message:
        return jsonify({"error": "Message is required."}), 400

    reply = generate_chat_reply(
        api_key=current_app.config["OPENAI_API_KEY"],
        model=current_app.config["OPENAI_MODEL"],
        user_message=message,
    )
    return jsonify({"reply": reply})
