from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from contextlib import asynccontextmanager
import time
from typing import AsyncGenerator

from config import settings
from database import engine, Base

# Import routers
from routers.public import (
    api_keys,
    auth,
    tracks,
    playlists,
    interactions,
    recommendations,
    search,
    users,
    password,
    browse,
    player,
    sessions,
    albums,
    artists,
    ml_recommendations,
    onboarding,
    security,
    audio,
    tracking,
)
from routers.premium import analytics
# from routers.admin import dashboard


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Lifespan events for startup and shutdown."""
    # Startup
    print("🚀 Starting TuneTrail API...")

    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    print("✅ Database tables created")
    print(f"📍 Edition: {settings.EDITION}")
    print(f"🌍 Environment: {settings.ENVIRONMENT}")

    yield

    # Shutdown
    print("👋 Shutting down TuneTrail API...")


# Create FastAPI app with enhanced metadata
app = FastAPI(
    title="TuneTrail API",
    description="""
    **TuneTrail** is a powerful music recommendation platform combining state-of-the-art
    machine learning models with a modern, scalable architecture.

    ## Features

    * 🎯 **Content-Based Filtering** - Audio feature analysis
    * 🤝 **Collaborative Filtering** - LightGCN graph neural networks
    * 🧠 **Neural CF** - Deep learning recommendations (Pro+)
    * 🎵 **Audio Processing** - Librosa + Essentia feature extraction
    * 📊 **Real-time Analytics** - Track usage and performance
    * 🔐 **Secure API Keys** - Scoped permissions and rate limiting

    ## Authentication

    All API requests require authentication using an API key:

    ```bash
    curl https://api.tunetrail.dev/tracks \\
      -H "Authorization: Bearer tt_your_api_key_here"
    ```

    [Get your API key →](https://community.tunetrail.dev/api-keys)

    ## Rate Limits

    | Plan | Per Minute | Per Hour | Per Day |
    |------|-----------|----------|---------|
    | Free | 10 | 100 | 1,000 |
    | Starter | 60 | 1,000 | 10,000 |
    | Pro | 300 | 10,000 | 100,000 |
    | Enterprise | Custom | Custom | Custom |

    ## Support

    * 📚 [Documentation](https://docs.tunetrail.dev)
    * 💬 [Community](https://community.tunetrail.dev)
    * 📧 [Email Support](mailto:support@tunetrail.dev)
    """,
    version="1.0.0",
    terms_of_service="https://tunetrail.dev/terms",
    contact={
        "name": "TuneTrail Support",
        "url": "https://tunetrail.dev/support",
        "email": "support@tunetrail.dev",
    },
    license_info={
        "name": "Dual License: AGPL-3.0 (Community) / Commercial (SaaS)",
        "url": "https://github.com/yourusername/tunetrail/blob/main/LICENSE",
    },
    openapi_tags=[
        {
            "name": "System",
            "description": "System health and status endpoints.",
        },
        {
            "name": "Authentication",
            "description": "User authentication and registration. Get JWT tokens for API access.",
        },
        {
            "name": "API Keys",
            "description": "Manage API keys for authentication and access control. "
            "Create, rotate, and monitor your API keys.",
            "externalDocs": {
                "description": "API Keys Guide",
                "url": "https://docs.tunetrail.dev/api-keys",
            },
        },
        {
            "name": "Tracks",
            "description": "Manage music tracks. Upload, update, and retrieve track information "
            "including metadata and audio features.",
        },
        {
            "name": "Recommendations",
            "description": "Get personalized music recommendations using ML models. "
            "Supports content-based, collaborative, and hybrid approaches.",
        },
        {
            "name": "Playlists",
            "description": "Create and manage playlists. Organize tracks and share with users.",
        },
        {
            "name": "Audio Processing",
            "description": "Extract audio features and analyze music tracks. "
            "Requires Starter plan or higher.",
        },
        {
            "name": "Webhooks",
            "description": "Configure webhooks for real-time event notifications. "
            "Available for Pro plan and higher.",
        },
        {
            "name": "Admin",
            "description": "Administrative endpoints for organization and user management.",
        },
    ],
    lifespan=lifespan,
    docs_url="/docs",  # Swagger UI
    redoc_url="/redoc",  # ReDoc
    openapi_url="/openapi.json",
)


# Custom OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
        terms_of_service=app.terms_of_service,
        contact=app.contact,
        license_info=app.license_info,
    )

    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "API Key",
            "description": "Enter your API key (format: tt_...)",
        },
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "Alternative API key authentication via custom header",
        },
    }

    # Add global security requirement
    openapi_schema["security"] = [{"BearerAuth": []}]

    # Add custom info
    openapi_schema["info"]["x-logo"] = {
        "url": "https://tunetrail.dev/logo.png",
        "altText": "TuneTrail Logo",
    }

    # Add servers
    openapi_schema["servers"] = [
        {
            "url": "https://api.tunetrail.dev",
            "description": "Production API",
        },
        {
            "url": "https://staging-api.tunetrail.dev",
            "description": "Staging API",
        },
        {
            "url": "http://localhost:8000",
            "description": "Local Development",
        },
    ]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Include routers - Public (all tiers)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(password.router, prefix="/api/v1")
app.include_router(security.router, prefix="/api/v1")
app.include_router(onboarding.router, prefix="/api/v1")
app.include_router(api_keys.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(tracks.router, prefix="/api/v1")
app.include_router(albums.router, prefix="/api/v1")
app.include_router(artists.router, prefix="/api/v1")
app.include_router(playlists.router, prefix="/api/v1")
app.include_router(interactions.router, prefix="/api/v1")
app.include_router(recommendations.router, prefix="/api/v1")
app.include_router(ml_recommendations.router, prefix="/api/v1")
app.include_router(search.router, prefix="/api/v1")
app.include_router(browse.router, prefix="/api/v1")
app.include_router(player.router, prefix="/api/v1")
app.include_router(sessions.router, prefix="/api/v1")
app.include_router(audio.router, prefix="/api/v1")
app.include_router(tracking.router, prefix="/api/v1")

# Include routers - Premium (Pro+ features)
app.include_router(analytics.router, prefix="/api/v1")


# Health check endpoint
@app.get(
    "/health",
    tags=["System"],
    summary="Health Check",
    description="Check if the API is running and healthy.",
    response_description="Returns the health status of the API",
)
async def health_check():
    """
    Simple health check endpoint for monitoring.

    Returns:
        - status: Current API status
        - version: API version
        - edition: Community or SaaS
    """
    return {
        "status": "healthy",
        "version": "1.0.0",
        "edition": settings.EDITION,
        "environment": settings.ENVIRONMENT,
    }


# Root endpoint
@app.get(
    "/",
    tags=["System"],
    summary="API Root",
    description="Welcome message and quick links",
)
async def root():
    """
    API root endpoint with helpful links.
    """
    return {
        "message": "Welcome to TuneTrail API 🎵",
        "version": "1.0.0",
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc",
            "openapi_json": "/openapi.json",
        },
        "links": {
            "community": "https://community.tunetrail.dev",
            "documentation": "https://docs.tunetrail.dev",
            "status": "https://status.tunetrail.dev",
        },
    }


# Exception handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": "Not Found",
            "message": f"The endpoint {request.url.path} does not exist",
            "documentation": "/docs",
        },
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred. Please try again later.",
            "support": "support@tunetrail.dev",
        },
    )