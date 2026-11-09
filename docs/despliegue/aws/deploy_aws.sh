#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# Despliegue de referencia de PlomApp en Ubuntu 24.04 (AWS EC2).
# Ejecutar como root o con sudo. Ajusta las variables antes de correrlo.
# ---------------------------------------------------------------------------
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

DOMAIN="${DOMAIN:-plomaap.duckdns.org}"
ALT_DOMAIN="${ALT_DOMAIN:-18-221-80-56.nip.io}"
EMAIL="${EMAIL:-admin@plomaap.com}"
REPO="${REPO:-https://github.com/Ricy24/plomaap_django.git}"
APP_DIR=/opt/plomaap/backend

echo "==> Paquetes del sistema"
apt update && apt upgrade -y
apt install -y python3.12 python3.12-venv python3-pip \
  build-essential libpq-dev \
  postgresql-16 postgresql-16-pgvector \
  nginx certbot python3-certbot-nginx \
  git ufw

echo "==> Firewall"
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 5000/tcp
ufw --force enable

echo "==> Código"
mkdir -p /opt/plomaap
chown ubuntu:ubuntu /opt/plomaap
if [ ! -d "$APP_DIR/.git" ]; then
  git clone "$REPO" "$APP_DIR"
fi
cd "$APP_DIR"
git fetch origin
git checkout main
git pull origin main

echo "==> Entorno virtual"
python3.12 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

echo "==> .env (debes copiarlo aparte, nunca versionarlo)"
if [ ! -f "$APP_DIR/.env" ]; then
  echo "ERROR: falta $APP_DIR/.env (cópialo desde tu gestor de secretos)."
  exit 1
fi
chmod 600 "$APP_DIR/.env"

echo "==> Migraciones y estáticos"
./venv/bin/python manage.py migrate
./venv/bin/python manage.py collectstatic --noinput

echo "==> Servicios Gunicorn"
install -m 644 "$(dirname "$0")/plomaap.service"  /etc/systemd/system/plomaap.service
install -m 644 "$(dirname "$0")/plomaap2.service" /etc/systemd/system/plomaap2.service
systemctl daemon-reload
systemctl enable --now plomaap plomaap2

echo "==> nginx"
install -m 644 "$(dirname "$0")/plomaap.nginx.conf" /etc/nginx/sites-available/plomaap
ln -sf /etc/nginx/sites-available/plomaap /etc/nginx/sites-enabled/plomaap
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

echo "==> Certificado SSL"
certbot certonly --webroot -w /var/www/html \
  -d "$DOMAIN" -d "$ALT_DOMAIN" \
  --non-interactive --agree-tos -m "$EMAIL" --keep-until-expiring

echo "==> Recargar nginx con TLS"
nginx -t
systemctl reload nginx

echo "==> Verificación"
curl -sS "https://$DOMAIN/api/health"; echo
curl -sS "https://$ALT_DOMAIN/api/health"; echo
