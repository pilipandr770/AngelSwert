import os
from urllib.parse import urlparse


def _database_uri_from_parts() -> str:
    host = os.getenv("PGHOST", "").strip() or os.getenv("DB_HOST", "").strip()
    port = os.getenv("PGPORT", "").strip() or os.getenv("DB_PORT", "").strip() or "5432"
    name = os.getenv("PGDATABASE", "").strip() or os.getenv("DB_NAME", "").strip()
    user = os.getenv("PGUSER", "").strip() or os.getenv("DB_USER", "").strip()
    password = os.getenv("PGPASSWORD", "").strip() or os.getenv("DB_PASSWORD", "").strip()
    ssl_mode = os.getenv("PGSSLMODE", "").strip()

    if not (host and name and user and password):
        return ""

    query = f"?sslmode={ssl_mode}" if ssl_mode else ""
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}{query}"


def _database_uri() -> str:
    is_render = os.getenv("RENDER") == "true" or bool(os.getenv("RENDER_EXTERNAL_HOSTNAME"))
    allow_render_sqlite_fallback = os.getenv("ALLOW_RENDER_SQLITE_FALLBACK", "false").lower() == "true"

    uri = ""
    for key in (
        "DATABASE_URL",
        "RENDER_DATABASE_URL",
        "POSTGRES_URL",
        "POSTGRESQL_URL",
    ):
        value = os.getenv(key, "").strip()
        if value:
            uri = value
            break

    if uri.startswith("postgres://"):
        uri = uri.replace("postgres://", "postgresql://", 1)

    if is_render and uri:
        parsed = urlparse(uri)
        if parsed.hostname == "db":
            uri = ""

    if uri:
        return uri

    uri = _database_uri_from_parts()
    if uri:
        return uri

    # In production on Render, avoid silent fallback to ephemeral SQLite.
    # Otherwise each redeploy can reset admin-managed data.
    if is_render:
        if allow_render_sqlite_fallback:
            return "sqlite:////tmp/angelswert_render_fallback.db"
        raise RuntimeError(
            "DATABASE_URL is not configured on Render. "
            "Configure a persistent Postgres connection or set "
            "ALLOW_RENDER_SQLITE_FALLBACK=true only for temporary troubleshooting."
        )

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
    S3_UPLOADS_ENABLED = os.getenv("S3_UPLOADS_ENABLED", "true").lower() == "true"
    S3_BUCKET = os.getenv("S3_BUCKET", "").strip()
    S3_REGION = os.getenv("S3_REGION", "").strip()
    S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL", "").strip()
    S3_PUBLIC_BASE_URL = os.getenv("S3_PUBLIC_BASE_URL", "").strip()
    S3_KEY_PREFIX = os.getenv("S3_KEY_PREFIX", "angelswert").strip().strip("/")
