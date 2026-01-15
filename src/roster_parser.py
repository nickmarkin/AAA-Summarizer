"""
Faculty roster CSV parser.

Parses CSV exports from the Faculty Calculator application
to import faculty into the AAA Summarizer roster.

Expected CSV columns (from Faculty Calculator export):
- last_name
- first_name
- epic_id (ignored)
- email
- department_start_date (ignored)
- clinical_practice_start_date (ignored)
- rank
- contract_type
- division
- salary_grouping (ignored)
- fte (ignored)
- clinical_admin (ignored)
- acgme_required_admin (ignored)
- research_fte (ignored)
- professional_obligation (ignored)
- has_buy_back (ignored)
- buy_back_days (ignored)
- has_non_dept_admin (ignored)
- non_dept_admin_days (ignored)
- notes (ignored)
"""

import csv
from io import StringIO


# Mapping from Faculty Calculator rank values to our choices
RANK_MAPPING = {
    'instructor': 'instructor',
    'assistant professor': 'assistant',
    'assistant': 'assistant',
    'associate professor': 'associate',
    'associate': 'associate',
    'professor': 'professor',
}

# Mapping from Faculty Calculator contract types to our choices
CONTRACT_MAPPING = {
    'academic': 'academic',
    'clinical': 'clinical',
    'early career (yrs 1-3)': 'early_career',
    'early career': 'early_career',
    'early_career': 'early_career',
}


def normalize_rank(rank_value):
    """Convert Faculty Calculator rank to our choice value."""
    if not rank_value:
        return ''
    return RANK_MAPPING.get(rank_value.lower().strip(), '')


def normalize_contract(contract_value):
    """Convert Faculty Calculator contract type to our choice value."""
    if not contract_value:
        return ''
    return CONTRACT_MAPPING.get(contract_value.lower().strip(), '')


def parse_roster_csv(file_input):
    """
    Parse Faculty Calculator CSV export.

    Args:
        file_input: Either a file path (str) or file-like object

    Returns:
        List of dicts with faculty data:
        [
            {
                'email': 'faculty@unmc.edu',
                'first_name': 'John',
                'last_name': 'Smith',
                'rank': 'assistant',  # normalized choice value
                'contract_type': 'clinical',  # normalized choice value
                'division': 'Critical Care',
            },
            ...
        ]

    Raises:
        ValueError: If CSV is missing required columns
    """
    # Read content from file path or file object
    if isinstance(file_input, str):
        with open(file_input, 'r', encoding='utf-8-sig') as f:
            content = f.read()
    else:
        content = file_input.read()
        if isinstance(content, bytes):
            content = content.decode('utf-8-sig')

    reader = csv.DictReader(StringIO(content))

    # Validate required columns exist
    fieldnames = reader.fieldnames or []
    fieldnames_lower = [f.lower().strip() for f in fieldnames]

    # Create mapping from lowercase to actual column names
    col_map = {f.lower().strip(): f for f in fieldnames}

    # Also map space-separated names to underscore versions
    # e.g., "first name" -> maps to same as "first_name"
    for f in fieldnames:
        normalized = f.lower().strip().replace(' ', '_')
        if normalized not in col_map:
            col_map[normalized] = f

    # Check for required columns (case-insensitive, allow spaces or underscores)
    fieldnames_normalized = [f.replace(' ', '_') for f in fieldnames_lower]
    required = ['email', 'first_name', 'last_name']
    missing = [r for r in required if r not in fieldnames_lower and r not in fieldnames_normalized]
    if missing:
        raise ValueError(f"CSV missing required columns: {', '.join(missing)}")

    faculty = []
    for row in reader:
        # Get values using original column names
        email = row.get(col_map.get('email', 'email'), '').lower().strip()
        first_name = row.get(col_map.get('first_name', 'first_name'), '').strip()
        last_name = row.get(col_map.get('last_name', 'last_name'), '').strip()

        # Skip rows without email or name
        if not email or not (first_name and last_name):
            continue

        # Get optional fields
        rank = row.get(col_map.get('rank', 'rank'), '')
        contract_type = row.get(col_map.get('contract_type', 'contract_type'), '')
        division = row.get(col_map.get('division', 'division'), '').strip()
        # Handle both "is_active" and "active" column names
        is_active = row.get(col_map.get('is_active', ''), '') or row.get(col_map.get('active', ''), '')
        is_active = is_active.strip().lower() if is_active else ''
        # Handle both "is_ccc_member" and "ccc member" column names
        is_ccc_member = row.get(col_map.get('is_ccc_member', ''), '') or row.get(col_map.get('ccc_member', ''), '')
        is_ccc_member = is_ccc_member.strip().lower() if is_ccc_member else ''

        faculty.append({
            'email': email,
            'first_name': first_name,
            'last_name': last_name,
            'rank': normalize_rank(rank),
            'contract_type': normalize_contract(contract_type),
            'division': division,
            'is_active': is_active in ('yes', 'true', '1', 'y') if is_active else None,
            'is_ccc_member': is_ccc_member in ('yes', 'true', '1', 'y') if is_ccc_member else None,
        })

    return faculty


def import_roster_to_db(file_input, update_existing=True):
    """
    Parse CSV and import faculty to database.

    Args:
        file_input: File path or file-like object
        update_existing: If True, update existing faculty records.
                        If False, skip existing records.

    Returns:
        Dict with import statistics:
        {
            'created': 5,
            'updated': 10,
            'skipped': 2,
            'errors': [],
        }
    """
    # Import here to avoid circular imports and allow standalone parsing
    from reports_app.models import FacultyMember

    faculty_list = parse_roster_csv(file_input)

    stats = {
        'created': 0,
        'updated': 0,
        'skipped': 0,
        'errors': [],
    }

    for fac_data in faculty_list:
        email = fac_data['email']
        try:
            existing = FacultyMember.objects.filter(email=email).first()

            if existing:
                if update_existing:
                    # Update existing record
                    existing.first_name = fac_data['first_name']
                    existing.last_name = fac_data['last_name']
                    if fac_data['rank']:
                        existing.rank = fac_data['rank']
                    if fac_data['contract_type']:
                        existing.contract_type = fac_data['contract_type']
                    if fac_data['division']:
                        existing.division = fac_data['division']
                    if fac_data.get('is_active') is not None:
                        existing.is_active = fac_data['is_active']
                    if fac_data.get('is_ccc_member') is not None:
                        existing.is_ccc_member = fac_data['is_ccc_member']
                    existing.save()
                    stats['updated'] += 1
                else:
                    stats['skipped'] += 1
            else:
                # Create new record
                FacultyMember.objects.create(
                    email=email,
                    first_name=fac_data['first_name'],
                    last_name=fac_data['last_name'],
                    rank=fac_data['rank'],
                    contract_type=fac_data['contract_type'],
                    division=fac_data['division'],
                    is_active=fac_data.get('is_active', True) if fac_data.get('is_active') is not None else True,
                    is_ccc_member=fac_data.get('is_ccc_member', False) if fac_data.get('is_ccc_member') is not None else False,
                )
                stats['created'] += 1

        except Exception as e:
            stats['errors'].append(f"{email}: {str(e)}")

    return stats
