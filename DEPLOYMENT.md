# IT Deployment Guide - Academic Achievement Award Summarizer

This document provides step-by-step instructions for deploying the Academic Achievement Award Summarizer web application to a production server.

## Overview

- **Framework**: Django 6.0
- **Language**: Python 3.11+
- **Database**: SQLite (persistent data for faculty, surveys, campaigns)
- **PDF Generation**: WeasyPrint (requires system libraries)
- **Email**: SMTP for sending survey invitations/reminders

## Prerequisites

### System Requirements

- Linux server (Ubuntu 22.04 LTS recommended) or macOS
- Python 3.11 or higher
- 1GB RAM minimum
- 1GB disk space (for database and static files)

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
```bash
# Security
SECRET_KEY=your-random-secret-key-here
DEBUG=False
ALLOWED_HOSTS=your-server-hostname.unmc.edu

# URL Configuration
SITE_URL=https://your-server-hostname.unmc.edu

# Email Configuration (for survey invitations)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.unmc.edu
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=service-account@unmc.edu
EMAIL_HOST_PASSWORD=your-smtp-password
DEFAULT_FROM_EMAIL=noreply@unmc.edu
SURVEY_EMAIL_SUBJECT_PREFIX=[UNMC Anesthesiology]
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
# Test: Create a campaign, add faculty, send test email
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

## Email Configuration

The application sends emails for:
- Survey invitations (initial)
- Survey reminders (follow-up)

### What IT Needs to Provide

Contact your IT department and request:

1. **SMTP server hostname** (e.g., `smtp.unmc.edu` or `smtp.office365.com`)
2. **SMTP port** (typically 587 for TLS, 25 for non-TLS)
3. **Authentication credentials**:
   - Service account email address
   - Password or app-specific password
4. **Sender address** that's authorized to send from this server
5. **Server IP whitelisting** (if required by mail server)

### SMTP Setup

Common configurations:

**Microsoft 365 / Office 365:**
```bash
EMAIL_HOST=smtp.office365.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=service-account@unmc.edu
EMAIL_HOST_PASSWORD=your-password-or-app-password
DEFAULT_FROM_EMAIL=service-account@unmc.edu
```
Note: Microsoft 365 often requires the FROM address to match the authenticated user.

**On-premises Exchange:**
```bash
EMAIL_HOST=mail.unmc.edu
EMAIL_PORT=25
EMAIL_USE_TLS=False
EMAIL_HOST_USER=           # May not be required for internal relay
EMAIL_HOST_PASSWORD=       # May not be required for internal relay
DEFAULT_FROM_EMAIL=noreply@unmc.edu
```
Note: Internal Exchange servers may allow unauthenticated relay from whitelisted IPs.

**Gmail (for testing only):**
```bash
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-gmail@gmail.com
EMAIL_HOST_PASSWORD=your-app-specific-password
```
Note: Requires app-specific password (not regular password) with 2FA enabled.

### Testing Email (Without SMTP)

To test email functionality without a working SMTP server, use the file-based backend:

```bash
# In .env
EMAIL_BACKEND=django.core.mail.backends.filebased.EmailBackend
EMAIL_FILE_PATH=/opt/academic-achievement/sent_emails
```

Emails will be written to files in the `sent_emails/` directory instead of being sent. You can review them to verify content and formatting.

### Testing Email (With SMTP)

Once SMTP is configured, test from Django shell:

```bash
source venv/bin/activate
python manage.py shell
```

```python
from django.core.mail import send_mail
send_mail(
    'Test Subject',
    'Test body text',
    'from-address@unmc.edu',
    ['your-email@unmc.edu'],
    fail_silently=False
)
```

If successful, you should receive the test email. If it fails, you'll see the error message.

### Mail Merge Fallback (If SMTP Unavailable)

If server-based email isn't working, you can use Outlook mail merge from a PC:

1. Go to **Survey Campaigns** → select campaign → **Export**
2. Download **Mail Merge CSV** (contains faculty names, emails, survey links)
3. Download **Mail Merge Word Template** (pre-formatted invitation letter)
4. Open the Word template in Microsoft Word
5. Use **Mailings** → **Start Mail Merge** → **Use Existing List** → select the CSV
6. **Finish & Merge** → **Send Email Messages**

This sends personalized emails through your Outlook account instead of the server.

### Common Email Issues

| Issue | Likely Cause | Solution |
|-------|--------------|----------|
| Connection refused | Wrong host/port | Verify SMTP settings with IT |
| Authentication failed | Wrong credentials | Check username/password, may need app-specific password |
| Relay access denied | Server not whitelisted | Ask IT to whitelist server IP |
| Timeout | Firewall blocking | Check port 587/25 is open outbound |
| FROM address rejected | Unauthorized sender | Use the authenticated account as FROM |

## Security Considerations

1. **HTTPS**: Use Let's Encrypt or institutional certificates
2. **Firewall**: Only expose ports 80/443
3. **Database**: SQLite file should not be web-accessible
4. **Tokens**: Faculty portal tokens are randomly generated (URL-safe)
5. **Session cleanup**: Sessions expire automatically

## Verification Checklist

After deployment, verify:

- [ ] Home page loads at configured URL
- [ ] Can create a survey campaign
- [ ] Can add faculty to campaign
- [ ] Can send test invitation email
- [ ] Faculty can access portal via email link
- [ ] Faculty can complete and submit survey
- [ ] Admin can view submissions
- [ ] Points CSV export downloads correctly
- [ ] Division dashboards load for chiefs

## Test Data

A sample CSV file is included in `test_data/sample_export.csv` for testing REDCap import functionality.

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

### Emails Not Sending

1. Check EMAIL_BACKEND is set to smtp (not filebased)
2. Verify SMTP credentials with IT (see Email Configuration section)
3. Test SMTP connection from Django shell (see Testing Email above)
4. Check email logs: `EmailLog.objects.all()` in Django shell
5. Check server can reach SMTP port: `telnet smtp.unmc.edu 587`
6. Review common issues table in Email Configuration section
7. **Fallback**: Use mail merge export if server email isn't working

### Survey Links Not Working

Verify SITE_URL is set correctly in `.env`:
- Include protocol (https://)
- Include any subpath if deployed at a subpath
- No trailing slash

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

### Database Backup

```bash
# Backup
cp /opt/academic-achievement/db.sqlite3 /backup/db.sqlite3.$(date +%Y%m%d)

# Restore
cp /backup/db.sqlite3.YYYYMMDD /opt/academic-achievement/db.sqlite3
sudo systemctl restart academic-achievement
```

### Log Rotation

Logs are written to systemd journal. Configure retention in `/etc/systemd/journald.conf`.

## Support

For application issues, contact the developer.
For server/infrastructure issues, contact UNMC IT.

## File Structure

```
/opt/academic-achievement/
├── reports_app/            # Reports, roster, import
├── survey_app/             # Survey campaigns and responses
├── webapp/                 # Django project settings
├── templates/              # HTML templates
├── static/                 # Static files (CSS, JS)
├── staticfiles/            # Collected static files (production)
├── venv/                   # Python virtual environment
├── db.sqlite3              # SQLite database
├── requirements.txt        # Python dependencies
├── manage.py               # Django management script
├── .env                    # Environment variables (create from .env.example)
└── gunicorn.sock           # Unix socket (created at runtime)
```
