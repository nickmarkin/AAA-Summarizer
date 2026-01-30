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
- `SurveyConfigOverride` - Year-specific survey configuration (JSON)
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

## Versioning

The app displays a version number in the sidebar footer: `2025 v1.2.30 (build a3f8b2c)`

**Format:** `YEAR vMAJOR.MINOR.DAY_OF_YEAR (build HASH)`
- **Year** - Auto-generated from current year
- **Major/Minor** - Manually controlled, bump for significant changes
- **Day of Year** - Day you made the update (Jan 30 = 30, Feb 15 = 46, etc.)
- **Build hash** - Auto-generated from git commit

**To update the version:**
1. Edit the `VERSION` file in the project root
2. Change to new version (e.g., `1.2.30` for a v1.2 update on day 30)
3. Commit your changes - the git hash updates automatically

**Day of year reference:**
- Jan 30 = day 30
- Feb 15 = day 46
- Mar 1 = day 60 (or 61 in leap year)
- Run `date +%j` in terminal to get today's day of year

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
- `/survey/admin/config/` - Survey configuration management
- `/divisions/` - Division dashboard list
- `/import/` - REDCap CSV import
- `/admin/` - Django admin (for deleting test campaigns, etc.)

**Faculty:**
- `/my/<token>/` - Faculty portal (token-based access)
- `/survey/s/<token>/` - Survey form

### Database Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

## Survey Configuration System

### Year-Based Configs
Each academic year can have its own survey configuration stored in `SurveyConfigOverride`:
- Links to `AcademicYear` via OneToOne relationship
- Stores complete config as JSON (categories, subsections, point values)
- All Q1-Q4 campaigns in a year share the same config
- Years without custom config use defaults from `survey_config.py`

### Key Files
- `survey_app/survey_config.py` - Default config and helper functions
- `survey_app/points_mapping.py` - Maps survey keys to ActivityType.data_variable
- `survey_app/models.py` - `SurveyConfigOverride` model

### Config Functions
```python
get_survey_config_for_year(academic_year)  # Get config for specific year
get_default_config()                        # Get default from survey_config.py
SurveyConfigOverride.copy_to_new_year(source, target)  # Copy config between years
```

### Points System
Point values can come from two sources:
1. **Database** (ActivityType table) - Single source of truth
2. **Fallback defaults** in `points_mapping.py` - Used if DB lookup fails

The `points_mapping.py` maps survey keys (e.g., `'comm_unmc'`) to database variables (e.g., `'CIT_COMMIT_UNMC'`).

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

### Info Buttons
Each survey subsection trigger has an `info_text` field that displays in a popup:
- Explains what qualifies for each activity type
- Shows in both faculty and demo survey templates
- Edit via `survey_config.py` (trigger → info_text field)
- Point values intentionally NOT shown to avoid gaming

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
