#!/bin/bash
set -e

echo "Creating airflow database and user..."

# Create airflow database and user with SUPERUSER privileges
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE airflow;
    CREATE USER airflow WITH ENCRYPTED PASSWORD 'airflow';
    ALTER USER airflow CREATEDB SUPERUSER;
    GRANT ALL PRIVILEGES ON DATABASE airflow TO airflow;
EOSQL

echo "Setting up airflow database permissions as postgres user..."

# Connect as postgres superuser to set up schema permissions
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "airflow" <<-EOSQL
    -- Grant ownership of public schema to airflow
    ALTER SCHEMA public OWNER TO airflow;
    
    -- Grant all privileges on public schema
    GRANT ALL ON SCHEMA public TO airflow;
    GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO airflow;
    GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO airflow;
    GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO airflow;
    
    -- Set default privileges for future objects created by airflow
    ALTER DEFAULT PRIVILEGES FOR USER airflow IN SCHEMA public GRANT ALL ON TABLES TO airflow;
    ALTER DEFAULT PRIVILEGES FOR USER airflow IN SCHEMA public GRANT ALL ON SEQUENCES TO airflow;
    ALTER DEFAULT PRIVILEGES FOR USER airflow IN SCHEMA public GRANT ALL ON FUNCTIONS TO airflow;
    
    -- Also set default privileges for postgres user creating objects
    ALTER DEFAULT PRIVILEGES FOR USER $POSTGRES_USER IN SCHEMA public GRANT ALL ON TABLES TO airflow;
    ALTER DEFAULT PRIVILEGES FOR USER $POSTGRES_USER IN SCHEMA public GRANT ALL ON SEQUENCES TO airflow;
    ALTER DEFAULT PRIVILEGES FOR USER $POSTGRES_USER IN SCHEMA public GRANT ALL ON FUNCTIONS TO airflow;
EOSQL

echo "Airflow database setup completed!"