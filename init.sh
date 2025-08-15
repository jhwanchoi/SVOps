#!/bin/bash

# SVOps Infrastructure Initialization Script
echo "🔧 Initializing SVOps infrastructure..."

# Clean up existing containers and volumes
echo "🧹 Cleaning up existing containers..."
docker-compose down -v --remove-orphans

# Remove old data directories
echo "🗑️ Removing old data..."
rm -rf ./data/postgres/* 2>/dev/null || true
rm -rf ./airflow/logs/* 2>/dev/null || true

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p ./data/postgres
mkdir -p ./airflow/logs
mkdir -p ./airflow/dags
mkdir -p ./airflow/plugins

# Set proper permissions
echo "🔐 Setting permissions..."
chmod 755 ./scripts/init-db.sh 2>/dev/null || true
chown -R $USER:$USER ./data 2>/dev/null || true
chown -R $USER:$USER ./airflow 2>/dev/null || true

# Pull latest images
echo "📦 Pulling latest Docker images..."
docker-compose pull

# Start database first
echo "🗄️ Starting database..."
docker-compose up -d postgres

# Wait for database to be ready
echo "⏳ Waiting for database to initialize..."
sleep 10

# Start Redis
echo "🔴 Starting Redis..."
docker-compose up -d redis

# Wait for Redis
sleep 5

# Create application database tables
echo "🗃️ Creating application database tables..."
docker-compose run --rm backend python create_tables.py

# Initialize Airflow database separately
echo "🌸 Initializing Airflow database..."
docker-compose run --rm airflow-webserver airflow db init

# Create Airflow admin user
echo "👤 Creating Airflow admin user..."
docker-compose run --rm airflow-webserver airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@svops.com \
    --password admin

echo "✅ Infrastructure initialized successfully!"
