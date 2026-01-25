# Academic Achievement Award Summarizer

A comprehensive faculty achievement tracking system for the UNMC Department of Anesthesiology. Faculty complete quarterly surveys online, and administrators manage campaigns, track progress, and generate reports.

## Features

### Survey System
- **Online Surveys** - Faculty complete quarterly achievement surveys via web form
- **Auto-save Drafts** - Progress saved automatically as faculty work
- **Edit Until Deadline** - Faculty can modify submissions until campaign closes
- **Mobile Friendly** - Responsive design works on all devices

### Campaign Management
- **Create Campaigns** - Set up survey periods with open/close dates
- **Email Integration** - Send invitation and reminder emails to faculty
- **Customizable Templates** - Edit email subject and body per campaign
- **Progress Tracking** - See who has submitted, in progress, or not started
- **Recipient Selection** - Choose specific faculty for emails

### Division Dashboards
- **Division Chief View** - Chiefs see only their division's faculty
- **Completion Status** - Track survey submissions by quarter
- **Point Summaries** - View totals by category
- **Verification** - Chiefs can verify their division's data

### Reports & Export
- **Points CSV** - Export all faculty points (Survey + Departmental = Total)
- **Individual Summaries** - PDF/Markdown reports per faculty
- **Activity Reports** - Reports by activity type across all faculty
- **Mail Merge Export** - CSV and Word templates for Outlook mail merge

### REDCap Import
- **Import Historical Data** - Upload CSV exports from REDCap
- **Comparison View** - See new, updated, and unchanged records
- **Skip Option** - Choose to skip records with point reductions
- **Campaign Integration** - Create survey responses from import data

## Installation

### Prerequisites

- Python 3.11 or higher
- pip (Python package manager)

### Quick Start

```bash
# Clone the repository
git clone https://github.com/nickmarkin/AAA-Summarizer.git
cd AAA-Summarizer

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Start development server
python manage.py runserver
```

Access at http://127.0.0.1:8000

### PDF Generation (Optional)

For PDF export, install system dependencies:

**macOS:**
```bash
brew install pango
```

**Ubuntu/Debian:**
```bash
sudo apt-get install libpango-1.0-0 libpangocairo-1.0-0
```

## Usage

### For Administrators

1. **Set up Academic Year** - Configure the current academic year
2. **Manage Roster** - Add/edit faculty members and their divisions
3. **Create Campaign** - Set up a survey campaign for a quarter
4. **Add Faculty** - Select which faculty to include in the campaign
5. **Send Emails** - Send invitation emails to faculty
6. **Monitor Progress** - Track submissions on campaign detail page
7. **Send Reminders** - Send reminder emails to non-submitters
8. **Export Data** - Download CSV or generate reports when complete

### For Faculty

1. **Receive Email** - Get invitation email with unique portal link
2. **Access Portal** - Click link to access personal portal
3. **Complete Survey** - Fill out activities by category
4. **Review & Submit** - Review all entries and submit
5. **Edit if Needed** - Can edit and resubmit until deadline

### For Division Chiefs

1. **Access Dashboard** - Go to division dashboard from home page
2. **Review Faculty** - See all faculty in your division
3. **Check Status** - View who has submitted each quarter
4. **Verify Data** - Mark division as verified after review

## Point Categories

### Survey Points (Faculty-Reported)
1. **Citizenship** - Evaluations, committees, department activities
2. **Education** - Teaching awards, lectures, board prep, mentorship
3. **Research** - Grant review, awards, submissions, thesis committees
4. **Leadership** - Education, society, board leadership
5. **Content Expert** - Speaking, publications, pathways, textbooks, abstracts, editorial

### Departmental Points (Admin-Entered)
- Trainee evaluations completion
- Teaching awards
- CCC membership

**Total Points** = Survey Points + Departmental Points

## Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
# Security
SECRET_KEY=your-secret-key-here
DEBUG=False

# Server
ALLOWED_HOSTS=your-server.unmc.edu
SITE_URL=https://your-server.unmc.edu

# Email (for sending survey invitations)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.unmc.edu
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@unmc.edu
EMAIL_HOST_PASSWORD=your-password
DEFAULT_FROM_EMAIL=noreply@unmc.edu
```

## Deployment

See `DEPLOYMENT.md` for full production deployment instructions.

### Quick Docker Deployment

```bash
docker-compose up -d
```

### Manual Deployment

1. Set up virtual environment and install dependencies
2. Configure `.env` with production settings
3. Run `python manage.py migrate`
4. Run `python manage.py collectstatic`
5. Configure Gunicorn and Nginx
6. Set up systemd service

## Project Structure

```
AAA Summarizer/
├── reports_app/            # Reports, roster, import, dashboards
├── survey_app/             # Survey campaigns and responses
├── webapp/                 # Django project settings
├── templates/              # HTML templates
├── static/                 # CSS, JS, images
├── src/                    # Legacy CLI (still functional)
├── requirements.txt        # Python dependencies
├── manage.py               # Django management
├── DEPLOYMENT.md           # IT deployment guide
└── README.md               # This file
```

## License

Internal use - UNMC Department of Anesthesiology

## Support

For application issues, contact the developer.
For server/infrastructure issues, contact UNMC IT.
