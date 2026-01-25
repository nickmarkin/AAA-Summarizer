# Claude Notes - Academic Achievement Award Summarizer

## Project Overview

This is a comprehensive faculty achievement tracking system for the UNMC Department of Anesthesiology. It includes:
- **Survey System** - Faculty complete quarterly surveys online
- **Campaign Management** - Admins create campaigns, send emails, track progress
- **Division Dashboards** - Division chiefs review their faculty
- **Reports & Export** - Generate summaries, CSV exports, PDF reports
- **REDCap Import** - Import historical data from REDCap CSV exports

## Key Architecture

### Django Apps

1. **reports_app** - Core reports, faculty roster, CSV import, division dashboards
2. **survey_app** - Survey campaigns, invitations, responses, email system
3. **webapp** - Django project settings

### Data Flow

```
REDCap CSV Import → FacultySurveyData (historical)
                          ↓
Survey Campaign → SurveyInvitation → SurveyResponse (current)
                          ↓
Division Dashboard / Reports / CSV Export
```

### Key Models

**reports_app:**
- `FacultyMember` - Faculty roster with email, division, access tokens
- `FacultySurveyData` - Imported REDCap data per faculty/year
- `DepartmentalData` - Admin-entered evaluations, teaching awards, CCC status
- `AcademicYear` - Academic year tracking (July-June cycle)
- `Division` - Department divisions with chiefs

**survey_app:**
- `SurveyCampaign` - Survey period with dates, email templates
- `SurveyInvitation` - Individual invitation with unique token
- `SurveyResponse` - Faculty responses (draft or submitted)
- `EmailLog` - Audit trail for sent emails

## File Structure

```
AAA Summarizer/
├── src/                    # Legacy CLI library (still works)
├── webapp/                 # Django project settings
├── reports_app/            # Reports, roster, import, dashboards
│   ├── models.py           # FacultyMember, FacultySurveyData, etc.
│   └── views.py            # All report and admin views
├── survey_app/             # Survey system
│   ├── models.py           # Campaign, Invitation, Response
│   ├── views.py            # Survey and campaign views
│   └── survey_config.py    # Activity definitions and point values
├── templates/
│   ├── base.html           # Main layout with sidebar
│   ├── reports/            # Report templates
│   ├── survey/             # Survey form templates
│   │   ├── admin/          # Campaign management
│   │   └── faculty/        # Faculty survey forms
│   └── import/             # CSV import templates
├── static/                 # CSS, JS, images
├── venv/                   # Python virtual environment
├── requirements.txt
├── manage.py
└── CLAUDE.md               # This file
```

## Common Tasks

### Running the Dev Server
```bash
cd "/Users/nmarkin/Library/CloudStorage/Dropbox/Claude Code Projects/AAA Summarizer"
source venv/bin/activate
python manage.py runserver
```
Access at http://127.0.0.1:8000

### Key URLs

**Admin/Staff:**
- `/` - Home dashboard
- `/roster/` - Faculty roster management
- `/survey/admin/campaigns/` - Survey campaign management
- `/divisions/` - Division dashboard list
- `/import/` - REDCap CSV import

**Faculty:**
- `/my/<token>/` - Faculty portal (token-based access)
- `/survey/s/<token>/` - Survey form

### Database Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

## Survey System

### Campaign Flow
1. Admin creates campaign (quarter, dates, email templates)
2. Admin adds faculty to campaign (creates SurveyInvitation)
3. Admin sends invitation emails
4. Faculty access portal via unique link
5. Faculty complete survey (auto-saves drafts)
6. Faculty submit survey
7. Admin can send reminder emails to non-submitters
8. Admin exports data when campaign closes

### Email Templates
Each campaign has customizable:
- **Invitation email** - Subject, body with placeholders
- **Reminder email** - Subject, body with placeholders
- Placeholders: `{first_name}`, `{last_name}`, `{survey_link}`, `{deadline}`, `{status}`

### Survey Categories
1. **Citizenship** - Evaluations, committees, department activities
2. **Education** - Teaching awards, lectures, board prep, mentorship
3. **Research** - Grant review, awards, submissions, thesis committees
4. **Leadership** - Education, society, board leadership
5. **Content Expert** - Speaking, publications, pathways, textbooks, abstracts, editorial

## Points Calculation

- **Survey Points** - From faculty survey responses
- **Departmental Points** - Admin-entered (evaluations + teaching awards + CCC membership)
- **Total** = Survey Points + Departmental Points

Note: CCC points are included in Departmental Points (not separate).

## Division Dashboard

Division chiefs can:
- View faculty in their division
- See survey completion status by quarter
- Review point totals
- Verify division data after Q4

## Import from REDCap

1. Upload CSV export from REDCap
2. Review comparison (new/updated/unchanged records)
3. Optionally skip records with point reductions
4. Select campaign to create SurveyResponses
5. Confirm import

## Environment Variables

Key settings in `.env`:
- `SECRET_KEY` - Django secret key
- `DEBUG` - True/False
- `ALLOWED_HOSTS` - Server hostnames
- `SITE_URL` - Full URL for email links
- `EMAIL_BACKEND` - smtp or filebased
- `EMAIL_HOST`, `EMAIL_PORT`, etc. - SMTP settings

## User Preferences

- Simple/clean formatting
- Reports sorted alphabetically by surname
- Incomplete submissions flagged with `[INCOMPLETE]`
- Faculty can edit surveys until campaign closes
