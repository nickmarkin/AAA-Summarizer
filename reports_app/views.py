"""
Django views for Academic Achievement Award Summarizer.
"""

import io
import json
import os
import tempfile
import zipfile
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.views.decorators.http import require_http_methods, require_POST
from django.db import transaction

from src import parser, reports, pdf_generator
from src.roster_parser import parse_roster_csv, import_roster_to_db
from .models import (
    AcademicYear,
    FacultyMember,
    SurveyImport,
    FacultySurveyData,
    DepartmentalData,
)


def get_academic_year():
    """
    Determine the academic year based on current date.
    Academic year runs July-June.
    Returns format like '25-26' for 2025-2026 academic year.
    """
    today = datetime.now()
    if today.month >= 7:  # July-December = first half of academic year
        start_year = today.year
    else:  # January-June = second half of academic year
        start_year = today.year - 1

    end_year = start_year + 1
    return f"{start_year % 100:02d}-{end_year % 100:02d}"


def make_faculty_filename(display_name, suffix="Summary"):
    """
    Create filename for faculty export.
    Format: LastName_FirstName_AVC_YY-YY_Summary
    """
    academic_year = get_academic_year()
    safe_name = display_name.replace(', ', '_').replace(' ', '_')
    return f"{safe_name}_AVC_{academic_year}_{suffix}"


def index(request):
    """Home page - upload CSV file."""
    if request.method == 'GET' and 'clear' in request.GET:
        request.session.flush()

    has_data = 'faculty_data' in request.session
    return render(request, 'index.html', {'has_data': has_data})


@require_http_methods(["POST"])
def upload_csv(request):
    """Handle CSV file upload."""
    if 'csv_file' not in request.FILES:
        messages.error(request, 'Please select a CSV file to upload.')
        return redirect('index')

    csv_file = request.FILES['csv_file']

    if not csv_file.name.endswith('.csv'):
        messages.error(request, 'Please upload a CSV file.')
        return redirect('index')

    try:
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as tmp:
            for chunk in csv_file.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name

        data = parser.parse_csv(tmp_path)
        os.unlink(tmp_path)

        faculty_data = {}
        for email, fac in data['faculty'].items():
            fac_copy = fac.copy()
            if 'quarters' in fac_copy and isinstance(fac_copy['quarters'], set):
                fac_copy['quarters'] = list(fac_copy['quarters'])
            faculty_data[email] = fac_copy

        request.session['faculty_data'] = faculty_data
        request.session['activity_index'] = data['activity_index']
        request.session['summary'] = data['summary']

        messages.success(request, f'Loaded {len(faculty_data)} faculty members.')
        return redirect('select_export')

    except Exception as e:
        messages.error(request, f'Error parsing CSV: {str(e)}')
        return redirect('index')


def select_export(request):
    """Select export type."""
    if 'faculty_data' not in request.session:
        messages.warning(request, 'Please upload a CSV file first.')
        return redirect('index')

    summary = request.session.get('summary', {})
    return render(request, 'select_export.html', {'summary': summary})


def export_points(request):
    """Export points summary as CSV."""
    if 'faculty_data' not in request.session:
        messages.warning(request, 'Please upload a CSV file first.')
        return redirect('index')

    faculty_data = request.session['faculty_data']
    csv_content = reports.generate_points_summary_csv(faculty_data)

    response = HttpResponse(csv_content, content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="points_summary.csv"'
    return response


def select_faculty(request):
    """Select faculty members to export."""
    if 'faculty_data' not in request.session:
        messages.warning(request, 'Please upload a CSV file first.')
        return redirect('index')

    faculty_data = request.session['faculty_data']
    faculty_list = parser.get_faculty_list(faculty_data)

    return render(request, 'select_faculty.html', {'faculty_list': faculty_list})


@require_http_methods(["POST"])
def export_faculty(request):
    """Export selected faculty summaries."""
    if 'faculty_data' not in request.session:
        messages.warning(request, 'Please upload a CSV file first.')
        return redirect('index')

    faculty_data = request.session['faculty_data']
    selected_emails = request.POST.getlist('faculty')
    output_format = request.POST.get('format', 'pdf')
    combined = request.POST.get('combined') == 'on'

    if not selected_emails:
        messages.error(request, 'Please select at least one faculty member.')
        return redirect('select_faculty')

    try:
        # Case 1: Single faculty member - always individual file
        if len(selected_emails) == 1:
            email = selected_emails[0]
            fac = faculty_data.get(email)
            if not fac:
                messages.error(request, 'Faculty not found.')
                return redirect('select_faculty')
            md_content = reports.generate_faculty_summary(fac)
            filename = make_faculty_filename(fac['display_name'])

            if output_format == 'md':
                response = HttpResponse(md_content, content_type='text/markdown')
                response['Content-Disposition'] = f'attachment; filename="{filename}.md"'
                return response
            else:
                pdf_bytes = pdf_generator.markdown_to_pdf(md_content)
                if pdf_bytes:
                    response = HttpResponse(pdf_bytes, content_type='application/pdf')
                    response['Content-Disposition'] = f'attachment; filename="{filename}.pdf"'
                    return response
                else:
                    response = HttpResponse(md_content, content_type='text/markdown')
                    response['Content-Disposition'] = f'attachment; filename="{filename}.md"'
                    return response

        # Case 2: Multiple faculty, combined into single document
        elif combined:
            summaries = reports.generate_batch_faculty_summaries(
                faculty_data, selected_emails, combined=True
            )
            md_content = summaries['combined']
            academic_year = get_academic_year()
            filename = f'Faculty_Combined_AVC_{academic_year}_Summary'

            if output_format == 'md':
                response = HttpResponse(md_content, content_type='text/markdown')
                response['Content-Disposition'] = f'attachment; filename="{filename}.md"'
                return response
            else:
                pdf_bytes = pdf_generator.markdown_to_pdf(md_content)
                if pdf_bytes:
                    response = HttpResponse(pdf_bytes, content_type='application/pdf')
                    response['Content-Disposition'] = f'attachment; filename="{filename}.pdf"'
                    return response
                else:
                    response = HttpResponse(md_content, content_type='text/markdown')
                    response['Content-Disposition'] = f'attachment; filename="{filename}.md"'
                    return response

        # Case 3: Multiple faculty, separate files - create ZIP
        else:
            academic_year = get_academic_year()
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for email in selected_emails:
                    fac = faculty_data.get(email)
                    if not fac:
                        continue
                    md_content = reports.generate_faculty_summary(fac)
                    filename = make_faculty_filename(fac['display_name'])

                    if output_format == 'md':
                        zip_file.writestr(f'{filename}.md', md_content)
                    else:
                        pdf_bytes = pdf_generator.markdown_to_pdf(md_content)
                        if pdf_bytes:
                            zip_file.writestr(f'{filename}.pdf', pdf_bytes)
                        else:
                            zip_file.writestr(f'{filename}.md', md_content)

            zip_buffer.seek(0)
            response = HttpResponse(zip_buffer.read(), content_type='application/zip')
            zip_filename = f'Faculty_AVC_{academic_year}_Summaries.zip'
            response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
            return response

    except Exception as e:
        messages.error(request, f'Error generating report: {str(e)}')
        return redirect('select_faculty')


def select_activities(request):
    """Select activity types to export."""
    if 'faculty_data' not in request.session:
        messages.warning(request, 'Please upload a CSV file first.')
        return redirect('index')

    activity_index = request.session.get('activity_index', {})
    activity_types = parser.get_activity_types_with_data(activity_index)

    categories = {}
    for act in activity_types:
        cat = act['category']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(act)

    return render(request, 'select_activities.html', {'categories': categories})


@require_http_methods(["POST"])
def export_activities(request):
    """Export selected activity reports."""
    if 'faculty_data' not in request.session:
        messages.warning(request, 'Please upload a CSV file first.')
        return redirect('index')

    activity_index = request.session.get('activity_index', {})
    selected_types = request.POST.getlist('activities')
    output_format = request.POST.get('format', 'pdf')
    sort_by = request.POST.get('sort', 'faculty')

    if not selected_types:
        messages.error(request, 'Please select at least one activity type.')
        return redirect('select_activities')

    try:
        if len(selected_types) == 1:
            key = selected_types[0]
            entries = activity_index.get(key, [])
            md_content = reports.generate_activity_report(key, entries, sort_by)
            parts = key.split('.')
            filename = f'activity_{parts[-1]}' if len(parts) == 2 else f'activity_{key.replace(".", "_")}'
        else:
            md_content = reports.generate_combined_activity_report(activity_index, selected_types, sort_by)
            filename = 'activities_combined'

        if output_format == 'md':
            response = HttpResponse(md_content, content_type='text/markdown')
            response['Content-Disposition'] = f'attachment; filename="{filename}.md"'
            return response
        else:
            pdf_bytes = pdf_generator.markdown_to_pdf(md_content)
            if pdf_bytes:
                response = HttpResponse(pdf_bytes, content_type='application/pdf')
                response['Content-Disposition'] = f'attachment; filename="{filename}.pdf"'
                return response
            else:
                messages.warning(request, 'PDF generation failed. Downloading as Markdown.')
                response = HttpResponse(md_content, content_type='text/markdown')
                response['Content-Disposition'] = f'attachment; filename="{filename}.md"'
                return response

    except Exception as e:
        messages.error(request, f'Error generating report: {str(e)}')
        return redirect('select_activities')


# =============================================================================
# ACADEMIC YEAR MANAGEMENT
# =============================================================================

def academic_year_list(request):
    """List all academic years."""
    years = AcademicYear.objects.all()
    current_year = AcademicYear.get_current()
    return render(request, 'years/list.html', {
        'years': years,
        'current_year': current_year,
    })


@require_POST
def set_current_year(request):
    """Set the current academic year."""
    year_code = request.POST.get('year_code')
    if year_code:
        try:
            year = AcademicYear.objects.get(year_code=year_code)
            year.is_current = True
            year.save()
            messages.success(request, f'Set {year} as current academic year.')
        except AcademicYear.DoesNotExist:
            messages.error(request, 'Academic year not found.')
    return redirect('year_list')


# =============================================================================
# FACULTY ROSTER MANAGEMENT
# =============================================================================

def faculty_roster(request):
    """Display faculty roster with filters."""
    faculty = FacultyMember.objects.filter(is_active=True)

    # Filters
    division = request.GET.get('division', '')
    rank = request.GET.get('rank', '')
    ccc_only = request.GET.get('ccc', '') == '1'

    if division:
        faculty = faculty.filter(division=division)
    if rank:
        faculty = faculty.filter(rank=rank)
    if ccc_only:
        faculty = faculty.filter(is_ccc_member=True)

    # Get distinct values for filter dropdowns
    divisions = FacultyMember.objects.filter(is_active=True).values_list(
        'division', flat=True
    ).distinct().order_by('division')

    return render(request, 'roster/list.html', {
        'faculty': faculty,
        'divisions': [d for d in divisions if d],
        'rank_choices': FacultyMember.RANK_CHOICES,
        'current_division': division,
        'current_rank': rank,
        'ccc_only': ccc_only,
    })


def import_roster(request):
    """Import faculty roster from CSV."""
    if request.method == 'POST':
        if 'csv_file' not in request.FILES:
            messages.error(request, 'Please select a CSV file.')
            return redirect('import_roster')

        csv_file = request.FILES['csv_file']
        update_existing = request.POST.get('update_existing') == 'on'

        try:
            stats = import_roster_to_db(csv_file, update_existing=update_existing)

            if stats['errors']:
                for error in stats['errors'][:5]:
                    messages.warning(request, error)
                if len(stats['errors']) > 5:
                    messages.warning(request, f"... and {len(stats['errors']) - 5} more errors")

            messages.success(
                request,
                f"Import complete: {stats['created']} created, "
                f"{stats['updated']} updated, {stats['skipped']} skipped."
            )
            return redirect('roster')

        except ValueError as e:
            messages.error(request, str(e))
            return redirect('import_roster')
        except Exception as e:
            messages.error(request, f'Error importing roster: {str(e)}')
            return redirect('import_roster')

    return render(request, 'roster/import.html')


def faculty_detail(request, email):
    """View faculty member details."""
    faculty = get_object_or_404(FacultyMember, email=email)
    current_year = AcademicYear.get_current()

    # Get survey data for current year
    survey_data = FacultySurveyData.objects.filter(
        faculty=faculty, academic_year=current_year
    ).first()

    # Get departmental data for current year
    dept_data = DepartmentalData.objects.filter(
        faculty=faculty, academic_year=current_year
    ).first()

    return render(request, 'roster/detail.html', {
        'faculty': faculty,
        'current_year': current_year,
        'survey_data': survey_data,
        'dept_data': dept_data,
    })


def faculty_edit(request, email):
    """Edit faculty member."""
    faculty = get_object_or_404(FacultyMember, email=email)

    if request.method == 'POST':
        faculty.first_name = request.POST.get('first_name', faculty.first_name)
        faculty.last_name = request.POST.get('last_name', faculty.last_name)
        faculty.rank = request.POST.get('rank', faculty.rank)
        faculty.contract_type = request.POST.get('contract_type', faculty.contract_type)
        faculty.division = request.POST.get('division', faculty.division)
        faculty.is_active = request.POST.get('is_active') == 'on'
        faculty.is_ccc_member = request.POST.get('is_ccc_member') == 'on'
        faculty.save()

        messages.success(request, f'Updated {faculty.display_name}')
        return redirect('faculty_detail', email=email)

    return render(request, 'roster/edit.html', {
        'faculty': faculty,
        'rank_choices': FacultyMember.RANK_CHOICES,
        'contract_choices': FacultyMember.CONTRACT_CHOICES,
    })


@require_POST
def toggle_ccc(request, email):
    """Toggle CCC membership for a faculty member (AJAX)."""
    faculty = get_object_or_404(FacultyMember, email=email)
    faculty.is_ccc_member = not faculty.is_ccc_member
    faculty.save()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'is_ccc_member': faculty.is_ccc_member,
        })

    messages.success(
        request,
        f"{'Added' if faculty.is_ccc_member else 'Removed'} {faculty.display_name} "
        f"{'to' if faculty.is_ccc_member else 'from'} CCC"
    )
    return redirect('roster')


# =============================================================================
# SURVEY IMPORT WITH ROSTER MATCHING
# =============================================================================

def import_survey(request):
    """Upload survey CSV for import to database."""
    if request.method == 'POST':
        if 'csv_file' not in request.FILES:
            messages.error(request, 'Please select a CSV file.')
            return redirect('import_survey')

        csv_file = request.FILES['csv_file']
        year_code = request.POST.get('year_code', '')

        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'Please upload a CSV file.')
            return redirect('import_survey')

        try:
            # Get or create academic year
            if year_code:
                academic_year = AcademicYear.objects.get(year_code=year_code)
            else:
                academic_year = AcademicYear.get_current()

            # Save file temporarily and parse
            with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as tmp:
                for chunk in csv_file.chunks():
                    tmp.write(chunk)
                tmp_path = tmp.name

            data = parser.parse_csv(tmp_path)
            os.unlink(tmp_path)

            # Store in session for review
            faculty_data = {}
            for email, fac in data['faculty'].items():
                fac_copy = fac.copy()
                if 'quarters' in fac_copy and isinstance(fac_copy['quarters'], set):
                    fac_copy['quarters'] = list(fac_copy['quarters'])
                faculty_data[email] = fac_copy

            request.session['import_faculty_data'] = faculty_data
            request.session['import_activity_index'] = data['activity_index']
            request.session['import_summary'] = data['summary']
            request.session['import_year_code'] = academic_year.year_code
            request.session['import_filename'] = csv_file.name

            return redirect('import_review')

        except AcademicYear.DoesNotExist:
            messages.error(request, 'Invalid academic year.')
            return redirect('import_survey')
        except Exception as e:
            messages.error(request, f'Error parsing CSV: {str(e)}')
            return redirect('import_survey')

    # GET request
    years = AcademicYear.objects.all()
    current_year = AcademicYear.get_current()

    return render(request, 'import/upload.html', {
        'years': years,
        'current_year': current_year,
    })


def import_review(request):
    """Review parsed data and roster matching."""
    if 'import_faculty_data' not in request.session:
        messages.warning(request, 'No import data. Please upload a CSV file.')
        return redirect('import_survey')

    faculty_data = request.session['import_faculty_data']
    year_code = request.session['import_year_code']

    # Get roster emails
    roster_emails = set(
        FacultyMember.objects.filter(is_active=True)
        .values_list('email', flat=True)
    )

    matched = []
    unmatched = []

    for email, data in faculty_data.items():
        entry = {
            'email': email,
            'display_name': data.get('display_name', ''),
            'total_points': data.get('totals', {}).get('total', 0),
            'quarters': data.get('quarters_reported', []),
            'has_incomplete': data.get('has_incomplete', False),
        }
        if email.lower() in [e.lower() for e in roster_emails]:
            matched.append(entry)
        else:
            unmatched.append(entry)

    # Sort by name
    matched.sort(key=lambda x: x['display_name'])
    unmatched.sort(key=lambda x: x['display_name'])

    return render(request, 'import/review.html', {
        'matched': matched,
        'unmatched': unmatched,
        'year_code': year_code,
        'filename': request.session.get('import_filename', ''),
        'total_count': len(faculty_data),
    })


@require_POST
def import_confirm(request):
    """Confirm and save import to database."""
    if 'import_faculty_data' not in request.session:
        messages.warning(request, 'No import data.')
        return redirect('import_survey')

    faculty_data = request.session['import_faculty_data']
    year_code = request.session['import_year_code']
    filename = request.session.get('import_filename', 'unknown.csv')

    try:
        academic_year = AcademicYear.objects.get(year_code=year_code)
    except AcademicYear.DoesNotExist:
        messages.error(request, 'Academic year not found.')
        return redirect('import_survey')

    # Get roster emails (case-insensitive lookup)
    roster_lookup = {
        fm.email.lower(): fm
        for fm in FacultyMember.objects.filter(is_active=True)
    }

    matched_count = 0
    unmatched_emails = []

    with transaction.atomic():
        # Create import record
        survey_import = SurveyImport.objects.create(
            academic_year=academic_year,
            filename=filename,
            faculty_count=len(faculty_data),
            activity_count=sum(
                len(fac.get('activities', {}))
                for fac in faculty_data.values()
            ),
        )

        for email, data in faculty_data.items():
            faculty = roster_lookup.get(email.lower())

            if faculty:
                # Update or create survey data
                survey_data, created = FacultySurveyData.objects.update_or_create(
                    faculty=faculty,
                    academic_year=academic_year,
                    defaults={
                        'survey_import': survey_import,
                        'quarters_reported': data.get('quarters_reported', []),
                        'has_incomplete': data.get('has_incomplete', False),
                        'citizenship_points': data.get('totals', {}).get('citizenship', 0),
                        'education_points': data.get('totals', {}).get('education', 0),
                        'research_points': data.get('totals', {}).get('research', 0),
                        'leadership_points': data.get('totals', {}).get('leadership', 0),
                        'content_expert_points': data.get('totals', {}).get('content_expert', 0),
                        'survey_total_points': data.get('totals', {}).get('total', 0),
                        'activities_json': data.get('activities', {}),
                    }
                )
                matched_count += 1

                # Create departmental data record if doesn't exist
                DepartmentalData.objects.get_or_create(
                    faculty=faculty,
                    academic_year=academic_year,
                )
            else:
                unmatched_emails.append(email)

        # Update import record with unmatched
        survey_import.unmatched_emails = unmatched_emails
        survey_import.save()

    # Clear session data
    for key in ['import_faculty_data', 'import_activity_index', 'import_summary',
                'import_year_code', 'import_filename']:
        request.session.pop(key, None)

    if unmatched_emails:
        messages.warning(
            request,
            f"Imported {matched_count} faculty. {len(unmatched_emails)} not in roster."
        )
    else:
        messages.success(request, f'Successfully imported {matched_count} faculty.')

    return redirect('departmental_data')


def import_history(request):
    """View import history."""
    imports = SurveyImport.objects.select_related('academic_year').all()[:50]
    return render(request, 'import/history.html', {'imports': imports})


# =============================================================================
# DEPARTMENTAL DATA ENTRY
# =============================================================================

def departmental_data(request, year_code=None):
    """Departmental data entry form."""
    if year_code:
        academic_year = get_object_or_404(AcademicYear, year_code=year_code)
    else:
        academic_year = AcademicYear.get_current()

    # Get all active faculty with their departmental data
    faculty_list = FacultyMember.objects.filter(is_active=True)

    # Create departmental records if they don't exist
    for faculty in faculty_list:
        DepartmentalData.objects.get_or_create(
            faculty=faculty,
            academic_year=academic_year,
        )

    # Get departmental data with faculty info
    dept_data = DepartmentalData.objects.filter(
        academic_year=academic_year,
        faculty__is_active=True,
    ).select_related('faculty').order_by('faculty__last_name', 'faculty__first_name')

    years = AcademicYear.objects.all()

    return render(request, 'departmental/entry.html', {
        'dept_data': dept_data,
        'academic_year': academic_year,
        'years': years,
        'point_values': DepartmentalData.POINT_VALUES,
    })


@require_POST
def departmental_update(request):
    """Update departmental data (AJAX)."""
    try:
        data = json.loads(request.body)
        email = data.get('email')
        year_code = data.get('year_code')
        field = data.get('field')
        value = data.get('value')

        if not all([email, year_code, field]):
            return JsonResponse({'success': False, 'error': 'Missing required fields'})

        faculty = get_object_or_404(FacultyMember, email=email)
        academic_year = get_object_or_404(AcademicYear, year_code=year_code)

        dept_data, _ = DepartmentalData.objects.get_or_create(
            faculty=faculty,
            academic_year=academic_year,
        )

        # Handle CCC membership (on FacultyMember model, persists across years)
        if field == 'is_ccc_member':
            faculty.is_ccc_member = bool(value)
            faculty.save()
        # Update departmental data fields
        elif field == 'mytip_count':
            value = min(int(value), 20)  # Enforce max
            setattr(dept_data, field, value)
            dept_data.save()
        elif field in ['new_innovations', 'mytip_winner', 'teaching_top_25',
                       'teaching_65_25', 'teacher_of_year', 'honorable_mention']:
            value = bool(value)
            setattr(dept_data, field, value)
            dept_data.save()

        return JsonResponse({
            'success': True,
            'evaluations_points': dept_data.evaluations_points,
            'teaching_awards_points': dept_data.teaching_awards_points,
            'departmental_total_points': dept_data.departmental_total_points,
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# =============================================================================
# DATABASE-BACKED REPORTS
# =============================================================================

def reports_dashboard(request):
    """Reports dashboard."""
    current_year = AcademicYear.get_current()
    years = AcademicYear.objects.all()

    # Get counts for current year
    faculty_count = FacultySurveyData.objects.filter(
        academic_year=current_year
    ).count()

    return render(request, 'reports/dashboard.html', {
        'current_year': current_year,
        'years': years,
        'faculty_count': faculty_count,
    })


def db_export_points(request):
    """Export points summary from database."""
    year_code = request.GET.get('year', '')
    if year_code:
        academic_year = get_object_or_404(AcademicYear, year_code=year_code)
    else:
        academic_year = AcademicYear.get_current()

    # Get all faculty with data for this year
    survey_data = FacultySurveyData.objects.filter(
        academic_year=academic_year
    ).select_related('faculty')

    dept_data = {
        d.faculty.email: d
        for d in DepartmentalData.objects.filter(academic_year=academic_year)
    }

    # Build CSV
    lines = ['Name,Email,Survey Points,Departmental Points,CCC Points,Total Points']

    for sd in survey_data.order_by('faculty__last_name', 'faculty__first_name'):
        faculty = sd.faculty
        dd = dept_data.get(faculty.email)
        dept_points = dd.departmental_total_points if dd else 0
        ccc_points = DepartmentalData.POINT_VALUES['ccc_member'] if faculty.is_ccc_member else 0
        total = sd.survey_total_points + dept_points + ccc_points

        lines.append(
            f'"{faculty.display_name}",{faculty.email},'
            f'{sd.survey_total_points},{dept_points},{ccc_points},{total}'
        )

    csv_content = '\n'.join(lines)
    response = HttpResponse(csv_content, content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="points_summary_{academic_year.year_code}.csv"'
    return response


def db_select_faculty(request):
    """Select faculty for export from database."""
    year_code = request.GET.get('year', '')
    if year_code:
        academic_year = get_object_or_404(AcademicYear, year_code=year_code)
    else:
        academic_year = AcademicYear.get_current()

    # Get faculty with survey data
    survey_data = FacultySurveyData.objects.filter(
        academic_year=academic_year
    ).select_related('faculty').order_by('faculty__last_name', 'faculty__first_name')

    dept_data = {
        d.faculty.email: d
        for d in DepartmentalData.objects.filter(academic_year=academic_year)
    }

    faculty_list = []
    for sd in survey_data:
        faculty = sd.faculty
        dd = dept_data.get(faculty.email)
        dept_points = dd.departmental_total_points if dd else 0
        ccc_points = DepartmentalData.POINT_VALUES['ccc_member'] if faculty.is_ccc_member else 0

        faculty_list.append({
            'email': faculty.email,
            'display_name': faculty.display_name,
            'survey_points': sd.survey_total_points,
            'dept_points': dept_points,
            'ccc_points': ccc_points,
            'total_points': sd.survey_total_points + dept_points + ccc_points,
            'has_incomplete': sd.has_incomplete,
            'quarters': sd.quarters_reported,
        })

    years = AcademicYear.objects.all()

    return render(request, 'reports/select_faculty.html', {
        'faculty_list': faculty_list,
        'academic_year': academic_year,
        'years': years,
    })


@require_POST
def db_export_faculty(request):
    """Export faculty summaries from database."""
    year_code = request.POST.get('year_code', '')
    if year_code:
        academic_year = get_object_or_404(AcademicYear, year_code=year_code)
    else:
        academic_year = AcademicYear.get_current()

    selected_emails = request.POST.getlist('faculty')
    output_format = request.POST.get('format', 'pdf')
    combined = request.POST.get('combined') == 'on'

    if not selected_emails:
        messages.error(request, 'Please select at least one faculty member.')
        return redirect('db_select_faculty')

    try:
        # Build faculty data dict from database
        faculty_data = {}
        for email in selected_emails:
            sd = FacultySurveyData.objects.filter(
                faculty__email=email,
                academic_year=academic_year,
            ).select_related('faculty').first()

            if sd:
                dd = DepartmentalData.objects.filter(
                    faculty=sd.faculty,
                    academic_year=academic_year,
                ).first()

                # Reconstruct data structure for report generator
                faculty_data[email] = {
                    'email': email,
                    'display_name': sd.faculty.display_name,
                    'first_name': sd.faculty.first_name,
                    'last_name': sd.faculty.last_name,
                    'quarters_reported': sd.quarters_reported,
                    'has_incomplete': sd.has_incomplete,
                    'total_points': sd.survey_total_points,
                    'totals': {
                        'citizenship': sd.citizenship_points,
                        'education': sd.education_points,
                        'research': sd.research_points,
                        'leadership': sd.leadership_points,
                        'content_expert': sd.content_expert_points,
                    },
                    'activities': sd.activities_json,
                    # Add departmental data
                    'departmental': {
                        'evaluations_points': dd.evaluations_points if dd else 0,
                        'teaching_awards_points': dd.teaching_awards_points if dd else 0,
                        'ccc_points': DepartmentalData.POINT_VALUES['ccc_member'] if sd.faculty.is_ccc_member else 0,
                    } if dd else {},
                }

        if not faculty_data:
            messages.error(request, 'No data found for selected faculty.')
            return redirect('db_select_faculty')

        # Generate reports using existing report generator
        if len(selected_emails) == 1:
            email = selected_emails[0]
            fac = faculty_data[email]
            md_content = reports.generate_faculty_summary(fac)
            filename = make_faculty_filename(fac['display_name'])

            if output_format == 'md':
                response = HttpResponse(md_content, content_type='text/markdown')
                response['Content-Disposition'] = f'attachment; filename="{filename}.md"'
                return response
            else:
                pdf_bytes = pdf_generator.markdown_to_pdf(md_content)
                if pdf_bytes:
                    response = HttpResponse(pdf_bytes, content_type='application/pdf')
                    response['Content-Disposition'] = f'attachment; filename="{filename}.pdf"'
                    return response
                else:
                    response = HttpResponse(md_content, content_type='text/markdown')
                    response['Content-Disposition'] = f'attachment; filename="{filename}.md"'
                    return response

        elif combined:
            summaries = reports.generate_batch_faculty_summaries(
                faculty_data, selected_emails, combined=True
            )
            md_content = summaries['combined']
            filename = f'Faculty_Combined_AVC_{academic_year.year_code}_Summary'

            if output_format == 'md':
                response = HttpResponse(md_content, content_type='text/markdown')
                response['Content-Disposition'] = f'attachment; filename="{filename}.md"'
                return response
            else:
                pdf_bytes = pdf_generator.markdown_to_pdf(md_content)
                if pdf_bytes:
                    response = HttpResponse(pdf_bytes, content_type='application/pdf')
                    response['Content-Disposition'] = f'attachment; filename="{filename}.pdf"'
                    return response
                else:
                    response = HttpResponse(md_content, content_type='text/markdown')
                    response['Content-Disposition'] = f'attachment; filename="{filename}.md"'
                    return response

        else:
            # Multiple separate files - ZIP
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for email in selected_emails:
                    fac = faculty_data.get(email)
                    if not fac:
                        continue
                    md_content = reports.generate_faculty_summary(fac)
                    filename = make_faculty_filename(fac['display_name'])

                    if output_format == 'md':
                        zip_file.writestr(f'{filename}.md', md_content)
                    else:
                        pdf_bytes = pdf_generator.markdown_to_pdf(md_content)
                        if pdf_bytes:
                            zip_file.writestr(f'{filename}.pdf', pdf_bytes)
                        else:
                            zip_file.writestr(f'{filename}.md', md_content)

            zip_buffer.seek(0)
            response = HttpResponse(zip_buffer.read(), content_type='application/zip')
            zip_filename = f'Faculty_AVC_{academic_year.year_code}_Summaries.zip'
            response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
            return response

    except Exception as e:
        messages.error(request, f'Error generating report: {str(e)}')
        return redirect('db_select_faculty')


def db_select_activities(request):
    """Select activity types to export from database."""
    year_code = request.GET.get('year', '')
    if year_code:
        academic_year = get_object_or_404(AcademicYear, year_code=year_code)
    else:
        academic_year = AcademicYear.get_current()

    # Build activity index from all FacultySurveyData records
    activity_index = {}
    survey_data = FacultySurveyData.objects.filter(academic_year=academic_year)

    for sd in survey_data:
        activities = sd.activities_json or {}
        for activity_key, activity_list in activities.items():
            if activity_key not in activity_index:
                activity_index[activity_key] = []
            # Add faculty info to each activity
            for activity in activity_list:
                activity_with_faculty = activity.copy()
                activity_with_faculty['faculty_name'] = sd.faculty.display_name
                activity_with_faculty['faculty_email'] = sd.faculty.email
                activity_index[activity_key].append(activity_with_faculty)

    # Get activity types with data
    activity_types = parser.get_activity_types_with_data(activity_index)

    # Group by category
    categories = {}
    for act in activity_types:
        cat = act['category']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(act)

    years = AcademicYear.objects.all()

    return render(request, 'reports/select_activities.html', {
        'categories': categories,
        'academic_year': academic_year,
        'years': years,
    })


@require_POST
def db_export_activities(request):
    """Export selected activity reports from database."""
    year_code = request.POST.get('year_code', '')
    if year_code:
        academic_year = get_object_or_404(AcademicYear, year_code=year_code)
    else:
        academic_year = AcademicYear.get_current()

    selected_types = request.POST.getlist('activities')
    output_format = request.POST.get('format', 'pdf')
    sort_by = request.POST.get('sort', 'faculty')

    if not selected_types:
        messages.error(request, 'Please select at least one activity type.')
        return redirect('db_select_activities')

    try:
        # Build activity index from database
        activity_index = {}
        survey_data = FacultySurveyData.objects.filter(academic_year=academic_year)

        for sd in survey_data:
            activities = sd.activities_json or {}
            for activity_key, activity_list in activities.items():
                if activity_key not in activity_index:
                    activity_index[activity_key] = []
                for activity in activity_list:
                    activity_with_faculty = activity.copy()
                    activity_with_faculty['faculty_name'] = sd.faculty.display_name
                    activity_with_faculty['faculty_email'] = sd.faculty.email
                    activity_index[activity_key].append(activity_with_faculty)

        # Generate combined activity report
        md_content = reports.generate_combined_activity_report(activity_index, selected_types, sort_by)
        filename = f'activities_AY_{academic_year.year_code}'

        if output_format == 'md':
            response = HttpResponse(md_content, content_type='text/markdown')
            response['Content-Disposition'] = f'attachment; filename="{filename}.md"'
            return response
        else:
            pdf_bytes = pdf_generator.markdown_to_pdf(md_content)
            if pdf_bytes:
                response = HttpResponse(pdf_bytes, content_type='application/pdf')
                response['Content-Disposition'] = f'attachment; filename="{filename}.pdf"'
                return response
            else:
                messages.warning(request, 'PDF generation failed. Downloading as Markdown.')
                response = HttpResponse(md_content, content_type='text/markdown')
                response['Content-Disposition'] = f'attachment; filename="{filename}.md"'
                return response

    except Exception as e:
        messages.error(request, f'Error generating report: {str(e)}')
        return redirect('db_select_activities')
