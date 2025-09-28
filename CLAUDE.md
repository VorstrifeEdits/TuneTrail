# Claude Code Configuration

This file helps Claude Code assistant understand the TuneTrail project structure and conventions.

## Project Overview
TuneTrail is a dual-model music recommendation platform with:
- Community Edition: Open source, self-hosted (AGPL-3.0)
- SaaS Edition: Commercial, cloud-hosted

## Available MCPs
- **Vercel**: Managing the hosting of the Application
- **Context7**: Always up-to-date Documentation
- **Stripe**: Pricing, Billing, Payments
- **Assailiant**: Managing Jira Tickets, Project Managment

## Tech Stack
- **Backend**: FastAPI 0.115, Python 3.12+, PyTorch 2.5
- **Frontend**: Next.js 15, React 19, TypeScript 5.6
- **Database**: PostgreSQL 16 with pgvector extension
- **Cache**: Redis 7.4
- **ML**: Librosa, Essentia, scikit-learn, FAISS

## Code Standards

### Python
- Formatter: `black` (line length: 100)
- Linter: `ruff`
- Type checker: `mypy`
- Test: `pytest`
- Lint command: `make lint` or `docker-compose exec api ruff check .`
- Format command: `make format` or `docker-compose exec api black .`
- Test command: `make test` or `docker-compose exec api pytest`

### TypeScript/Frontend
- Linter: ESLint with Next.js config
- Formatter: Prettier with Tailwind plugin
- Type checker: TypeScript 5.6
- Lint command: `npm run lint`
- Format command: `npm run format`
- Type check: `npm run type-check`

## Project Structure
```
tunetrail/
├── services/
│   ├── api/              # FastAPI backend
│   ├── frontend/         # Next.js frontend
│   ├── ml-engine/        # ML recommendation engine
│   └── audio-processor/  # Audio feature extraction
├── core/                 # Shared Python modules
├── database/             # Migrations & seeds
├── deployment/           # K8s & Terraform
└── docs/                 # Documentation
```

## Development Workflow
1. Start services: `make up` or `docker-compose up -d`
2. View logs: `make logs` or `docker-compose logs -f`
3. Run tests: `make test`
4. Format code: `make format`
5. Lint code: `make lint`

## Key Commands
- `make dev` - Start with hot reload
- `make test` - Run all tests
- `make lint` - Lint all code
- `make format` - Format all code
- `make clean` - Clean up everything

## Important Notes
- Use async/await for all database and API calls
- Follow REST API conventions for endpoints
- Use Pydantic for data validation
- Follow Next.js App Router conventions
- Use server components by default, client components only when needed
- All ML models should support both CPU and GPU
- Implement proper error handling and logging
- Write tests for all new features