# FestNest Render Deploy (Fast)

## 1) Push latest code to GitHub

Make sure your repo contains:
- `render.yaml`
- `requirements.txt`
- `Procfile`

## 2) Deploy from Render Blueprint

1. Login to Render
2. Click `New +` -> `Blueprint`
3. Connect your GitHub repo `FestNest`
4. Render will detect `render.yaml`
5. Click `Apply`

This creates:
- Web service: `festnest`
- Postgres database: `festnest-db`

## 3) Set required env vars in Render Web Service

In `festnest` -> `Environment`, set:

- `DJANGO_SECRET_KEY` (long random string)
- `DJANGO_ALLOWED_HOSTS` = your Render hostname (example: `festnest.onrender.com`)
- `DJANGO_CSRF_TRUSTED_ORIGINS` = `https://your-render-hostname`
- `DJANGO_EMAIL_BACKEND` and SMTP vars only if you want real emails

`DATABASE_URL` is wired automatically by `render.yaml`.

## 4) First deploy behavior

Start command runs:
- `python manage.py migrate`
- `gunicorn FestNest.wsgi:application`

Build command runs:
- `pip install -r requirements.txt`
- `python manage.py collectstatic --noinput`

## 5) After deploy

1. Open your Render URL
2. Visit `/admin/`
3. Create superuser using Render shell if needed:

```bash
python manage.py createsuperuser
```

