# Pixiserve

Self-hosted Google Photos replacement with ML-powered organization.

## Features (Planned)

- Local username/password authentication
- Photo & video upload with SHA256 deduplication
- Face recognition and clustering
- Object and scene detection
- Offline-first mobile sync
- Family library sharing

## Quick Start

### Prerequisites

- Docker & Docker Compose

### Setup

1. Clone the repository

2. Copy environment file and configure:
   ```bash
   cd deploy
   cp .env.example .env
   # Edit .env - set SECRET_KEY and POSTGRES_PASSWORD
   ```

3. Start services:
   ```bash
   docker compose up -d
   ```

4. Run database migrations:
   ```bash
   docker compose exec api alembic upgrade head
   ```

5. Register your admin account:
   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/register \
     -H "Content-Type: application/json" \
     -d '{"username": "admin", "email": "admin@example.com", "password": "your-password"}'
   ```

   The first registered user automatically becomes admin.

6. (Optional) Disable registration in `.env`:
   ```
   ALLOW_REGISTRATION=false
   ```

## API Authentication

### Register
```bash
POST /api/v1/auth/register
{
  "username": "myuser",
  "email": "user@example.com",
  "password": "securepassword"
}
```

### Login
```bash
POST /api/v1/auth/login
{
  "username": "myuser",  # or email
  "password": "securepassword"
}
```

Returns a JWT token to use in subsequent requests:
```
Authorization: Bearer <token>
```

## Development

### Backend (Python/FastAPI)

```bash
cd backend
poetry install
cp .env.example .env
# Edit .env with your settings

# Start dependencies
docker compose -f ../deploy/docker-compose.yml up db redis -d

# Run migrations
alembic upgrade head

# Start dev server
uvicorn app.main:app --reload
```

### API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Architecture

See `/architecture` for detailed system design:
- `ml-pipeline.md` - Hardware-agnostic ML processing
- `sync-protocol.md` - Offline-first sync protocol
- `security.md` - Security model

## Tech Stack

- **Backend:** Python, FastAPI, SQLAlchemy, Celery
- **Database:** PostgreSQL, Redis
- **Auth:** Local username/password with bcrypt + JWT
- **Storage:** Local filesystem or S3-compatible

## License

MIT
