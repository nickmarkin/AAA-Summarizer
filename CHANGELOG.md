# Changelog

All notable changes to the Academic Achievement Award Summarizer.

Version format: `MAJOR.MINOR.DAY_OF_YEAR` (e.g., v1.2.30 = version 1.2, updated on day 30 of the year)

---

## v1.2.50 - 2026-02-19

### Security
- DEBUG now defaults to `False` (was `True`) for production safety
- SECRET_KEY no longer has a hardcoded fallback; app fails with helpful error if not set
- Production security headers (HSTS, secure cookies, SSL redirect) auto-enabled when DEBUG=False
- Fixed open redirect vulnerability in academic year selector
- SurveyConfigOverride enforces single active config per academic year via save() override

### Fixed
- Simulation Event (Resident/Fellow) point value corrected from 100 to 150 (matching database)
- Removed stale "needs to be added to DB" comments in points_mapping.py for QA attendance

### Changed
- Access control delegated to department IT (server/network level); Django login not enforced
- Updated CLAUDE.md with deployment notes, security docs, and dev server instructions
- Updated file structure documentation

---

## v1.2.30 - 2026-01-30

### Added
- Version display in sidebar footer showing `YEAR vX.X.XX (build HASH)`
- Database now tracked in git for easier deployment

### Changed
- REDCap data import updated with latest faculty data (Brakke)

### Technical
- Added `VERSION` file for manual version tracking
- Added `get_app_version()` context processor for version display
- Removed `db.sqlite3` from `.gitignore`

---

## v1.1 - 2026-01 (Prior releases)

### Features
- Year-based survey configuration system
- Email setup documentation for IT
- Survey info text entries
- Division verification workflow
- Faculty portal with personal links
- Campaign management with email templates
- REDCap CSV import
- Reports and CSV export

---

## v1.0 - Initial Release

### Features
- Faculty roster management
- Survey campaigns (Q1-Q4)
- Point calculation system
- Division dashboards
- Basic reporting
