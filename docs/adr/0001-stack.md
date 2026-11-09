# ADR 0001: Technology stack

Status: accepted

- Backend: FastAPI (Python), SQLAlchemy 2.0, Alembic
- Database: PostgreSQL with pgvector
- Jobs: Celery + Redis
- Frontend: React + Vite + TypeScript (POS is an installable offline web app)
- AI service: Python / FastAPI, separate from the main API

Why: one language for backend and AI; PostgreSQL is safe for money, ledgers and stock (transactions, joins,
database-level rules); MongoDB and a Node backend were considered and not chosen.

SEO (SRS question 22): solved with server-rendered pages for bots, see ADR 0005.
