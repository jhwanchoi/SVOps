# SVOps - Event-Driven Workflow Platform

A comprehensive event-driven workflow orchestration platform built with FastAPI, Apache Airflow, Redis, and WebSocket for real-time monitoring and control.

## Architecture

### Core Components

- **FastAPI Backend**: REST API server with JWT authentication
- **Apache Airflow**: Workflow orchestration and DAG execution
- **Redis**: Real-time pub/sub messaging and caching
- **WebSocket**: Live status streaming to clients
- **Celery**: Background task processing
- **PostgreSQL**: Primary database for application data

### Event-Driven Flow

```
Frontend → FastAPI → Airflow REST API → DAG Execution
    ↑                     ↓
WebSocket ← Redis Pub/Sub ← Background Tasks
```

## Features

### Implemented Features

- **Airflow REST API Integration**: Complete workflow control via HTTP
- **Real-time Status Updates**: Redis pub/sub + WebSocket streaming
- **JWT Authentication**: Secure API endpoints with role-based access
- **Background Task Monitoring**: Celery tasks for DAG status tracking
- **Error Handling & Retry Logic**: Circuit breakers and exponential backoff
- **Dynamic Workflow Control**: Stop, retry, pause workflow runs
- **Notification System**: Slack/webhook alerts for workflow events
- **Comprehensive API**: RESTful endpoints for all operations

### Core Capabilities

1. **Workflow Triggering**: API-driven DAG execution with custom parameters
2. **Real-time Monitoring**: Live WebSocket updates for workflow status
3. **Dynamic Control**: Stop, retry, or modify running workflows
4. **Event Broadcasting**: Redis pub/sub for distributed event handling
5. **Notification Integration**: Slack and webhook notifications
6. **Background Processing**: Automated monitoring and status updates
7. **Error Recovery**: Robust retry mechanisms and circuit breakers
8. **Authentication**: JWT-based security with scoped permissions

## Project Structure

```
SVOps/
├── backend/                    # FastAPI application
│   ├── app/
│   │   ├── application/        # Use cases and services
│   │   │   ├── services/       # External service clients
│   │   │   ├── tasks/          # Celery background tasks
│   │   │   └── use_cases/      # Business logic
│   │   ├── core/               # Configuration and utilities
│   │   ├── domain/             # Domain entities and value objects
│   │   ├── infrastructure/     # Data access and repositories
│   │   ├── presentation/       # API routes and WebSocket endpoints
│   │   │   ├── api/            # REST API routes
│   │   │   ├── schemas/        # Pydantic schemas
│   │   │   └── websocket/      # WebSocket handlers
│   │   └── shared/             # Shared utilities and exceptions
│   ├── main.py                 # FastAPI application entry point
│   └── requirements.txt        # Python dependencies
├── airflow/                    # Airflow configuration and DAGs
│   ├── dags/                   # Workflow definitions
│   ├── config/                 # Airflow configuration
│   └── logs/                   # Airflow logs
├── frontend/                   # Next.js frontend (placeholder)
└── docker-compose.yml          # Multi-service setup
```

## Setup & Installation

### Prerequisites

- Docker & Docker Compose
- Python 3.9+
- Node.js 18+ (for frontend)

### Quick Start

1. **Clone the repository**
```bash
git clone <repository-url>
cd SVOps
```

2. **Initialize the project** (first time only)
```bash
./init.sh
```

3. **Start local development environment**
```bash
./deploy-local.sh
```

4. **Access the services**
- Frontend: http://localhost:3000
- FastAPI Backend: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Airflow Web UI: http://localhost:8080

5. **Default credentials**
- Username: admin
- Password: admin123

## 🛠️ Management Scripts

### `init.sh` - Project Initialization
First-time setup script that:
- Builds Docker containers
- Starts database and Redis
- Creates database tables
- Creates default admin user

```bash
./init.sh
```

### `deploy-local.sh` - Local Development
Starts all services for local development:
- Performs health checks
- Shows service status
- Provides access URLs

```bash
./deploy-local.sh
```

### `deploy.sh` - Production Deployment
Production deployment with environment configuration:
```bash
./deploy.sh production  # Use .env.production
./deploy.sh staging     # Use .env.staging
```

Features:
- Environment-specific configuration
- Database migration checks
- Health monitoring
- Backup creation

### `logs.sh` - Log Management
Comprehensive log viewing tool:
```bash
./logs.sh                    # All services
./logs.sh backend            # Backend only
./logs.sh backend true       # Follow backend logs
./logs.sh backend true 100   # Last 100 lines, follow
./logs.sh status             # Service status
```

Available services: backend, frontend, postgres, redis, airflow-webserver, airflow-scheduler

### Service URLs

- **API Documentation**: http://localhost:8000/docs
- **Airflow Dashboard**: http://localhost:8080
- **Redis**: localhost:6379
- **PostgreSQL**: localhost:5432

## API Reference

### Authentication

```bash
# Register new user
POST /api/v1/auth/register
{
  "username": "user",
  "email": "user@example.com", 
  "name": "User Name",
  "password": "password123"
}

# Login
POST /api/v1/auth/login
{
  "username": "user",
  "password": "password123"
}
```

### Workflow Management

```bash
# Create workflow
POST /api/v1/workflows
{
  "name": "My Workflow",
  "description": "Example workflow",
  "dag_id": "simple_workflow_example"
}

# Trigger workflow run
POST /api/v1/workflows/{workflow_id}/runs
{
  "task_id": 123,
  "dataset_id": 456,
  "parameters": {"processing_time": 30}
}

# Control workflow run
POST /api/v1/workflows/{workflow_id}/runs/{run_id}/control
{
  "action": "stop",  # or "retry"
  "note": "Manual stop"
}
```

### WebSocket Connections

```javascript
// Global events
ws://localhost:8000/api/v1/ws

// User-specific events  
ws://localhost:8000/api/v1/ws/user/{user_id}

// Workflow-specific events
ws://localhost:8000/api/v1/ws/workflow/{workflow_id}

// Combined user + workflow events
ws://localhost:8000/api/v1/ws/user/{user_id}/workflow/{workflow_id}
```

### Notification Configuration

```bash
# Add Slack notification
POST /api/v1/notifications/configs
{
  "name": "slack-alerts",
  "channel": "slack",
  "webhook_url": "https://hooks.slack.com/...",
  "notification_types": ["workflow_failed", "workflow_completed"]
}
```

## Example DAGs

### 1. Simple Workflow
- **DAG ID**: `simple_workflow_example`
- **Description**: Basic workflow with start, processing, and completion steps
- **Duration**: ~30-60 seconds

### 2. Data Processing Pipeline  
- **DAG ID**: `data_processing_pipeline`
- **Description**: ETL pipeline with extraction, transformation, and loading
- **Duration**: ~2-3 minutes

### 3. ML Training Pipeline
- **DAG ID**: `ml_training_pipeline` 
- **Description**: Machine learning workflow with data prep, training, and evaluation
- **Duration**: ~3-5 minutes

## Event Types

### Workflow Events
- `workflow.triggered` - Workflow run started
- `workflow.started` - Execution began
- `workflow.completed` - Finished successfully
- `workflow.failed` - Execution failed
- `workflow.stopped` - Manually stopped
- `workflow.retried` - Restarted after failure

### Task Events
- `task.started` - Individual task began
- `task.completed` - Task finished successfully
- `task.failed` - Task execution failed

## Development

### Running Backend Locally

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Running Celery Workers

```bash
cd backend
celery -A app.core.celery_app worker --loglevel=info
celery -A app.core.celery_app beat --loglevel=info
```

### Environment Variables

```bash
# Database
POSTGRES_SERVER=localhost
POSTGRES_USER=svops
POSTGRES_PASSWORD=password
POSTGRES_DB=svops

# Airflow
AIRFLOW_URL=http://localhost:8080
AIRFLOW_USERNAME=admin
AIRFLOW_PASSWORD=admin

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Security
SECRET_KEY=your-secret-key
```

## Monitoring & Observability

### WebSocket Events
Real-time events are broadcast via WebSocket for:
- Workflow status changes
- Task progress updates  
- System notifications
- Error alerts

### Background Tasks
Celery tasks automatically:
- Monitor active workflow runs
- Sync task statuses from Airflow
- Send notifications
- Clean up completed workflows

### Notification Channels
- **Slack**: Rich formatted messages with workflow details
- **Webhook**: JSON payloads for custom integrations
- **Email**: Basic notification support (configurable)

## Security Features

- **JWT Authentication**: Stateless token-based auth
- **Role-based Access**: Admin, user, and read-only permissions
- **API Rate Limiting**: Protection against abuse
- **Input Validation**: Comprehensive request validation
- **Error Sanitization**: Secure error responses

## Troubleshooting

### Common Issues

1. **Airflow Connection Failed**
   - Check if Airflow container is running: `docker-compose ps`
   - Verify Airflow credentials in environment variables

2. **Redis Connection Issues**
   - Ensure Redis container is healthy: `docker-compose logs redis`
   - Check Redis connectivity: `redis-cli ping`

3. **Database Connection Problems**
   - Verify PostgreSQL is running: `docker-compose logs postgres`
   - Check database credentials and connection string

4. **WebSocket Connection Drops**
   - Verify Redis pub/sub is working
   - Check background task status
   - Review WebSocket connection manager logs

### Logs

```bash
# View all service logs
docker-compose logs -f

# Specific service logs
docker-compose logs -f backend
docker-compose logs -f airflow-webserver
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**Built with modern workflow orchestration in mind**