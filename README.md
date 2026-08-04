# Locker

A 3D-flavored digital vault: personal file storage, group collaboration, a
30-day trash with restore, favorites/tags, search and filters, and
in-app notifications — built on Django, styled as a cyberpunk/glassmorphism
experience with a Three.js hero and ambient particle background.

## What's actually here

This is a real, working Django project, tested end-to-end (register → upload
→ download → favorite → trash → restore → permanent delete → create group →
join by code → share a file with the group → notifications fire). It is
**not** the full spec from the original brief — some things were simplified
on purpose to ship something real instead of a pile of TODOs:

- **Notifications are polling-based** (checked every 20s), not WebSockets /
  Django Channels. Good enough for a small team; swap in Channels + Redis
  later if you need true push.
- **No Celery/Redis task queue** — uploads and deletes happen synchronously,
  which is fine at this scale.
- **No S3 wired in** — files save to local disk (`/media`) by default. Point
  `DEFAULT_FILE_STORAGE` at `django-storages` + S3 yourself if you need
  cloud storage; the model layer doesn't care where files live.
- **3D effects are on the hero and file cards**, not on literally every
  micro-interaction described in the original brief (shatter animations,
  drag-trail physics, etc.) — those are diminishing returns for a first
  ship and can be layered in later.

## Stack

- Django 6.0, SQLite by default (Postgres via `DATABASE_URL`)
- Vanilla JS + Three.js (via CDN) for the 3D hero and particle background
- Whitenoise for static files in production, Gunicorn as the app server
- Docker + docker-compose for deployment

## Local development

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env              # edit as needed — defaults work for local dev

python manage.py migrate
python manage.py createsuperuser  # optional, for /admin/
python manage.py runserver
```

Visit `http://127.0.0.1:8000/`. Emails (password reset, etc.) print to the
console by default — no SMTP setup needed for local dev.

## Running with Docker (production-shaped)

```bash
cp .env.example .env
# edit .env: set SECRET_KEY, ALLOWED_HOSTS to your real domain, DEBUG=False

docker compose up -d --build
```

This starts Postgres + the Django app behind Gunicorn, running migrations
and `collectstatic` automatically on boot. Visit `http://<your-host>:8000/`.

## Deploying for real

1. Set a strong, random `SECRET_KEY` in `.env` (never reuse the dev one).
2. Set `ALLOWED_HOSTS` to your actual domain(s).
3. Set `DEBUG=False`.
4. Put the app behind a reverse proxy (Nginx / Caddy / your host's load
   balancer) terminating HTTPS — `SECURE_SSL_REDIRECT=True` in `.env` once
   that's in place.
5. Use a real database — `DATABASE_URL=postgresql://user:pass@host:5432/db`.
6. Configure real SMTP (`EMAIL_HOST`, `EMAIL_HOST_USER`,
   `EMAIL_HOST_PASSWORD`) so password-reset emails actually send.
7. For file storage beyond local disk, add `django-storages` and an S3
   (or compatible) bucket.

## Project layout

```
locker/
├── manage.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── locker/              # project settings, urls, wsgi/asgi
└── core/                # the app: models, views, forms, templates, static
    ├── models.py         # Profile, VaultFile, Group, GroupMembership,
    │                     # Tag, ActivityLog, Notification
    ├── views.py
    ├── forms.py
    ├── urls.py
    ├── admin.py
    ├── signals.py        # auto-creates a Profile for every new User
    ├── context_processors.py  # unread notification count, everywhere
    ├── templates/
    └── static/
        ├── css/style.css
        └── js/           # particles.js, vault-hero.js, app.js
```

## Feature checklist (what's implemented)

- [x] Register / login / logout, password reset via email
- [x] Personal vault: upload, download, delete (soft), search, filter by
      type, sort, favorites
- [x] 30-day trash with restore and permanent delete
- [x] Groups: create, join by invite code, member add/remove (admin-only),
      shared uploads, leave group
- [x] Activity log (per user and per group)
- [x] In-app notifications (group joins, uploads) with a polling badge
- [x] Storage usage tracking per user
- [x] Django admin for all models
- [x] Docker + docker-compose, Postgres-ready, Whitenoise static serving

## Next steps if you want to push it further

- Swap notification polling for Django Channels + Redis if you want true
  real-time push and online-status indicators.
- Add `django-storages` for S3-backed file storage.
- Add automated tests (`python manage.py test`) — none are included yet.
- Layer in more of the original 3D micro-interactions (upload fly-in,
  delete shatter effect) once the core flows are solid in production.
