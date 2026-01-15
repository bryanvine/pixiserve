# Unraid Deployment Guide

## Quick Install via Community Applications

Once Pixiserve is listed in Community Applications:

1. Go to **Apps** tab in Unraid
2. Search for "Pixiserve"
3. Install in this order:
   - **Pixiserve-PostgreSQL** - Database
   - **Pixiserve-Redis** - Cache/Queue
   - **Pixiserve** - Main application

## Manual Installation

### Step 1: Install PostgreSQL

1. Go to **Docker** > **Add Container**
2. Use template URL: `https://raw.githubusercontent.com/pixiserve/pixiserve/main/deploy/unraid/pixiserve-postgres.xml`
3. Configure:
   - **Data Storage**: `/mnt/user/appdata/pixiserve/postgres`
   - **Database Password**: Change from default!
4. Click **Apply**

### Step 2: Install Redis

1. Go to **Docker** > **Add Container**
2. Use template URL: `https://raw.githubusercontent.com/pixiserve/pixiserve/main/deploy/unraid/pixiserve-redis.xml`
3. Configure:
   - **Data Storage**: `/mnt/user/appdata/pixiserve/redis`
4. Click **Apply**

### Step 3: Install Pixiserve

1. Go to **Docker** > **Add Container**
2. Use template URL: `https://raw.githubusercontent.com/pixiserve/pixiserve/main/deploy/unraid/pixiserve.xml`
3. Configure:
   - **Photos Storage**: `/mnt/user/photos` (or your preferred location)
   - **Thumbnails Storage**: `/mnt/user/appdata/pixiserve/thumbnails`
   - **Database URL**: `postgresql+asyncpg://pixiserve:YOUR_PASSWORD@Pixiserve-PostgreSQL:5432/pixiserve`
   - **Redis URL**: `redis://Pixiserve-Redis:6379/0`
4. Click **Apply**

### Step 4: Run Database Migrations

1. Open Pixiserve container console
2. Run: `alembic upgrade head`

### Step 5: Create Admin User

```bash
curl -X POST http://YOUR_UNRAID_IP:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "email": "admin@example.com", "password": "your-secure-password"}'
```

### Step 6: Disable Registration (Recommended)

1. Edit Pixiserve container
2. Set **Allow Registration** to `false`
3. Apply changes

## Storage Recommendations

### Photos Storage
- Use a share on your array or cache pool
- Recommended: `/mnt/user/photos/pixiserve`
- Enable **Use Cache: Prefer** for best performance

### Thumbnails Storage
- Can use appdata or a dedicated cache location
- Recommended: `/mnt/cache/appdata/pixiserve/thumbnails`
- These are regeneratable, so cache-only is fine

### Database Storage
- Keep on SSD/cache for best performance
- Recommended: `/mnt/cache/appdata/pixiserve/postgres`

## Network Configuration

### Default Ports
- Pixiserve API: 8000
- PostgreSQL: 5432 (internal only)
- Redis: 6379 (internal only)

### Reverse Proxy (Recommended)

For external access, use Nginx Proxy Manager or Traefik:

```nginx
server {
    listen 443 ssl http2;
    server_name photos.yourdomain.com;

    location / {
        proxy_pass http://YOUR_UNRAID_IP:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # For large uploads
        client_max_body_size 500M;
    }
}
```

## GPU Passthrough (Future)

For ML acceleration, you can pass through your GPU:

1. Install NVIDIA drivers on Unraid
2. Edit Pixiserve container
3. Add `--runtime=nvidia` to Extra Parameters
4. Set `NVIDIA_VISIBLE_DEVICES=all`

## Backup

### What to Back Up
- `/mnt/user/appdata/pixiserve/postgres` - Database (critical)
- `/mnt/user/photos/pixiserve` - Original photos
- Configuration settings from container

### What's Regeneratable
- `/mnt/user/appdata/pixiserve/thumbnails`
- `/mnt/user/appdata/pixiserve/redis`

## Troubleshooting

### Container Won't Start
- Check PostgreSQL and Redis are running first
- Verify DATABASE_URL and REDIS_URL are correct
- Check container logs for errors

### Can't Connect to Database
- Ensure container names match in URLs (e.g., `Pixiserve-PostgreSQL`)
- Try using IP address instead of container name
- Check PostgreSQL container is healthy

### Photos Not Uploading
- Check Photos Storage path exists and is writable
- Verify file size limits in reverse proxy
- Check container logs for errors
