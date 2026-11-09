# Despliegue completo de PlomApp — AWS + Neon + Vercel

> Documento de estudio y operación.
> Última actualización: **2026-11-09**
> Autor del despliegue: Andrés Durán (cuenta AWS *Sunlit Servers*, usuario IAM `Andres`).
> Repositorios:
> - Backend: <https://github.com/Ricy24/plomaap_django>
> - Frontend: <https://github.com/Ricy24/plomaap_react_estable>

---

## Índice

1. [Resumen ejecutivo](#1-resumen-ejecutivo)
2. [Arquitectura final](#2-arquitectura-final)
3. [URLs públicas](#3-urls-públicas)
4. [Inventario de infraestructura](#4-inventario-de-infraestructura)
5. [Parte A — Despliegue en AWS EC2](#5-parte-a--despliegue-en-aws-ec2)
6. [Parte B — Base de datos gratuita en Neon](#6-parte-b--base-de-datos-gratuita-en-neon)
7. [Parte C — Despliegue en Vercel](#7-parte-c--despliegue-en-vercel)
8. [Parte D — El código, archivo por archivo](#8-parte-d--el-código-archivo-por-archivo)
9. [Flujo completo de una petición](#9-flujo-completo-de-una-petición)
10. [Verificación y pruebas](#10-verificación-y-pruebas)
11. [Seguridad](#11-seguridad)
12. [Costos](#12-costos)
13. [Decisiones técnicas y limitaciones](#13-decisiones-técnicas-y-limitaciones)
14. [Solución de problemas](#14-solución-de-problemas)
15. [Guía de estudio recomendada](#15-guía-de-estudio-recomendada)
16. [Anexos: configuraciones completas](#16-anexos-configuraciones-completas)

---

## 1. Resumen ejecutivo

PlomApp es una aplicación de servicios de plomería compuesta por:

- **Backend Django** (API REST pura, sin panel de Django, autenticación JWT).
- **Frontend React + Vite** (SPA).
- **PostgreSQL con pgvector** (búsqueda semántica / recomendaciones).

El despliegue quedó así:

| Capa | Plataforma | Costo |
|---|---|---|
| Frontend React | **Vercel Hobby** (CDN global) | Gratis |
| Backend API (principal, serverless) | **Vercel Hobby** (funciones Python) | Gratis |
| Backend API (respaldo con balanceador) | **AWS EC2 t3.micro** + nginx + Gunicorn | Free tier 12 meses |
| Base de datos | **Neon Free** (PostgreSQL 18.6 + pgvector 0.8.6) | Gratis |
| DNS | **DuckDNS** (`plomaap.duckdns.org`) | Gratis |
| SSL | **Let's Encrypt** (certbot) | Gratis |

Hay **dos backends funcionales apuntando a la misma base de datos Neon**:

1. **Vercel** (`https://plomaap-api.vercel.app`): es el que usa el frontend desplegado. No hay servidor que administrar; Vercel ejecuta Django como función serverless.
2. **AWS** (`https://plomaap.duckdns.org`): servidor Ubuntu con nginx como **balanceador de carga** entre dos procesos Gunicorn (`:8000` y `:8001`), certificado SSL y IP elástica. Sirve como respaldo y como ejemplo real de infraestructura con balanceador.

> **Idea clave para estudiar:** el mismo código Django corre de dos formas distintas sin cambios: con **Gunicorn + nginx** (proceso persistente) o con **una función serverless** (WSGI envuelto por Vercel). La base de datos es la misma, por lo que ambas APIs ven exactamente los mismos datos.

---

## 2. Arquitectura final

![Diagrama de arquitectura](arquitectura.svg)

> El mismo diagrama está disponible en formato Mermaid (renderiza automáticamente en GitHub):

```mermaid
flowchart TD
    Browser["Navegador<br/>plomaap-react.vercel.app"]
    VCDN["Vercel CDN<br/>Frontend React (Vite)"]
    VS["Vercel Serverless<br/>Django WSGI (index.py)"]
    AWS["AWS EC2 t3.micro<br/>nginx round-robin"]
    G1["Gunicorn :8000"]
    G2["Gunicorn :8001"]
    NEON["Neon PostgreSQL 18.6<br/>+ pgvector"]
    CLD["Cloudinary<br/>(fotos / avatares)"]
    DNS["DuckDNS + Let's Encrypt"]

    Browser -->|fetch JSON+JWT| VCDN
    VCDN --> VS
    VS -->|psycopg2 SSL| NEON
    Browser -->|HTTPS / :5000| AWS
    AWS --> G1
    AWS --> G2
    G1 -->|psycopg2 SSL| NEON
    G2 -->|psycopg2 SSL| NEON
    Browser -.->|subida directa| CLD

    style VCDN fill:#e0f2fe,stroke:#0284c7
    style VS fill:#dbeafe,stroke:#2563eb
    style AWS fill:#ffedd5,stroke:#ea580c
    style NEON fill:#dcfce7,stroke:#16a34a
    style CLD fill:#fef9c3,stroke:#ca8a04
```

```
                              ┌─────────────────────────────┐
                              │        Navegador            │
                              │  https://plomaap-react...   │
                              └──────────────┬──────────────┘
                                             │ HTTPS
                                             ▼
                    ┌────────────────────────────────────────┐
                    │        VERCEL (CDN global)             │
                    │  Proyecto: plomaap-react               │
                    │  Sirve la SPA React (Vite)             │
                    │  https://plomaap-react.vercel.app      │
                    └──────────────┬─────────────────────────┘
                                   │ fetch() a VITE_API_URL
                                   │ (JSON + JWT)
                                   ▼
              ┌──────────────────────────────────────────────┐
              │        VERCEL (función serverless)           │
              │  Proyecto: plomaap-api                       │
              │  index.py  ->  app = get_wsgi_application()  │
              │  https://plomaap-api.vercel.app              │
              └───────────────────┬──────────────────────────┘
                                  │ psycopg2 + SSL
                                  ▼
              ┌──────────────────────────────────────────────┐
              │        NEON (PostgreSQL 18.6 gratis)         │
              │  neondb  +  extensión pgvector 0.8.6         │
              │  ep-restless-lab-...us-east-2.aws.neon.tech  │
              └──────────────────────────────────────────────┘

   ── Camino alterno / respaldo (misma base de datos) ──

              ┌──────────────────────────────────────────────┐
              │        AWS EC2  t3.micro  (Ubuntu 24.04)     │
              │        IP elástica 18.221.80.56              │
              │                                              │
   HTTPS ───► │  nginx :443  (balanceador round-robin)       │
              │      ├── Gunicorn 127.0.0.1:8000             │
              │      └── Gunicorn 127.0.0.1:8001             │
              │  Certificado Let's Encrypt                   │
              └───────────────────┬──────────────────────────┘
                                  │
                                  ▼
                         (la misma base Neon)
```

### ¿Por qué dos backends?

- **Vercel** cumple el requisito “todo en Vercel” y no cuesta nada.
- **AWS** cumple el requisito explícito de tener **balanceador de carga** y **certificado SSL** con un servidor real. Además demuestra cómo se hace en la industria.
- Ambos comparten Neon, así que no hay datos duplicados ni migraciones pendientes.

---

## 3. URLs públicas

| Servicio | URL | Estado |
|---|---|---|
| Frontend | <https://plomaap-react.vercel.app> | ✅ |
| API principal (Vercel) | <https://plomaap-api.vercel.app/api> | ✅ |
| Health check Vercel | <https://plomaap-api.vercel.app/api/health> | ✅ |
| API respaldo (AWS) | <https://plomaap.duckdns.org/api> | ✅ |
| Health check AWS | <https://plomaap.duckdns.org/api/health> | ✅ |
| Dominio alterno AWS | <https://18-221-80-56.nip.io/api> | ✅ |
| HTTP directo AWS | <http://18.221.80.56:5000/api> | ✅ |

### Cuentas de prueba

| Rol | Email | Contraseña |
|---|---|---|
| Administrador | `admin@plomaap.com` | Ver `.env` del servidor / gestor de secretos |
| Técnico | `carlos@plomaap.com` | `123456` (¡cambiar en producción!) |
| Técnico | `roberto@plomaap.com` | `123456` (¡cambiar en producción!) |

> Las contraseñas **no se escriben en este documento** porque el repositorio es público. En el servidor viven en `/opt/plomaap/backend/.env` y en Vercel como *Environment Variables* cifradas.

---

## 4. Inventario de infraestructura

### 4.1 AWS

| Recurso | Valor |
|---|---|
| Cuenta | `433306738256` (*Sunlit Servers*) |
| Región | `us-east-2` (Ohio) |
| Instancia EC2 | `i-02ff7ac21f7d6d155` |
| Tipo | `t3.micro` (2 vCPU, 1 GiB RAM) |
| Zona | `us-east-2b` |
| Disco | 20 GB `gp3` |
| IP elástica | `18.221.80.56` |
| Security Group | `plomaap-sg` / `sg-0d01b48cf62cff454` |
| Llave SSH | `plomaap_aws.pem` (guardada en `C:\Users\Anrid\.ssh\plomaap_aws.pem`) |
| SO | Ubuntu 24.04 LTS |
| Python | 3.12 |
| Usuario SSH | `ubuntu` |

**Reglas del Security Group**

| Puerto | Protocolo | Origen | Para qué |
|---|---|---|---|
| 22 | TCP | `181.32.211.255/32` | SSH (solo la IP del desarrollador) |
| 80 | TCP | `0.0.0.0/0` | HTTP → redirección a HTTPS / ACME |
| 443 | TCP | `0.0.0.0/0` | HTTPS |
| 5000 | TCP | `0.0.0.0/0` | HTTP de compatibilidad (frontend viejo / pruebas) |

> **Nota:** el puerto 5000 se deja abierto solo por compatibilidad. En un entorno real se cerraría y se obligaría HTTPS.

### 4.2 Neon

| Dato | Valor |
|---|---|
| Organización | `Andres ricardo` (`org-steep-cloud-46434877`) |
| Proyecto | `my-first-project` (`still-feather-60435059`) |
| Rama | `production` |
| Base de datos | `neondb` |
| Usuario | `neondb_owner` |
| Región | AWS US East 2 (Ohio) |
| Motor | PostgreSQL 18.6 |
| Extensión | `vector` 0.8.6 (pgvector) |
| Host directo | `ep-restless-lab-bdv0vp50.c-8.us-east-2.aws.neon.tech` |
| Host con pooling | `ep-restless-lab-bdv0vp50-pooler.c-8.us-east-2.aws.neon.tech` |

- **AWS usa el host directo.**
- **Vercel usa el host con `-pooler`**, porque las funciones serverless abren y cierran conexiones constantemente y el pooler evita agotar las conexiones de Postgres.

### 4.3 Vercel

| Dato | Valor |
|---|---|
| Usuario CLI | `discordandres20` |
| Equipo / scope | `discordandres20s-projects` (`team_tCjWstnGVcyQsvddkj2WSqoP`) |
| Proyecto frontend | `plomaap-react` (`prj_I8vWxDOxaA7Ijp9mVz5UDe4mtJRT`) |
| URL frontend | `https://plomaap-react.vercel.app` |
| Proyecto backend | `plomaap-api` (`prj_lACSenPBRrHRBaVU8hYqTP7YdgA6`) |
| URL backend | `https://plomaap-api.vercel.app` |
| Plan | Hobby (gratis) |

### 4.4 Dominios

| Dominio | Proveedor | Apunta a |
|---|---|---|
| `plomaap.duckdns.org` | DuckDNS (gratis) | `18.221.80.56` |
| `18-221-80-56.nip.io` | nip.io (gratis) | `18.221.80.56` |
| `plomaap-react.vercel.app` | Vercel | CDN de Vercel |
| `plomaap-api.vercel.app` | Vercel | Función serverless |

### 4.5 Google Cloud / OAuth

| Dato | Valor |
|---|---|
| Proyecto | `plomaap-498517` |
| Cliente web (frontend) | `664888808352-v93273q2nab33bdeoupfk47112fi2p8t.apps.googleusercontent.com` |
| Cliente Android (app móvil) | `664888808352-c94rm998nrabopsd3chjgkrif2081448.apps.googleusercontent.com` |
| Orígenes JS autorizados | `http://localhost:5173`, `http://localhost:3000`, `https://plomaap-react.vercel.app`, `https://plomaap.duckdns.org` |

> **Detalle importante:** el backend valida el `aud` (audience) del token contra `GOOGLE_CLIENT_ID`. Para que el login con Google funcione desde la web, el backend de Vercel usa el **cliente web** (`...v932...`). El backend de AWS usa el **cliente Android** (`...c94r...`), pensado para la app móvil; si se quiere login con Google también desde la web apuntando a AWS, hay que alinear ese valor o aceptar varios audiences en el código.
>
> Los cambios en los orígenes autorizados pueden tardar **de 5 minutos a algunas horas** en aplicarse. Si el botón de Google muestra `origin_mismatch`, espera y vuelve a probar.

---

## 5. Parte A — Despliegue en AWS EC2

Esta parte reproduce, en orden, todo lo que se hizo en la instancia. Los scripts originales usados durante la sesión fueron `deploy1.sh` … `deploy6.sh` (en la carpeta temporal de la sesión). Aquí están consolidados y limpios.

### 5.1 Crear la infraestructura (AWS CLI desde CloudShell)

Se usó **AWS CloudShell** en lugar de la consola web porque es más rápido y reproducible.

```bash
# Variables
REGION=us-east-2
INSTANCE_TYPE=t3.micro
AMI=ami-0b8b1a4b0c1d2e3f4   # Ubuntu 24.04 LTS (us-east-2) — usar el AMI vigente

# 1) Security Group
SG_ID=$(aws ec2 create-security-group \
  --group-name plomaap-sg \
  --description "PlomApp: SSH, HTTP, HTTPS, 5000" \
  --region $REGION \
  --query GroupId --output text)

aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 22   --cidr 181.32.211.255/32 --region $REGION
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 80   --cidr 0.0.0.0/0     --region $REGION
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 443  --cidr 0.0.0.0/0     --region $REGION
aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 5000 --cidr 0.0.0.0/0     --region $REGION

# 2) Llave SSH
aws ec2 create-key-pair --key-name plomaap-aws \
  --query KeyMaterial --output text --region $REGION > plomaap_aws.pem
chmod 400 plomaap_aws.pem

# 3) Instancia
INSTANCE_ID=$(aws ec2 run-instances \
  --image-id $AMI \
  --instance-type $INSTANCE_TYPE \
  --key-name plomaap-aws \
  --security-group-ids $SG_ID \
  --block-device-mappings '[{"DeviceName":"/dev/sda1","Ebs":{"VolumeSize":20,"VolumeType":"gp3","DeleteOnTermination":true}}]' \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=plomaap-backend}]' \
  --region $REGION \
  --query 'Instances[0].InstanceId' --output text)

# 4) IP elástica (para que la IP no cambie al reiniciar)
ALLOC_ID=$(aws ec2 allocate-address --domain vpc --region $REGION --query AllocationId --output text)
aws ec2 associate-address --instance-id $INSTANCE_ID --allocation-id $ALLOC_ID --region $REGION
```

> La llave privada se descargó a `C:\Users\Anrid\.ssh\plomaap_aws.pem` y la copia de CloudShell se borró con `shred`.

### 5.2 Preparar Ubuntu

```bash
ssh -i ~/.ssh/plomaap_aws.pem ubuntu@18.221.80.56

sudo apt update && sudo apt upgrade -y
sudo apt install -y \
  python3.12 python3.12-venv python3-pip \
  build-essential libpq-dev \
  postgresql-16 postgresql-16-pgvector \
  nginx certbot python3-certbot-nginx \
  git ufw

sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 5000/tcp
sudo ufw --force enable
```

### 5.3 Código y entorno Python

```bash
sudo mkdir -p /opt/plomaap
sudo chown ubuntu:ubuntu /opt/plomaap

# Clonar el backend
cd /opt/plomaap
git clone https://github.com/Ricy24/plomaap_django.git backend
cd backend
git checkout main

# Entorno virtual
python3.12 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt
```

`requirements.txt` (runtime):

```text
Django==6.1.2
python-dotenv==1.2.4
django-cors-headers==4.9.0
PyJWT==2.15.1
bcrypt==5.0.0
requests==2.34.2
google-auth==2.62.0
google-auth-oauthlib==1.5.0
google-auth-httplib2==0.4.4
cryptography==50.0.2
pgvector==0.5.1
psycopg2-binary==2.9.13
PyMySQL==1.2.3
webauthn==3.0.1
tzdata==2026.5
```

### 5.4 Base de datos local (respaldo)

La base local de la EC2 se creó con Postgres 16 + pgvector. **Después se apagó** para ahorrar RAM, porque la base real es Neon.

```bash
sudo -u postgres psql <<'SQL'
CREATE USER plomaap WITH PASSWORD '********';
CREATE DATABASE plomapp OWNER plomaap;
\c plomapp
CREATE EXTENSION IF NOT EXISTS vector;
SQL
```

Migraciones y datos iniciales:

```bash
cd /opt/plomaap/backend
export $(grep -v '^#' .env | xargs)   # o usar EnvironmentFile en systemd
./venv/bin/python manage.py migrate
./venv/bin/python manage.py seed_admin
./venv/bin/python manage.py seed_technicians
./venv/bin/python manage.py seed_services
./venv/bin/python manage.py collectstatic --noinput
```

> El dump local se exportó con `pg_dump -Fc` y se restauró en Neon. Ver [Parte B](#6-parte-b--base-de-datos-gratuita-en-neon).

### 5.5 Gunicorn con systemd

Se crearon **dos servicios** para que nginx tenga dos backends reales y pueda balancear.

`/etc/systemd/system/plomaap.service`:

```ini
[Unit]
Description=Plomaap Django backend (gunicorn 8000)
After=network.target postgresql.service

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/opt/plomaap/backend
EnvironmentFile=/opt/plomaap/backend/.env
ExecStart=/opt/plomaap/backend/venv/bin/gunicorn config.wsgi:application \
  --bind 127.0.0.1:8000 --workers 1 --threads 2 --timeout 90 \
  --access-logfile - --error-logfile -
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

`/etc/systemd/system/plomaap2.service` es idéntico pero con `--bind 127.0.0.1:8001` y descripción “gunicorn 8001”.

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now plomaap plomaap2
sudo systemctl status plomaap plomaap2
```

> **¿Por qué 1 worker y 2 threads?** La instancia tiene 1 GiB de RAM. Un worker de Django pesa ~120–180 MB. Dos procesos con 1 worker cada uno caben; 2 workers por proceso no.

### 5.6 nginx como balanceador de carga

`/etc/nginx/sites-available/plomaap` (resumen; completo en el [Anexo 16.1](#161-nginx-aws)):

```nginx
upstream plomaap_backend {
    server 127.0.0.1:8000 max_fails=3 fail_timeout=10s;
    server 127.0.0.1:8001 max_fails=3 fail_timeout=10s;
}

server {
    listen 80;
    server_name plomaap.duckdns.org 18-221-80-56.nip.io;
    location /.well-known/acme-challenge/ { root /var/www/html; }
    location / { return 301 https://$host$request_uri; }
}

server {
    listen 5000;
    server_name _;
    client_max_body_size 12M;
    location / { proxy_pass http://plomaap_backend; ... }
}

server {
    listen 443 ssl;
    server_name plomaap.duckdns.org 18-221-80-56.nip.io;
    ssl_certificate     /etc/letsencrypt/live/18-221-80-56.nip.io/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/18-221-80-56.nip.io/privkey.pem;
    client_max_body_size 12M;
    location /static/uploads/ { proxy_pass http://plomaap_backend; ... }
    location /static/ { alias /opt/plomaap/backend/staticfiles/; expires 7d; }
    location / { proxy_pass http://plomaap_backend; ... }
}
```

Puntos importantes:

- `upstream` con **round-robin** (reparto 1:1).
- `max_fails=3 fail_timeout=10s`: si un backend falla 3 veces en 10 s, nginx deja de enviarle tráfico temporalmente.
- Cabeceras `X-Forwarded-For` y `X-Forwarded-Proto` para que Django sepa que viene de HTTPS.
- `/static/` se sirve directo desde disco (más rápido que Django).
- `/static/uploads/` se proxya porque los archivos los sirve una vista de Django (`serve_uploaded_file`).

```bash
sudo ln -sf /etc/nginx/sites-available/plomaap /etc/nginx/sites-enabled/plomaap
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

### 5.7 SSL con Let's Encrypt

```bash
sudo certbot certonly --webroot -w /var/www/html \
  -d plomaap.duckdns.org -d 18-221-80-56.nip.io \
  --non-interactive --agree-tos -m admin@plomaap.com \
  --keep-until-expiring
```

- Certificado en `/etc/letsencrypt/live/18-221-80-56.nip.io/`.
- Válido hasta **2027-02-07**.
- Renovación automática con `certbot.timer` (comprobar con `systemctl list-timers | grep certbot`).
- El **Subject Alternative Name** incluye ambos dominios.

### 5.8 DuckDNS

1. Entrar a <https://www.duckdns.org> con Google (`anriduco2019@gmail.com`).
2. Crear el subdominio `plomaap` → queda `plomaap.duckdns.org`.
3. Asignar la IP `18.221.80.56`.
4. Verificar: `nslookup plomaap.duckdns.org` debe devolver la IP elástica.

También se puede actualizar por API (útil para automatizar):

```bash
curl "https://www.duckdns.org/update?domains=plomaap&token=TU_TOKEN&ip=18.221.80.56"
```

### 5.9 Operación diaria en AWS

```bash
# Estado de servicios
sudo systemctl status plomaap plomaap2 nginx
sudo systemctl restart plomaap plomaap2
sudo systemctl reload nginx

# Logs en vivo
sudo journalctl -u plomaap -f
sudo journalctl -u plomaap2 -f
sudo tail -f /var/log/nginx/access.log

# Actualizar código
cd /opt/plomaap/backend
git pull origin main
./venv/bin/pip install -r requirements.txt
./venv/bin/python manage.py migrate
./venv/bin/python manage.py collectstatic --noinput
sudo systemctl restart plomaap plomaap2

# Renovar certificado manualmente
sudo certbot renew --dry-run

# Memoria
free -h
```

---

## 6. Parte B — Base de datos gratuita en Neon

### 6.1 Crear el proyecto

1. <https://console.neon.tech> → login con Google (`anriduco2019@gmail.com`).
2. Crear proyecto en **AWS US East 2 (Ohio)** para que esté en la misma región que la EC2.
3. Guardar la cadena de conexión.

### 6.2 Restaurar el dump local

En la EC2:

```bash
export PGPASSWORD='********'
NEON="postgresql://neondb_owner:********@ep-restless-lab-bdv0vp50.c-8.us-east-2.aws.neon.tech/neondb?sslmode=require"

# 1) Extensión pgvector
psql "$NEON" -c "CREATE EXTENSION IF NOT EXISTS vector;"

# 2) Dump de la base local
sudo -u postgres pg_dump -Fc -f /tmp/plomapp.dump plomapp

# 3) Restaurar en Neon
pg_restore --no-owner --no-acl --clean --if-exists -d "$NEON" /tmp/plomapp.dump || true

# 4) Verificar
psql "$NEON" -tAc "select count(*) from users;"      # 3
psql "$NEON" -tAc "select count(*) from services;"   # 4
psql "$NEON" -tAc "select extversion from pg_extension where extname='vector';"  # 0.8.6
```

### 6.3 Variables de entorno

En AWS (`/opt/plomaap/backend/.env`):

```dotenv
DATABASE_URL=postgresql://neondb_owner:********@ep-restless-lab-bdv0vp50.c-8.us-east-2.aws.neon.tech/neondb?sslmode=require
PGSSLMODE=require
```

En Vercel (proyecto `plomaap-api`), usando el **pooler**:

```dotenv
DATABASE_URL=postgresql://neondb_owner:********@ep-restless-lab-bdv0vp50-pooler.c-8.us-east-2.aws.neon.tech/neondb?sslmode=require
```

> **¿Por qué `-pooler` en Vercel?** Cada invocación serverless puede abrir una conexión nueva. Sin pooler, muchas invocaciones concurrentes agotan el límite de conexiones de Neon. El pooler multiplexa conexiones y evita el error `too many connections`.

### 6.4 Cómo resuelve Django la base de datos

En `config/settings.py`, función `_build_database()`:

1. Si existe `DATABASE_URL`, la parsea y usa PostgreSQL (o MySQL/SQLite según el esquema).
2. Si no, usa `DB_ENGINE` + variables `POSTGRES_*`.
3. Si no, MySQL (`MYSQL_*`).
4. Si no, SQLite.

Esto permite que **el mismo código** funcione en local (Postgres en Docker), en AWS (Neon) y en Vercel (Neon pooler) sin cambios.

---

## 7. Parte C — Despliegue en Vercel

### 7.1 Frontend React (proyecto `plomaap-react`)

El repositorio `plomaap_react_estable` ya trae un `vercel.json`:

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "framework": "vite",
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "rewrites": [
    { "source": "/((?!assets/).*)", "destination": "/index.html" }
  ],
  "headers": [
    {
      "source": "/assets/(.*)",
      "headers": [
        { "key": "Cache-Control", "value": "public, max-age=31536000, immutable" }
      ]
    }
  ]
}
```

- `rewrites` es lo que hace que funcione el **router de React**: cualquier ruta que no sea un asset devuelve `index.html`, y React Router resuelve `/admin`, `/ingresar`, etc.
- `headers` cachea los assets con hash para siempre (Vite les pone hash en el nombre).

**Variables de entorno en Vercel (Production):**

| Variable | Valor |
|---|---|
| `VITE_API_URL` | `https://plomaap-api.vercel.app` |
| `VITE_GEOCODING_API` | `https://nominatim.openstreetmap.org/search` |
| `VITE_CLOUDINARY_CLOUD_NAME` | `dxoejokli` |
| `VITE_CLOUDINARY_UPLOAD_PRESET` | `plomaap` |
| `VITE_GOOGLE_CLIENT_ID` | `664888808352-v93273q2nab33bdeoupfk47112fi2p8t.apps.googleusercontent.com` |

> **Importante:** las variables de Vite se “hornean” en el bundle en **tiempo de build**. Si cambias `VITE_API_URL`, tienes que **volver a desplegar**; no basta con guardar la variable.

**Desplegar:**

```bash
cd C:\Users\Anrid\plomaap_react_estable
npx vercel --prod --yes
```

La CLI usa el proyecto ya vinculado en `.vercel/project.json`. Resultado: `https://plomaap-react.vercel.app`.

### 7.2 Backend Django serverless (proyecto `plomaap-api`)

Vercel no ejecuta Gunicorn, pero **sí ejecuta WSGI** dentro de una función Python. En la **raíz del repositorio** se agregaron estos archivos:

**`index.py`** — punto de entrada:

```python
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

from django.core.wsgi import get_wsgi_application

app = get_wsgi_application()
```

**`vercel.json`** — le dice a Vercel que use el runtime de Python y enrute todo a `index.py`:

```json
{
  "version": 2,
  "builds": [
    {
      "src": "index.py",
      "use": "@vercel/python",
      "config": { "maxLambdaSize": "50mb" }
    }
  ],
  "routes": [
    { "src": "/(.*)", "dest": "index.py" }
  ]
}
```

**`.vercelignore`** — excluye `pyproject.toml` (que solo tiene configuración de Ruff) para que Vercel instale las dependencias desde `requirements.txt`:

```text
pyproject.toml
venv
.git
.github
docs
backups
api/tests
.pytest_cache
.ruff_cache
.playwright-mcp
*.dump
*.sqlite3
```

> **Trampa encontrada:** el repositorio tiene un `pyproject.toml` que solo contiene configuración de Ruff (no dependencias). Vercel lo detectó y dijo “Installing required dependencies from pyproject.toml…”, por lo que **no instaló nada** y la función devolvía 500. Solución: `.vercelignore` excluye `pyproject.toml` para que Vercel use `requirements.txt`. Si algún día agregas dependencias reales a `pyproject.toml`, decláralas con `[project] dependencies = [...]` o mantén solo `requirements.txt` para Vercel.

**Variables de entorno del backend en Vercel:**

| Variable | Valor / nota |
|---|---|
| `SECRET_KEY` | Secreto generado (distinto al de AWS o el mismo, da igual) |
| `JWT_SECRET_KEY` | Secreto generado |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | `plomaap-api.vercel.app,.vercel.app,plomaap.duckdns.org,...,localhost,127.0.0.1` |
| `DATABASE_URL` | Neon con `-pooler` |
| `PGSSLMODE` | `require` |
| `CORS_ALLOW_ALL_ORIGINS` | `True` |
| `CORS_ORIGINS` | `https://plomaap-react.vercel.app` |
| `WEBAUTHN_RP_ID` | `plomaap-react.vercel.app` |
| `WEBAUTHN_ORIGIN` | `https://plomaap-react.vercel.app` |
| `CSRF_TRUSTED_ORIGINS` | `https://plomaap-react.vercel.app,https://plomaap.duckdns.org,...` |
| `USE_X_FORWARDED_PROTO` | `True` |
| `SECURE_SSL_REDIRECT` | `False` (Vercel ya termina TLS) |
| `GOOGLE_CLIENT_ID` | El **mismo** que usa el frontend (`...v932...`) |
| `MAIL_*`, `GEMINI_API_KEY`, `VOYAGE_API_KEY`, `EMBEDDING_*` | Igual que en AWS |

**Desplegar (desde la raíz del repositorio):**

```bash
cd C:\Users\Anrid\backend_plomaap
npx vercel link --yes --project plomaap-api   # solo la primera vez
npx vercel --prod --yes
```

`vercel.json`, `index.py` y `.vercelignore` viven en la **raíz** del repositorio, así que ya no hace falta copiar el proyecto a una carpeta temporal. `.vercelignore` se encarga de no subir `venv`, `.git`, `docs`, `backups`, `api/tests`, etc., y de excluir `pyproject.toml`.

Resultado: `https://plomaap-api.vercel.app`.

### 7.3 Variables de entorno por CLI

```bash
# Crear/actualizar (sobrescribe con --force)
npx vercel env add VITE_API_URL production \
  --value "https://plomaap-api.vercel.app" --force --yes

# Listar
npx vercel env ls production

# Descargar a un archivo local (¡contiene secretos!)
npx vercel env pull .env.vercel.production --environment production
```

> `vercel env pull` descarga los valores **descifrados**. Ese archivo está en `.gitignore` (`.env.*`), nunca lo subas.

### 7.4 Volver a desplegar tras un cambio

**Frontend:**

```bash
cd C:\Users\Anrid\plomaap_react_estable
git pull
npx vercel --prod --yes
```

**Backend:**

```bash
cd C:\Users\Anrid\backend_plomaap
git pull
npx vercel --prod --yes
```

Eso es todo: `vercel.json` enruta todo a `index.py` y `.vercelignore` excluye lo que no debe subir. La CLI recuerda el proyecto vinculado en `.vercel/project.json`.

> **Ojo con `.vercelignore`:** si algún día necesitas que Vercel incluya un archivo o carpeta nueva (por ejemplo, un directorio de datos), agrégalo a la lista de exclusión con cuidado o usa el patrón inverso `!carpeta/archivo`.

---

## 8. Parte D — El código, archivo por archivo

### 8.1 Mapa del backend

```text
backend_plomaap/
├── manage.py                     # CLI de Django
├── requirements.txt              # dependencias de producción
├── requirements-dev.txt          # pytest, ruff, etc.
├── .env.example                  # plantilla de variables (sin secretos)
├── index.py                      # entrada WSGI para Vercel (app = get_wsgi_application())
├── vercel.json                   # build @vercel/python + ruta /(.*) -> index.py
├── .vercelignore                 # excluye pyproject.toml, venv, docs, etc. del deploy
├── config/
│   ├── settings.py               # configuración central (DB, CORS, JWT, seguridad)
│   ├── urls.py                   # rutas raíz: /api/ y /static/uploads/
│   ├── wsgi.py                   # aplicación WSGI (la usa Gunicorn y Vercel)
│   └── asgi.py                   # aplicación ASGI (no usada en este despliegue)
├── api/
│   ├── urls.py                   # TODAS las rutas /api/*
│   ├── models.py                 # modelos/tablas (User, Service, Appointment, ...)
│   ├── middleware.py             # errores JSON + logging de seguridad
│   ├── errors.py                 # handlers 400/401/403/404/500
│   ├── views/                    # controladores HTTP por dominio
│   │   ├── auth_views.py
│   │   ├── service_views.py
│   │   ├── technician_views.py
│   │   ├── appointment_views.py
│   │   ├── admin_views.py
│   │   ├── address_views.py
│   │   ├── favorite_views.py
│   │   ├── event_views.py
│   │   ├── home_views.py
│   │   ├── onboarding_views.py
│   │   ├── embedding_views.py
│   │   ├── search_views.py
│   │   ├── intelligence_views.py
│   │   ├── recommendation_views.py
│   │   ├── upload_views.py
│   │   └── health_views.py
│   ├── controllers/              # lógica de auth y passkeys
│   │   ├── auth_controller.py
│   │   └── passkey_controller.py
│   ├── services/                 # lógica de negocio reutilizable
│   │   ├── appointment_service.py
│   │   ├── embedding_provider.py
│   │   ├── embedding_service.py
│   │   ├── event_service.py
│   │   ├── hybrid_search_service.py
│   │   ├── nlu_service.py
│   │   ├── onboarding_service.py
│   │   ├── profile_service.py
│   │   └── recommendation_service.py
│   ├── utils/                    # helpers
│   │   ├── jwt_utils.py          # firmar/verificar JWT HS256
│   │   ├── decorators.py         # @jwt_required_custom
│   │   ├── dispatch.py           # methods(GET=..., POST=...) → 405 JSON
│   │   ├── rate_limit.py         # límite de peticiones por IP
│   │   ├── request_utils.py      # json_body()
│   │   ├── email_utils.py        # envío SMTP (Zoho)
│   │   └── validators.py         # validaciones de email, teléfono, etc.
│   ├── management/commands/      # comandos de siembra
│   │   ├── seed_admin.py
│   │   ├── seed_technicians.py
│   │   ├── seed_services.py
│   │   └── seed.py
│   ├── migrations/               # esquema de la base de datos
│   └── tests/                    # unitarias + integración
├── static/uploads/evidence/      # fotos de evidencia (disco local en AWS)
└── docs/                         # documentación y plan de pruebas
```

### 8.2 `config/settings.py` — lo más importante

**a) Carga del `.env`**

```python
load_dotenv(BASE_DIR / '.env')
```

Así el mismo código lee variables de entorno en local, en AWS y en Vercel.

**b) Resolución de base de datos**

```python
def _build_database():
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        ...
        return {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': parsed.path.lstrip('/'),
            'USER': parsed.username,
            'PASSWORD': parsed.password,
            'HOST': parsed.hostname,
            'PORT': str(parsed.port or 5432),
            'CONN_MAX_AGE': 60,
        }
    ...
```

**c) CORS**

```python
CORS_ALLOW_ALL_ORIGINS = os.getenv('CORS_ALLOW_ALL_ORIGINS', 'True').lower() in {...}
CORS_ALLOW_CREDENTIALS = True
```

Se dejó abierto para que funcione cualquier dominio de Vercel (`*.vercel.app`) y el dominio de AWS. En producción estricta se pondría `CORS_ORIGINS=https://plomaap-react.vercel.app`.

**d) JWT**

```python
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', ...)
JWT_ALGORITHM = 'HS256'
JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=int(os.getenv('JWT_EXPIRATION_HOURS', '24')))
```

**e) WebAuthn / passkeys**

```python
WEBAUTHN_RP_ID = os.getenv('WEBAUTHN_RP_ID', 'localhost')
WEBAUTHN_ORIGIN = os.getenv('WEBAUTHN_ORIGIN', ...)
```

El `RP_ID` **debe coincidir con el dominio del frontend**. Por eso:

- En Vercel: `plomaap-react.vercel.app`.
- En AWS: `plomaap.duckdns.org`.

**f) Seguridad de producción**

```python
SECURE_SSL_REDIRECT = _env_bool('SECURE_SSL_REDIRECT', False)
SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '0'))
...
if _env_bool('USE_X_FORWARDED_PROTO', False):
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
```

- En AWS, nginx termina TLS y manda `X-Forwarded-Proto: https`; Django lo cree gracias a `USE_X_FORWARDED_PROTO=True`.
- En Vercel, la plataforma también termina TLS; por eso `USE_X_FORWARDED_PROTO=True` y `SECURE_SSL_REDIRECT=False` (si se pone `True`, Vercel podría entrar en un bucle de redirección).

**g) Protección contra secretos débiles**

```python
if not DEBUG:
    if SECRET_KEY in _weak_secrets or JWT_SECRET_KEY in _weak_secrets:
        raise ImproperlyConfigured(...)
```

Si intentas arrancar en producción con los valores de ejemplo, Django **no arranca**. Es una buena práctica.

### 8.3 `config/urls.py`

```python
urlpatterns = [
    re_path(r'^static/uploads/(?P<path>.*)$', serve_uploaded_file),
    path('api/', include('api.urls')),
]
```

- `/api/...` → todas las rutas de la API.
- `/static/uploads/...` → sirve las fotos de evidencia subidas.
- Los handlers `handler400/401/403/404/500` devuelven **JSON**, no HTML.

### 8.4 `api/urls.py`

Es el contrato de la API. Agrupa por “blueprint” (equivalente Flask):

| Prefijo | Archivo de vistas | Ejemplos |
|---|---|---|
| `/api/health` | `health_views.py` | `GET /api/health` |
| `/api/auth/*` | `auth_views.py` | `POST /api/auth/login`, `/register`, `/google-login`, `/profile`, passkeys |
| `/api/services*` | `service_views.py` | `GET /api/services`, `/categories`, `/<id>` |
| `/api/technicians/*` | `technician_views.py` | `GET /api/technicians`, `/available`, `/slots`, `/appointments` |
| `/api/appointments/*` | `appointment_views.py` | `GET/POST /api/appointments`, `PATCH /<id>` |
| `/api/admin/*` | `admin_views.py` | `/dashboard`, `/users`, `/appointments/<id>` |
| `/api/user/addresses*` | `address_views.py` | CRUD de direcciones |
| `/api/user/favorites*` | `favorite_views.py` | favoritos |
| `/api/events` | `event_views.py` | analítica de eventos |
| `/api/homes/*` | `home_views.py` | casas, cuartos, activos |
| `/api/onboarding/*` | `onboarding_views.py` | onboarding |
| `/api/embeddings/*` | `embedding_views.py` | embeddings con Voyage |
| `/api/search/hybrid` | `search_views.py` | búsqueda híbrida (texto + vector) |
| `/api/intelligence/understand` | `intelligence_views.py` | NLU |
| `/api/recommendations*` | `recommendation_views.py` | recomendaciones |
| `/api/upload/*` | `upload_views.py` | evidencia |

El helper `methods(...)` de `api/utils/dispatch.py` hace que un método no permitido devuelva **405 JSON** en vez de la página HTML de Django. Eso mantiene compatibilidad exacta con el backend Flask original.

### 8.5 `config/wsgi.py`

```python
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()
```

- **Gunicorn** lo usa así: `gunicorn config.wsgi:application`.
- **Vercel** lo usa a través de `index.py`, que hace `app = get_wsgi_application()`.

### 8.6 Autenticación (flujo JWT)

1. El frontend hace `POST /api/auth/login` con `{email, password, role}`.
2. `api/views/auth_views.py::login_route` → `api/controllers/auth_controller.py`.
3. Se verifica la contraseña con **bcrypt** (`bcrypt==5.0.0`).
4. Se genera un JWT HS256 con `sub = str(user.id)` (`api/utils/jwt_utils.py`).
5. El frontend guarda el token en `localStorage` (`authToken`).
6. Cada petición protegida manda `Authorization: Bearer <token>`.
7. `@jwt_required_custom` (`api/utils/decorators.py`) valida el token y carga el usuario.

El frontend valida el token antes de usarlo (`src/services/api.js` → `isValidAuthToken`), y si expiró limpia la sesión.

### 8.7 Subida de evidencia

`api/views/upload_views.py::upload_evidence`:

- Acepta `png/jpg/jpeg/webp/gif`.
- Verifica la **firma binaria** del archivo (no solo la extensión) para evitar subir un `.exe` renombrado.
- Límite de 10 MB.
- Guarda en `settings.UPLOADS_STATIC_DIR` (`static/uploads/evidence/`) con nombre UUID.
- Devuelve la URL pública.

> **Limitación en Vercel:** el sistema de archivos de una función serverless es de solo lectura (salvo `/tmp`, que no persiste). Por eso la subida de evidencia funciona en **AWS** (disco real) pero no en Vercel. El frontend actual usa **Cloudinary** para avatares e imágenes de registro, así que esta limitación no afecta el flujo principal. Si se necesita evidencia en Vercel, habría que subirla a Cloudinary/S3/Vercel Blob.

### 8.8 Frontend: archivos clave

| Archivo | Función |
|---|---|
| `src/config/env.js` | Lee `VITE_API_URL` y las demás variables; `cleanUrl()` quita `/` finales |
| `src/services/api.js` | `apiFetch()`: agrega `Authorization`, maneja timeout de 20 s, normaliza respuestas |
| `src/context/AuthContext.jsx` | Estado global de sesión |
| `src/components/ProtectedRoute.jsx` | Protege rutas por rol |
| `src/pages/auth/*` | Login de cliente, técnico y admin |
| `src/pages/admin/*` | Panel de administración |
| `src/pages/technician/*` | Panel del técnico |
| `src/pages/client/*` | Panel del cliente |
| `src/utils/cloudinary.js` | Subida directa a Cloudinary (avatares) |
| `vercel.json` | Build de Vite + rewrites SPA + cache |
| `.env` | Variables locales (no versionado) |

`apiFetch` construye la URL así:

```js
fetch(`${env.apiUrl}${path}`, { ... })
```

Por eso `VITE_API_URL=https://plomaap-api.vercel.app` y `path=/api/health` producen `https://plomaap-api.vercel.app/api/health`.

---

## 9. Flujo completo de una petición

Ejemplo: **login del administrador** desde el navegador.

```
1. Usuario abre https://plomaap-react.vercel.app/admin
2. Vercel CDN devuelve index.html + assets (React).
3. React Router muestra el formulario de admin.
4. Usuario envía email/contraseña.
5. authApi.login() → apiFetch('/api/auth/login')
6. fetch('https://plomaap-api.vercel.app/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, role: 'admin' })
   })
7. Vercel invoca la función Python (index.py → Django).
8. Django:
   - CorsMiddleware agrega cabeceras CORS.
   - login_route valida datos.
   - auth_controller busca el usuario y compara bcrypt.
   - generate_token() firma un JWT HS256.
   - Consulta a Neon por psycopg2 (SSL).
9. Respuesta JSON: { token, user }.
10. El frontend guarda token en localStorage y navega a /admin/panel.
11. Cada petición posterior manda Authorization: Bearer <token>.
12. En AWS el mismo flujo pasa por nginx :443 → upstream → Gunicorn :8000 o :8001.
```

---

## 10. Verificación y pruebas

### 10.1 Health checks

```bash
curl https://plomaap-api.vercel.app/api/health
# {"status":"healthy","timestamp":"...","database":"connected"}

curl https://plomaap.duckdns.org/api/health
# {"status":"healthy","timestamp":"...","database":"connected"}

curl https://18-221-80-56.nip.io/api/health
# {"status":"healthy","timestamp":"...","database":"connected"}
```

### 10.2 Datos

```bash
curl https://plomaap-api.vercel.app/api/services | head -c 200
```

Debe devolver los 4 servicios (`Fugas de agua`, `Destapes`, `Instalaciones`, `Mantenimiento`).

### 10.3 Login

```bash
curl -X POST https://plomaap-api.vercel.app/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@plomaap.com","password":"********"}'
```

### 10.4 CORS

```bash
curl -i -X OPTIONS https://plomaap-api.vercel.app/api/auth/login \
  -H "Origin: https://plomaap-react.vercel.app" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: content-type"
```

Debe incluir `Access-Control-Allow-Origin: https://plomaap-react.vercel.app`.

### 10.5 Balanceador AWS

```bash
for i in 1 2 3 4 5 6; do curl -s https://plomaap.duckdns.org/api/health; echo; done
```

Y revisar los logs para ver que alterna entre `plomaap` (8000) y `plomaap2` (8001):

```bash
sudo journalctl -u plomaap  -n 20 --no-pager | grep health
sudo journalctl -u plomaap2 -n 20 --no-pager | grep health
```

### 10.6 SSL

```bash
openssl x509 -in /etc/letsencrypt/live/18-221-80-56.nip.io/fullchain.pem \
  -noout -subject -enddate -ext subjectAltName
```

### 10.7 Pruebas del proyecto

```bash
cd /opt/plomaap/backend
./venv/bin/python -m pytest
```

El proyecto tiene pruebas unitarias e integración en `api/tests/`.

---

## 11. Seguridad

| Medida | Dónde |
|---|---|
| `DEBUG=False` | `.env` de AWS y Vercel |
| `SECRET_KEY` y `JWT_SECRET_KEY` fuertes | `.env` / Vercel env (cifradas) |
| Validación de secretos débiles al arrancar | `config/settings.py` |
| Contraseñas con **bcrypt** | `auth_controller.py` |
| JWT HS256 con expiración 24 h | `jwt_utils.py` |
| Rate limiting en login y Google login | `api/utils/rate_limit.py` |
| CORS | `settings.py` |
| HTTPS obligatorio en AWS | nginx 80 → 301 a 443 |
| Certificado Let's Encrypt | certbot |
| SSH restringido a una IP | Security Group |
| Validación de firma de imágenes | `upload_views.py` |
| Límite de subida 10 MB | `settings.py` y `upload_views.py` |
| Logging de seguridad | `api/middleware.py` |
| `.env` fuera de git | `.gitignore` |

### Buenas prácticas pendientes (para un entorno real)

1. **Cambiar las contraseñas `123456`** de los técnicos.
2. **Cerrar el puerto 5000** en el Security Group.
3. **Restringir CORS** a los dominios exactos (`CORS_ALLOW_ALL_ORIGINS=False`).
4. **Rotar** las claves de Neon, AWS y Google si alguna se filtró.
5. **No usar `CORS_ALLOW_ALL_ORIGINS=True`** en producción real.
6. **Configurar HSTS** (`SECURE_HSTS_SECONDS=31536000`) cuando el dominio sea definitivo.
7. **Mover evidencia** a Cloudinary/S3 si se usa el backend de Vercel.
8. **Agregar monitoreo** (Sentry, UptimeRobot) y alertas.
9. **Backups automáticos** de Neon (el plan free tiene retención limitada).
10. **Google OAuth**: los orígenes `https://plomaap-react.vercel.app` y `https://plomaap.duckdns.org` ya quedaron autorizados en el cliente web de Google Cloud (`plomaap-498517`).

---

## 12. Costos

| Recurso | Costo | Nota |
|---|---|---|
| Vercel Hobby (frontend) | $0 | 100 GB de ancho de banda/mes aprox. |
| Vercel Hobby (backend) | $0 | 100 GB-horas de funciones/mes; cold starts |
| Neon Free | $0 | 0.5 GB de almacenamiento, 1 proyecto |
| DuckDNS | $0 | subdominio gratuito |
| Let's Encrypt | $0 | renovación automática |
| EC2 `t3.micro` | Free tier 12 meses | Después ~$8–10/mes |
| EBS 20 GB `gp3` | Free tier 30 GB | Después ~$1.60/mes |
| **IPv4 pública** | **~$3.65/mes** | AWS cobra desde 2024 aunque la instancia esté apagada |
| Transferencia de salida | 100 GB gratis/mes | Luego ~$0.09/GB |

> **Advertencia:** la IP elástica ya **no es gratis** si está asociada a una instancia encendida (se cobra la IPv4 pública). Para un proyecto escolar, el free tier de 12 meses cubre la EC2, pero revisa **Billing → Cost Explorer** cada mes. Si quieres costo cero absoluto, apaga la EC2 y usa solo Vercel + Neon.

---

## 13. Decisiones técnicas y limitaciones

### 13.1 ¿Por qué nginx y no un ALB de AWS?

Un **Application Load Balancer** cuesta ~$16–20/mes + cargos por LCU. No entra en el free tier. nginx:

- Es gratis.
- Corre en la misma instancia.
- Hace round-robin, health checks pasivos (`max_fails`), TLS y compresión.
- Para un proyecto escolar es la opción correcta.

**Limitación:** si la instancia entera se cae, el balanceador también. Alta disponibilidad real requiere 2 instancias en 2 zonas + ALB (ya no gratis).

### 13.2 ¿Vercel sirve como balanceador?

**No para un backend con procesos persistentes.** Vercel:

- Es una plataforma serverless/CDN.
- No mantiene Gunicorn ni workers.
- Puede ejecutar Django como función (lo hicimos), pero **cada invocación es efímera**.
- Sus “rewrites” son un proxy CDN, no balanceo entre instancias.

Vercel sí es excelente para el **frontend** (lo que hicimos) y para APIs serverless ligeras.

### 13.3 Limitaciones de Django en Vercel

| Limitación | Impacto | Mitigación |
|---|---|---|
| Sistema de archivos de solo lectura | Subida de evidencia falla | Cloudinary / S3 / Vercel Blob |
| Cold starts (~1–3 s) | Primera petición lenta | Aceptable para demo; plan Pro reduce |
| Límite de 4.5 MB por request | Subidas grandes fallan | Subida directa a Cloudinary |
| Timeout de función (10 s Hobby / 60 s Pro) | Procesos largos fallan | Mover a worker/cola |
| Conexiones a DB | Se agotan sin pooler | Usar host `-pooler` de Neon |
| `pyproject.toml` sin dependencias | Vercel no instala nada | Eliminarlo o declarar `[project]` |

### 13.4 ¿Por qué dos backends?

- **Cumplir “todo en Vercel”**: el frontend y la API principal están en Vercel.
- **Cumplir “balanceador + SSL”**: AWS tiene nginx + Let's Encrypt.
- **Respaldo**: si Vercel falla o se agotan las cuotas, cambias `VITE_API_URL` a `https://plomaap.duckdns.org` y redeployas.

### 13.5 ¿Por qué Neon y no RDS?

- RDS free tier dura 12 meses y luego cuesta.
- Neon free es **permanente** (con límites), tiene pgvector y está en la misma región.
- Neon permite branching y conexión por pooler, ideal para serverless.

---

## 14. Solución de problemas

### El frontend carga pero las peticiones fallan

1. Revisa `VITE_API_URL` en Vercel (`vercel env ls production`).
2. Recuerda que Vite la **hornea en el build**: cambia la variable y **redeploy**.
3. Abre DevTools → Network y mira la URL real.
4. Verifica CORS con el `curl OPTIONS` de la sección 10.4.

### `500` en `https://plomaap-api.vercel.app/api/health`

1. Revisa los logs de la función en Vercel → Deployments → Functions → Logs.
2. Causa típica: dependencias no instaladas (`pyproject.toml` sin `[project]`).
3. Causa típica: `DATABASE_URL` mal o sin `sslmode=require`.
4. Causa típica: `ALLOWED_HOSTS` no incluye el dominio.

### `DisallowedHost` en Django

Agrega el dominio a `ALLOWED_HOSTS` en `.env` (AWS) o en Vercel env, y reinicia/redeploy.

### `too many connections` en Neon

Usa el host con `-pooler` en `DATABASE_URL` (Vercel) y no aumentes `CONN_MAX_AGE` en serverless.

### nginx devuelve 502

```bash
sudo systemctl status plomaap plomaap2
sudo journalctl -u plomaap -n 50 --no-pager
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8001/api/health
```

Si un backend no responde, revisa el `.env`, la conexión a Neon y la RAM (`free -h`).

### El certificado no renueva

```bash
sudo systemctl status certbot.timer
sudo certbot renew --dry-run
```

Asegúrate de que el puerto 80 esté abierto y que `/.well-known/acme-challenge/` apunte a `/var/www/html`.

### `vercel env add` falla con valor vacío

No se pueden crear variables vacías. Si no necesitas `CORS_ORIGINS` porque `CORS_ALLOW_ALL_ORIGINS=True`, omítela o pon un valor real.

### `ModuleNotFoundError: No module named 'config'` en Vercel

Asegúrate de que `index.py` esté en la **raíz** del proyecto y agregue esa raíz a `sys.path` (es lo que hace el archivo).

---

## 15. Guía de estudio recomendada

Si quieres entender el proyecto de punta a punta, sigue este orden:

1. **`README.md`** del backend: qué es y cómo correrlo en local.
2. **`config/settings.py`**: cómo se configura Django y cómo elige la base de datos.
3. **`config/urls.py` + `api/urls.py`**: el contrato de la API.
4. **`api/views/auth_views.py` + `api/controllers/auth_controller.py` + `api/utils/jwt_utils.py`**: autenticación.
5. **`api/models.py`**: las tablas y relaciones.
6. **`api/views/appointment_views.py` + `api/services/appointment_service.py`**: lógica de citas.
7. **`api/services/hybrid_search_service.py` + `embedding_service.py`**: búsqueda semántica con pgvector.
8. **`api/middleware.py` + `api/errors.py`**: manejo de errores JSON.
9. **`api/tests/`**: cómo se prueba.
10. **Frontend `src/services/api.js` + `src/config/env.js`**: cómo consume la API.
11. **Este documento, secciones 5–7**: cómo se despliega.
12. **`docs/despliegue/aws/` y `docs/despliegue/vercel/`**: copias de las configuraciones para comparar.

Preguntas guía:

- ¿Qué diferencia hay entre `WSGI_APPLICATION` y `app = get_wsgi_application()`?
- ¿Por qué el JWT usa `sub` como string?
- ¿Cómo sabe Django si debe usar SQLite, MySQL o PostgreSQL?
- ¿Qué hace `methods(GET=..., POST=...)` que no hace `path()` solo?
- ¿Por qué el balanceador necesita `X-Forwarded-Proto`?
- ¿Por qué Vercel necesita el pooler de Neon?
- ¿Qué pasa con los archivos subidos en una función serverless?

---

## 16. Anexos: configuraciones completas

### 16.1 nginx AWS

```nginx
upstream plomaap_backend {
    server 127.0.0.1:8000 max_fails=3 fail_timeout=10s;
    server 127.0.0.1:8001 max_fails=3 fail_timeout=10s;
}

server {
    listen 80;
    listen [::]:80;
    server_name plomaap.duckdns.org 18-221-80-56.nip.io;

    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}

server {
    listen 5000;
    server_name _;

    client_max_body_size 12M;

    location /static/uploads/ {
        proxy_pass http://plomaap_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /opt/plomaap/backend/staticfiles/;
        expires 7d;
        access_log off;
    }

    location / {
        proxy_pass http://plomaap_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }
}

server {
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name plomaap.duckdns.org 18-221-80-56.nip.io;

    ssl_certificate     /etc/letsencrypt/live/18-221-80-56.nip.io/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/18-221-80-56.nip.io/privkey.pem;

    client_max_body_size 12M;

    location /static/uploads/ {
        proxy_pass http://plomaap_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /opt/plomaap/backend/staticfiles/;
        expires 7d;
        access_log off;
    }

    location / {
        proxy_pass http://plomaap_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }
}
```

### 16.2 `plomaap.service` y `plomaap2.service`

Ver sección [5.5](#55-gunicorn-con-systemd). El único cambio entre ambos es el puerto (`8000` vs `8001`) y la descripción.

### 16.3 `vercel.json` del frontend

Ver sección [7.1](#71-frontend-react-proyecto-plomaap-react).

### 16.4 Backend Vercel (`index.py`, `vercel.json`, `.vercelignore`)

Ver sección [7.2](#72-backend-django-serverless-proyecto-plomaap-api).

### 16.5 Plantilla de `.env` de producción

```dotenv
# Django
SECRET_KEY=cambia-esto-por-una-clave-larga-y-aleatoria
DEBUG=False
ALLOWED_HOSTS=plomaap-api.vercel.app,.vercel.app,plomaap.duckdns.org,18-221-80-56.nip.io,18.221.80.56,localhost,127.0.0.1

# Base de datos (Neon)
DATABASE_URL=postgresql://USUARIO:PASSWORD@HOST/neondb?sslmode=require
PGSSLMODE=require

# JWT
JWT_SECRET_KEY=cambia-esto-por-otra-clave-larga-y-aleatoria
JWT_EXPIRATION_HOURS=24

# CORS
CORS_ALLOW_ALL_ORIGINS=True
CORS_ORIGINS=https://plomaap-react.vercel.app

# Google
GOOGLE_CLIENT_ID=tu-client-id.apps.googleusercontent.com

# Correo (Zoho)
MAIL_SERVER=smtp.zoho.com
MAIL_PORT=465
MAIL_USE_TLS=False
MAIL_USE_SSL=True
MAIL_USERNAME=tu-correo@zohomail.com
MAIL_PASSWORD=tu-password

# App
APP_NAME=PlomApp
APP_VERSION=1.0.0

# IA
GEMINI_API_KEY=
VOYAGE_API_KEY=
EMBEDDING_PROVIDER=voyage
EMBEDDING_MODEL=voyage-3-lite

# Passkeys
WEBAUTHN_RP_ID=plomaap-react.vercel.app
WEBAUTHN_RP_NAME=PlomApp
WEBAUTHN_ORIGIN=https://plomaap-react.vercel.app

# Seguridad detrás de proxy TLS
USE_X_FORWARDED_PROTO=True
SECURE_SSL_REDIRECT=False
CSRF_TRUSTED_ORIGINS=https://plomaap-react.vercel.app,https://plomaap.duckdns.org
```

---

## Cierre

Este despliegue demuestra tres formas de ejecutar el mismo backend y una base de datos compartida:

1. **Local**: `python manage.py runserver` + Postgres en Docker.
2. **AWS**: Gunicorn + nginx (balanceador) + Let's Encrypt + IP elástica.
3. **Vercel**: función serverless Python + CDN + Neon pooler.

Lo más valioso para estudiar no es “dónde se hizo clic”, sino **por qué** cada pieza existe:

- El **balanceador** reparte carga y tolera la caída de un proceso.
- El **SSL** protege credenciales y tokens en tránsito.
- El **dominio** desacopla la IP del servicio y habilita certificados.
- La **base externa** permite que dos backends distintos vean los mismos datos.
- El **pooler** es lo que hace viable Postgres en un entorno serverless.

Con eso entiendes el 90 % de lo que se hace en un despliegue real.
