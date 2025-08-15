from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import engine
from app.core.redis import redis_client
from app.core.error_handlers import setup_exception_handlers
from app.core.rate_limit import setup_rate_limiting
from app.presentation.api.api import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting up...")
    try:
        await redis_client.connect()
        print("Redis connected")
    except Exception as e:
        print(f"Failed to connect to Redis: {e}")

    yield

    # Shutdown
    print("Shutting down...")
    try:
        await redis_client.disconnect()
        print("Redis disconnected")
    except Exception as e:
        print(f"Failed to disconnect from Redis: {e}")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up exception handlers
setup_exception_handlers(app)

# Set up rate limiting
setup_rate_limiting(app)

app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    return {"message": "SVOps API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
