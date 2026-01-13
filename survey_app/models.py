"""
Django models for the Survey feature.

This module defines:
- SurveyCampaign: Groups survey invitations for a quarter
- SurveyInvitation: Individual invitation with unique token
- SurveyResponse: Draft/submitted survey data
- EmailLog: Audit trail for sent emails
"""

import secrets
from django.db import models
from django.utils import timezone

from reports_app.models import AcademicYear, FacultyMember


def generate_token():
    """Generate a secure random token for survey invitations."""
    return secrets.token_urlsafe(32)


class SurveyCampaign(models.Model):
    """
    A survey campaign for a specific quarter.

    Groups all invitations sent for that quarter and tracks
    campaign status, dates, and reminder scheduling.
    """
    QUARTER_CHOICES = [
        ('Q1-Q2', 'Q1-Q2 (Jul-Dec)'),
        ('Q3', 'Q3 (Jan-Mar)'),
        ('Q4', 'Q4 (Apr-Jun)'),
    ]

    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.CASCADE,
        related_name='survey_campaigns'
    )
    quarter = models.CharField(max_length=10, choices=QUARTER_CHOICES)
    name = models.CharField(
        max_length=100,
        help_text='Display name, e.g., "AY 24-25 Q1-Q2 Survey"'
    )

    # Campaign timing
    opens_at = models.DateTimeField(help_text='When survey becomes accessible')
    closes_at = models.DateTimeField(help_text='Submission deadline')

    # Status tracking
    is_active = models.BooleanField(
        default=True,
        help_text='Inactive campaigns cannot accept submissions'
    )

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(
        max_length=100,
        blank=True,
        help_text='Username if authentication is enabled'
    )

    class Meta:
        unique_together = ['academic_year', 'quarter']
        ordering = ['-academic_year__year_code', '-quarter']
        verbose_name = 'Survey Campaign'
        verbose_name_plural = 'Survey Campaigns'

    def __str__(self):
        return self.name

    @property
    def is_open(self):
        """Check if campaign is currently accepting submissions."""
        now = timezone.now()
        return (
            self.is_active and
            self.opens_at <= now <= self.closes_at
        )

    @property
    def status(self):
        """Return human-readable status."""
        now = timezone.now()
        if not self.is_active:
            return 'Inactive'
        if now < self.opens_at:
            return 'Scheduled'
        if now > self.closes_at:
            return 'Closed'
        return 'Open'

    @property
    def submission_stats(self):
        """Return submission statistics."""
        total = self.invitations.count()
        submitted = self.invitations.filter(status='submitted').count()
        in_progress = self.invitations.filter(status='in_progress').count()
        pending = self.invitations.filter(status='pending').count()
        return {
            'total': total,
            'submitted': submitted,
            'in_progress': in_progress,
            'pending': pending,
            'completion_rate': (submitted / total * 100) if total > 0 else 0
        }


class SurveyInvitation(models.Model):
    """
    Individual survey invitation sent to a faculty member.

    Contains a unique token for access and tracks submission status.
    """
    STATUS_CHOICES = [
        ('pending', 'Not Started'),
        ('in_progress', 'In Progress'),
        ('submitted', 'Submitted'),
    ]

    campaign = models.ForeignKey(
        SurveyCampaign,
        on_delete=models.CASCADE,
        related_name='invitations'
    )
    faculty = models.ForeignKey(
        FacultyMember,
        on_delete=models.CASCADE,
        related_name='survey_invitations'
    )

    # Unique access token (URL-safe, 32 bytes = 43 chars)
    token = models.CharField(
        max_length=64,
        unique=True,
        default=generate_token,
        db_index=True
    )

    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending'
    )

    # Timestamps
    email_sent_at = models.DateTimeField(null=True, blank=True)
    first_accessed_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['campaign', 'faculty']
        ordering = ['faculty__last_name', 'faculty__first_name']
        verbose_name = 'Survey Invitation'
        verbose_name_plural = 'Survey Invitations'

    def __str__(self):
        return f"{self.faculty.display_name} - {self.campaign.name}"

    def mark_accessed(self):
        """Mark first access time if not already set."""
        if not self.first_accessed_at:
            self.first_accessed_at = timezone.now()
            if self.status == 'pending':
                self.status = 'in_progress'
            self.save(update_fields=['first_accessed_at', 'status', 'updated_at'])

    def mark_submitted(self):
        """Mark invitation as submitted."""
        self.status = 'submitted'
        self.submitted_at = timezone.now()
        self.save(update_fields=['status', 'submitted_at', 'updated_at'])


class SurveyResponse(models.Model):
    """
    Survey response data (draft or submitted).

    Stores response data as JSON matching the FacultySurveyData.activities_json
    schema for seamless integration with existing reports.
    """
    invitation = models.OneToOneField(
        SurveyInvitation,
        on_delete=models.CASCADE,
        related_name='response'
    )

    # Response data in JSON format (matches activities_json schema)
    response_data = models.JSONField(
        default=dict,
        help_text='Survey response data structured by category'
    )

    # Category completion tracking (for progress indicator)
    citizenship_complete = models.BooleanField(default=False)
    education_complete = models.BooleanField(default=False)
    research_complete = models.BooleanField(default=False)
    leadership_complete = models.BooleanField(default=False)
    content_expert_complete = models.BooleanField(default=False)

    # Calculated point totals (updated on save)
    citizenship_points = models.IntegerField(default=0)
    education_points = models.IntegerField(default=0)
    research_points = models.IntegerField(default=0)
    leadership_points = models.IntegerField(default=0)
    content_expert_points = models.IntegerField(default=0)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Survey Response'
        verbose_name_plural = 'Survey Responses'

    def __str__(self):
        return f"Response: {self.invitation}"

    @property
    def total_points(self):
        """Calculate total points across all categories."""
        return (
            self.citizenship_points +
            self.education_points +
            self.research_points +
            self.leadership_points +
            self.content_expert_points
        )

    @property
    def completion_percentage(self):
        """Calculate overall completion percentage."""
        completed = sum([
            self.citizenship_complete,
            self.education_complete,
            self.research_complete,
            self.leadership_complete,
            self.content_expert_complete,
        ])
        return int(completed / 5 * 100)

    def get_category_data(self, category):
        """Get response data for a specific category."""
        return self.response_data.get(category, {})

    def set_category_data(self, category, data):
        """Set response data for a specific category."""
        self.response_data[category] = data
        self.save()


class EmailLog(models.Model):
    """
    Audit log for emails sent for survey campaigns.
    """
    EMAIL_TYPE_CHOICES = [
        ('invitation', 'Initial Invitation'),
        ('reminder', 'Reminder'),
        ('confirmation', 'Submission Confirmation'),
    ]

    STATUS_CHOICES = [
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('bounced', 'Bounced'),
    ]

    invitation = models.ForeignKey(
        SurveyInvitation,
        on_delete=models.CASCADE,
        related_name='email_logs'
    )

    email_type = models.CharField(max_length=20, choices=EMAIL_TYPE_CHOICES)
    recipient = models.EmailField()
    subject = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='sent'
    )
    error_message = models.TextField(blank=True)

    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-sent_at']
        verbose_name = 'Email Log'
        verbose_name_plural = 'Email Logs'

    def __str__(self):
        return f"{self.email_type} to {self.recipient} ({self.status})"


class SurveyResponseHistory(models.Model):
    """
    Audit log tracking all changes to survey responses.

    Stores a snapshot of the response data whenever it changes,
    allowing administrators to review edit history and restore
    previous versions if needed.
    """
    ACTION_CHOICES = [
        ('create', 'Created'),
        ('update', 'Updated'),
        ('submit', 'Submitted'),
        ('unlock', 'Unlocked'),
    ]

    response = models.ForeignKey(
        SurveyResponse,
        on_delete=models.CASCADE,
        related_name='history'
    )

    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    category = models.CharField(
        max_length=50,
        blank=True,
        help_text='Category that was modified (if applicable)'
    )

    # Snapshot of data at this point
    response_data_snapshot = models.JSONField(
        default=dict,
        help_text='Complete response data at time of change'
    )
    points_snapshot = models.JSONField(
        default=dict,
        help_text='Points by category at time of change'
    )

    # Who made the change (IP for faculty, could add user for admin)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Response History'
        verbose_name_plural = 'Response History'

    def __str__(self):
        return f"{self.get_action_display()} - {self.response.invitation.faculty.display_name} - {self.created_at}"

    @classmethod
    def log_change(cls, response, action, category='', request=None):
        """Create a history record for a response change."""
        ip_address = None
        user_agent = ''

        if request:
            # Get IP address
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip_address = x_forwarded_for.split(',')[0].strip()
            else:
                ip_address = request.META.get('REMOTE_ADDR')
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]

        return cls.objects.create(
            response=response,
            action=action,
            category=category,
            response_data_snapshot=response.response_data.copy() if response.response_data else {},
            points_snapshot={
                'citizenship': response.citizenship_points,
                'education': response.education_points,
                'research': response.research_points,
                'leadership': response.leadership_points,
                'content_expert': response.content_expert_points,
                'total': response.total_points,
            },
            ip_address=ip_address,
            user_agent=user_agent,
        )
