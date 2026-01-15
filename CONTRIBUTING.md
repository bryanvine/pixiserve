# Contributing to Pixiserve

## Development Setup

### Prerequisites
- Docker & Docker Compose
- Node.js 20+
- Python 3.11+
- Poetry

### Local Development

```bash
# Clone the repository
git clone https://github.com/pixiserve/pixiserve.git
cd pixiserve

# Start dependencies
cd deploy
docker compose up -d db redis

# Backend
cd ../backend
poetry install
alembic upgrade head
uvicorn app.main:app --reload

# Frontend (new terminal)
cd ../web
npm install
npm run dev

# Worker (new terminal)
cd ../backend
celery -A app.workers.celery_app worker --loglevel=info
```

### Docker Development

```bash
cd deploy
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

## CI/CD Pipeline

### GitHub Actions Workflows

1. **docker-build.yml** - Builds and pushes images on push to main or tags
2. **release.yml** - Creates GitHub releases on version tags
3. **manual-build.yml** - Manual trigger for testing builds

### Required Secrets

Set these in your GitHub repository settings (Settings > Secrets and variables > Actions):

| Secret | Description |
|--------|-------------|
| `DOCKERHUB_USERNAME` | Your Docker Hub username |
| `DOCKERHUB_TOKEN` | Docker Hub access token (not password) |

#### Creating a Docker Hub Token

1. Log in to [Docker Hub](https://hub.docker.com)
2. Go to Account Settings > Security > Access Tokens
3. Click "New Access Token"
4. Name: `pixiserve-github-actions`
5. Permissions: Read, Write, Delete
6. Copy the token and add it as `DOCKERHUB_TOKEN` secret

### Building Images

#### Automatic (on push to main)
Images are automatically built and pushed with:
- `latest` tag for main branch
- Version tags (e.g., `v1.0.0` creates `1.0.0` and `1.0` tags)
- Git SHA tags for traceability

#### Manual (for testing)
1. Go to Actions > Manual Build and Push
2. Click "Run workflow"
3. Select image(s) to build
4. Enter a tag (default: `dev`)

### Releasing

1. Update version in `backend/pyproject.toml`
2. Commit changes
3. Create and push a tag:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```
4. GitHub Actions will:
   - Build all images with version tags
   - Create a GitHub release
   - Update Community Applications templates

## Docker Images

| Image | Description | Architectures |
|-------|-------------|---------------|
| `pixiserve/pixiserve` | FastAPI backend | amd64, arm64 |
| `pixiserve/pixiserve-web` | React frontend | amd64, arm64 |
| `pixiserve/pixiserve-worker` | Celery worker (CPU) | amd64, arm64 |
| `pixiserve/pixiserve-worker:cuda` | Celery worker (NVIDIA) | amd64 only |

## Code Style

### Python
- Black for formatting (line length: 100)
- Ruff for linting
- Type hints required

```bash
cd backend
poetry run black app/
poetry run ruff check app/ --fix
```

### TypeScript
- ESLint + Prettier
- Strict TypeScript

```bash
cd web
npm run lint
npm run format
```

## Pull Requests

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make changes and commit: `git commit -m "Add my feature"`
4. Push to your fork: `git push origin feature/my-feature`
5. Open a Pull Request

### PR Guidelines
- Keep changes focused and small
- Include tests for new features
- Update documentation as needed
- Follow existing code style
