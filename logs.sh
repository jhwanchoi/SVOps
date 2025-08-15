#!/bin/bash

# SVOps Logs Viewer Script
SERVICE_NAME=${1:-""}

if [ -z "$SERVICE_NAME" ]; then
    echo "🔍 Available services:"
    docker-compose ps --format "table {{.Service}}\t{{.Status}}\t{{.Ports}}"
    echo ""
    echo "📊 Usage: ./logs.sh [service_name]"
    echo "   Examples:"
    echo "     ./logs.sh backend"
    echo "     ./logs.sh airflow-webserver"
    echo "     ./logs.sh frontend"
    echo ""
    echo "📊 Show all logs: ./logs.sh all"
    exit 0
fi

if [ "$SERVICE_NAME" = "all" ]; then
    echo "📊 Showing logs for all services..."
    docker-compose logs -f
else
    echo "📊 Showing logs for: $SERVICE_NAME"
    docker-compose logs -f "$SERVICE_NAME"
fi
