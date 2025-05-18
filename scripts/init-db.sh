#!/bin/bash
# Этот файл больше не используется, так как каждый сервис теперь имеет свою БД

# Старый код, сохраненный для справки:
# ====================================
# set -e
# 
# psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
#     SELECT 'CREATE DATABASE auth_db' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'auth_db')\gexec
#     SELECT 'CREATE DATABASE marketplace_db' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'marketplace_db')\gexec
#     -- Добавьте сюда создание других БД для payment_svc и chat_svc, когда будете готовы
#     -- SELECT 'CREATE DATABASE payment_db' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'payment_db')\gexec
#     -- SELECT 'CREATE DATABASE chat_db' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'chat_db')\gexec
# EOSQL 