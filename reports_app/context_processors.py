"""
Context processors for reports_app.

These add variables to all template contexts automatically.
"""

import subprocess
from pathlib import Path

from django.conf import settings

from .models import AcademicYear


def get_app_version():
    """
    Read version from VERSION file and git commit hash.

    Returns dict with:
    - version: The full version string (e.g., "1.0.30")
    - git_hash: Short git commit hash (e.g., "a3f8b2c")
    - display: Formatted display string (e.g., "v1.0.30 (build a3f8b2c)")
    """
    version = "0.0.0"
    git_hash = None

    # Read VERSION file
    version_file = settings.BASE_DIR / 'VERSION'
    if version_file.exists():
        try:
            version = version_file.read_text().strip()
        except Exception:
            pass

    # Get git commit hash
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            capture_output=True,
            text=True,
            cwd=settings.BASE_DIR,
            timeout=5
        )
        if result.returncode == 0:
            git_hash = result.stdout.strip()
    except Exception:
        pass

    # Build display string with year
    from datetime import datetime
    year = datetime.now().year

    if git_hash:
        display = f"{year} v{version} (build {git_hash})"
    else:
        display = f"{year} v{version}"

    return {
        'version': version,
        'git_hash': git_hash,
        'display': display,
    }


def academic_year_context(request):
    """
    Add academic year information to all templates.

    Provides:
    - academic_years: All academic years (most recent first)
    - current_academic_year: The currently selected year (from session or default)
    """
    # Get all years
    years = AcademicYear.objects.all().order_by('-year_code')

    # Get selected year from session, or use the marked current year
    selected_year_code = request.session.get('selected_academic_year')

    if selected_year_code:
        try:
            selected_year = AcademicYear.objects.get(year_code=selected_year_code)
        except AcademicYear.DoesNotExist:
            selected_year = AcademicYear.get_current()
    else:
        selected_year = AcademicYear.get_current()

    return {
        'academic_years': years,
        'selected_academic_year': selected_year,
        'app_version': get_app_version(),
    }
