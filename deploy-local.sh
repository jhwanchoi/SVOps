#!/bin/bash

# SVOps Local Development Deployment Script
echo "🚀 Starting SVOps local development environment..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Function to check if services are healthy
check_service_health() {
    local service_name=$1
    local max_attempts=30
    local attempt=1
    
    echo "⏳ Waiting for $service_name to be healthy..."
    
    while [ $attempt -le $max_attempts ]; do
        if docker-compose ps | grep -q "$service_name.*healthy\|$service_name.*Up"; then
            echo "✅ $service_name is ready!"
            return 0
        fi
        
        echo "   Attempt $attempt/$max_attempts - $service_name not ready yet..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo "❌ $service_name failed to start within expected time"
    return 1
}

# Start all services
echo "📦 Starting all services..."
docker-compose up -d

# Check service health
echo "🔍 Checking service health..."

# Check database
if ! check_service_health "postgres"; then
    echo "❌ Database failed to start"
    exit 1
fi

# Check Redis
if ! check_service_health "redis"; then
    echo "❌ Redis failed to start"
    exit 1
fi

# Check backend
if ! check_service_health "backend"; then
    echo "❌ Backend failed to start"
    exit 1
fi

# Check frontend
if ! check_service_health "frontend"; then
    echo "❌ Frontend failed to start"
    exit 1
fi

echo ""
echo "🎉 SVOps is now running locally!"
echo ""
echo "📋 Service URLs:"
echo "   🌐 Frontend:    http://localhost:3000"
echo "   🔧 Backend API: http://localhost:8000"
echo "   📚 API Docs:    http://localhost:8000/docs"
echo "   🌸 Airflow:     http://localhost:8080"
echo ""
echo "🔑 Default credentials:"
echo "   Username: admin"
echo "   Password: admin123"
echo ""
echo "📊 To view logs: ./logs.sh [service_name]"
echo "📊 To stop:      docker-compose down"