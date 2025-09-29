# TuneTrail Database Architecture

## Overview

TuneTrail uses a **dual-edition database initialization system** that provides different approaches for Community and Commercial editions:

- **Community Edition**: Simple SQLAlchemy `create_all` for zero-friction setup
- **Commercial Edition**: Alembic migrations for production-grade database management

## Edition-Based Initialization

### Community Edition (`EDITION=community`)

**Approach**: SQLAlchemy automatic table creation
**Use Case**: Self-hosted deployments, development, small teams

```python
# Automatic table creation from models
async with engine.begin() as conn:
    await conn.run_sync(Base.metadata.create_all)
```

**Advantages**:
- ✅ Zero-friction setup
- ✅ Schema always matches code
- ✅ No migration management required
- ✅ Perfect for self-hosted deployments

**Limitations**:
- ❌ No migration history
- ❌ No rollback capability
- ❌ Not suitable for production data

### Commercial Edition (`EDITION=commercial|saas|enterprise`)

**Approach**: Alembic migration-based system
**Use Case**: Production SaaS deployments, enterprise customers

```bash
# Professional migration management
alembic upgrade head
```

**Advantages**:
- ✅ Full migration history
- ✅ Rollback capabilities
- ✅ Zero-downtime deployments
- ✅ Schema versioning
- ✅ Production-safe

**Features**:
- Migration tracking in `alembic_version` table
- Automatic schema generation from models
- Environment-aware execution
- Professional deployment practices

## Implementation Details

### Database Initializer Class

Located in `services/api/database_init.py`:

```python
class DatabaseInitializer:
    def __init__(self, db_engine: AsyncEngine):
        self.engine = db_engine
        self.edition = settings.EDITION.lower()
        self.environment = settings.ENVIRONMENT.lower()

    async def initialize(self) -> bool:
        if self.edition == "community":
            return await self._initialize_community()
        elif self.edition in ["commercial", "saas", "enterprise"]:
            return await self._initialize_commercial()
```

### Environment-Aware Behavior

| Edition | Environment | Behavior |
|---------|-------------|----------|
| Community | Any | SQLAlchemy `create_all` |
| Commercial | Development/Staging | Auto-run Alembic migrations |
| Commercial | Production | Skip auto-migrations (manual control) |

## Commercial Edition Setup

### 1. Initial Setup

```bash
# Set commercial edition
export EDITION=commercial

# Generate initial migration from current models
cd services/api
./scripts/commercial-db-init.sh setup
```

### 2. Managing Migrations

```bash
# Generate new migration after model changes
./scripts/commercial-db-init.sh generate "Add user preferences table"

# Apply pending migrations
./scripts/commercial-db-init.sh migrate

# Check migration status
./scripts/commercial-db-init.sh status
```

### 3. Production Deployment

```bash
# Production environments require manual migration control
export ENVIRONMENT=production
export EDITION=commercial

# Run migrations separately before app deployment
alembic upgrade head

# Then start the application (it will skip auto-migrations)
uvicorn main:app --host 0.0.0.0 --port 8000
```

## File Structure

```
services/api/
├── database_init.py           # Edition-aware initialization
├── migrations/                # Commercial edition migrations
│   ├── alembic.ini           # Alembic configuration
│   ├── env.py                # Migration environment
│   ├── script.py.mako        # Migration template
│   └── versions/             # Generated migration files
├── models/                   # SQLAlchemy model definitions
│   ├── user.py
│   ├── track.py
│   └── ...
└── main.py                   # Application startup with DB init

scripts/
└── commercial-db-init.sh     # Commercial DB management utility
```

## Model-First Development

Both editions use **model-first development**:

1. Define/modify SQLAlchemy models in `services/api/models/`
2. **Community**: Tables auto-created on next restart
3. **Commercial**: Generate migration with `alembic revision --autogenerate`

## Migration Best Practices

### For Commercial Edition

1. **Always review generated migrations** before applying
2. **Test migrations on staging** before production
3. **Backup database** before major schema changes
4. **Use descriptive migration messages**
5. **Keep migrations atomic** (one logical change per migration)

### Schema Changes

```python
# Example: Adding a new field to User model
class User(Base):
    __tablename__ = "users"

    id = Column(UUID, primary_key=True)
    email = Column(String, unique=True)
    preferences = Column(JSON, default={})  # New field
```

```bash
# Generate migration for the change
alembic revision --autogenerate -m "Add user preferences field"

# Review generated migration in versions/
# Apply migration
alembic upgrade head
```

## Database Schema Information

The system provides runtime schema information:

```python
# Get current database state
db_info = await get_database_info()
# Returns:
{
    "edition": "community",
    "environment": "development",
    "table_count": 23,
    "migration_version": None,  # or version for commercial
    "initialization_method": "sqlalchemy"  # or "alembic"
}
```

## Switching Between Editions

### Community → Commercial

```bash
# 1. Set commercial edition
export EDITION=commercial

# 2. Generate initial migration from current schema
./scripts/commercial-db-init.sh setup

# 3. Restart application (will use Alembic)
docker compose restart api
```

### Commercial → Community

```bash
# 1. Set community edition
export EDITION=community

# 2. Restart application (will use SQLAlchemy)
docker compose restart api

# Note: Migration history will be preserved but not used
```

## Monitoring & Troubleshooting

### Logs

Application startup shows initialization details:

```
🚀 Starting TuneTrail API...
🏠 Initializing Community Edition database...
✅ Database initialized (23 tables)
📍 Edition: community
🌍 Environment: development
🗄️  Init Method: sqlalchemy
```

### Health Check

```bash
curl http://localhost:8000/health
# Returns edition and database info
```

### Common Issues

1. **"Alembic not configured"**: Missing `migrations/alembic.ini`
   - Solution: Run `./scripts/commercial-db-init.sh setup`

2. **Migration conflicts**: Manual schema changes conflict with migrations
   - Solution: Reset migrations or manually resolve conflicts

3. **Production auto-migration**: Commercial edition trying to auto-migrate in production
   - Solution: Ensure `ENVIRONMENT=production` is set

## Security Considerations

- **Production**: Never auto-run migrations in production
- **Permissions**: Database user should have appropriate schema permissions
- **Backups**: Always backup before major migrations
- **Validation**: Review all generated migrations before applying

This architecture provides the flexibility needed for both simple self-hosted deployments and complex commercial SaaS operations.