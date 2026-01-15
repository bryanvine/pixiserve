# Pixiserve Community Applications Templates

This directory contains the Unraid Community Applications templates for Pixiserve.

## Submitting to Community Applications

To get Pixiserve listed in the Unraid Community Applications store:

### Option 1: Submit via GitHub (Recommended)

1. Fork the [Community Applications repository](https://github.com/Squidly271/community.applications)

2. Copy the template files from `templates/` to your fork under a new directory

3. Create a pull request with your templates

### Option 2: Request Addition

1. Open an issue on the [Community Applications repository](https://github.com/Squidly271/community.applications/issues)

2. Include links to your templates:
   - Main template: `https://raw.githubusercontent.com/pixiserve/pixiserve/main/deploy/unraid/pixiserve.xml`
   - PostgreSQL: `https://raw.githubusercontent.com/pixiserve/pixiserve/main/deploy/unraid/pixiserve-postgres.xml`
   - Redis: `https://raw.githubusercontent.com/pixiserve/pixiserve/main/deploy/unraid/pixiserve-redis.xml`

3. Provide the Docker Hub repository URL: `https://hub.docker.com/r/pixiserve/pixiserve`

## Template Requirements

Before submitting, ensure:

- [ ] Docker image is published to Docker Hub
- [ ] All template XML files are valid
- [ ] Icons are accessible via public URLs
- [ ] Support/Project URLs are correct
- [ ] Template has been tested on Unraid

## Directory Structure

```
community-applications/
├── README.md                    # This file
├── templates-repository.json    # Repository manifest
└── templates/
    ├── pixiserve.xml           # Main application template
    ├── pixiserve-postgres.xml  # PostgreSQL database template
    └── pixiserve-redis.xml     # Redis cache template
```

## Testing Templates

To test templates before submission:

1. On your Unraid server, go to **Apps** > **Settings**

2. Under **Template Repositories**, add:
   ```
   https://raw.githubusercontent.com/YOUR_USERNAME/pixiserve/main/community-applications/templates-repository.json
   ```

3. Click **Save** and wait for the repository to sync

4. Search for "Pixiserve" in the Apps tab

## Icons

Place icon files in `deploy/unraid/`:
- `pixiserve-icon.png` - 512x512 PNG for the main app
- `postgres-icon.png` - PostgreSQL icon
- `redis-icon.png` - Redis icon

Icons should be:
- PNG format
- 512x512 pixels recommended
- Transparent background preferred
