# IT Quick Reference - Academic Achievement Summarizer

## Server Location
```
/opt/academic-achievement/
```

---

## Fix 1: UNMC Logo Not Showing

The logo and other static files need to be collected after deployment/updates.

```bash
cd /opt/academic-achievement
source venv/bin/activate
python manage.py collectstatic --noinput
```

**Verify it worked:**
```bash
ls -la /opt/academic-achievement/staticfiles/images/unmc-logo.png
```

**Note:** Run `collectstatic` after every code update.

---

## Fix 2: Enable Email Sending

Currently, emails are saved as files instead of being sent. To enable real email delivery:

### Step 1: Edit the environment file

```bash
nano /opt/academic-achievement/.env
```

### Step 2: Add these settings

```bash
# Email Backend - REQUIRED for sending real emails
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend

# SMTP Server Settings - Get these from your email/IT team
EMAIL_HOST=smtp.unmc.edu
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=service-account@unmc.edu
EMAIL_HOST_PASSWORD=your-smtp-password

# Default sender (used if campaign doesn't specify one)
DEFAULT_FROM_EMAIL=UNMC Anesthesiology <anesthesiology@unmc.edu>
```

### Step 3: Restart the application

```bash
sudo systemctl restart academic-achievement
```

### Step 4: Test email

In the web app:
1. Go to Survey Campaigns
2. Click on a campaign
3. Find a single faculty member and click "Resend Email" (sends just one test email)
4. Check if they received it

---

## Where Are the "Sent" Emails?

Before SMTP is configured, emails are saved to files here:
```bash
ls /opt/academic-achievement/sent_emails/
```

You can view what emails would have been sent:
```bash
cat /opt/academic-achievement/sent_emails/*.log
```

---

## Common SMTP Configurations

### Office 365 / Microsoft 365
```bash
EMAIL_HOST=smtp.office365.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-account@unmc.edu
EMAIL_HOST_PASSWORD=your-password
```

### Gmail (with App Password)
```bash
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-account@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

### Internal SMTP Relay (no auth)
```bash
EMAIL_HOST=mail-relay.unmc.edu
EMAIL_PORT=25
EMAIL_USE_TLS=False
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
```

---

## Checking Logs

```bash
# Application logs
sudo journalctl -u academic-achievement -f

# Recent errors only
sudo journalctl -u academic-achievement --since "1 hour ago" | grep -i error
```

---

## Restarting Services

```bash
# Restart the app
sudo systemctl restart academic-achievement

# Restart nginx (if static files still not loading)
sudo systemctl restart nginx

# Check status
sudo systemctl status academic-achievement
```

---

## After Code Updates

Always run these commands after pulling new code:

```bash
cd /opt/academic-achievement
source venv/bin/activate

# Update dependencies (if requirements.txt changed)
pip install -r requirements.txt

# Run database migrations
python manage.py migrate

# Collect static files (images, CSS, JS)
python manage.py collectstatic --noinput

# Restart the app
sudo systemctl restart academic-achievement
```

---

## Contact

For application issues: [Developer contact]
For server/infrastructure issues: UNMC IT
