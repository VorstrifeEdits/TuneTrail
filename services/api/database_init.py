"""
TuneTrail Database Initialization
Handles both Community and Commercial edition database setup
"""

import os
import subprocess
import asyncio
from pathlib import Path
from typing import Optional
import logging

from sqlalchemy.ext.asyncio import AsyncEngine
from database import Base, engine
from config import settings

logger = logging.getLogger(__name__)


class DatabaseInitializer:
    """Handles database initialization for different TuneTrail editions."""

    def __init__(self, db_engine: AsyncEngine):
        self.engine = db_engine
        self.edition = settings.EDITION.lower()
        self.environment = settings.ENVIRONMENT.lower()

    async def initialize(self) -> bool:
        """Initialize database based on edition and environment."""
        try:
            if self.edition == "community":
                return await self._initialize_community()
            elif self.edition in ["commercial", "saas", "enterprise"]:
                return await self._initialize_commercial()
            else:
                logger.warning(f"Unknown edition '{self.edition}', defaulting to community")
                return await self._initialize_community()
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            return False

    async def _initialize_community(self) -> bool:
        """Community edition: Simple SQLAlchemy create_all approach."""
        logger.info("🏠 Initializing Community Edition database...")

        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        logger.info("✅ Community Edition database initialized")
        return True

    async def _initialize_commercial(self) -> bool:
        """Commercial edition: Alembic migration-based approach."""
        logger.info("🏢 Initializing Commercial Edition database...")

        # Check if Alembic is configured
        alembic_ini = Path("migrations/alembic.ini")
        if not alembic_ini.exists():
            logger.warning("Alembic not configured, falling back to community approach")
            return await self._initialize_community()

        # In production, migrations should be run separately
        if self.environment == "production":
            logger.info("🔒 Production environment: Skipping automatic migrations")
            logger.info("   Migrations should be run manually in production")
            return True

        # Development/staging: Run migrations automatically
        try:
            await self._run_alembic_migrations()
            logger.info("✅ Commercial Edition database initialized")
            return True
        except Exception as e:
            logger.error(f"Alembic migration failed: {e}")
            logger.info("Falling back to community approach...")
            return await self._initialize_community()

    async def _run_alembic_migrations(self):
        """Run Alembic migrations in a subprocess."""
        logger.info("🔄 Running Alembic migrations...")

        # Run in a separate thread to avoid blocking the event loop
        def run_migration():
            result = subprocess.run(
                ["alembic", "upgrade", "head"],
                cwd="migrations",
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                raise Exception(f"Alembic failed: {result.stderr}")
            return result.stdout

        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        output = await loop.run_in_executor(None, run_migration)
        logger.info(f"Alembic output: {output}")

    async def get_schema_info(self) -> dict:
        """Get information about the current database schema."""
        from sqlalchemy import text

        async with self.engine.begin() as conn:
            # Check table count
            result = await conn.execute(
                text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'")
            )
            table_count = result.scalar()

            # Check if we have migration tracking
            migration_info = None
            try:
                if self.edition != "community":
                    result = await conn.execute(
                        text("SELECT version_num FROM alembic_version LIMIT 1")
                    )
                    migration_info = result.scalar()
            except:
                pass  # Table doesn't exist

            return {
                "edition": self.edition,
                "environment": self.environment,
                "table_count": table_count,
                "migration_version": migration_info,
                "initialization_method": "alembic" if migration_info else "sqlalchemy"
            }


# Global initializer instance
db_initializer = DatabaseInitializer(engine)


async def initialize_database() -> bool:
    """Main entry point for database initialization."""
    return await db_initializer.initialize()


async def get_database_info() -> dict:
    """Get current database schema information."""
    return await db_initializer.get_schema_info()