# IT Deployment Guide - Academic Achievement Award Summarizer

This document provides step-by-step instructions for deploying the Academic Achievement Award Summarizer web application to a production server.

## Overview

- **Framework**: Django 6.0
- **Language**: Python 3.11+
- **Database**: SQLite (sessions only, no persistent data)
- **PDF Generation**: WeasyPrint (requires system libraries)

## Prerequisites

### System Requirements

- Linux server (Ubuntu 22.04 LTS recommended) or macOS
- Python 3.11 or higher
- 1GB RAM minimum
- 500MB disk space

### System Dependencies (Ubuntu/Debian)

```bash
sudo apt-get update
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info
```

### System Dependencies (macOS)

```bash
brew install python pango
```

## Deployment Options

### Option 1: Docker (Recommended)

Docker provides the easiest deployment with all dependencies bundled.

```bash
# Clone or copy the project
cd /opt/academic-achievement

# Build and run
docker-compose up -d

# Access at http://localhost:8000
```

### Option 2: Manual Deployment

#### Step 1: Set Up Project Directory

```bash
# Create application directory
sudo mkdir -p /opt/academic-achievement
sudo chown $USER:$USER /opt/academic-achievement
cd /opt/academic-achievement

# Copy project files (from handoff package)
cp -r /path/to/handoff/* .
```

#### Step 2: Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

#### Step 3: Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit with production values
nano .env
```

Required environment variables:
```
SECRET_KEY=your-random-secret-key-here
DEBUG=False
ALLOWED_HOSTS=your-server-hostname.unmc.edu
SITE_URL=https://your-server-hostname.unmc.edu
```

**Important**: If the application is deployed at a subpath (e.g., `/secure/academic-achievement`), include the full path in `SITE_URL`:
```
SITE_URL=https://your-server-hostname.unmc.edu/secure/academic-achievement
```
This ensures survey invitation links are generated correctly.

Generate a secret key:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

#### Step 4: Initialize Database

```bash
source venv/bin/activate
python manage.py migrate
python manage.py collectstatic --noinput
```

#### Step 5: Test the Application

```bash
# Run development server to verify
python manage.py runserver 0.0.0.0:8000

# Access at http://server-ip:8000
# Upload test CSV and verify exports work
```

#### Step 6: Configure Production Server (Gunicorn + Nginx)

Install Gunicorn:
```bash
pip install gunicorn
```

Create systemd service (`/etc/systemd/system/academic-achievement.service`):
```ini
[Unit]
Description=Academic Achievement Summarizer
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/academic-achievement
Environment="PATH=/opt/academic-achievement/venv/bin"
EnvironmentFile=/opt/academic-achievement/.env
ExecStart=/opt/academic-achievement/venv/bin/gunicorn \
    --workers 3 \
    --bind unix:/opt/academic-achievement/gunicorn.sock \
    webapp.wsgi:application

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable academic-achievement
sudo systemctl start academic-achievement
```

Configure Nginx (`/etc/nginx/sites-available/academic-achievement`):
```nginx
server {
    listen 80;
    server_name your-server-hostname.unmc.edu;

    location /static/ {
        alias /opt/academic-achievement/staticfiles/;
    }

    location / {
        proxy_pass http://unix:/opt/academic-achievement/gunicorn.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

Enable site:
```bash
sudo ln -s /etc/nginx/sites-available/academic-achievement /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## Security Considerations

1. **HTTPS**: Use Let's Encrypt or institutional certificates
2. **Firewall**: Only expose ports 80/443
3. **No persistent data**: CSV uploads are processed in memory, not stored
4. **Session cleanup**: Sessions expire automatically

## Verification Checklist

After deployment, verify:

- [ ] Home page loads at configured URL
- [ ] Can upload test CSV file
- [ ] Faculty list displays correctly
- [ ] Points CSV export downloads
- [ ] Faculty summary PDF generates
- [ ] Activity report PDF generates

## Test Data

A sample CSV file is included in `test_data/sample_export.csv` for testing the deployment.

## Troubleshooting

### PDF Generation Fails

Check that pango libraries are installed:
```bash
# Ubuntu
dpkg -l | grep pango

# Test WeasyPrint
python -c "from weasyprint import HTML; HTML(string='<p>Test</p>').write_pdf('/tmp/test.pdf')"
```

### Static Files Not Loading

```bash
python manage.py collectstatic --noinput
```

### Permission Errors

```bash
sudo chown -R www-data:www-data /opt/academic-achievement
sudo chmod -R 755 /opt/academic-achievement
```

### Server Won't Start

Check logs:
```bash
sudo journalctl -u academic-achievement -f
```

## Maintenance

### Updating the Application

```bash
cd /opt/academic-achievement
source venv/bin/activate

# Pull new code or copy new files
git pull  # or copy updated files

# Update dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Collect static files (REQUIRED - copies images, CSS, JS to web server location)
python manage.py collectstatic --noinput

# Restart service
sudo systemctl restart academic-achievement
```

**Important**: Always run `collectstatic` after updates. If images or styles are missing/broken, this is usually the fix.

### Log Rotation

Logs are written to systemd journal. Configure retention in `/etc/systemd/journald.conf`.

## Support

For application issues, contact the developer.
For server/infrastructure issues, contact UNMC IT.

## File Structure

```
/opt/academic-achievement/
├── src/                    # Core Python library
├── reports_app/            # Django app
├── webapp/                 # Django project settings
├── templates/              # HTML templates
├── static/                 # Static files (CSS, JS)
├── staticfiles/            # Collected static files (production)
├── venv/                   # Python virtual environment
├── requirements.txt        # Python dependencies
├── manage.py               # Django management script
├── .env                    # Environment variables (create from .env.example)
└── gunicorn.sock           # Unix socket (created at runtime)
```
