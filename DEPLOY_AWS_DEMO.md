# FestNest Demo Deployment (AWS EC2 + MySQL + MinIO)

This guide deploys FestNest for project/demo with low cost:
- Django app on EC2
- MySQL on same VM
- MinIO (open-source object storage) on same VM

## 1) Server setup

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip nginx mysql-server git docker.io docker-compose-plugin
sudo usermod -aG docker ubuntu
```

Log out and log in again once after adding docker group.

## 2) Clone project and install dependencies

```bash
cd /home/ubuntu
git clone <YOUR_GITHUB_REPO_URL> FestNest
cd FestNest
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 3) Create MySQL database

```bash
sudo mysql
```

Run inside MySQL:

```sql
CREATE DATABASE festnest_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'festnest_user'@'localhost' IDENTIFIED BY 'StrongPass123!';
GRANT ALL PRIVILEGES ON festnest_db.* TO 'festnest_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

## 4) Start MinIO

```bash
cd /home/ubuntu/FestNest/deploy/minio
cp .env.example .env
nano .env
```

Set strong values for `MINIO_ROOT_USER` and `MINIO_ROOT_PASSWORD`.

```bash
docker compose up -d
docker ps
```

Open MinIO console at: `http://<EC2_PUBLIC_IP>:9001`

Create bucket: `festnest-media`

## 5) Create environment file

```bash
cd /home/ubuntu/FestNest
cp .env.example .env
nano .env
```

Use this template:

```env
DJANGO_ENV=production
DJANGO_SECRET_KEY=replace-with-very-long-random-secret
DJANGO_DEBUG=false
DJANGO_ALLOWED_HOSTS=<EC2_PUBLIC_IP>
DJANGO_CSRF_TRUSTED_ORIGINS=http://<EC2_PUBLIC_IP>
DJANGO_TIME_ZONE=Asia/Kolkata

DJANGO_DB_ENGINE=django.db.backends.mysql
DJANGO_DB_NAME=festnest_db
DJANGO_DB_USER=festnest_user
DJANGO_DB_PASSWORD=StrongPass123!
DJANGO_DB_HOST=localhost
DJANGO_DB_PORT=3306

DJANGO_USE_S3=true
DJANGO_AWS_STORAGE_BUCKET_NAME=festnest-media
DJANGO_AWS_S3_ENDPOINT_URL=http://127.0.0.1:9000
DJANGO_AWS_ACCESS_KEY_ID=<MINIO_ROOT_USER>
DJANGO_AWS_SECRET_ACCESS_KEY=<MINIO_ROOT_PASSWORD>
DJANGO_AWS_S3_ADDRESSING_STYLE=path
DJANGO_AWS_QUERYSTRING_AUTH=false

DJANGO_DEFAULT_FROM_EMAIL=no-reply@festnest.local
```

## 6) Migrate and collect static

```bash
cd /home/ubuntu/FestNest
source .venv/bin/activate
set -a; source .env; set +a
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput
python manage.py check --deploy
```

## 7) Configure Gunicorn

```bash
sudo cp /home/ubuntu/FestNest/deploy/systemd/festnest.service /etc/systemd/system/festnest.service
sudo systemctl daemon-reload
sudo systemctl enable festnest
sudo systemctl start festnest
sudo systemctl status festnest --no-pager
```

## 8) Configure Nginx

```bash
sudo cp /home/ubuntu/FestNest/deploy/nginx/festnest.conf /etc/nginx/sites-available/festnest
sudo ln -sf /etc/nginx/sites-available/festnest /etc/nginx/sites-enabled/festnest
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

Visit:
`http://<EC2_PUBLIC_IP>`

## 9) Security group ports

Allow inbound:
- 80 (HTTP)
- 22 (SSH)
- 9001 (MinIO console, demo only)

Do not expose 9000 publicly in production; keep it internal if possible.

## 10) Useful operations

```bash
# App logs
sudo journalctl -u festnest -f

# Restart app
sudo systemctl restart festnest

# Restart nginx
sudo systemctl restart nginx

# MinIO logs
docker logs -f festnest-minio
```

