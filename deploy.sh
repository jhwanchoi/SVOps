#!/bin/bash

# SVOps Production Deployment Script
echo "🚀 Starting SVOps production deployment..."

# Configuration
ENVIRONMENT=${1:-production}
BUILD_FRONTEND=${BUILD_FRONTEND:-true}
PULL_LATEST=${PULL_LATEST:-true}

echo "📋 Deployment Configuration:"
echo "   Environment: $ENVIRONMENT"
echo "   Build Frontend: $BUILD_FRONTEND"
echo "   Pull Latest: $PULL_LATEST"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Check for required environment file
if [ ! -f ".env.${ENVIRONMENT}" ]; then
    echo "❌ Environment file .env.${ENVIRONMENT} not found"
    echo "   Please create it with production settings"
    exit 1
fi

# Backup current environment
if [ -f ".env" ]; then
    echo "💾 Backing up current .env file..."
    cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
fi

# Copy environment configuration
echo "⚙️ Setting up environment configuration..."
cp .env.${ENVIRONMENT} .env

# Pull latest images if requested
if [ "$PULL_LATEST" = "true" ]; then
    echo "📥 Pulling latest Docker images..."
    docker-compose pull
fi

# Build services
echo "🔨 Building services..."
if [ "$BUILD_FRONTEND" = "true" ]; then
    docker-compose build
else
    docker-compose build backend
fi

# Stop existing services gracefully
echo "🛑 Stopping existing services..."
docker-compose down --remove-orphans

# Start database and Redis first
echo "🗄️ Starting core services..."
docker-compose up -d postgres redis

# Wait for database to be ready
echo "⏳ Waiting for database to be ready..."
sleep 15

# Check database connection
echo "🔍 Checking database connection..."
if ! docker-compose exec -T postgres pg_isready -U svops -d svops; then
    echo "❌ Database is not ready"
    exit 1
fi

# Run database migrations/initialization if needed
echo "📊 Ensuring database schema is up to date..."
docker-compose run --rm backend python -c "
import asyncio
from app.core.database import engine
from app.infrastructure.database.models import Base

async def ensure_tables():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print('✅ Database schema updated')
    except Exception as e:
        print(f'❌ Error updating schema: {e}')
    finally:
        await engine.dispose()

asyncio.run(ensure_tables())
"

# Start application services
echo "🚀 Starting application services..."
docker-compose up -d backend frontend airflow-webserver airflow-scheduler

# Health checks
echo "🔍 Performing health checks..."
sleep 10

# Check backend health
if ! curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "❌ Backend health check failed"
    echo "📊 Backend logs:"
    docker-compose logs --tail=20 backend
    exit 1
fi

# Check frontend (if built)
if [ "$BUILD_FRONTEND" = "true" ]; then
    if ! curl -f http://localhost:3000 > /dev/null 2>&1; then
        echo "⚠️ Frontend health check failed - checking logs..."
        docker-compose logs --tail=10 frontend
    fi
fi

echo ""
echo "🎉 SVOps production deployment completed successfully!"
echo ""
echo "📋 Service Status:"
docker-compose ps
echo ""
echo "📊 To monitor: ./logs.sh [service_name]"
echo "📊 To stop:    docker-compose down"

# Cleanup
if [ -f ".env.backup"* ]; then
    echo "📁 Environment backup created"
fi