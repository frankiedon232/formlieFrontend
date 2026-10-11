#!/usr/bin/env bash
# A MariaDB server in Ubuntu (WSL) for testing data sources (B9): Formalie writes responses into a customer's own
# database, and the tests connect to this one as a "customer" would. Development only.
# Run inside Ubuntu:  bash /mnt/c/UNETPROJECTS/formlyBackend/scripts/wsl/setup-mariadb.sh
# Safe to run again. Prints one line for .env at the end.
set -euo pipefail

DB_USER="${DB_USER:-formalie_customer}"
DB_PASS="${DB_PASS:-$(openssl rand -hex 16)}"

echo "== packages"
sudo apt-get update -y
sudo apt-get install -y mariadb-server openssl

echo "== mariadb (127.0.0.1:3306 only)"
sudo tee /etc/mysql/mariadb.conf.d/60-formalie.cnf >/dev/null <<CNF
[mysqld]
bind-address = 127.0.0.1
character-set-server = utf8mb4
collation-server = utf8mb4_unicode_ci
CNF
sudo systemctl enable --now mariadb
sudo systemctl restart mariadb

echo "== test databases and a user that owns them (like a customer's application user)"
sudo mariadb <<SQL
CREATE DATABASE IF NOT EXISTS customer_dev CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE IF NOT EXISTS customer_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS '${DB_USER}'@'127.0.0.1' IDENTIFIED BY '${DB_PASS}';
CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASS}';
ALTER USER '${DB_USER}'@'127.0.0.1' IDENTIFIED BY '${DB_PASS}';
ALTER USER '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASS}';
GRANT ALL PRIVILEGES ON customer_dev.* TO '${DB_USER}'@'127.0.0.1', '${DB_USER}'@'localhost';
GRANT ALL PRIVILEGES ON customer_test.* TO '${DB_USER}'@'127.0.0.1', '${DB_USER}'@'localhost';
FLUSH PRIVILEGES;
SQL

echo
echo "   TEST_MYSQL_URL=mysql://${DB_USER}:${DB_PASS}@127.0.0.1:3306/customer_test   <- copy this line into .env"
