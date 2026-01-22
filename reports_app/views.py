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
from django.conf import settings
from .models import (
    AcademicYear,
    FacultyMember,
    SurveyImport,
    FacultySurveyData,
    DepartmentalData,
    ActivityCategory,
    ActivityGoal,
    ActivityType,
    Division,
    DivisionVerification,
    ActivityReview,
    FacultyAnnualReview,
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
    """Home page - dashboard with data overview."""
    if request.method == 'GET' and 'clear' in request.GET:
        request.session.flush()

    has_data = 'faculty_data' in request.session

    # Get selected academic year from context processor
    academic_year = request.session.get('selected_academic_year')
    if academic_year:
        academic_year = AcademicYear.objects.filter(year_code=academic_year).first()
    if not academic_year:
        academic_year = AcademicYear.get_current()

    # Gather statistics for the dashboard
    stats = {
        'total_faculty': FacultyMember.objects.filter(is_active=True).count(),
        'avc_eligible_faculty': FacultyMember.objects.filter(is_active=True, is_avc_eligible=True).count(),
        'faculty_with_data': 0,
        'q1_q2': 0,
        'q3': 0,
        'q4': 0,
        'total_activities': 0,
        'activity_counts': {},
    }

    if academic_year:
        survey_data = FacultySurveyData.objects.filter(academic_year=academic_year)
        stats['faculty_with_data'] = survey_data.count()

        # Count quarters and activities
        for sd in survey_data:
            # Count quarters
            for q in sd.quarters_reported or []:
                if 'Q1' in q or 'Q2' in q:
                    stats['q1_q2'] += 1
                elif 'Q3' in q:
                    stats['q3'] += 1
                elif 'Q4' in q:
                    stats['q4'] += 1

            # Count activities
            activities = sd.activities_json or {}
            for category, subcats in activities.items():
                if category not in stats['activity_counts']:
                    stats['activity_counts'][category] = 0
                for subcat, entries in subcats.items():
                    if isinstance(entries, list):
                        count = len(entries)
                    elif isinstance(entries, dict):
                        count = 1
                    else:
                        count = 0
                    stats['activity_counts'][category] += count
                    stats['total_activities'] += count

    return render(request, 'index.html', {
        'has_data': has_data,
        'stats': stats,
        'academic_year': academic_year,
    })


@require_POST
def toggle_review_mode(request):
    """Toggle review mode for the current academic year."""
    academic_year = AcademicYear.get_current()
    academic_year.review_mode_enabled = not academic_year.review_mode_enabled
    academic_year.save()

    if academic_year.review_mode_enabled:
        messages.success(request, f'Review mode enabled for AY {academic_year.year_code}. Division chiefs can now review and verify faculty activities.')
    else:
        messages.info(request, f'Review mode disabled for AY {academic_year.year_code}.')

    return redirect('index')


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


def select_year(request):
    """Select the academic year to view (stored in session)."""
    year_code = request.GET.get('year') or request.POST.get('year_code')
    if year_code:
        try:
            year = AcademicYear.objects.get(year_code=year_code)
            request.session['selected_academic_year'] = year_code
        except AcademicYear.DoesNotExist:
            messages.error(request, 'Academic year not found.')

    # Redirect back to referring page or home
    referer = request.META.get('HTTP_REFERER', '/')
    return redirect(referer)


def create_year(request):
    """Create a new academic year."""
    from datetime import date
    import re

    if request.method == 'POST':
        year_code = request.POST.get('year_code', '').strip()

        if not year_code or '-' not in year_code:
            messages.error(request, 'Invalid year format. Use format like "24-25" or "2024-2025".')
            return redirect('year_list')

        try:
            # Parse year code - handle both "24-25" and "2024-2025" formats
            parts = year_code.split('-')
            if len(parts) != 2:
                raise ValueError("Invalid format")

            start_part = parts[0].strip()
            end_part = parts[1].strip()

            # Parse start year
            if len(start_part) == 2:
                start_year = 2000 + int(start_part)
            elif len(start_part) == 4:
                start_year = int(start_part)
            else:
                raise ValueError("Invalid start year")

            # Parse end year
            if len(end_part) == 2:
                end_year = 2000 + int(end_part)
            elif len(end_part) == 4:
                end_year = int(end_part)
            else:
                raise ValueError("Invalid end year")

            # Validate sequence
            if end_year != start_year + 1:
                messages.error(request, 'End year must be one year after start year.')
                return redirect('year_list')

            # Create the year
            year, created = AcademicYear.objects.get_or_create(
                year_code=year_code,
                defaults={
                    'start_date': date(start_year, 7, 1),
                    'end_date': date(end_year, 6, 30),
                    'is_current': False,
                }
            )

            if created:
                messages.success(request, f'Created academic year {year}.')
            else:
                messages.info(request, f'Academic year {year} already exists.')

        except ValueError:
            messages.error(request, 'Invalid year format. Use format like "24-25" or "2024-2025".')

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
    contract = request.GET.get('contract', '')
    ccc_only = request.GET.get('ccc', '') == '1'

    if division:
        faculty = faculty.filter(division=division)
    if rank:
        faculty = faculty.filter(rank=rank)
    if contract:
        faculty = faculty.filter(contract_type=contract)
    if ccc_only:
        faculty = faculty.filter(is_ccc_member=True)

    # Get selected academic year
    selected_year_code = request.session.get('selected_academic_year')
    if selected_year_code:
        academic_year = AcademicYear.objects.filter(year_code=selected_year_code).first()
    if not selected_year_code or not academic_year:
        academic_year = AcademicYear.get_current()

    # Get all campaigns for this academic year
    from survey_app.models import SurveyInvitation, SurveyCampaign
    campaigns = SurveyCampaign.objects.filter(
        academic_year=academic_year
    ).order_by('quarter')

    # Build invitation status for each faculty for each campaign
    # Structure: {email: {campaign_id: status}}
    invitation_status = {}
    for campaign in campaigns:
        invitations = SurveyInvitation.objects.filter(
            campaign=campaign
        ).select_related('faculty')
        for inv in invitations:
            if inv.faculty.email not in invitation_status:
                invitation_status[inv.faculty.email] = {}
            invitation_status[inv.faculty.email][campaign.id] = inv.status

    # Check which faculty have survey data (from imports or submissions)
    # Use dict for template compatibility with get_item filter
    faculty_with_data = {
        email: True for email in FacultySurveyData.objects.filter(
            academic_year=academic_year
        ).values_list('faculty__email', flat=True)
    }

    return render(request, 'roster/list.html', {
        'faculty': faculty,
        'division_choices': FacultyMember.DIVISION_CHOICES,
        'rank_choices': FacultyMember.RANK_CHOICES,
        'contract_choices': FacultyMember.CONTRACT_CHOICES,
        'current_division': division,
        'current_rank': rank,
        'current_contract': contract,
        'ccc_only': ccc_only,
        'academic_year': academic_year,
        'campaigns': campaigns,
        'invitation_status': invitation_status,
        'faculty_with_data': faculty_with_data,
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


def faculty_summary(request):
    """
    Faculty Summary view - high-level overview of all faculty points.

    Shows all faculty with their domain points, total, and departmental indicators.
    """
    from survey_app.models import SurveyInvitation

    # Use selected academic year from session
    selected_year_code = request.session.get('selected_academic_year')
    if selected_year_code:
        academic_year = AcademicYear.objects.filter(year_code=selected_year_code).first()
    if not selected_year_code or not academic_year:
        academic_year = AcademicYear.get_current()

    # Get all active faculty
    faculty_list = FacultyMember.objects.filter(is_active=True).order_by('last_name', 'first_name')

    # Get all survey invitations for this year, grouped by faculty
    invitations = SurveyInvitation.objects.filter(
        campaign__academic_year=academic_year
    ).select_related('campaign', 'faculty')

    # Build quarters map: faculty_email -> list of {quarter, status}
    faculty_quarters = {}
    for inv in invitations:
        email = inv.faculty.email
        if email not in faculty_quarters:
            faculty_quarters[email] = []
        faculty_quarters[email].append({
            'quarter': inv.campaign.quarter,
            'status': inv.status,
        })

    # Build summary data for each faculty
    summary_data = []
    for faculty in faculty_list:
        # Get survey data
        survey = FacultySurveyData.objects.filter(
            faculty=faculty, academic_year=academic_year
        ).first()

        # Get departmental data
        dept = DepartmentalData.objects.filter(
            faculty=faculty, academic_year=academic_year
        ).first()

        # Calculate points
        citizenship = survey.citizenship_points if survey else 0
        education = survey.education_points if survey else 0
        research = survey.research_points if survey else 0
        leadership = survey.leadership_points if survey else 0
        content_expert = survey.content_expert_points if survey else 0
        survey_total = citizenship + education + research + leadership + content_expert

        dept_total = dept.departmental_total_points if dept else 0
        grand_total = survey_total + dept_total

        # Check for departmental activities
        has_dept_activities = False
        if dept:
            has_dept_activities = (
                dept.new_innovations or
                dept.mytip_winner or
                dept.mytip_count > 0 or
                dept.teaching_top_25 or
                dept.teaching_65_25 or
                dept.teacher_of_year or
                dept.honorable_mention or
                faculty.is_ccc_member
            )

        # Get quarters info for this faculty
        quarters = faculty_quarters.get(faculty.email, [])
        quarters_submitted = [q for q in quarters if q['status'] == 'submitted']

        summary_data.append({
            'faculty': faculty,
            'citizenship': citizenship,
            'education': education,
            'research': research,
            'leadership': leadership,
            'content_expert': content_expert,
            'survey_total': survey_total,
            'dept_total': dept_total,
            'grand_total': grand_total,
            'has_dept_activities': has_dept_activities,
            'has_survey_data': survey is not None,
            'quarters': quarters,
            'quarters_submitted': len(quarters_submitted),
        })

    # Calculate totals
    total_faculty = len(summary_data)
    faculty_with_data = sum(1 for s in summary_data if s['has_survey_data'])

    return render(request, 'roster/summary.html', {
        'summary_data': summary_data,
        'academic_year': academic_year,
        'total_faculty': total_faculty,
        'faculty_with_data': faculty_with_data,
    })


def faculty_detail(request, email):
    """View faculty member details with full activity breakdown."""
    from src.config import ACTIVITY_CATEGORIES, ACTIVITY_DISPLAY_NAMES

    faculty = get_object_or_404(FacultyMember, email=email)

    # Use selected academic year from session (set by context processor)
    selected_year_code = request.session.get('selected_academic_year')
    if selected_year_code:
        academic_year = AcademicYear.objects.filter(year_code=selected_year_code).first()
    if not selected_year_code or not academic_year:
        academic_year = AcademicYear.get_current()

    # Get survey data for selected year
    survey_data = FacultySurveyData.objects.filter(
        faculty=faculty, academic_year=academic_year
    ).first()

    # Get departmental data for selected year
    dept_data = DepartmentalData.objects.filter(
        faculty=faculty, academic_year=academic_year
    ).first()

    # Get combined activities for display
    # Structure: [{name, total, subcategories: {name: entries}}]
    activity_sections = []
    if survey_data:
        combined = get_combined_activities(survey_data)
        for cat_key, cat_info in ACTIVITY_CATEGORIES.items():
            cat_name = cat_info['name']
            cat_total = 0
            subcategories = {}
            if cat_key in combined:
                for subcat, entries in combined[cat_key].items():
                    if not entries:
                        continue
                    display_name = ACTIVITY_DISPLAY_NAMES.get(subcat, subcat)
                    # Normalize entries to list format for template
                    if isinstance(entries, list) and entries:
                        subcategories[display_name] = entries
                        # Sum points for this subcategory
                        for entry in entries:
                            cat_total += entry.get('points', 0)
                    elif isinstance(entries, dict) and entries:
                        # Handle {trigger, entries} format from survey responses
                        if 'entries' in entries:
                            entry_list = entries.get('entries', [])
                            if entry_list:
                                subcategories[display_name] = entry_list
                                for entry in entry_list:
                                    cat_total += entry.get('points', 0)
                        # Single entry stored as dict - convert to list
                        # Only include if it has meaningful data
                        elif entries.get('points') or entries.get('type') or entries.get('rotations'):
                            subcategories[display_name] = [entries]
                            cat_total += entries.get('points', 0)
            if subcategories:
                activity_sections.append({
                    'name': cat_name,
                    'total': cat_total,
                    'subcategories': subcategories,
                })

    # Calculate totals
    survey_total = 0
    dept_total = 0
    if survey_data:
        survey_total = (
            (survey_data.citizenship_points or 0) +
            (survey_data.education_points or 0) +
            (survey_data.research_points or 0) +
            (survey_data.leadership_points or 0) +
            (survey_data.content_expert_points or 0)
        )
    if dept_data:
        dept_total = dept_data.departmental_total_points
    grand_total = survey_total + dept_total

    # Get current survey invitation (most recent active campaign)
    from survey_app.models import SurveyInvitation, SurveyCampaign
    current_invitation = None
    current_campaign = SurveyCampaign.objects.filter(is_active=True).order_by('-opens_at').first()
    if current_campaign:
        current_invitation = SurveyInvitation.objects.filter(
            campaign=current_campaign,
            faculty=faculty
        ).select_related('campaign').first()

    return render(request, 'roster/detail.html', {
        'faculty': faculty,
        'academic_year': academic_year,
        'survey_data': survey_data,
        'dept_data': dept_data,
        'activity_sections': activity_sections,
        'survey_total': survey_total,
        'dept_total': dept_total,
        'grand_total': grand_total,
        'current_invitation': current_invitation,
        'current_campaign': current_campaign,
    })


def faculty_edit(request, email):
    """Edit faculty member."""
    from .models import Division

    faculty = get_object_or_404(FacultyMember, email=email)

    if request.method == 'POST':
        faculty.first_name = request.POST.get('first_name', faculty.first_name)
        faculty.last_name = request.POST.get('last_name', faculty.last_name)
        faculty.rank = request.POST.get('rank', faculty.rank)
        faculty.contract_type = request.POST.get('contract_type', faculty.contract_type)
        faculty.division = request.POST.get('division', faculty.division)
        faculty.is_active = request.POST.get('is_active') == 'on'
        faculty.is_ccc_member = request.POST.get('is_ccc_member') == 'on'

        # Handle end_date - can be blank to clear it
        end_date_str = request.POST.get('end_date', '').strip()
        if end_date_str:
            from datetime import datetime
            faculty.end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        else:
            faculty.end_date = None

        faculty.save()

        messages.success(request, f'Updated {faculty.display_name}')
        return redirect('faculty_detail', email=email)

    divisions = Division.objects.filter(is_active=True).order_by('name')

    return render(request, 'roster/edit.html', {
        'faculty': faculty,
        'rank_choices': FacultyMember.RANK_CHOICES,
        'contract_choices': FacultyMember.CONTRACT_CHOICES,
        'divisions': divisions,
    })


def faculty_add(request):
    """Add a new faculty member."""
    from .models import Division

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()

        # Validate required fields
        if not email or not first_name or not last_name:
            messages.error(request, 'Email, first name, and last name are required.')
            return redirect('faculty_add')

        # Check if email already exists
        if FacultyMember.objects.filter(email=email).exists():
            messages.error(request, f'A faculty member with email {email} already exists.')
            return redirect('faculty_add')

        # Create new faculty member
        faculty = FacultyMember(
            email=email,
            first_name=first_name,
            last_name=last_name,
            rank=request.POST.get('rank', ''),
            contract_type=request.POST.get('contract_type', ''),
            division=request.POST.get('division', ''),
            is_active=request.POST.get('is_active') == 'on',
            is_ccc_member=request.POST.get('is_ccc_member') == 'on',
        )
        faculty.save()

        messages.success(request, f'Added {faculty.display_name} to the roster.')
        return redirect('faculty_detail', email=email)

    # GET request - show form
    divisions = Division.objects.filter(is_active=True).order_by('name')

    return render(request, 'roster/add.html', {
        'rank_choices': FacultyMember.RANK_CHOICES,
        'contract_choices': FacultyMember.CONTRACT_CHOICES,
        'divisions': divisions,
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
                # Check if record exists to preserve manual activities
                existing = FacultySurveyData.objects.filter(
                    faculty=faculty,
                    academic_year=academic_year,
                ).first()

                # Preserve manual activities if they exist
                manual_activities = {}
                if existing and existing.manual_activities_json:
                    manual_activities = existing.manual_activities_json

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
                        'manual_activities_json': manual_activities,  # Preserve manual entries
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

    return redirect('faculty_summary')


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
        'point_values': DepartmentalData.get_point_values(),
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
        # Handle AVC eligibility (on FacultyMember model, persists across years)
        elif field == 'is_avc_eligible':
            faculty.is_avc_eligible = bool(value)
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
    filter_type = request.GET.get('filter', 'all')

    if year_code:
        academic_year = get_object_or_404(AcademicYear, year_code=year_code)
    else:
        academic_year = AcademicYear.get_current()

    # Get all faculty with data for this year
    survey_queryset = FacultySurveyData.objects.filter(
        academic_year=academic_year
    ).select_related('faculty')

    # Filter by AVC eligibility if requested
    if filter_type == 'avc_eligible':
        survey_queryset = survey_queryset.filter(faculty__is_avc_eligible=True)

    dept_data = {
        d.faculty.email: d
        for d in DepartmentalData.objects.filter(academic_year=academic_year)
    }

    # Build CSV
    lines = ['Name,Email,AVC Eligible,Survey Points,Departmental Points,CCC Points,Total Points']

    for sd in survey_queryset.order_by('faculty__last_name', 'faculty__first_name'):
        faculty = sd.faculty
        dd = dept_data.get(faculty.email)
        dept_points = dd.departmental_total_points if dd else 0
        ccc_points = DepartmentalData.get_point_values()['ccc_member'] if faculty.is_ccc_member else 0
        total = sd.survey_total_points + dept_points + ccc_points
        avc_eligible = 'Yes' if faculty.is_avc_eligible else 'No'

        lines.append(
            f'"{faculty.display_name}",{faculty.email},{avc_eligible},'
            f'{sd.survey_total_points},{dept_points},{ccc_points},{total}'
        )

    csv_content = '\n'.join(lines)
    filename_suffix = '_avc_eligible' if filter_type == 'avc_eligible' else ''
    response = HttpResponse(csv_content, content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="points_summary_{academic_year.year_code}{filename_suffix}.csv"'
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
        ccc_points = DepartmentalData.get_point_values()['ccc_member'] if faculty.is_ccc_member else 0

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
                # Combine imported + manual activities
                combined_activities = get_combined_activities(sd)

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
                    'activities': combined_activities,
                    # Add departmental data
                    'departmental': {
                        'evaluations_points': dd.evaluations_points if dd else 0,
                        'teaching_awards_points': dd.teaching_awards_points if dd else 0,
                        'ccc_points': DepartmentalData.get_point_values()['ccc_member'] if sd.faculty.is_ccc_member else 0,
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

    # Build activity index from all FacultySurveyData records (including manual)
    # Format: {"category.subcategory": [entries with faculty info]}
    activity_index = {}
    survey_data = FacultySurveyData.objects.filter(academic_year=academic_year).select_related('faculty')

    for sd in survey_data:
        # Use combined activities (imported + manual)
        activities = get_combined_activities(sd)
        # activities is {category: {subcategory: [entries]}}
        for category, subcats in activities.items():
            if not isinstance(subcats, dict):
                continue
            for subcategory, entries in subcats.items():
                activity_key = f"{category}.{subcategory}"
                if activity_key not in activity_index:
                    activity_index[activity_key] = []
                # Add faculty info to each activity
                if isinstance(entries, list):
                    for entry in entries:
                        entry_with_faculty = entry.copy() if isinstance(entry, dict) else {'value': entry}
                        entry_with_faculty['faculty_name'] = sd.faculty.display_name
                        entry_with_faculty['faculty_email'] = sd.faculty.email
                        activity_index[activity_key].append(entry_with_faculty)
                elif isinstance(entries, dict) and entries:
                    entry_with_faculty = entries.copy()
                    entry_with_faculty['faculty_name'] = sd.faculty.display_name
                    entry_with_faculty['faculty_email'] = sd.faculty.email
                    activity_index[activity_key].append(entry_with_faculty)

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
        # Build activity index from database (including manual)
        # Format needed: {"category.subcategory": [entries with faculty info]}
        activity_index = {}
        survey_data = FacultySurveyData.objects.filter(academic_year=academic_year).select_related('faculty')

        for sd in survey_data:
            # Use combined activities (imported + manual)
            # Structure is {category: {subcategory: [entries]}}
            activities = get_combined_activities(sd)
            for category, subcats in activities.items():
                if not isinstance(subcats, dict):
                    continue
                for subcategory, entries in subcats.items():
                    activity_key = f"{category}.{subcategory}"
                    if activity_key not in activity_index:
                        activity_index[activity_key] = []
                    if isinstance(entries, list):
                        for entry in entries:
                            entry_with_faculty = entry.copy() if isinstance(entry, dict) else {'value': entry}
                            # Use 'display_name' - this is what reports.py expects
                            entry_with_faculty['display_name'] = sd.faculty.display_name
                            entry_with_faculty['email'] = sd.faculty.email
                            activity_index[activity_key].append(entry_with_faculty)
                    elif isinstance(entries, dict) and entries:
                        entry_with_faculty = entries.copy()
                        entry_with_faculty['display_name'] = sd.faculty.display_name
                        entry_with_faculty['email'] = sd.faculty.email
                        activity_index[activity_key].append(entry_with_faculty)

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


# =============================================================================
# ACTIVITY BROWSE & EDIT
# =============================================================================

def get_combined_activities(survey_data):
    """Merge imported and manual activities for a faculty member."""
    import copy
    combined = copy.deepcopy(survey_data.activities_json or {})
    manual = survey_data.manual_activities_json or {}

    for category, subcats in manual.items():
        if category not in combined:
            combined[category] = {}
        if isinstance(subcats, dict):
            for subcat, entries in subcats.items():
                if subcat not in combined[category]:
                    combined[category][subcat] = []
                if isinstance(entries, list):
                    for entry in entries:
                        entry_copy = entry.copy()
                        entry_copy['source'] = 'manual'
                        combined[category][subcat].append(entry_copy)

    return combined


def activity_category_list(request):
    """Show all activity categories with counts."""
    from src.config import ACTIVITY_CATEGORIES

    year_code = request.GET.get('year', '')
    if year_code:
        academic_year = get_object_or_404(AcademicYear, year_code=year_code)
    else:
        academic_year = AcademicYear.get_current()

    # Get all survey data for this year
    survey_data = FacultySurveyData.objects.filter(academic_year=academic_year)

    # Count activities by category
    category_counts = {}
    for cat_key, cat_info in ACTIVITY_CATEGORIES.items():
        category_counts[cat_key] = {
            'name': cat_info['name'],
            'imported': 0,
            'manual': 0,
            'subcategories': cat_info['subcategories'],
        }

    for sd in survey_data:
        # Count imported activities
        activities = sd.activities_json or {}
        for cat_key in category_counts:
            if cat_key in activities:
                cat_data = activities[cat_key]
                if isinstance(cat_data, dict):
                    for subcat, entries in cat_data.items():
                        if isinstance(entries, list):
                            category_counts[cat_key]['imported'] += len(entries)
                        elif isinstance(entries, dict):
                            # Handle {trigger, entries} format from survey responses
                            if 'entries' in entries:
                                category_counts[cat_key]['imported'] += len(entries.get('entries', []))
                            elif entries:  # Single entry dict
                                category_counts[cat_key]['imported'] += 1

        # Count manual activities
        manual = sd.manual_activities_json or {}
        for cat_key in category_counts:
            if cat_key in manual:
                cat_data = manual[cat_key]
                if isinstance(cat_data, dict):
                    for subcat, entries in cat_data.items():
                        if isinstance(entries, list):
                            category_counts[cat_key]['manual'] += len(entries)

    years = AcademicYear.objects.all()

    return render(request, 'activities/category_list.html', {
        'categories': category_counts,
        'academic_year': academic_year,
        'years': years,
    })


def activity_type_list(request, category):
    """Show subcategories within a category."""
    from src.config import ACTIVITY_CATEGORIES, ACTIVITY_DISPLAY_NAMES

    if category not in ACTIVITY_CATEGORIES:
        messages.error(request, f'Unknown category: {category}')
        return redirect('activity_categories')

    year_code = request.GET.get('year', '')
    if year_code:
        academic_year = get_object_or_404(AcademicYear, year_code=year_code)
    else:
        academic_year = AcademicYear.get_current()

    cat_info = ACTIVITY_CATEGORIES[category]
    survey_data = FacultySurveyData.objects.filter(academic_year=academic_year)

    # Count activities by subcategory
    subcat_counts = {}
    for subcat in cat_info['subcategories']:
        subcat_counts[subcat] = {
            'display_name': ACTIVITY_DISPLAY_NAMES.get(subcat, subcat),
            'entries': 0,
            'faculty_count': 0,
            'faculty_set': set(),
        }

    for sd in survey_data:
        # Count imported
        activities = sd.activities_json or {}
        if category in activities:
            cat_data = activities[category]
            if isinstance(cat_data, dict):
                for subcat, entries in cat_data.items():
                    if subcat in subcat_counts:
                        if isinstance(entries, list):
                            subcat_counts[subcat]['entries'] += len(entries)
                            if entries:
                                subcat_counts[subcat]['faculty_set'].add(sd.faculty.email)
                        elif isinstance(entries, dict):
                            # Handle {trigger, entries} format from survey responses
                            if 'entries' in entries:
                                entry_list = entries.get('entries', [])
                                subcat_counts[subcat]['entries'] += len(entry_list)
                                if entry_list:
                                    subcat_counts[subcat]['faculty_set'].add(sd.faculty.email)
                            elif entries:
                                subcat_counts[subcat]['entries'] += 1
                                subcat_counts[subcat]['faculty_set'].add(sd.faculty.email)

        # Count manual
        manual = sd.manual_activities_json or {}
        if category in manual:
            cat_data = manual[category]
            if isinstance(cat_data, dict):
                for subcat, entries in cat_data.items():
                    if subcat in subcat_counts and isinstance(entries, list):
                        subcat_counts[subcat]['entries'] += len(entries)
                        if entries:
                            subcat_counts[subcat]['faculty_set'].add(sd.faculty.email)

    # Convert faculty sets to counts
    for subcat in subcat_counts:
        subcat_counts[subcat]['faculty_count'] = len(subcat_counts[subcat]['faculty_set'])
        del subcat_counts[subcat]['faculty_set']

    years = AcademicYear.objects.all()

    return render(request, 'activities/type_list.html', {
        'category': category,
        'category_name': cat_info['name'],
        'subcategories': subcat_counts,
        'academic_year': academic_year,
        'years': years,
    })


def activity_role_list(request, category, subcategory):
    """Show roles/types within a subcategory (e.g., Shadow, Visiting Professor)."""
    from src.config import ACTIVITY_CATEGORIES, ACTIVITY_DISPLAY_NAMES

    if category not in ACTIVITY_CATEGORIES:
        messages.error(request, f'Unknown category: {category}')
        return redirect('activity_categories')

    year_code = request.GET.get('year', '')
    if year_code:
        academic_year = get_object_or_404(AcademicYear, year_code=year_code)
    else:
        academic_year = AcademicYear.get_current()

    cat_info = ACTIVITY_CATEGORIES[category]
    survey_data = FacultySurveyData.objects.filter(academic_year=academic_year)

    # Collect unique roles/types and count entries
    role_counts = {}
    for sd in survey_data:
        # Check imported activities
        activities = sd.activities_json or {}
        if category in activities:
            cat_data = activities[category]
            if isinstance(cat_data, dict) and subcategory in cat_data:
                subcat_data = cat_data[subcategory]
                # Handle {trigger, entries} format from survey responses
                if isinstance(subcat_data, dict) and 'entries' in subcat_data:
                    entries = subcat_data.get('entries', [])
                elif isinstance(subcat_data, list):
                    entries = subcat_data
                elif subcat_data:
                    entries = [subcat_data]
                else:
                    entries = []
                for entry in entries:
                    role = entry.get('type') or entry.get('internal_type') or 'Other'
                    if role not in role_counts:
                        role_counts[role] = {'entries': 0, 'faculty_set': set()}
                    role_counts[role]['entries'] += 1
                    role_counts[role]['faculty_set'].add(sd.faculty.email)

        # Check manual activities
        manual = sd.manual_activities_json or {}
        if category in manual:
            cat_data = manual[category]
            if isinstance(cat_data, dict) and subcategory in cat_data:
                subcat_data = cat_data[subcategory]
                entries = subcat_data if isinstance(subcat_data, list) else [subcat_data] if subcat_data else []
                for entry in entries:
                    role = entry.get('type') or entry.get('internal_type') or 'Other'
                    if role not in role_counts:
                        role_counts[role] = {'entries': 0, 'faculty_set': set()}
                    role_counts[role]['entries'] += 1
                    role_counts[role]['faculty_set'].add(sd.faculty.email)

    # Convert sets to counts
    roles = []
    for role_name, data in sorted(role_counts.items()):
        roles.append({
            'name': role_name,
            'entries': data['entries'],
            'faculty_count': len(data['faculty_set']),
        })

    years = AcademicYear.objects.all()
    total_entries = sum(r['entries'] for r in roles)

    return render(request, 'activities/role_list.html', {
        'category': category,
        'category_name': cat_info['name'],
        'subcategory': subcategory,
        'subcategory_name': ACTIVITY_DISPLAY_NAMES.get(subcategory, subcategory),
        'roles': roles,
        'total_entries': total_entries,
        'academic_year': academic_year,
        'years': years,
    })


def activity_entries(request, category, subcategory):
    """Show all entries for an activity type."""
    from src.config import ACTIVITY_CATEGORIES, ACTIVITY_DISPLAY_NAMES

    if category not in ACTIVITY_CATEGORIES:
        messages.error(request, f'Unknown category: {category}')
        return redirect('activity_categories')

    year_code = request.GET.get('year', '')
    if year_code:
        academic_year = get_object_or_404(AcademicYear, year_code=year_code)
    else:
        academic_year = AcademicYear.get_current()

    cat_info = ACTIVITY_CATEGORIES[category]
    survey_data = FacultySurveyData.objects.filter(
        academic_year=academic_year
    ).select_related('faculty')

    # Collect all entries
    entries = []
    for sd in survey_data:
        # Imported entries
        activities = sd.activities_json or {}
        if category in activities:
            cat_data = activities[category]
            if isinstance(cat_data, dict) and subcategory in cat_data:
                subcat_data = cat_data[subcategory]
                if isinstance(subcat_data, list):
                    for i, entry in enumerate(subcat_data):
                        entries.append({
                            'faculty_email': sd.faculty.email,
                            'faculty_name': sd.faculty.display_name,
                            'source': 'REDCap',
                            'index': i,
                            'data': entry,
                        })
                elif isinstance(subcat_data, dict):
                    # Handle {trigger, entries} format from survey responses
                    if 'entries' in subcat_data:
                        for i, entry in enumerate(subcat_data.get('entries', [])):
                            entries.append({
                                'faculty_email': sd.faculty.email,
                                'faculty_name': sd.faculty.display_name,
                                'source': 'REDCap',
                                'index': i,
                                'data': entry,
                            })
                    elif subcat_data:  # Single entry dict
                        entries.append({
                            'faculty_email': sd.faculty.email,
                            'faculty_name': sd.faculty.display_name,
                            'source': 'REDCap',
                            'index': 0,
                            'data': subcat_data,
                        })

        # Manual entries
        manual = sd.manual_activities_json or {}
        if category in manual:
            cat_data = manual[category]
            if isinstance(cat_data, dict) and subcategory in cat_data:
                subcat_data = cat_data[subcategory]
                if isinstance(subcat_data, list):
                    for i, entry in enumerate(subcat_data):
                        entries.append({
                            'faculty_email': sd.faculty.email,
                            'faculty_name': sd.faculty.display_name,
                            'source': 'Manual',
                            'index': i,
                            'data': entry,
                            'editable': True,
                        })

    # Sort by faculty name
    entries.sort(key=lambda x: x['faculty_name'])

    years = AcademicYear.objects.all()

    return render(request, 'activities/entries.html', {
        'category': category,
        'category_name': cat_info['name'],
        'subcategory': subcategory,
        'subcategory_name': ACTIVITY_DISPLAY_NAMES.get(subcategory, subcategory),
        'entries': entries,
        'academic_year': academic_year,
        'years': years,
        'role_filter': None,
    })


def activity_entries_by_role(request, category, subcategory, role):
    """Show entries filtered by a specific role/type."""
    from src.config import ACTIVITY_CATEGORIES, ACTIVITY_DISPLAY_NAMES
    from urllib.parse import unquote

    role = unquote(role)  # URL decode the role name

    if category not in ACTIVITY_CATEGORIES:
        messages.error(request, f'Unknown category: {category}')
        return redirect('activity_categories')

    year_code = request.GET.get('year', '')
    if year_code:
        academic_year = get_object_or_404(AcademicYear, year_code=year_code)
    else:
        academic_year = AcademicYear.get_current()

    cat_info = ACTIVITY_CATEGORIES[category]
    survey_data = FacultySurveyData.objects.filter(
        academic_year=academic_year
    ).select_related('faculty')

    # Collect entries matching the role
    entries = []
    for sd in survey_data:
        # Imported entries
        activities = sd.activities_json or {}
        if category in activities:
            cat_data = activities[category]
            if isinstance(cat_data, dict) and subcategory in cat_data:
                subcat_data = cat_data[subcategory]
                if isinstance(subcat_data, list):
                    for i, entry in enumerate(subcat_data):
                        entry_role = entry.get('type') or entry.get('internal_type') or 'Other'
                        if entry_role == role:
                            entries.append({
                                'faculty_email': sd.faculty.email,
                                'faculty_name': sd.faculty.display_name,
                                'source': 'REDCap',
                                'index': i,
                                'data': entry,
                            })
                elif isinstance(subcat_data, dict):
                    # Handle {trigger, entries} format from survey responses
                    if 'entries' in subcat_data:
                        for i, entry in enumerate(subcat_data.get('entries', [])):
                            entry_role = entry.get('type') or entry.get('internal_type') or 'Other'
                            if entry_role == role:
                                entries.append({
                                    'faculty_email': sd.faculty.email,
                                    'faculty_name': sd.faculty.display_name,
                                    'source': 'REDCap',
                                    'index': i,
                                    'data': entry,
                                })
                    elif subcat_data:
                        entry_role = subcat_data.get('type') or subcat_data.get('internal_type') or 'Other'
                        if entry_role == role:
                            entries.append({
                                'faculty_email': sd.faculty.email,
                                'faculty_name': sd.faculty.display_name,
                                'source': 'REDCap',
                                'index': 0,
                                'data': subcat_data,
                            })

        # Manual entries
        manual = sd.manual_activities_json or {}
        if category in manual:
            cat_data = manual[category]
            if isinstance(cat_data, dict) and subcategory in cat_data:
                subcat_data = cat_data[subcategory]
                if isinstance(subcat_data, list):
                    for i, entry in enumerate(subcat_data):
                        entry_role = entry.get('type') or entry.get('internal_type') or 'Other'
                        if entry_role == role:
                            entries.append({
                                'faculty_email': sd.faculty.email,
                                'faculty_name': sd.faculty.display_name,
                                'source': 'Manual',
                                'index': i,
                                'data': entry,
                                'editable': True,
                            })

    # Sort by faculty name
    entries.sort(key=lambda x: x['faculty_name'])

    years = AcademicYear.objects.all()

    return render(request, 'activities/entries.html', {
        'category': category,
        'category_name': cat_info['name'],
        'subcategory': subcategory,
        'subcategory_name': ACTIVITY_DISPLAY_NAMES.get(subcategory, subcategory),
        'entries': entries,
        'academic_year': academic_year,
        'years': years,
        'role_filter': role,
    })


def all_activities(request):
    """Show all activity entries across all categories."""
    from src.config import ACTIVITY_CATEGORIES, ACTIVITY_DISPLAY_NAMES

    year_code = request.GET.get('year', '')
    if year_code:
        academic_year = get_object_or_404(AcademicYear, year_code=year_code)
    else:
        academic_year = AcademicYear.get_current()

    # Get filter parameters
    category_filter = request.GET.get('category', '')
    source_filter = request.GET.get('source', '')  # 'survey' or 'manual'
    search_query = request.GET.get('q', '').strip().lower()

    survey_data = FacultySurveyData.objects.filter(
        academic_year=academic_year
    ).select_related('faculty')

    # Collect all entries
    entries = []
    for sd in survey_data:
        # Process imported activities
        activities = sd.activities_json or {}
        if source_filter != 'manual':
            for cat_key, cat_data in activities.items():
                if category_filter and cat_key != category_filter:
                    continue
                if not isinstance(cat_data, dict):
                    continue
                cat_name = ACTIVITY_CATEGORIES.get(cat_key, {}).get('name', cat_key)
                for subcat, subcat_data in cat_data.items():
                    subcat_name = ACTIVITY_DISPLAY_NAMES.get(subcat, subcat)
                    # Handle different data formats
                    if isinstance(subcat_data, dict) and 'entries' in subcat_data:
                        entry_list = subcat_data.get('entries', [])
                    elif isinstance(subcat_data, list):
                        entry_list = subcat_data
                    elif subcat_data:
                        entry_list = [subcat_data]
                    else:
                        entry_list = []

                    for entry in entry_list:
                        # Apply search filter
                        if search_query:
                            entry_text = ' '.join(str(v).lower() for v in entry.values() if v)
                            if search_query not in entry_text and search_query not in sd.faculty.display_name.lower():
                                continue
                        entries.append({
                            'faculty_email': sd.faculty.email,
                            'faculty_name': sd.faculty.display_name,
                            'category': cat_key,
                            'category_name': cat_name,
                            'subcategory': subcat,
                            'subcategory_name': subcat_name,
                            'source': 'Survey',
                            'data': entry,
                        })

        # Process manual activities
        manual = sd.manual_activities_json or {}
        if source_filter != 'survey':
            for cat_key, cat_data in manual.items():
                if category_filter and cat_key != category_filter:
                    continue
                if not isinstance(cat_data, dict):
                    continue
                cat_name = ACTIVITY_CATEGORIES.get(cat_key, {}).get('name', cat_key)
                for subcat, subcat_data in cat_data.items():
                    subcat_name = ACTIVITY_DISPLAY_NAMES.get(subcat, subcat)
                    entry_list = subcat_data if isinstance(subcat_data, list) else [subcat_data] if subcat_data else []

                    for entry in entry_list:
                        # Apply search filter
                        if search_query:
                            entry_text = ' '.join(str(v).lower() for v in entry.values() if v)
                            if search_query not in entry_text and search_query not in sd.faculty.display_name.lower():
                                continue
                        entries.append({
                            'faculty_email': sd.faculty.email,
                            'faculty_name': sd.faculty.display_name,
                            'category': cat_key,
                            'category_name': cat_name,
                            'subcategory': subcat,
                            'subcategory_name': subcat_name,
                            'source': 'Manual',
                            'data': entry,
                        })

    # Sort by faculty name, then category
    entries.sort(key=lambda x: (x['faculty_name'], x['category_name'], x['subcategory_name']))

    # Build category choices for filter dropdown
    category_choices = [(k, v['name']) for k, v in ACTIVITY_CATEGORIES.items()]

    years = AcademicYear.objects.all()

    return render(request, 'activities/all_entries.html', {
        'entries': entries,
        'academic_year': academic_year,
        'years': years,
        'category_filter': category_filter,
        'source_filter': source_filter,
        'search_query': request.GET.get('q', ''),
        'category_choices': category_choices,
    })


def faculty_activities(request, email):
    """Show all activities for a single faculty member."""
    from src.config import ACTIVITY_CATEGORIES, ACTIVITY_DISPLAY_NAMES

    faculty = get_object_or_404(FacultyMember, email=email)

    year_code = request.GET.get('year', '')
    if year_code:
        academic_year = get_object_or_404(AcademicYear, year_code=year_code)
    else:
        academic_year = AcademicYear.get_current()

    survey_data = FacultySurveyData.objects.filter(
        faculty=faculty,
        academic_year=academic_year,
    ).first()

    # Build activity summary by category with edit metadata for manual entries
    activity_summary = {}
    if survey_data:
        combined = get_combined_activities(survey_data)
        manual = survey_data.manual_activities_json or {}

        for cat_key, cat_info in ACTIVITY_CATEGORIES.items():
            cat_name = cat_info['name']
            if cat_key in combined:
                activity_summary[cat_name] = {}
                cat_data = combined[cat_key]
                if isinstance(cat_data, dict):
                    for subcat, entries in cat_data.items():
                        subcat_name = ACTIVITY_DISPLAY_NAMES.get(subcat, subcat)
                        if isinstance(entries, list) and entries:
                            # Add metadata for manual entries
                            enriched_entries = []
                            manual_index = 0
                            for entry in entries:
                                entry_copy = entry.copy()
                                if entry.get('source') == 'manual':
                                    entry_copy['category'] = cat_key
                                    entry_copy['subcategory'] = subcat
                                    entry_copy['index'] = manual_index
                                    manual_index += 1
                                enriched_entries.append(entry_copy)
                            activity_summary[cat_name][subcat_name] = enriched_entries
                        elif isinstance(entries, dict) and entries:
                            # Handle {trigger, entries} format from survey responses
                            if 'entries' in entries:
                                enriched_entries = []
                                for entry in entries.get('entries', []):
                                    entry_copy = entry.copy()
                                    enriched_entries.append(entry_copy)
                                if enriched_entries:
                                    activity_summary[cat_name][subcat_name] = enriched_entries
                            else:
                                activity_summary[cat_name][subcat_name] = [entries]

    years = AcademicYear.objects.all()

    return render(request, 'activities/faculty_activities.html', {
        'faculty': faculty,
        'survey_data': survey_data,
        'activity_summary': activity_summary,
        'academic_year': academic_year,
        'years': years,
    })


def add_activity(request, email):
    """Select activity type to add for a faculty member."""
    from src.config import ACTIVITY_CATEGORIES, ACTIVITY_DISPLAY_NAMES

    faculty = get_object_or_404(FacultyMember, email=email)

    year_code = request.GET.get('year', '')
    if year_code:
        academic_year = get_object_or_404(AcademicYear, year_code=year_code)
    else:
        academic_year = AcademicYear.get_current()

    # Build category/subcategory choices
    categories = {}
    for cat_key, cat_info in ACTIVITY_CATEGORIES.items():
        categories[cat_key] = {
            'name': cat_info['name'],
            'subcategories': [
                (subcat, ACTIVITY_DISPLAY_NAMES.get(subcat, subcat))
                for subcat in cat_info['subcategories']
            ]
        }

    return render(request, 'activities/add.html', {
        'faculty': faculty,
        'categories': categories,
        'academic_year': academic_year,
    })


def add_activity_form(request, email, category, subcategory):
    """Form to add a specific activity type."""
    from src.config import ACTIVITY_CATEGORIES, ACTIVITY_DISPLAY_NAMES, REPEATING_FIELD_PATTERNS

    faculty = get_object_or_404(FacultyMember, email=email)

    if category not in ACTIVITY_CATEGORIES:
        messages.error(request, f'Unknown category: {category}')
        return redirect('add_activity', email=email)

    year_code = request.GET.get('year', '')
    if year_code:
        academic_year = get_object_or_404(AcademicYear, year_code=year_code)
    else:
        academic_year = AcademicYear.get_current()

    # Get field definitions for this activity type
    fields = []
    if subcategory in REPEATING_FIELD_PATTERNS:
        pattern = REPEATING_FIELD_PATTERNS[subcategory]
        for field_key, field_label in pattern['fields'].items():
            if field_key != 'points':  # Points will be entered separately
                fields.append({
                    'key': field_key,
                    'label': field_label.replace('#{n}', ''),
                })

    if request.method == 'POST':
        # Get or create survey data
        survey_data, created = FacultySurveyData.objects.get_or_create(
            faculty=faculty,
            academic_year=academic_year,
            defaults={'quarters_reported': []}
        )

        # Build the activity entry
        entry = {
            'source': 'manual',
            'added_at': datetime.now().isoformat(),
        }
        for field in fields:
            entry[field['key']] = request.POST.get(field['key'], '')

        points = request.POST.get('points', '')
        try:
            entry['points'] = int(points) if points else 0
        except ValueError:
            entry['points'] = 0

        # Add to manual_activities_json
        manual = survey_data.manual_activities_json or {}
        if category not in manual:
            manual[category] = {}
        if subcategory not in manual[category]:
            manual[category][subcategory] = []
        manual[category][subcategory].append(entry)

        survey_data.manual_activities_json = manual
        survey_data.save()

        messages.success(request, f'Activity added successfully.')
        return redirect('faculty_activities', email=email)

    return render(request, 'activities/add_form.html', {
        'faculty': faculty,
        'category': category,
        'category_name': ACTIVITY_CATEGORIES[category]['name'],
        'subcategory': subcategory,
        'subcategory_name': ACTIVITY_DISPLAY_NAMES.get(subcategory, subcategory),
        'fields': fields,
        'academic_year': academic_year,
    })


def edit_activity(request, email, category, subcategory, index):
    """Edit a manual activity."""
    from src.config import ACTIVITY_CATEGORIES, ACTIVITY_DISPLAY_NAMES, REPEATING_FIELD_PATTERNS

    faculty = get_object_or_404(FacultyMember, email=email)

    if category not in ACTIVITY_CATEGORIES:
        messages.error(request, f'Unknown category: {category}')
        return redirect('activity_categories')

    year_code = request.GET.get('year', '')
    if year_code:
        academic_year = get_object_or_404(AcademicYear, year_code=year_code)
    else:
        academic_year = AcademicYear.get_current()

    survey_data = FacultySurveyData.objects.filter(
        faculty=faculty,
        academic_year=academic_year,
    ).first()

    if not survey_data:
        messages.error(request, 'No survey data found for this faculty member.')
        return redirect('faculty_activities', email=email)

    # Get the manual activity entry
    manual = survey_data.manual_activities_json or {}
    if category not in manual or subcategory not in manual[category]:
        messages.error(request, 'Activity not found.')
        return redirect('faculty_activities', email=email)

    entries = manual[category][subcategory]
    if not isinstance(entries, list) or index >= len(entries):
        messages.error(request, 'Activity not found.')
        return redirect('faculty_activities', email=email)

    entry = entries[index]

    # Get field definitions
    fields = []
    if subcategory in REPEATING_FIELD_PATTERNS:
        pattern = REPEATING_FIELD_PATTERNS[subcategory]
        for field_key, field_label in pattern['fields'].items():
            if field_key != 'points':
                fields.append({
                    'key': field_key,
                    'label': field_label.replace('#{n}', ''),
                    'value': entry.get(field_key, ''),
                })

    if request.method == 'POST':
        # Update the entry
        for field in fields:
            entry[field['key']] = request.POST.get(field['key'], '')

        points = request.POST.get('points', '')
        try:
            entry['points'] = int(points) if points else 0
        except ValueError:
            entry['points'] = 0

        entry['edited_at'] = datetime.now().isoformat()

        # Save back
        manual[category][subcategory][index] = entry
        survey_data.manual_activities_json = manual
        survey_data.save()

        messages.success(request, 'Activity updated successfully.')
        return redirect('faculty_activities', email=email)

    return render(request, 'activities/edit.html', {
        'faculty': faculty,
        'category': category,
        'category_name': ACTIVITY_CATEGORIES[category]['name'],
        'subcategory': subcategory,
        'subcategory_name': ACTIVITY_DISPLAY_NAMES.get(subcategory, subcategory),
        'fields': fields,
        'entry': entry,
        'index': index,
        'academic_year': academic_year,
    })


@require_POST
def delete_activity(request, email, category, subcategory, index):
    """Delete a manual activity."""
    from src.config import ACTIVITY_CATEGORIES

    faculty = get_object_or_404(FacultyMember, email=email)

    if category not in ACTIVITY_CATEGORIES:
        messages.error(request, f'Unknown category: {category}')
        return redirect('activity_categories')

    year_code = request.POST.get('year_code', '')
    if year_code:
        academic_year = get_object_or_404(AcademicYear, year_code=year_code)
    else:
        academic_year = AcademicYear.get_current()

    survey_data = FacultySurveyData.objects.filter(
        faculty=faculty,
        academic_year=academic_year,
    ).first()

    if not survey_data:
        messages.error(request, 'No survey data found.')
        return redirect('faculty_activities', email=email)

    # Get and modify manual activities
    manual = survey_data.manual_activities_json or {}
    if category not in manual or subcategory not in manual[category]:
        messages.error(request, 'Activity not found.')
        return redirect('faculty_activities', email=email)

    entries = manual[category][subcategory]
    if not isinstance(entries, list) or index >= len(entries):
        messages.error(request, 'Activity not found.')
        return redirect('faculty_activities', email=email)

    # Remove the entry
    del manual[category][subcategory][index]

    # Clean up empty subcategories/categories
    if not manual[category][subcategory]:
        del manual[category][subcategory]
    if not manual[category]:
        del manual[category]

    survey_data.manual_activities_json = manual
    survey_data.save()

    messages.success(request, 'Activity deleted successfully.')
    return redirect('faculty_activities', email=email)


# =============================================================================
# ACTIVITY POINTS CONFIGURATION
# =============================================================================

def activity_points_config(request):
    """Display all activity types organized by category and goal with point values."""
    categories = ActivityCategory.objects.prefetch_related(
        'goals__activity_types'
    ).filter(is_active=True)

    # Build structured data for template
    config_data = []
    for category in categories:
        cat_data = {
            'category': category,
            'goals': [],
            'total_types': 0,
        }
        for goal in category.goals.filter(is_active=True):
            activity_types = goal.activity_types.filter(is_active=True)
            if activity_types.exists():
                cat_data['goals'].append({
                    'goal': goal,
                    'activity_types': activity_types,
                })
                cat_data['total_types'] += activity_types.count()
        config_data.append(cat_data)

    return render(request, 'config/activity_points.html', {
        'config_data': config_data,
        'total_activities': ActivityType.objects.filter(is_active=True).count(),
    })


def activity_type_edit(request, pk):
    """Edit an activity type's point value and settings."""
    activity_type = get_object_or_404(ActivityType, pk=pk)

    if request.method == 'POST':
        # Update fields
        activity_type.display_name = request.POST.get('display_name', activity_type.display_name)
        activity_type.base_points = int(request.POST.get('base_points', activity_type.base_points))
        activity_type.modifier_type = request.POST.get('modifier_type', activity_type.modifier_type)

        max_count = request.POST.get('max_count', '')
        activity_type.max_count = int(max_count) if max_count else None

        max_points = request.POST.get('max_points', '')
        activity_type.max_points = int(max_points) if max_points else None

        activity_type.notes = request.POST.get('notes', '')
        activity_type.is_active = request.POST.get('is_active') == 'on'

        activity_type.save()

        messages.success(request, f'Updated {activity_type.display_name}')
        return redirect('activity_points_config')

    return render(request, 'config/activity_type_edit.html', {
        'activity_type': activity_type,
        'modifier_choices': ActivityType.MODIFIER_CHOICES,
    })


@require_POST
def activity_type_quick_edit(request, pk):
    """Quick inline edit for activity type base points."""
    activity_type = get_object_or_404(ActivityType, pk=pk)

    base_points = request.POST.get('base_points', '')
    if base_points:
        try:
            activity_type.base_points = int(base_points)
            activity_type.save(update_fields=['base_points'])
            messages.success(request, f'Updated {activity_type.display_name} to {base_points} points')
        except ValueError:
            messages.error(request, 'Invalid points value')

    return redirect('activity_points_config')


def activity_type_create(request):
    """Create a new activity type."""
    categories = ActivityCategory.objects.filter(is_active=True).prefetch_related('goals')
    goals = ActivityGoal.objects.filter(is_active=True).select_related('category')

    if request.method == 'POST':
        goal_id = request.POST.get('goal')
        goal = get_object_or_404(ActivityGoal, pk=goal_id)

        data_variable = request.POST.get('data_variable', '').strip()

        # Check for duplicate data_variable
        if ActivityType.objects.filter(data_variable=data_variable).exists():
            messages.error(request, f'Data variable "{data_variable}" already exists.')
            return render(request, 'config/activity_type_create.html', {
                'categories': categories,
                'goals': goals,
                'modifier_choices': ActivityType.MODIFIER_CHOICES,
                'form_data': request.POST,
            })

        max_count = request.POST.get('max_count', '')
        max_points = request.POST.get('max_points', '')

        activity_type = ActivityType.objects.create(
            goal=goal,
            name=request.POST.get('name', '').strip(),
            display_name=request.POST.get('display_name', '').strip(),
            data_variable=data_variable,
            base_points=int(request.POST.get('base_points', 0)),
            modifier_type=request.POST.get('modifier_type', 'fixed'),
            max_count=int(max_count) if max_count else None,
            max_points=int(max_points) if max_points else None,
            notes=request.POST.get('notes', ''),
            is_departmental=request.POST.get('is_departmental') == 'on',
            is_active=True,
        )

        messages.success(request, f'Created activity type: {activity_type.display_name}')
        return redirect('activity_points_config')

    return render(request, 'config/activity_type_create.html', {
        'categories': categories,
        'goals': goals,
        'modifier_choices': ActivityType.MODIFIER_CHOICES,
    })


def verify_impact_factors(request):
    """
    Verify self-reported impact factors against OpenAlex data.

    Looks up DOIs via CrossRef, gets journal metrics from OpenAlex,
    and flags publications where the difference is >= 2.
    """
    from .doi_lookup import verify_all_publications

    # Get verification results
    results = verify_all_publications()

    # Process results for display
    publications = []
    flagged_count = 0
    total_count = len(results)
    successful_lookups = 0

    for r in results:
        if r.get('lookup_success'):
            successful_lookups += 1

        openalex_if = r.get('openalex_citedness')
        reported_if = r.get('reported_if', 0)

        # Calculate difference
        if openalex_if is not None:
            difference = reported_if - openalex_if
            flagged = abs(difference) >= 2
            if flagged:
                flagged_count += 1
        else:
            difference = None
            flagged = False

        publications.append({
            'faculty_name': r.get('faculty_name', ''),
            'faculty_email': r.get('faculty_email', ''),
            'journal_reported': r.get('journal_reported', ''),
            'journal_crossref': r.get('journal_name', ''),
            'title': r.get('pub_title_reported', ''),
            'doi': r.get('doi', ''),
            'reported_if': reported_if,
            'openalex_if': round(openalex_if, 2) if openalex_if else None,
            'difference': round(difference, 2) if difference is not None else None,
            'flagged': flagged,
            'points': r.get('points', 0),
            'lookup_success': r.get('lookup_success', False),
        })

    # Sort flagged first, then by difference magnitude
    publications.sort(key=lambda x: (not x['flagged'], -(abs(x['difference']) if x['difference'] else 0)))

    return render(request, 'reports/verify_if.html', {
        'publications': publications,
        'total_count': total_count,
        'successful_lookups': successful_lookups,
        'flagged_count': flagged_count,
    })


# =============================================================================
# DIVISION MANAGEMENT
# =============================================================================

def divisions_list(request):
    """List all divisions with their chiefs and faculty counts."""
    divisions = Division.objects.all()
    academic_year = AcademicYear.get_current()

    # Enrich with faculty counts, verification status, and faculty list for chief selection
    division_data = []
    for div in divisions:
        faculty = div.get_faculty()
        avc_eligible = div.get_avc_eligible_faculty()
        faculty_count = faculty.count()

        # Get division verification status
        div_verification = DivisionVerification.objects.filter(
            division=div,
            academic_year=academic_year
        ).first()

        # Count faculty with verified annual reviews
        verified_faculty_count = FacultyAnnualReview.objects.filter(
            faculty__in=faculty,
            academic_year=academic_year,
            status='verified'
        ).count()

        # Count faculty with any data (eligible for review)
        faculty_with_data = FacultySurveyData.objects.filter(
            faculty__in=faculty,
            academic_year=academic_year
        ).count()

        division_data.append({
            'division': div,
            'faculty_count': faculty_count,
            'avc_eligible_count': avc_eligible.count(),
            'faculty_list': faculty.order_by('last_name', 'first_name'),
            'verification': div_verification,
            'verified_faculty_count': verified_faculty_count,
            'faculty_with_data': faculty_with_data,
            'all_faculty_verified': faculty_with_data > 0 and verified_faculty_count >= faculty_with_data,
        })

    return render(request, 'reports/divisions_list.html', {
        'divisions': division_data,
        'academic_year': academic_year,
    })


@require_POST
def division_update_chief(request, code):
    """Update the division chief."""
    division = get_object_or_404(Division, code=code)

    chief_email = request.POST.get('chief_email', '').strip()

    if chief_email:
        try:
            chief = FacultyMember.objects.get(email=chief_email)
            division.chief = chief
            messages.success(request, f'{chief.display_name} assigned as {division.name} Division Chief')
        except FacultyMember.DoesNotExist:
            messages.error(request, 'Faculty member not found')
            return redirect('divisions_list')
    else:
        division.chief = None
        messages.info(request, f'{division.name} Division Chief cleared')

    division.save()
    return redirect('divisions_list')


@require_POST
def division_create(request):
    """Create a new division."""
    name = request.POST.get('name', '').strip()
    code = request.POST.get('code', '').strip().lower().replace(' ', '_')

    if not name or not code:
        messages.error(request, 'Division name and code are required')
        return redirect('divisions_list')

    # Check if code already exists
    if Division.objects.filter(code=code).exists():
        messages.error(request, f'Division with code "{code}" already exists')
        return redirect('divisions_list')

    Division.objects.create(code=code, name=name)
    messages.success(request, f'Division "{name}" created')
    return redirect('divisions_list')


@require_POST
def division_edit(request, code):
    """Edit a division's name."""
    division = get_object_or_404(Division, code=code)

    name = request.POST.get('name', '').strip()
    if name:
        division.name = name
        division.save()
        messages.success(request, f'Division renamed to "{name}"')
    else:
        messages.error(request, 'Division name is required')

    return redirect('divisions_list')


@require_POST
def division_delete(request, code):
    """Delete a division."""
    division = get_object_or_404(Division, code=code)

    # Check if any faculty are assigned to this division
    faculty_count = FacultyMember.objects.filter(division=code).count()
    if faculty_count > 0:
        messages.error(request, f'Cannot delete "{division.name}" - {faculty_count} faculty members are assigned to it')
        return redirect('divisions_list')

    name = division.name
    division.delete()
    messages.success(request, f'Division "{name}" deleted')
    return redirect('divisions_list')


# =============================================================================
# COMBINED ANNUAL VIEW
# =============================================================================

def faculty_annual_view(request, email):
    """Combined annual view of all activities for a faculty member."""
    from survey_app.models import SurveyResponse, SurveyInvitation
    from survey_app.survey_config import SURVEY_CATEGORIES, get_carry_forward_subsections

    faculty = get_object_or_404(FacultyMember, email=email)
    academic_year = AcademicYear.get_current()
    academic_year_code = academic_year.year_code

    # Get all survey responses for this faculty in the current academic year
    responses = SurveyResponse.objects.filter(
        invitation__faculty=faculty,
        invitation__campaign__academic_year=academic_year,
    ).select_related('invitation__campaign').order_by('invitation__campaign__quarter')

    # Also get FacultySurveyData (imported/manual data)
    survey_data = FacultySurveyData.objects.filter(
        faculty=faculty,
        academic_year=academic_year
    ).first()

    # Merge all response data and track source quarters
    merged_activities = {}
    quarters_responded = []
    category_points = {
        'citizenship': 0,
        'education': 0,
        'research': 0,
        'leadership': 0,
        'content_expert': 0,
    }

    carry_forward_subs = get_carry_forward_subsections()

    # First, include data from FacultySurveyData (imported/manual activities)
    if survey_data:
        combined = get_combined_activities(survey_data)
        for cat_key, cat_data in combined.items():
            if cat_key not in merged_activities:
                merged_activities[cat_key] = {}

            for sub_key, entries in cat_data.items():
                is_carry_forward = cat_key in carry_forward_subs and sub_key in carry_forward_subs.get(cat_key, [])

                if sub_key not in merged_activities[cat_key]:
                    merged_activities[cat_key][sub_key] = {
                        'entries': [],
                        'is_carry_forward': is_carry_forward,
                    }

                # Handle different entry formats
                if isinstance(entries, dict) and 'entries' in entries:
                    entry_list = entries.get('entries', [])
                elif isinstance(entries, list):
                    entry_list = entries
                elif isinstance(entries, dict):
                    entry_list = [entries] if entries else []
                else:
                    entry_list = []

                for entry in entry_list:
                    if not entry:
                        continue
                    entry_copy = entry.copy() if isinstance(entry, dict) else {'value': entry}
                    if '_source' not in entry_copy:
                        entry_copy['_source'] = 'imported'
                    merged_activities[cat_key][sub_key]['entries'].append(entry_copy)

        # Use points from FacultySurveyData
        category_points['citizenship'] = survey_data.citizenship_points or 0
        category_points['education'] = survey_data.education_points or 0
        category_points['research'] = survey_data.research_points or 0
        category_points['leadership'] = survey_data.leadership_points or 0
        category_points['content_expert'] = survey_data.content_expert_points or 0

    # Then add/merge data from SurveyResponse (web survey data)
    for resp in responses:
        quarter = resp.invitation.campaign.quarter
        quarters_responded.append({
            'quarter': quarter,
            'status': resp.invitation.status,
            'submitted_at': resp.invitation.submitted_at,
            'points': resp.total_points,
        })

        if not resp.response_data:
            continue

        # Process each category
        for cat_key, cat_data in resp.response_data.items():
            if cat_key not in merged_activities:
                merged_activities[cat_key] = {}

            # Process each subsection
            for sub_key, sub_data in cat_data.items():
                if not isinstance(sub_data, dict):
                    continue

                is_carry_forward = cat_key in carry_forward_subs and sub_key in carry_forward_subs.get(cat_key, [])

                # For carry-forward items, only include from first quarter they appear
                if is_carry_forward and sub_key in merged_activities[cat_key]:
                    # Skip if we already have entries from import or earlier quarter
                    if merged_activities[cat_key][sub_key]['entries']:
                        continue

                if sub_key not in merged_activities[cat_key]:
                    merged_activities[cat_key][sub_key] = {
                        'entries': [],
                        'is_carry_forward': is_carry_forward,
                    }

                entries = sub_data.get('entries', [])
                for entry in entries:
                    entry_copy = entry.copy()
                    if '_source_quarter' not in entry_copy:
                        entry_copy['_source_quarter'] = quarter
                    entry_copy['_source'] = 'survey'
                    merged_activities[cat_key][sub_key]['entries'].append(entry_copy)

    # If we have SurveyResponse data, use those points instead (they're more current)
    if responses.exists():
        # Reset and recalculate from survey responses
        survey_points = {
            'citizenship': 0,
            'education': 0,
            'research': 0,
            'leadership': 0,
            'content_expert': 0,
        }
        for resp in responses:
            if resp.invitation.status == 'submitted':
                survey_points['citizenship'] += resp.citizenship_points or 0
                survey_points['education'] += resp.education_points or 0
                survey_points['research'] += resp.research_points or 0
                survey_points['leadership'] += resp.leadership_points or 0
                survey_points['content_expert'] += resp.content_expert_points or 0

        # Use survey points if they have any submitted responses
        if any(v > 0 for v in survey_points.values()):
            category_points = survey_points

    total_points = sum(category_points.values())

    # Get category configs for display names
    category_configs = {}
    for cat_key in ['citizenship', 'education', 'research', 'leadership', 'content_expert']:
        if cat_key in SURVEY_CATEGORIES:
            category_configs[cat_key] = SURVEY_CATEGORIES[cat_key]

    # Check for review mode (division chief viewing)
    # Only allow if review_mode_enabled for the academic year
    review_mode = False
    reviewer_division = None

    if request.GET.get('review') == '1' and academic_year.review_mode_enabled:
        review_mode = True
        # Check if faculty belongs to a division with a chief
        if faculty.division:
            reviewer_division = Division.objects.filter(
                code=faculty.division,
                is_active=True,
                chief__isnull=False
            ).first()

    # Get existing reviews for this faculty/year
    activity_reviews = {}
    if review_mode:
        for review in ActivityReview.objects.filter(
            faculty=faculty,
            academic_year=academic_year
        ):
            key = f"{review.category}|{review.subcategory}|{review.activity_index}"
            activity_reviews[key] = {
                'status': review.status,
                'notes': review.notes,
                'reviewed_at': review.reviewed_at,
            }

    # Get overall annual review
    annual_review = None
    if review_mode:
        annual_review = FacultyAnnualReview.objects.filter(
            faculty=faculty,
            academic_year=academic_year
        ).first()

    return render(request, 'reports/faculty_annual_view.html', {
        'faculty': faculty,
        'academic_year': academic_year,
        'quarters_responded': quarters_responded,
        'merged_activities': merged_activities,
        'category_configs': category_configs,
        'category_points': category_points,
        'total_points': total_points,
        'review_mode': review_mode,
        'reviewer_division': reviewer_division,
        'activity_reviews': activity_reviews,
        'annual_review': annual_review,
    })


def division_dashboard(request, code):
    """
    Division Chief Dashboard - shows faculty summary for a single division.

    Division chiefs can view their division's faculty and their survey responses.
    """
    from survey_app.models import SurveyInvitation

    division = get_object_or_404(Division, code=code)
    academic_year = get_academic_year()

    # Get verification status for this division/year
    verification = DivisionVerification.objects.filter(
        division=division,
        academic_year=academic_year
    ).first()

    # Get faculty in this division
    faculty_list = division.get_faculty().order_by('last_name', 'first_name')

    # Get all survey invitations for this year for division faculty
    invitations = SurveyInvitation.objects.filter(
        campaign__academic_year=academic_year,
        faculty__in=faculty_list
    ).select_related('campaign', 'faculty')

    # Build quarters map
    faculty_quarters = {}
    for inv in invitations:
        email = inv.faculty.email
        if email not in faculty_quarters:
            faculty_quarters[email] = []
        faculty_quarters[email].append({
            'quarter': inv.campaign.quarter,
            'status': inv.status,
        })

    # Build summary data for each faculty
    summary_data = []
    for faculty in faculty_list:
        # Get survey data
        survey = FacultySurveyData.objects.filter(
            faculty=faculty, academic_year=academic_year
        ).first()

        # Get departmental data
        dept = DepartmentalData.objects.filter(
            faculty=faculty, academic_year=academic_year
        ).first()

        # Calculate points
        citizenship = survey.citizenship_points if survey else 0
        education = survey.education_points if survey else 0
        research = survey.research_points if survey else 0
        leadership = survey.leadership_points if survey else 0
        content_expert = survey.content_expert_points if survey else 0
        survey_total = citizenship + education + research + leadership + content_expert

        dept_total = dept.departmental_total_points if dept else 0
        grand_total = survey_total + dept_total

        # Get quarters info
        quarters = faculty_quarters.get(faculty.email, [])
        quarters_submitted = [q for q in quarters if q['status'] == 'submitted']

        # Get review status
        annual_review = FacultyAnnualReview.objects.filter(
            faculty=faculty,
            academic_year=academic_year
        ).first()

        # Count activity reviews
        review_counts = {
            'verified': ActivityReview.objects.filter(
                faculty=faculty, academic_year=academic_year, status='verified'
            ).count(),
            'flagged': ActivityReview.objects.filter(
                faculty=faculty, academic_year=academic_year, status='flagged'
            ).count(),
            'stricken': ActivityReview.objects.filter(
                faculty=faculty, academic_year=academic_year, status='stricken'
            ).count(),
        }

        summary_data.append({
            'faculty': faculty,
            'citizenship': citizenship,
            'education': education,
            'research': research,
            'leadership': leadership,
            'content_expert': content_expert,
            'survey_total': survey_total,
            'dept_total': dept_total,
            'grand_total': grand_total,
            'has_survey_data': survey is not None,
            'quarters': quarters,
            'quarters_submitted': len(quarters_submitted),
            'annual_review': annual_review,
            'review_counts': review_counts,
        })

    # Calculate totals
    total_faculty = len(summary_data)
    faculty_with_data = sum(1 for s in summary_data if s['has_survey_data'])
    avc_eligible_count = sum(1 for s in summary_data if s['faculty'].is_avc_eligible)

    # Check if all faculty with data are verified
    verified_faculty_count = sum(
        1 for s in summary_data
        if s['annual_review'] and s['annual_review'].status == 'verified'
    )
    all_faculty_verified = faculty_with_data > 0 and verified_faculty_count >= faculty_with_data

    return render(request, 'reports/division_dashboard.html', {
        'division': division,
        'summary_data': summary_data,
        'academic_year': academic_year,
        'total_faculty': total_faculty,
        'faculty_with_data': faculty_with_data,
        'avc_eligible_count': avc_eligible_count,
        'verification': verification,
        'verified_faculty_count': verified_faculty_count,
        'all_faculty_verified': all_faculty_verified,
        'review_mode_enabled': academic_year.review_mode_enabled,
    })


def division_verify(request, code):
    """
    Handle division verification - create or remove verification record.

    Division chiefs use this to mark their division's content as verified
    after reviewing the dashboard.
    """
    if request.method != 'POST':
        return redirect('division_dashboard', code=code)

    division = get_object_or_404(Division, code=code)
    academic_year = get_academic_year()
    action = request.POST.get('action')

    if action == 'verify':
        # Create verification record
        # Use the division chief as the verifier, or None if no chief assigned
        DivisionVerification.objects.update_or_create(
            division=division,
            academic_year=academic_year,
            defaults={
                'verified_by': division.chief,
                'notes': request.POST.get('notes', ''),
            }
        )
    elif action == 'unverify':
        # Remove verification record
        DivisionVerification.objects.filter(
            division=division,
            academic_year=academic_year
        ).delete()

    return redirect('division_dashboard', code=code)


@require_POST
def activity_review_action(request, email):
    """
    Handle activity review actions (verify, flag, strike, clear).

    Division chiefs use this to review individual activities or entire submissions.
    """
    faculty = get_object_or_404(FacultyMember, email=email)
    academic_year = AcademicYear.get_current()
    action = request.POST.get('action')

    # Get the division chief (reviewer) - use the division's chief
    reviewer = None
    if faculty.division:
        division = Division.objects.filter(code=faculty.division, is_active=True).first()
        if division:
            reviewer = division.chief

    if action == 'verify_all':
        # Create/update overall annual review as verified
        FacultyAnnualReview.objects.update_or_create(
            faculty=faculty,
            academic_year=academic_year,
            defaults={
                'status': 'verified',
                'reviewed_by': reviewer,
                'notes': '',
            }
        )

    elif action == 'unverify_all':
        # Remove overall verification
        FacultyAnnualReview.objects.filter(
            faculty=faculty,
            academic_year=academic_year
        ).delete()
        # Also clear all individual activity reviews
        ActivityReview.objects.filter(
            faculty=faculty,
            academic_year=academic_year
        ).delete()

    elif action == 'verify_section':
        # Verify all activities in a category/section
        category = request.POST.get('category')
        if category:
            # Get all activities in this category and mark them verified
            # We need to count how many entries exist in this category
            survey_data = FacultySurveyData.objects.filter(
                faculty=faculty,
                academic_year=academic_year
            ).first()

            if survey_data:
                combined = get_combined_activities(survey_data)
                if category in combined:
                    for sub_key, entries in combined[category].items():
                        if isinstance(entries, dict) and 'entries' in entries:
                            entry_list = entries.get('entries', [])
                        elif isinstance(entries, list):
                            entry_list = entries
                        else:
                            entry_list = [entries] if entries else []

                        for idx in range(len(entry_list)):
                            ActivityReview.objects.update_or_create(
                                faculty=faculty,
                                academic_year=academic_year,
                                category=category,
                                subcategory=sub_key,
                                activity_index=idx,
                                defaults={
                                    'status': 'verified',
                                    'reviewed_by': reviewer,
                                    'notes': '',
                                }
                            )

    elif action in ('verify', 'flag', 'strike', 'clear'):
        # Handle individual activity review
        category = request.POST.get('category')
        subcategory = request.POST.get('subcategory')
        activity_index = request.POST.get('activity_index')
        notes = request.POST.get('notes', '')

        if category and subcategory and activity_index is not None:
            try:
                activity_index = int(activity_index)
            except ValueError:
                pass
            else:
                if action == 'clear':
                    # Remove the review
                    ActivityReview.objects.filter(
                        faculty=faculty,
                        academic_year=academic_year,
                        category=category,
                        subcategory=subcategory,
                        activity_index=activity_index,
                    ).delete()
                else:
                    # Map action to status
                    status_map = {
                        'verify': 'verified',
                        'flag': 'flagged',
                        'strike': 'stricken',
                    }
                    status = status_map.get(action)

                    if status:
                        ActivityReview.objects.update_or_create(
                            faculty=faculty,
                            academic_year=academic_year,
                            category=category,
                            subcategory=subcategory,
                            activity_index=activity_index,
                            defaults={
                                'status': status,
                                'reviewed_by': reviewer,
                                'notes': notes,
                            }
                        )

                        # If we have any stricken or flagged items, update annual review status
                        has_issues = ActivityReview.objects.filter(
                            faculty=faculty,
                            academic_year=academic_year,
                            status__in=['stricken', 'flagged']
                        ).exists()

                        if has_issues:
                            FacultyAnnualReview.objects.update_or_create(
                                faculty=faculty,
                                academic_year=academic_year,
                                defaults={
                                    'status': 'has_issues',
                                    'reviewed_by': reviewer,
                                }
                            )

    # Redirect back with review mode enabled
    # Use HTTP_REFERER to preserve scroll position via hash, or fallback to annual view
    referer = request.META.get('HTTP_REFERER', '')
    if referer:
        return redirect(referer)
    return redirect(f"/reports/annual/{email}/?review=1")


def export_portal_links(request):
    """Export all faculty portal links as CSV."""
    import csv
    from django.conf import settings

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="faculty_portal_links.csv"'

    writer = csv.writer(response)
    writer.writerow(['Last Name', 'First Name', 'Email', 'Division', 'Portal URL'])

    # Use SITE_URL from settings (includes subpath if configured)
    site_url = getattr(settings, 'SITE_URL', None)
    if not site_url:
        site_url = request.build_absolute_uri('/')[:-1]

    for faculty in FacultyMember.objects.filter(is_active=True).order_by('last_name', 'first_name'):
        portal_url = f"{site_url}/my/{faculty.access_token}/"
        writer.writerow([
            faculty.last_name,
            faculty.first_name,
            faculty.email,
            faculty.get_division_display() or '',
            portal_url,
        ])

    return response


def export_roster(request):
    """Export full roster as CSV for editing."""
    import csv

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="faculty_roster.csv"'

    writer = csv.writer(response)
    writer.writerow([
        'email',
        'first_name',
        'last_name',
        'rank',
        'contract_type',
        'division',
        'is_active',
        'is_ccc_member'
    ])

    for faculty in FacultyMember.objects.all().order_by('last_name', 'first_name'):
        writer.writerow([
            faculty.email,
            faculty.first_name,
            faculty.last_name,
            faculty.rank or '',
            faculty.contract_type or '',
            faculty.division or '',
            'yes' if faculty.is_active else 'no',
            'yes' if faculty.is_ccc_member else 'no',
        ])

    return response
