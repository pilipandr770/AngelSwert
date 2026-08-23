"""Boots the real Flask app against a throwaway SQLite DB and hits every public
route (in both languages) plus the admin login page, failing the build on any
non-2xx/3xx response or unhandled exception. Run in CI via GitHub Actions.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app

PUBLIC_PATHS = [
    "/",
    "/about",
    "/services",
    "/programs",
    "/contact",
    "/blog",
    "/impressum",
    "/privacy",
    "/terms",
    "/withdrawal",
    "/cookie-policy",
]

STATIC_ROUTES = [
    "/health",
    "/robots.txt",
    "/llms.txt",
    "/ai.txt",
    "/geo.txt",
    "/humans.txt",
    "/sitemap.xml",
]

ADMIN_ROUTES = [
    "/admin/login",
]


def main() -> int:
    app = create_app()
    client = app.test_client()
    failures: list[str] = []

    for path in PUBLIC_PATHS:
        for lang in ("de", "en"):
            url = f"{path}?lang={lang}"
            response = client.get(url)
            if response.status_code >= 400:
                failures.append(f"{url} -> {response.status_code}")

    for path in STATIC_ROUTES + ADMIN_ROUTES:
        response = client.get(path)
        if response.status_code >= 400:
            failures.append(f"{path} -> {response.status_code}")

    if failures:
        print("CI smoke test FAILED:")
        for failure in failures:
            print(f"  - {failure}")
        return 1

    print(f"CI smoke test OK: {len(PUBLIC_PATHS) * 2 + len(STATIC_ROUTES) + len(ADMIN_ROUTES)} requests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
