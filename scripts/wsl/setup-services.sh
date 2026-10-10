#!/usr/bin/env bash
# Formalie development services inside WSL (Ubuntu 24.04): Redis 7, RabbitMQ 3, PgBouncer, MinIO, Mailpit.
# Run inside Ubuntu:  bash /mnt/c/UNETPROJECTS/formlyBackend/scripts/wsl/setup-services.sh
# Safe to run again. Needs systemd (default on new WSL installs; check /etc/wsl.conf has [boot] systemd=true).
set -euo pipefail

RABBIT_USER="${RABBIT_USER:-formalie}"
RABBIT_VHOST="${RABBIT_VHOST:-formalie}"
RABBIT_PASS="${RABBIT_PASS:-$(openssl rand -hex 16)}"
MINIO_USER="${MINIO_USER:-formalie}"
MINIO_PASS="${MINIO_PASS:-$(openssl rand -hex 16)}"
PG_HOST="${PG_HOST:-127.0.0.1}"   # Windows PostgreSQL 18 (mirrored networking)
PG_PORT="${PG_PORT:-5432}"

echo "== packages"
sudo apt-get update -y
sudo apt-get install -y redis-server rabbitmq-server pgbouncer curl openssl

echo "== redis (127.0.0.1:6379)"
sudo sed -i 's/^supervised .*/supervised systemd/' /etc/redis/redis.conf
sudo sed -i 's/^bind .*/bind 127.0.0.1 ::1/' /etc/redis/redis.conf
sudo systemctl enable --now redis-server
sudo systemctl restart redis-server

echo "== rabbitmq (5672, management on 15672)"
sudo systemctl enable --now rabbitmq-server
sudo rabbitmq-plugins enable rabbitmq_management >/dev/null
sudo rabbitmqctl add_vhost "$RABBIT_VHOST" 2>/dev/null || true
if sudo rabbitmqctl list_users | grep -q "^$RABBIT_USER\b"; then
  sudo rabbitmqctl change_password "$RABBIT_USER" "$RABBIT_PASS"
else
  sudo rabbitmqctl add_user "$RABBIT_USER" "$RABBIT_PASS"
fi
sudo rabbitmqctl set_user_tags "$RABBIT_USER" management
sudo rabbitmqctl set_permissions -p "$RABBIT_VHOST" "$RABBIT_USER" ".*" ".*" ".*"

echo "== pgbouncer (6432, transaction pooling to Windows PostgreSQL ${PG_HOST}:${PG_PORT})"
sudo tee /etc/pgbouncer/pgbouncer.ini >/dev/null <<EOF
[databases]
formalie = host=${PG_HOST} port=${PG_PORT} dbname=formalie
formalie_test = host=${PG_HOST} port=${PG_PORT} dbname=formalie_test

[pgbouncer]
listen_addr = 127.0.0.1
listen_port = 6432
auth_type = scram-sha-256
auth_file = /etc/pgbouncer/userlist.txt
pool_mode = transaction
max_client_conn = 500
default_pool_size = 20
ignore_startup_parameters = extra_float_digits,options,statement_timeout,application_name,timezone
server_tls_sslmode = prefer
EOF
if [ ! -s /etc/pgbouncer/userlist.txt ]; then
  echo "   Add the users to /etc/pgbouncer/userlist.txt as: \"formalie_app\" \"<password or SCRAM secret>\""
  sudo touch /etc/pgbouncer/userlist.txt
fi
sudo chown postgres:postgres /etc/pgbouncer/userlist.txt 2>/dev/null || true
sudo systemctl enable --now pgbouncer
sudo systemctl restart pgbouncer

echo "== minio (9000, console 9001)"
if ! command -v minio >/dev/null; then
  curl -fsSL https://dl.min.io/server/minio/release/linux-amd64/minio -o /tmp/minio
  sudo install -m 0755 /tmp/minio /usr/local/bin/minio
fi
sudo mkdir -p /srv/minio
sudo tee /etc/default/minio >/dev/null <<EOF
MINIO_ROOT_USER=${MINIO_USER}
MINIO_ROOT_PASSWORD=${MINIO_PASS}
MINIO_VOLUMES=/srv/minio
MINIO_OPTS="--address 127.0.0.1:9000 --console-address 127.0.0.1:9001"
EOF
sudo tee /etc/systemd/system/minio.service >/dev/null <<'EOF'
[Unit]
Description=MinIO
After=network-online.target
[Service]
EnvironmentFile=/etc/default/minio
ExecStart=/usr/local/bin/minio server $MINIO_OPTS $MINIO_VOLUMES
Restart=always
[Install]
WantedBy=multi-user.target
EOF

echo "== mailpit (SMTP 1025, UI 8025)"
if ! command -v mailpit >/dev/null; then
  curl -fsSL https://raw.githubusercontent.com/axllent/mailpit/develop/install.sh | sudo bash
fi
sudo tee /etc/systemd/system/mailpit.service >/dev/null <<'EOF'
[Unit]
Description=Mailpit
After=network-online.target
[Service]
ExecStart=/usr/local/bin/mailpit --smtp 127.0.0.1:1025 --listen 127.0.0.1:8025
Restart=always
[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now minio mailpit
sudo systemctl restart minio mailpit

cat <<EOF

Done. Put these in C:\\UNETPROJECTS\\formlyBackend\\.env:
  REDIS_URL=redis://127.0.0.1:6379/0
  CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/1
  RABBITMQ_URL=amqp://${RABBIT_USER}:${RABBIT_PASS}@127.0.0.1:5672/${RABBIT_VHOST}
  (MinIO: user ${MINIO_USER}, password ${MINIO_PASS}; console http://127.0.0.1:9001. Mailpit: http://127.0.0.1:8025)
EOF
