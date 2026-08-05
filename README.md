# AngelSwert Flask Platform

Dockerized Flask + PostgreSQL project with:
- 5 public pages (home, about, services, programs, contact)
- Blog page with SEO posts and automatic AI generation by schedule
- Public AI chatbot (`/api/chat`)
- Admin panel with custom mini-CRM and AI assistant tips
- Homepage management of 4 YouTube links from admin panel

## Stack
- Flask + SQLAlchemy + Flask-Login
- PostgreSQL 16
- APScheduler for background blog automation
- OpenAI API (optional but recommended)
- Docker / Docker Compose

## Quick Start (Local)
1. Copy `.env.example` to `.env` and fill values.
2. Run:
   ```bash
   docker compose up --build
   ```
3. Open:
   - Website: http://localhost:5000
   - Admin login: http://localhost:5000/admin/login
4. Admin credentials are read from `.env` (`ADMIN_EMAIL`, `ADMIN_PASSWORD`).

## AI Features
- Public chatbot widget calls `POST /api/chat`
- Blog article generation in admin (`/admin/blog`)
- Scheduled blog posting from topic list in admin
- CRM AI hints in lead detail view

If `OPENAI_API_KEY` is empty, the app still works and returns fallback demo AI responses.

## Project Structure
- `app/routes` - public/api/auth/admin routes
- `app/models.py` - database models
- `app/services/ai_service.py` - OpenAI integration
- `app/services/blog_scheduler.py` - periodic blog generation
- `app/templates` - Jinja templates for website and admin
- `app/static` - CSS and JS

## Render Deployment Notes
- `render.yaml` is included as starter config
- For production, configure Render environment variables:
  - `SECRET_KEY`
  - `DATABASE_URL`
  - `OPENAI_API_KEY`
  - `ADMIN_EMAIL`
  - `ADMIN_PASSWORD`

## Important
- `db.create_all()` is used for MVP speed. For production evolution, add Alembic migrations.
- Scheduler runs inside the web process; keep one worker (`gunicorn -w 1`) to avoid duplicate scheduled jobs.
