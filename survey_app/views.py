"""
Views for the Survey feature.

Admin views for campaign management and faculty views for survey completion.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, Http404
from django.utils import timezone
from django.db import transaction
from django.views.decorators.http import require_POST, require_GET

from reports_app.models import AcademicYear, FacultyMember
from .models import SurveyCampaign, SurveyInvitation, SurveyResponse, EmailLog
from .survey_config import (
    get_category_config, calculate_category_points,
    get_next_category, get_prev_category, CATEGORY_ORDER, CATEGORY_NAMES,
    get_carry_forward_subsections, extract_carry_forward_data
)


# =============================================================================
# ADMIN VIEWS - Campaign Management
# =============================================================================

def campaign_list(request):
    """List all survey campaigns with status and statistics."""
    campaigns = SurveyCampaign.objects.select_related('academic_year').all()

    # Get current academic year for "create new" default
    current_year = AcademicYear.get_current()

    context = {
        'campaigns': campaigns,
        'current_year': current_year,
    }
    return render(request, 'survey/admin/campaign_list.html', context)


def campaign_create(request):
    """Create a new survey campaign."""
    if request.method == 'POST':
        # Get form data
        year_code = request.POST.get('academic_year')
        quarter = request.POST.get('quarter')
        name = request.POST.get('name')
        opens_at = request.POST.get('opens_at')
        closes_at = request.POST.get('closes_at')

        # Validate
        errors = []
        if not year_code:
            errors.append('Academic year is required')
        if not quarter:
            errors.append('Quarter is required')
        if not opens_at:
            errors.append('Open date is required')
        if not closes_at:
            errors.append('Close date is required')

        # Check for existing campaign
        if year_code and quarter:
            if SurveyCampaign.objects.filter(
                academic_year_id=year_code,
                quarter=quarter
            ).exists():
                errors.append(f'A campaign for {quarter} already exists for this academic year')

        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            # Create the campaign
            academic_year = get_object_or_404(AcademicYear, year_code=year_code)

            # Auto-generate name if not provided
            if not name:
                name = f"AY {year_code} {quarter} Survey"

            campaign = SurveyCampaign.objects.create(
                academic_year=academic_year,
                quarter=quarter,
                name=name,
                opens_at=opens_at,
                closes_at=closes_at,
            )

            # Create invitations for all active faculty
            active_faculty = FacultyMember.objects.filter(is_active=True)
            invitations = [
                SurveyInvitation(campaign=campaign, faculty=faculty)
                for faculty in active_faculty
            ]
            SurveyInvitation.objects.bulk_create(invitations)

            messages.success(
                request,
                f'Campaign "{campaign.name}" created with {len(invitations)} invitations'
            )
            return redirect('survey:campaign_detail', pk=campaign.pk)

    # GET request - show form
    academic_years = AcademicYear.objects.all()
    current_year = AcademicYear.get_current()

    context = {
        'academic_years': academic_years,
        'current_year': current_year,
        'quarter_choices': SurveyCampaign.QUARTER_CHOICES,
    }
    return render(request, 'survey/admin/campaign_create.html', context)


def campaign_detail(request, pk):
    """View campaign details, invitations, and statistics."""
    campaign = get_object_or_404(
        SurveyCampaign.objects.select_related('academic_year'),
        pk=pk
    )

    # Get invitations with faculty info
    invitations = campaign.invitations.select_related('faculty').all()

    # Group by status
    pending = invitations.filter(status='pending')
    in_progress = invitations.filter(status='in_progress')
    submitted = invitations.filter(status='submitted')

    # Get all active faculty for management section
    all_faculty = FacultyMember.objects.filter(is_active=True).order_by('last_name', 'first_name')
    invited_emails = set(invitations.values_list('faculty__email', flat=True))

    context = {
        'campaign': campaign,
        'invitations': invitations,
        'pending': pending,
        'in_progress': in_progress,
        'submitted': submitted,
        'stats': campaign.submission_stats,
        'all_faculty': all_faculty,
        'invited_emails': invited_emails,
    }
    return render(request, 'survey/admin/campaign_detail.html', context)


def campaign_edit(request, pk):
    """Edit campaign settings."""
    campaign = get_object_or_404(SurveyCampaign, pk=pk)

    if request.method == 'POST':
        campaign.name = request.POST.get('name', campaign.name)
        campaign.opens_at = request.POST.get('opens_at', campaign.opens_at)
        campaign.closes_at = request.POST.get('closes_at', campaign.closes_at)
        campaign.is_active = request.POST.get('is_active') == 'on'

        # Email customization
        campaign.email_from_name = request.POST.get('email_from_name', '').strip()
        campaign.email_from_address = request.POST.get('email_from_address', '').strip()
        campaign.email_subject = request.POST.get('email_subject', '').strip()
        campaign.email_body = request.POST.get('email_body', '').strip()

        campaign.save()

        messages.success(request, 'Campaign updated successfully')
        return redirect('survey:campaign_detail', pk=campaign.pk)

    context = {
        'campaign': campaign,
    }
    return render(request, 'survey/admin/campaign_edit.html', context)


@require_POST
def campaign_update_faculty(request, pk):
    """Update which faculty are included in a campaign."""
    campaign = get_object_or_404(SurveyCampaign, pk=pk)

    # Get selected faculty emails from form
    selected_emails = set(request.POST.getlist('faculty'))

    # Get current invitations
    current_invitations = {
        inv.faculty.email: inv
        for inv in campaign.invitations.select_related('faculty')
    }
    current_emails = set(current_invitations.keys())

    # Determine additions and removals
    to_add = selected_emails - current_emails
    to_remove = current_emails - selected_emails

    added_count = 0
    removed_count = 0
    skipped_count = 0

    # Add new invitations
    for email in to_add:
        faculty = FacultyMember.objects.filter(email=email).first()
        if faculty:
            SurveyInvitation.objects.create(campaign=campaign, faculty=faculty)
            added_count += 1

    # Remove invitations (only if not submitted or in progress with data)
    for email in to_remove:
        inv = current_invitations.get(email)
        if inv:
            # Don't remove submitted surveys
            if inv.status == 'submitted':
                skipped_count += 1
                continue
            # Don't remove in-progress surveys that have response data
            if inv.status == 'in_progress' and hasattr(inv, 'response'):
                skipped_count += 1
                continue
            inv.delete()
            removed_count += 1

    # Build feedback message
    msg_parts = []
    if added_count:
        msg_parts.append(f'{added_count} added')
    if removed_count:
        msg_parts.append(f'{removed_count} removed')
    if skipped_count:
        msg_parts.append(f'{skipped_count} kept (have data)')

    if msg_parts:
        messages.success(request, 'Faculty updated: ' + ', '.join(msg_parts))
    else:
        messages.info(request, 'No changes made')

    return redirect('survey:campaign_detail', pk=pk)


def campaign_send_invitations(request, pk):
    """Send invitation emails to all pending faculty or a single faculty."""
    campaign = get_object_or_404(SurveyCampaign, pk=pk)
    redirect_url = request.META.get('HTTP_REFERER', None)

    if request.method == 'POST':
        # Check for single faculty resend
        single_faculty_email = request.POST.get('single_faculty')

        if single_faculty_email:
            # Send to single faculty (resend)
            invitation = campaign.invitations.filter(faculty__email=single_faculty_email).first()
            if invitation:
                success = _send_invitation_email(invitation)
                if success:
                    messages.success(request, f'Invitation email sent to {invitation.faculty.display_name}')
                else:
                    messages.error(request, f'Failed to send email to {invitation.faculty.display_name}')
            else:
                messages.error(request, 'Faculty not found in this campaign')

            # Redirect back to where we came from (faculty detail page)
            if redirect_url:
                return redirect(redirect_url)
        else:
            # Send to all pending
            pending = campaign.invitations.filter(email_sent_at__isnull=True)
            pending_count = pending.count()

            if pending_count == 0:
                messages.info(request, 'No pending invitations to send. All faculty have already been emailed.')
            else:
                sent_count = 0
                failed_count = 0

                for invitation in pending:
                    success = _send_invitation_email(invitation)
                    if success:
                        sent_count += 1
                    else:
                        failed_count += 1

                if sent_count > 0:
                    messages.success(request, f'Sent {sent_count} invitation emails')
                if failed_count > 0:
                    messages.warning(request, f'{failed_count} emails failed to send')

    return redirect('survey:campaign_detail', pk=pk)


def campaign_send_reminders(request, pk):
    """Send reminder emails to non-submitted faculty."""
    campaign = get_object_or_404(SurveyCampaign, pk=pk)

    if request.method == 'POST':
        # Get invitations that are not submitted
        not_submitted = campaign.invitations.exclude(status='submitted')

        sent_count = 0
        failed_count = 0

        for invitation in not_submitted:
            success = _send_reminder_email(invitation)
            if success:
                sent_count += 1
            else:
                failed_count += 1

        if sent_count > 0:
            messages.success(request, f'Sent {sent_count} reminder emails')
        if failed_count > 0:
            messages.warning(request, f'{failed_count} emails failed to send')

    return redirect('survey:campaign_detail', pk=pk)


@require_POST
def invitation_unlock(request, pk):
    """Unlock a submitted survey to allow editing."""
    invitation = get_object_or_404(SurveyInvitation.objects.select_related('response'), pk=pk)

    if invitation.status != 'submitted':
        messages.warning(request, 'This survey is not submitted, no need to unlock')
    else:
        invitation.status = 'in_progress'
        invitation.submitted_at = None
        invitation.save()

        # Log the unlock for audit trail
        if hasattr(invitation, 'response'):
            from .models import SurveyResponseHistory
            SurveyResponseHistory.log_change(
                response=invitation.response,
                action='unlock',
                request=request
            )

        messages.success(
            request,
            f'Survey unlocked for {invitation.faculty.display_name}. '
            f'They can now edit using their original link.'
        )

    return redirect('survey:campaign_detail', pk=invitation.campaign.pk)


def invitation_history(request, pk):
    """View edit history for a survey invitation."""
    from .models import SurveyResponseHistory

    invitation = get_object_or_404(
        SurveyInvitation.objects.select_related('campaign', 'faculty', 'response'),
        pk=pk
    )

    history = []
    if hasattr(invitation, 'response'):
        history = invitation.response.history.all()[:50]  # Last 50 entries

    context = {
        'invitation': invitation,
        'history': history,
    }
    return render(request, 'survey/admin/invitation_history.html', context)


def campaign_export_csv(request, pk):
    """Export campaign survey responses to CSV with labels."""
    import csv
    from django.http import HttpResponse
    from .survey_config import CATEGORY_NAMES, get_category_config

    campaign = get_object_or_404(SurveyCampaign, pk=pk)

    # Create the HttpResponse object with CSV header
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="survey_export_{campaign.pk}_{timezone.now().strftime("%Y%m%d_%H%M")}.csv"'

    writer = csv.writer(response)

    # Build header row
    headers = [
        'Faculty Name',
        'Email',
        'Status',
        'Submitted At',
        'Citizenship Points',
        'Education Points',
        'Research Points',
        'Leadership Points',
        'Content Expert Points',
        'Total Points',
    ]

    # Add headers for each category's data
    for cat_key in ['citizenship', 'education', 'research', 'leadership', 'content_expert']:
        config = get_category_config(cat_key)
        if config:
            for sub in config.get('subsections', []):
                headers.append(f"{config['name']}: {sub['name']} (Trigger)")
                headers.append(f"{config['name']}: {sub['name']} (Data)")

    writer.writerow(headers)

    # Get all invitations with responses
    invitations = campaign.invitations.select_related(
        'faculty', 'response'
    ).all().order_by('faculty__last_name', 'faculty__first_name')

    for inv in invitations:
        row = [
            inv.faculty.display_name,
            inv.faculty.email,
            inv.get_status_display(),
            inv.submitted_at.strftime('%Y-%m-%d %H:%M') if inv.submitted_at else '',
        ]

        # Get response data
        resp = getattr(inv, 'response', None)
        if resp:
            row.extend([
                resp.citizenship_points,
                resp.education_points,
                resp.research_points,
                resp.leadership_points,
                resp.content_expert_points,
                resp.total_points,
            ])

            # Add category data
            response_data = resp.response_data or {}
            for cat_key in ['citizenship', 'education', 'research', 'leadership', 'content_expert']:
                config = get_category_config(cat_key)
                if config:
                    cat_data = response_data.get(cat_key, {})
                    for sub in config.get('subsections', []):
                        sub_data = cat_data.get(sub['key'], {})
                        trigger = sub_data.get('trigger', '')
                        entries = sub_data.get('entries', [])
                        # Format entries as readable string
                        if entries:
                            entry_strs = []
                            for e in entries:
                                parts = [f"{k}: {v}" for k, v in e.items() if v]
                                entry_strs.append('; '.join(parts))
                            row.append(trigger)
                            row.append(' | '.join(entry_strs))
                        else:
                            row.append(trigger)
                            row.append('')
        else:
            # No response - fill with empty values
            row.extend(['', '', '', '', '', ''])  # Points columns
            for cat_key in ['citizenship', 'education', 'research', 'leadership', 'content_expert']:
                config = get_category_config(cat_key)
                if config:
                    for sub in config.get('subsections', []):
                        row.extend(['', ''])  # Trigger and Data columns

        writer.writerow(row)

    return response


# =============================================================================
# FACULTY SURVEY VIEWS - Token-based access
# =============================================================================

def _get_carry_forward_data_for_faculty(faculty, academic_year, exclude_campaign=None):
    """
    Get carry-forward data from previous quarters for a faculty member.

    Args:
        faculty: FacultyMember instance
        academic_year: AcademicYear instance
        exclude_campaign: Campaign to exclude (current campaign)

    Returns:
        dict: Merged carry-forward data from previous submissions
    """
    # Find all submitted responses from this faculty in this academic year
    previous_responses = SurveyResponse.objects.filter(
        invitation__faculty=faculty,
        invitation__campaign__academic_year=academic_year,
        invitation__status='submitted'
    ).exclude(
        invitation__campaign=exclude_campaign
    ).select_related('invitation__campaign').order_by(
        'invitation__campaign__quarter'  # Earlier quarters first
    )

    merged_data = {}

    for resp in previous_responses:
        carry_forward = extract_carry_forward_data(resp.response_data or {})

        # Merge into result (later quarters override earlier)
        for cat_key, cat_data in carry_forward.items():
            if cat_key not in merged_data:
                merged_data[cat_key] = {}
            for sub_key, sub_data in cat_data.items():
                # Mark entries as carried forward
                if 'entries' in sub_data:
                    for entry in sub_data['entries']:
                        entry['_carried_from'] = resp.invitation.campaign.quarter
                merged_data[cat_key][sub_key] = sub_data

    return merged_data


# =============================================================================
# FACULTY PORTAL - Permanent link for each faculty member
# =============================================================================

def faculty_portal(request, token):
    """
    Faculty portal - permanent link that shows current survey and history.

    Each faculty member has a unique token that never changes.
    This is their personal entry point to fill out surveys.
    """
    faculty = get_object_or_404(FacultyMember, access_token=token)

    # Get current academic year
    academic_year = AcademicYear.get_current()

    # Find current open campaign
    current_campaign = SurveyCampaign.objects.filter(
        status='open',
    ).order_by('-opens_at').first()

    # If there's an open campaign, get or create the invitation for this faculty
    current_invitation = None
    current_response = None
    if current_campaign:
        current_invitation = SurveyInvitation.objects.filter(
            campaign=current_campaign,
            faculty=faculty
        ).first()

        if current_invitation:
            current_response = SurveyResponse.objects.filter(
                invitation=current_invitation
            ).first()

    # Get past submissions for this academic year
    past_submissions = SurveyInvitation.objects.filter(
        faculty=faculty,
        campaign__academic_year=academic_year,
        status='submitted'
    ).select_related('campaign').order_by('-submitted_at')

    # Exclude current campaign from past submissions
    if current_campaign:
        past_submissions = past_submissions.exclude(campaign=current_campaign)

    # Calculate total points for the year
    from reports_app.models import FacultySurveyData
    survey_data = FacultySurveyData.objects.filter(
        faculty=faculty,
        academic_year=academic_year
    ).first()

    total_points = survey_data.survey_total_points if survey_data else 0

    return render(request, 'survey/faculty/portal.html', {
        'faculty': faculty,
        'academic_year': academic_year,
        'current_campaign': current_campaign,
        'current_invitation': current_invitation,
        'current_response': current_response,
        'past_submissions': past_submissions,
        'total_points': total_points,
    })


def survey_landing(request, token):
    """Landing page after clicking email link."""
    invitation = get_object_or_404(
        SurveyInvitation.objects.select_related('campaign', 'faculty', 'campaign__academic_year'),
        token=token
    )

    # Check if campaign is open
    if not invitation.campaign.is_open:
        context = {
            'invitation': invitation,
            'campaign_closed': True,
        }
        return render(request, 'survey/faculty/landing.html', context)

    # Mark first access
    invitation.mark_accessed()

    # Get or create response
    response, created = SurveyResponse.objects.get_or_create(
        invitation=invitation
    )

    # If new response, pre-populate with carry-forward data from previous quarters
    if created:
        carry_forward_data = _get_carry_forward_data_for_faculty(
            invitation.faculty,
            invitation.campaign.academic_year,
            exclude_campaign=invitation.campaign
        )
        if carry_forward_data:
            response.response_data = carry_forward_data
            response.save(update_fields=['response_data'])

    # Build category list from config (only show configured categories)
    categories = []
    for cat_key in CATEGORY_ORDER:
        cat_config = get_category_config(cat_key)
        if cat_config:
            is_complete = getattr(response, f'{cat_key}_complete', False)
            points = getattr(response, f'{cat_key}_points', 0)
            categories.append({
                'key': cat_key,
                'name': cat_config['name'],
                'complete': is_complete,
                'points': points,
            })

    # Find first incomplete category for "Continue" button
    first_incomplete = None
    for cat in categories:
        if not cat['complete']:
            first_incomplete = cat['key']
            break

    context = {
        'invitation': invitation,
        'response': response,
        'categories': categories,
        'first_incomplete': first_incomplete or (categories[0]['key'] if categories else 'citizenship'),
    }
    return render(request, 'survey/faculty/landing.html', context)


def survey_category(request, token, category):
    """Category form page with repeating sections - config-driven."""
    invitation = get_object_or_404(
        SurveyInvitation.objects.select_related('campaign', 'faculty'),
        token=token
    )

    # Get category config
    category_config = get_category_config(category)
    if not category_config:
        raise Http404("Invalid category")

    # Check if campaign is open
    if not invitation.campaign.is_open:
        messages.error(request, 'This survey is no longer accepting submissions')
        return redirect('survey:survey_landing', token=token)

    # Get or create response
    response, _ = SurveyResponse.objects.get_or_create(invitation=invitation)

    if request.method == 'POST':
        # Process form submission using config
        category_data = _process_category_form_from_config(request.POST, category_config)
        response.response_data[category] = category_data

        # Calculate points for this category using config
        points = calculate_category_points(category, category_data)
        setattr(response, f'{category}_points', points)

        # Mark category complete
        setattr(response, f'{category}_complete', True)

        response.save()

        # Log the change for audit trail
        from .models import SurveyResponseHistory
        SurveyResponseHistory.log_change(
            response=response,
            action='update',
            category=category,
            request=request
        )

        messages.success(request, f'{category_config["name"]} saved')

        # Check if "Save & Continue" or just "Save"
        action = request.POST.get('action', 'save')
        if action == 'continue':
            next_cat = get_next_category(category)
            if next_cat and get_category_config(next_cat):
                return redirect('survey:survey_category', token=token, category=next_cat)
            else:
                return redirect('survey:survey_review', token=token)

        # Stay on current page if just saving
        return redirect('survey:survey_category', token=token, category=category)

    # GET - Display form with existing data
    category_data = response.get_category_data(category)

    # Build navigation info for tabs
    nav_categories = []
    for cat_key in CATEGORY_ORDER:
        cat_config = get_category_config(cat_key)
        if cat_config:
            is_complete = getattr(response, f'{cat_key}_complete', False)
            points = getattr(response, f'{cat_key}_points', 0)
            nav_categories.append({
                'key': cat_key,
                'name': cat_config['name'],
                'complete': is_complete,
                'points': points,
                'active': cat_key == category,
            })

    context = {
        'invitation': invitation,
        'response': response,
        'category': category,
        'category_config': category_config,
        'category_data': category_data,
        'nav_categories': nav_categories,
        'prev_category': get_prev_category(category),
        'next_category': get_next_category(category),
    }
    return render(request, 'survey/faculty/category_form.html', context)


def survey_review(request, token):
    """Review all responses before submission."""
    invitation = get_object_or_404(
        SurveyInvitation.objects.select_related('campaign', 'faculty'),
        token=token
    )

    # Check if campaign is open
    if not invitation.campaign.is_open:
        messages.error(request, 'This survey is no longer accepting submissions')
        return redirect('survey:survey_landing', token=token)

    response = get_object_or_404(SurveyResponse, invitation=invitation)

    context = {
        'invitation': invitation,
        'response': response,
        'categories': [
            ('citizenship', 'Citizenship', response.citizenship_points, response.citizenship_complete),
            ('education', 'Education', response.education_points, response.education_complete),
            ('research', 'Research', response.research_points, response.research_complete),
            ('leadership', 'Leadership', response.leadership_points, response.leadership_complete),
            ('content_expert', 'Content Expert', response.content_expert_points, response.content_expert_complete),
        ],
    }
    return render(request, 'survey/faculty/review.html', context)


@require_POST
def survey_submit(request, token):
    """Submit the survey and merge into FacultySurveyData."""
    invitation = get_object_or_404(
        SurveyInvitation.objects.select_related('campaign', 'faculty', 'campaign__academic_year'),
        token=token
    )

    # Check if campaign is open
    if not invitation.campaign.is_open:
        messages.error(request, 'This survey is no longer accepting submissions')
        return redirect('survey:survey_landing', token=token)

    response = get_object_or_404(SurveyResponse, invitation=invitation)
    is_resubmission = invitation.status == 'submitted'

    with transaction.atomic():
        # Merge response into FacultySurveyData
        _merge_response_to_faculty_data(response)

        # Mark invitation as submitted (updates timestamp)
        invitation.mark_submitted()

        # Log the submission for audit trail
        from .models import SurveyResponseHistory
        SurveyResponseHistory.log_change(
            response=response,
            action='resubmit' if is_resubmission else 'submit',
            request=request
        )

        # Send confirmation email only on first submission
        if not is_resubmission:
            _send_confirmation_email(invitation)

    if is_resubmission:
        messages.success(request, 'Your changes have been saved!')
    else:
        messages.success(request, 'Your survey has been submitted successfully!')
    return redirect('survey:survey_confirmation', token=token)


def survey_confirmation(request, token):
    """Confirmation page after submission."""
    invitation = get_object_or_404(
        SurveyInvitation.objects.select_related('campaign', 'faculty'),
        token=token
    )

    response = get_object_or_404(SurveyResponse, invitation=invitation)

    context = {
        'invitation': invitation,
        'response': response,
    }
    return render(request, 'survey/faculty/confirmation.html', context)


@require_POST
def survey_save_draft(request, token):
    """AJAX endpoint to save draft data."""
    invitation = get_object_or_404(SurveyInvitation, token=token)

    if not invitation.campaign.is_open:
        return JsonResponse({'error': 'Survey is closed'}, status=400)

    response, _ = SurveyResponse.objects.get_or_create(invitation=invitation)

    # Parse JSON data from request
    import json
    try:
        data = json.loads(request.body)
        category = data.get('category')
        category_data = data.get('data', {})

        if category:
            response.response_data[category] = category_data
            points = _calculate_category_points(category_data, category)
            setattr(response, f'{category}_points', points)
            response.save()

        return JsonResponse({
            'success': True,
            'points': points if category else 0,
        })
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)


# =============================================================================
# FACULTY LOGIN FALLBACK
# =============================================================================

def faculty_login(request):
    """Magic link login for faculty without their original invitation."""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()

        if not email:
            messages.error(request, 'Please enter your email address')
        else:
            # Find active invitations for this faculty
            invitations = SurveyInvitation.objects.filter(
                faculty__email__iexact=email,
                campaign__is_active=True,
            ).select_related('campaign')

            if invitations.exists():
                # Send magic link email with all active survey links
                _send_magic_link_email(email, invitations)
                messages.success(
                    request,
                    'If your email is in our system, you will receive a link shortly.'
                )
            else:
                # Don't reveal if email exists
                messages.success(
                    request,
                    'If your email is in our system, you will receive a link shortly.'
                )

    return render(request, 'survey/faculty/login.html')


def faculty_my_survey(request):
    """View current survey status (requires session or redirect from magic link)."""
    # This would be implemented with session-based auth
    # For now, redirect to login
    return redirect('survey:faculty_login')


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _send_invitation_email(invitation):
    """Send invitation email to faculty. Returns True on success."""
    from django.core.mail import send_mail
    from django.conf import settings
    from django.urls import reverse

    try:
        campaign = invitation.campaign
        faculty = invitation.faculty

        # Build survey URL
        survey_url = settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://localhost:8000'
        survey_url += reverse('survey:survey_landing', kwargs={'token': invitation.token})

        # Format deadline
        deadline = campaign.closes_at.strftime('%B %d, %Y at %I:%M %p')

        # Use campaign-specific settings or defaults
        if campaign.email_from_name and campaign.email_from_address:
            from_email = f"{campaign.email_from_name} <{campaign.email_from_address}>"
        elif campaign.email_from_address:
            from_email = campaign.email_from_address
        else:
            from_email = settings.DEFAULT_FROM_EMAIL

        if campaign.email_subject:
            subject = campaign.email_subject
        else:
            subject = f"{settings.SURVEY_EMAIL_SUBJECT_PREFIX}Academic Achievement Survey - {campaign.quarter}"

        if campaign.email_body:
            # Use custom body with placeholder replacement
            message = campaign.email_body
            message = message.replace('{first_name}', faculty.first_name)
            message = message.replace('{last_name}', faculty.last_name)
            message = message.replace('{survey_link}', survey_url)
            message = message.replace('{deadline}', deadline)
        else:
            # Default message
            message = f"""Dear {faculty.first_name} {faculty.last_name},

You are invited to complete the Academic Achievement Survey for {campaign.quarter}.

Please click the link below to begin:
{survey_url}

Deadline: {deadline}

This link is unique to you. Please do not share it.

Thank you,
UNMC Department of Anesthesiology"""

        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=[faculty.email],
            fail_silently=False,
        )

        # Update invitation
        invitation.email_sent_at = timezone.now()
        invitation.save(update_fields=['email_sent_at'])

        # Log email
        EmailLog.objects.create(
            invitation=invitation,
            email_type='invitation',
            recipient=faculty.email,
            subject=subject,
            status='sent',
        )

        return True

    except Exception as e:
        # Log failure
        EmailLog.objects.create(
            invitation=invitation,
            email_type='invitation',
            recipient=invitation.faculty.email,
            subject=f"Failed: {invitation.campaign.quarter} Survey",
            status='failed',
            error_message=str(e),
        )
        return False


def _send_reminder_email(invitation):
    """Send reminder email. Returns True on success."""
    from django.core.mail import send_mail
    from django.conf import settings
    from django.urls import reverse

    try:
        campaign = invitation.campaign
        faculty = invitation.faculty

        survey_url = settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://localhost:8000'
        survey_url += reverse('survey:survey_landing', kwargs={'token': invitation.token})

        # Use campaign-specific from address or default
        if campaign.email_from_name and campaign.email_from_address:
            from_email = f"{campaign.email_from_name} <{campaign.email_from_address}>"
        elif campaign.email_from_address:
            from_email = campaign.email_from_address
        else:
            from_email = settings.DEFAULT_FROM_EMAIL

        subject = f"{settings.SURVEY_EMAIL_SUBJECT_PREFIX}REMINDER: Academic Achievement Survey - {campaign.quarter}"

        status_msg = "not yet started" if invitation.status == 'pending' else "in progress"
        deadline = campaign.closes_at.strftime('%B %d, %Y at %I:%M %p')

        message = f"""Dear {faculty.first_name} {faculty.last_name},

This is a reminder that your Academic Achievement Survey for {campaign.quarter} is {status_msg}.

Please click the link below to complete your submission:
{survey_url}

Deadline: {deadline}

Thank you,
UNMC Department of Anesthesiology"""

        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=[faculty.email],
            fail_silently=False,
        )

        # Log email
        EmailLog.objects.create(
            invitation=invitation,
            email_type='reminder',
            recipient=faculty.email,
            subject=subject,
            status='sent',
        )

        return True

    except Exception as e:
        EmailLog.objects.create(
            invitation=invitation,
            email_type='reminder',
            recipient=invitation.faculty.email,
            subject=f"Failed reminder: {invitation.campaign.quarter}",
            status='failed',
            error_message=str(e),
        )
        return False


def _send_confirmation_email(invitation):
    """Send submission confirmation email."""
    from django.core.mail import send_mail
    from django.conf import settings

    try:
        campaign = invitation.campaign
        faculty = invitation.faculty

        # Use campaign-specific from address or default
        if campaign.email_from_name and campaign.email_from_address:
            from_email = f"{campaign.email_from_name} <{campaign.email_from_address}>"
        elif campaign.email_from_address:
            from_email = campaign.email_from_address
        else:
            from_email = settings.DEFAULT_FROM_EMAIL

        subject = f"{settings.SURVEY_EMAIL_SUBJECT_PREFIX}Survey Submitted - {campaign.quarter}"

        message = f"""Dear {faculty.first_name} {faculty.last_name},

Thank you for completing the Academic Achievement Survey for {campaign.quarter}.

Your submission has been recorded.

Submitted: {invitation.submitted_at.strftime('%B %d, %Y at %I:%M %p')}

If you have any questions, please contact the department.

Thank you,
UNMC Department of Anesthesiology"""

        send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=[faculty.email],
            fail_silently=False,
        )

        EmailLog.objects.create(
            invitation=invitation,
            email_type='confirmation',
            recipient=faculty.email,
            subject=subject,
            status='sent',
        )

    except Exception as e:
        EmailLog.objects.create(
            invitation=invitation,
            email_type='confirmation',
            recipient=invitation.faculty.email,
            subject=f"Failed confirmation: {invitation.campaign.quarter}",
            status='failed',
            error_message=str(e),
        )


def _send_magic_link_email(email, invitations):
    """Send email with links to all active surveys."""
    from django.core.mail import send_mail
    from django.conf import settings
    from django.urls import reverse

    try:
        base_url = settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://localhost:8000'

        links = []
        for inv in invitations:
            url = base_url + reverse('survey:survey_landing', kwargs={'token': inv.token})
            links.append(f"- {inv.campaign.name}: {url}")

        subject = f"{settings.SURVEY_EMAIL_SUBJECT_PREFIX}Your Survey Links"

        message = f"""
You requested access to your Academic Achievement Surveys.

Here are your survey links:

{chr(10).join(links)}

These links are unique to you. Please do not share them.

Thank you,
UNMC Department of Anesthesiology
"""

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )

    except Exception:
        pass  # Silent fail for security


def _process_category_form_from_config(post_data, category_config):
    """
    Process POST data for a category form based on config.

    Returns structured data matching REDCap pattern:
    {
        'committees': {
            'trigger': 'yes',
            'entries': [
                {'type': 'unmc', 'name': 'IRB', 'role': 'member'},
            ]
        },
        'dept_activities': {
            'trigger': 'no',
            'entries': [
                {'type': 'gr_host', 'date': '2024-01-15', 'description': 'AI in Anesthesia'},
            ]
        }
    }
    """
    result = {}

    for subsection in category_config['subsections']:
        subsection_key = subsection['key']
        sub_data = {}

        # Get trigger value
        trigger_value = post_data.get(f'{subsection_key}_trigger', '')
        if trigger_value:
            sub_data['trigger'] = trigger_value

        # Process entries for repeating types
        if subsection['type'] == 'repeating':
            entries = []

            # Dynamically find all entry indices from POST data
            # Look for pattern: subsection_key_{index}_{field_name}
            entry_indices = set()
            prefix = f"{subsection_key}_"
            for key in post_data.keys():
                if key.startswith(prefix) and key != f"{subsection_key}_trigger":
                    # Extract index from key like "committees_3_type"
                    parts = key[len(prefix):].split('_', 1)
                    if len(parts) >= 1 and parts[0].isdigit():
                        entry_indices.add(int(parts[0]))

            # Process each found entry
            for i in sorted(entry_indices):
                entry = {}
                has_data = False

                for field in subsection['fields']:
                    field_name = f"{subsection_key}_{i}_{field['name']}"
                    value = post_data.get(field_name, '').strip()
                    if value:
                        entry[field['name']] = value
                        has_data = True

                # Only include entry if it has data and type is not '99' (opt-out)
                if has_data and entry.get('type') != '99':
                    entries.append(entry)

            sub_data['entries'] = entries

        result[subsection_key] = sub_data

    return result


def _merge_response_to_faculty_data(response):
    """Merge survey response into FacultySurveyData for reports."""
    from reports_app.models import FacultySurveyData

    invitation = response.invitation
    faculty = invitation.faculty
    academic_year = invitation.campaign.academic_year
    quarter = invitation.campaign.quarter

    # Get or create FacultySurveyData
    faculty_data, created = FacultySurveyData.objects.get_or_create(
        faculty=faculty,
        academic_year=academic_year,
    )

    # Merge activities - survey data goes into activities_json
    # The response_data structure should match the expected format
    existing = faculty_data.activities_json or {}

    # Deep merge: for each category, update with survey data
    for category in ['citizenship', 'education', 'research', 'leadership', 'content_expert']:
        if category in response.response_data:
            existing[category] = response.response_data[category]

    faculty_data.activities_json = existing

    # Update point totals
    faculty_data.citizenship_points = response.citizenship_points
    faculty_data.education_points = response.education_points
    faculty_data.research_points = response.research_points
    faculty_data.leadership_points = response.leadership_points
    faculty_data.content_expert_points = response.content_expert_points
    faculty_data.survey_total_points = response.total_points

    # Update quarters reported
    quarters = set(faculty_data.quarters_reported or [])
    quarters.add(quarter)
    faculty_data.quarters_reported = list(quarters)

    faculty_data.save()
