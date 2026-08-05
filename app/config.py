import os


def _database_uri() -> str:
    uri = os.getenv("DATABASE_URL", "")
    if uri.startswith("postgres://"):
        uri = uri.replace("postgres://", "postgresql://", 1)
    if not uri:
        uri = "postgresql+psycopg2://angel:angelpass@db:5432/angelswert"
    return uri


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = _database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    BLOG_AI_MODEL = os.getenv("BLOG_AI_MODEL", OPENAI_MODEL)
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@angelswert.de")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "ChangeThisStrongPassword")
    PUBLIC_BRAND_NAME = os.getenv("PUBLIC_BRAND_NAME", "AngelSwert")
    ENABLE_BLOG_SCHEDULER = os.getenv("ENABLE_BLOG_SCHEDULER", "true").lower() == "true"
