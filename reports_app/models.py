"""
Django models for Academic Achievement Award Summarizer.

This module defines the database schema for persistent storage of:
- Academic years
- Faculty roster
- Survey imports and data
- Departmental tracking items
"""

import secrets
from django.db import models
from datetime import date


class AcademicYear(models.Model):
    """
    Academic year tracking (July-June cycle).

    The academic year runs from July 1 to June 30.
    Format: "24-25" for the 2024-2025 academic year.
    """
    year_code = models.CharField(
        max_length=12,
        unique=True,
        primary_key=True,
        help_text='Format: "24-25" or "2024-2025" for academic year'
    )
    start_date = models.DateField(help_text='July 1 of start year')
    end_date = models.DateField(help_text='June 30 of end year')
    is_current = models.BooleanField(default=False)

    class Meta:
        ordering = ['-year_code']
        verbose_name = 'Academic Year'
        verbose_name_plural = 'Academic Years'

    def __str__(self):
        return f"AY {self.year_code}"

    def save(self, *args, **kwargs):
        # Ensure only one year is marked as current
        if self.is_current:
            AcademicYear.objects.filter(is_current=True).update(is_current=False)
        super().save(*args, **kwargs)

    @classmethod
    def get_current(cls):
        """Get or create the current academic year based on today's date."""
        today = date.today()
        if today.month >= 7:  # July-December
            start_year = today.year
        else:  # January-June
            start_year = today.year - 1

        year_code = f"{start_year % 100:02d}-{(start_year + 1) % 100:02d}"

        year, created = cls.objects.get_or_create(
            year_code=year_code,
            defaults={
                'start_date': date(start_year, 7, 1),
                'end_date': date(start_year + 1, 6, 30),
                'is_current': True,
            }
        )

        # If retrieved existing year, ensure it's marked current
        if not created and not year.is_current:
            year.is_current = True
            year.save()

        return year


class FacultyMember(models.Model):
    """
    Faculty roster - source of truth for department faculty.

    ============================================================
    IT DEPLOYMENT NOTE - DATABASE SOURCE OPTIONS
    ============================================================

    DEFAULT (Development): Uses local SQLite/PostgreSQL table.
    Data is imported from Faculty Calculator CSV export and
    managed locally within this application.

    ALTERNATIVE (Shared Database): Connect to external faculty database.
    To enable shared database mode:
    1. Configure 'faculty_db' in DATABASES (webapp/settings.py)
    2. Uncomment DATABASE_ROUTERS in settings.py
    3. Change Meta below to: managed = False
    4. Update db_table to match your shared database table name

    See DEPLOYMENT.md for connection string format and examples.
    ============================================================
    """
    email = models.EmailField(
        primary_key=True,
        help_text='Primary identifier - must match survey submissions'
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)

    RANK_CHOICES = [
        ('instructor', 'Instructor'),
        ('assistant', 'Assistant Professor'),
        ('associate', 'Associate Professor'),
        ('professor', 'Professor'),
    ]
    rank = models.CharField(
        max_length=20,
        choices=RANK_CHOICES,
        blank=True,
        default=''
    )

    CONTRACT_CHOICES = [
        ('academic', 'Academic'),
        ('clinical', 'Clinical'),
        ('early_career', 'Early Career (Yrs 1-3)'),
    ]
    contract_type = models.CharField(
        max_length=20,
        choices=CONTRACT_CHOICES,
        blank=True,
        default=''
    )

    DIVISION_CHOICES = [
        ('cardiac', 'Cardiac'),
        ('critical_care', 'Critical Care'),
        ('multispecialty', 'Multispecialty'),
        ('pain', 'Pain'),
        ('transplant', 'Transplant'),
        ('pediatric', 'Pediatric'),
        ('surgery', 'Surgery'),
        ('emergency_medicine', 'Emergency Medicine'),
    ]
    division = models.CharField(
        max_length=50,
        choices=DIVISION_CHOICES,
        blank=True,
        default=''
    )
    is_active = models.BooleanField(default=True)

    # CCC membership persists year-to-year (1000 points)
    is_ccc_member = models.BooleanField(
        default=False,
        verbose_name='CCC Member',
        help_text='Clinical Competency Committee member (1000 pts, persists year-to-year)'
    )

    # AVC eligibility - determines if faculty is included in AVC reports
    is_avc_eligible = models.BooleanField(
        default=True,
        verbose_name='AVC Eligible',
        help_text='Include this faculty in AVC point calculations and reports'
    )

    # Permanent access token for faculty portal
    access_token = models.CharField(
        max_length=64,
        unique=True,
        blank=True,
        null=True,
        help_text='Permanent unique link for faculty to access their surveys'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['last_name', 'first_name']
        verbose_name = 'Faculty Member'
        verbose_name_plural = 'Faculty Members'
        # ============================================================
        # IT DEPLOYMENT: Uncomment the following for shared database
        # ============================================================
        # managed = False
        # db_table = 'faculty_roster'  # Change to match your table name

    def __str__(self):
        return self.display_name

    def save(self, *args, **kwargs):
        # Auto-generate access token if not set
        if not self.access_token:
            self.access_token = secrets.token_urlsafe(32)
        super().save(*args, **kwargs)

    @property
    def display_name(self):
        """Return name in 'Last, First' format."""
        return f"{self.last_name}, {self.first_name}"

    def get_portal_url(self):
        """Get the permanent portal URL for this faculty member."""
        from django.urls import reverse
        return reverse('faculty_portal', args=[self.access_token])


class SurveyImport(models.Model):
    """
    Tracks each REDCap CSV import for audit trail.
    """
    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.CASCADE,
        related_name='survey_imports'
    )
    imported_at = models.DateTimeField(auto_now_add=True)
    imported_by = models.CharField(
        max_length=100,
        blank=True,
        help_text='Username if authentication is enabled'
    )
    filename = models.CharField(max_length=255)
    faculty_count = models.IntegerField(default=0)
    activity_count = models.IntegerField(default=0)

    # Store unmatched faculty emails for review
    unmatched_emails = models.JSONField(
        default=list,
        help_text='List of email addresses not found in roster'
    )

    class Meta:
        ordering = ['-imported_at']
        verbose_name = 'Survey Import'
        verbose_name_plural = 'Survey Imports'

    def __str__(self):
        return f"{self.filename} ({self.imported_at.strftime('%Y-%m-%d %H:%M')})"


class FacultySurveyData(models.Model):
    """
    Survey submission data for a faculty member in an academic year.

    Stores aggregated totals from REDCap survey submissions,
    including all activities across quarters (Q1-Q2, Q3, Q4).
    """
    faculty = models.ForeignKey(
        FacultyMember,
        on_delete=models.CASCADE,
        related_name='survey_data'
    )
    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.CASCADE,
        related_name='survey_data'
    )
    survey_import = models.ForeignKey(
        SurveyImport,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='faculty_data'
    )

    # Submission tracking
    quarters_reported = models.JSONField(
        default=list,
        help_text='List of quarters submitted: ["Q1-Q2", "Q3", "Q4"]'
    )
    has_incomplete = models.BooleanField(
        default=False,
        help_text='True if any submission was marked incomplete'
    )

    # Point totals by category (from survey)
    citizenship_points = models.IntegerField(default=0)
    education_points = models.IntegerField(default=0)
    research_points = models.IntegerField(default=0)
    leadership_points = models.IntegerField(default=0)
    content_expert_points = models.IntegerField(default=0)
    survey_total_points = models.IntegerField(default=0)

    # Raw activities data (full JSON from parser for detailed reports)
    activities_json = models.JSONField(
        default=dict,
        help_text='Complete activity data structure from parser (overwrites on import)'
    )

    # Manually added/edited activities (preserved during CSV imports)
    manual_activities_json = models.JSONField(
        default=dict,
        help_text='Manually added activities - never overwritten by import'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['faculty', 'academic_year']
        ordering = ['faculty__last_name', 'faculty__first_name']
        verbose_name = 'Faculty Survey Data'
        verbose_name_plural = 'Faculty Survey Data'

    def __str__(self):
        return f"{self.faculty.display_name} - AY {self.academic_year.year_code}"


class DepartmentalData(models.Model):
    """
    Department-tracked items for faculty that are not part of the survey.

    These items are entered manually by department administrators
    before generating final point summaries.

    Point Values:
    - new_innovations: 2,000 pts (80%+ evaluations)
    - mytip_winner: 250 pts
    - mytip_count: 25 pts each (max 20 = 500 pts)
    - teaching_top_25: 2,500 pts
    - teaching_65_25: 1,000 pts
    - teacher_of_year: 7,500 pts
    - honorable_mention: 5,000 pts

    Note: CCC membership (1,000 pts) is stored on FacultyMember model
    as it persists year-to-year.
    """
    faculty = models.ForeignKey(
        FacultyMember,
        on_delete=models.CASCADE,
        related_name='departmental_data'
    )
    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.CASCADE,
        related_name='departmental_data'
    )

    # === Evaluations Section ===
    new_innovations = models.BooleanField(
        default=False,
        verbose_name='New Innovations (80%+)',
        help_text='Completed 80%+ of assigned evaluations (2,000 pts)'
    )
    mytip_winner = models.BooleanField(
        default=False,
        verbose_name='MyTIP Report Winner',
        help_text='MyTIP Report Winner for the quarter (250 pts)'
    )
    mytip_count = models.PositiveIntegerField(
        default=0,
        verbose_name='MyTIP Report Count',
        help_text='Number of MyTIP evaluations (25 pts each, max 20)'
    )

    # === Teaching Awards Section ===
    teaching_top_25 = models.BooleanField(
        default=False,
        verbose_name='Top 25%',
        help_text='Teaching evaluation in top 25% (2,500 pts)'
    )
    teaching_65_25 = models.BooleanField(
        default=False,
        verbose_name='Top 65-25%',
        help_text='Teaching evaluation in 65-25% range (1,000 pts)'
    )
    teacher_of_year = models.BooleanField(
        default=False,
        verbose_name='Teacher of the Year',
        help_text='Teacher of the Year award (7,500 pts)'
    )
    honorable_mention = models.BooleanField(
        default=False,
        verbose_name='Honorable Mention',
        help_text='Honorable Mention for teaching (5,000 pts)'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['faculty', 'academic_year']
        ordering = ['faculty__last_name', 'faculty__first_name']
        verbose_name = 'Departmental Data'
        verbose_name_plural = 'Departmental Data'

    def __str__(self):
        return f"{self.faculty.display_name} - AY {self.academic_year.year_code} (Dept)"

    def clean(self):
        """Validate mytip_count is within range."""
        from django.core.exceptions import ValidationError
        if self.mytip_count > 20:
            raise ValidationError({'mytip_count': 'Maximum value is 20'})

    def save(self, *args, **kwargs):
        # Enforce max mytip_count
        if self.mytip_count > 20:
            self.mytip_count = 20
        super().save(*args, **kwargs)

    # === Point Calculation Properties ===

    # Default point values (used as fallback if DB lookup fails)
    DEFAULT_POINT_VALUES = {
        'new_innovations': 2000,
        'mytip_winner': 250,
        'mytip_per': 25,  # per count, max 20
        'teaching_top_25': 2500,
        'teaching_65_25': 1000,
        'teacher_of_year': 7500,
        'honorable_mention': 5000,
        'ccc_member': 1000,  # stored on FacultyMember
    }

    @classmethod
    def get_point_values(cls):
        """
        Get current point values from database, with fallback to defaults.

        This allows point values to be configured via the Activity Points Config page.
        """
        # Import here to avoid circular import
        try:
            from .points_utils import get_departmental_point_values
            db_values = get_departmental_point_values()
            # Merge with defaults (DB values override defaults)
            return {**cls.DEFAULT_POINT_VALUES, **db_values}
        except Exception:
            return cls.DEFAULT_POINT_VALUES

    # For backwards compatibility, expose POINT_VALUES as property
    @property
    def POINT_VALUES(self):
        return self.get_point_values()

    @property
    def evaluations_points(self):
        """Calculate total points from evaluations section."""
        pv = self.get_point_values()
        total = 0
        if self.new_innovations:
            total += pv['new_innovations']
        if self.mytip_winner:
            total += pv['mytip_winner']
        total += min(self.mytip_count, 20) * pv['mytip_per']
        return total

    @property
    def teaching_awards_points(self):
        """Calculate total points from teaching awards section."""
        pv = self.get_point_values()
        total = 0
        if self.teaching_top_25:
            total += pv['teaching_top_25']
        if self.teaching_65_25:
            total += pv['teaching_65_25']
        if self.teacher_of_year:
            total += pv['teacher_of_year']
        if self.honorable_mention:
            total += pv['honorable_mention']
        return total

    @property
    def ccc_points(self):
        """Calculate CCC points (from FacultyMember)."""
        pv = self.get_point_values()
        return pv['ccc_member'] if self.faculty.is_ccc_member else 0

    @property
    def departmental_total_points(self):
        """Calculate total departmental points (including CCC)."""
        return self.evaluations_points + self.teaching_awards_points + self.ccc_points


# =============================================================================
# ACTIVITY POINTS CONFIGURATION
# =============================================================================

class ActivityCategory(models.Model):
    """
    Top-level category for activities (e.g., Citizenship, Education, Research).

    These are the 5 main categories in the AVC points system.
    """
    name = models.CharField(max_length=100, unique=True)
    display_name = models.CharField(max_length=100)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name = 'Activity Category'
        verbose_name_plural = 'Activity Categories'

    def __str__(self):
        return self.display_name


class ActivityGoal(models.Model):
    """
    Goal/subcategory within a category (e.g., Evaluation, Committee Membership, Teaching).

    Groups related activity types together.
    """
    category = models.ForeignKey(
        ActivityCategory,
        on_delete=models.CASCADE,
        related_name='goals'
    )
    name = models.CharField(max_length=100)
    display_name = models.CharField(max_length=100)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['category', 'sort_order', 'name']
        unique_together = ['category', 'name']
        verbose_name = 'Activity Goal'
        verbose_name_plural = 'Activity Goals'

    def __str__(self):
        return f"{self.category.display_name} - {self.display_name}"


class ActivityType(models.Model):
    """
    Specific activity type with point value (e.g., Grand Round Host = 300 pts).

    Maps to REDCap data variables and defines the point calculation.
    """
    MODIFIER_CHOICES = [
        ('fixed', 'Fixed Points'),
        ('count', 'Points × Count'),
        ('impact_factor', 'Points × Impact Factor'),
    ]

    goal = models.ForeignKey(
        ActivityGoal,
        on_delete=models.CASCADE,
        related_name='activity_types'
    )
    name = models.CharField(max_length=200, help_text='Role/activity name')
    display_name = models.CharField(max_length=200)
    data_variable = models.CharField(
        max_length=100,
        unique=True,
        help_text='REDCap data variable name (e.g., CIT_DEPT_GR_HOST)'
    )
    base_points = models.IntegerField(default=0, help_text='Base point value')
    modifier_type = models.CharField(
        max_length=20,
        choices=MODIFIER_CHOICES,
        default='fixed',
        help_text='How points are calculated'
    )
    max_count = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Maximum count for count-based activities (blank = no limit)'
    )
    max_points = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Maximum points cap (blank = no limit)'
    )
    notes = models.TextField(blank=True, help_text='Additional notes or requirements')
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    # For departmental tracking (not in REDCap survey)
    is_departmental = models.BooleanField(
        default=False,
        help_text='True if this is tracked by department, not in survey'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['goal__category', 'goal', 'sort_order', 'name']
        verbose_name = 'Activity Type'
        verbose_name_plural = 'Activity Types'

    def __str__(self):
        return f"{self.display_name} ({self.base_points} pts)"

    def calculate_points(self, count=1, impact_factor=1):
        """Calculate points for this activity type."""
        if self.modifier_type == 'fixed':
            points = self.base_points
        elif self.modifier_type == 'count':
            effective_count = count
            if self.max_count:
                effective_count = min(count, self.max_count)
            points = self.base_points * effective_count
        elif self.modifier_type == 'impact_factor':
            # Cap impact factor at 15, minimum 1
            effective_if = max(1, min(impact_factor, 15))
            points = self.base_points * effective_if
        else:
            points = self.base_points

        # Apply max points cap if set
        if self.max_points:
            points = min(points, self.max_points)

        return points


class Division(models.Model):
    """
    Department divisions with assigned division chiefs.

    Division chiefs can view their faculty's survey responses and activities.
    """
    DIVISION_CODES = [
        ('cardiac', 'Cardiac'),
        ('critical_care', 'Critical Care'),
        ('multispecialty', 'Multispecialty'),
        ('pain', 'Pain'),
        ('pediatric', 'Pediatric'),
    ]

    code = models.CharField(
        max_length=50,
        choices=DIVISION_CODES,
        unique=True,
        primary_key=True
    )
    name = models.CharField(max_length=100)
    chief = models.ForeignKey(
        FacultyMember,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='divisions_led',
        help_text='Division chief who can view division faculty data'
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Division'
        verbose_name_plural = 'Divisions'

    def __str__(self):
        return self.name

    def get_faculty(self):
        """Get all active faculty in this division."""
        return FacultyMember.objects.filter(
            division=self.code,
            is_active=True
        )

    def get_avc_eligible_faculty(self):
        """Get AVC-eligible faculty in this division."""
        return self.get_faculty().filter(is_avc_eligible=True)
