from __future__ import annotations

from typing import Optional

from openai import OpenAI


def _get_client(api_key: str) -> Optional[OpenAI]:
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


def generate_chat_reply(api_key: str, model: str, user_message: str) -> str:
    client = _get_client(api_key)
    if not client:
        return (
            "AI mode is off because OPENAI_API_KEY is not set. "
            "Set API key in .env to enable smart assistant replies."
        )

    response = client.chat.completions.create(
        model=model,
        temperature=0.5,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an assistant for a coaching and consulting website. "
                    "Reply briefly, politely, and suggest a clear next step."
                ),
            },
            {"role": "user", "content": user_message},
        ],
    )
    return response.choices[0].message.content.strip()


def generate_blog_post(api_key: str, model: str, topic: str, language: str = "de") -> dict:
    client = _get_client(api_key)
    if not client:
        title = f"{topic}: practical guide"
        body = (
            f"# {title}\n\n"
            "This is a demo article. Set OPENAI_API_KEY to generate full SEO articles automatically.\n\n"
            "## Key points\n"
            "- Define the goal of the article\n"
            "- Add practical examples and use cases\n"
            "- Finish with a clear call to action\n"
        )
        return {
            "title": title,
            "excerpt": "Demo article. Connect AI for full generation.",
            "content": body,
            "seo_keywords": f"{topic}, consulting, digital strategy",
        }

    prompt = (
        f"Write an SEO-friendly blog article in {language} on topic: {topic}. "
        "Return strict JSON with keys: title, excerpt, content, seo_keywords. "
        "Content must be markdown with H2 sections and practical examples."
    )
    response = client.chat.completions.create(
        model=model,
        temperature=0.7,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": "You are an expert SEO copywriter for a consulting business website.",
            },
            {"role": "user", "content": prompt},
        ],
    )
    import json

    payload = json.loads(response.choices[0].message.content)
    return {
        "title": payload.get("title", topic),
        "excerpt": payload.get("excerpt", ""),
        "content": payload.get("content", ""),
        "seo_keywords": payload.get("seo_keywords", topic),
    }


def generate_crm_hint(api_key: str, model: str, lead_name: str, lead_stage: str, question: str) -> str:
    client = _get_client(api_key)
    if not client:
        return "AI hint is unavailable without OPENAI_API_KEY."

    response = client.chat.completions.create(
        model=model,
        temperature=0.4,
        messages=[
            {
                "role": "system",
                "content": "You are a sales assistant helping with CRM communication strategy.",
            },
            {
                "role": "user",
                "content": (
                    f"Client name: {lead_name}\n"
                    f"Stage: {lead_stage}\n"
                    f"Question: {question}\n"
                    "Provide actionable response in 3-5 bullet points."
                ),
            },
        ],
    )
    return response.choices[0].message.content.strip()
