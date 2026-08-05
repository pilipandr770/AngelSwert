import os


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

    if uri:
        return uri

    uri = _database_uri_from_parts()
    if uri:
        return uri

    # On Render we should fail fast to avoid accidentally using local Docker host names.
    if os.getenv("RENDER") == "true" or os.getenv("RENDER_EXTERNAL_HOSTNAME"):
        raise RuntimeError(
            "Database URL is not configured for Render. "
            "Link a managed PostgreSQL database and set DATABASE_URL."
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
