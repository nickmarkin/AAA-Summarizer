"""
Survey Configuration - Defines activity types, point values, and form structure.

This configuration mirrors the REDCap data dictionary structure with:
- Trigger questions (yes/no) that gate each subsection
- "Add another" pattern for repeating entries
- Correction options for mistaken "No" answers
- Opt-out choice for mistaken "Yes" answers

POINT VALUES:
Point values are pulled from the database (ActivityType table) via the
points_mapping module. The Activity Points Config page is the single source
of truth for both REDCap imports and the survey system.

The POINT_VALUES dict below serves as fallback defaults if database
lookup fails. Edit values via the Activity Points Config page, not here.
"""

from .points_mapping import get_all_point_values, DEFAULT_POINT_VALUES

# Get point values from database, with fallback to defaults
def _load_point_values():
    """Load point values from database, falling back to defaults."""
    try:
        return get_all_point_values()
    except Exception:
        return DEFAULT_POINT_VALUES.copy()

# POINT_VALUES is loaded dynamically from database
# Edit via Activity Points Config page, not here
POINT_VALUES = _load_point_values()

# Legacy fallback values (used if database unavailable)
_FALLBACK_POINT_VALUES = {
    # Citizenship - Committees
    'cit_eval_80': 2000,
    'comm_unmc': 1000,
    'comm_nebmed': 500,
    'comm_minor': 100,
    'comm_other': 0,
    # Short-form keys used in survey choices
    'unmc': 1000,
    'nebmed': 500,
    'minor': 100,
    'other': 0,

    # Citizenship - Department Activities
    'dept_gr_host': 300,
    'dept_gr_attend': 50,
    'dept_qa_attend': 50,
    'dept_jc_host': 300,
    'dept_jc_attend': 50,
    'dept_shadow': 50,
    # Short-form keys used in survey choices
    'gr_host': 300,
    'gr_attend': 50,
    'qa_attend': 50,
    'jc_host': 300,
    'jc_attend': 50,
    'shadow': 50,

    # Education - Teaching Recognition
    'teacher_of_year': 7500,
    'teacher_of_year_honorable': 5000,
    'teaching_top25': 2500,
    'teaching_25_65': 1000,

    # Education - Lectures
    'lecture_new': 250,
    'lecture_revised': 100,
    'lecture_existing': 50,
    'lecture_orals_mm': 75,
    'sim_event_resfel': 150,
    'unmc_grand_rounds_presenter': 500,
    'com_core_new': 500,
    'com_core_revised': 250,
    'com_adhoc_new': 250,
    'com_adhoc_revised': 100,

    # Education - Board Prep
    'mock_applied_exam': 1000,
    'osce_new': 250,
    'osce_reviewer': 150,
    'mock_oral_examiner': 50,

    # Education - Mentorship & Other
    'mentorship_poster': 250,
    'mentorship_abstract': 500,
    'mentorship_presentation': 100,
    'mentorship_publication': 100,
    'resident_advisor': 50,
    'rotation_director': 500,
    'mtr_winner': 250,
    'mytip_each': 25,

    # Research
    'nih_standing': 5000,
    'nih_adhoc': 2500,
    'grant_100k_plus': 5000,
    'grant_50_99k': 3000,
    'grant_10_49k': 2500,
    'grant_under_10k': 1500,
    'grant_sub_scored': 2000,
    'grant_sub_not_scored': 500,
    'grant_sub_mentor': 250,
    'thesis_member': 1000,

    # Leadership - Education
    'course_director_national': 3000,
    'workshop_director': 500,
    'panel_moderator': 250,
    'unmc_course_director': 1000,
    'unmc_moderator': 100,
    'guideline_writing_lead': 1000,

    # Leadership - Society
    'society_bod': 5000,
    'society_rrc': 5000,
    'society_committee_chair': 3000,
    'society_committee_member': 1000,

    # Leadership - Board
    'boards_editor': 5000,
    'writing_committee_chair': 3000,
    'board_examiner': 2000,
    'question_writer': 1000,

    # Content Expert - Speaking
    'lecture_national_international': 500,
    'lecture_regional_unmc': 250,
    'workshop_national': 250,
    'workshop_regional': 100,
    'visiting_prof_grand_rounds': 500,
    'non_anes_unmc_grand_rounds': 250,

    # Content Expert - Publications
    'pub_peer_first_senior_per_if': 1000,  # Per IF point
    'pub_peer_coauth_per_if': 300,  # Per IF point
    'pub_nonpeer_first_senior': 500,
    'pub_nonpeer_coauth': 150,
    # Short-form keys used in survey choices (peer-reviewed)
    'first_senior': 1000,  # Per IF point for peer-reviewed
    'coauth': 300,  # Per IF point for peer-reviewed

    # Content Expert - Pathways
    'pathway_new': 300,
    'pathway_revised': 150,

    # Content Expert - Textbooks
    'textbook_senior_editor_major': 20000,
    'textbook_senior_editor_minor': 10000,
    'textbook_section_editor_major': 10000,
    'textbook_section_editor_minor': 5000,
    'chapter_first_senior_major': 7000,
    'chapter_first_senior_minor': 3000,
    'chapter_coauth_major': 3000,
    'chapter_coauth_minor': 500,

    # Content Expert - Abstracts
    'abstract_first_senior': 500,
    'abstract_2nd_trainee_1st': 500,
    'abstract_coauth': 250,

    # Content Expert - Journal Editorial
    'journal_editor_chief': 20000,
    'journal_section_editor': 10000,
    'journal_special_edition': 10000,
    'journal_editorial_board': 5000,
    'journal_adhoc_reviewer': 1000,
}

# Citizenship Category Configuration
CITIZENSHIP_CONFIG = {
    'name': 'Citizenship',
    'description': 'Committee work and department activities',
    'subsections': [
        {
            'key': 'committees',
            'name': 'Committee Membership',
            'carry_forward': True,  # Report once per year, carries to subsequent quarters
            'trigger': {
                'field': 'trig_cit_commit',
                'label': 'Are you serving on any committees this year (UNMC standing, Nebraska Medicine standing, or minor committees)?',
                'type': 'yesno',
                'help_text': 'Select Yes to enter details below',
                'info_text': '<strong>UNMC Standing:</strong> Admissions, GME, curriculum, senate; IRB or other with approval.<br><br><strong>NebMed Standing:</strong> Nebraska Medicine standing MEC/med staff committee.<br><br><strong>Minor:</strong> Minor or ad hoc Nebraska Medicine or UNMC committee.<br><br><strong>Other:</strong> Committees that do not fit other categories.<br><br><em>Report once per academic year - this will carry forward to subsequent quarters.</em>',
            },
            'type': 'repeating',
            'add_another_label': 'Add another committee?',
            'fields': [
                {
                    'name': 'type',
                    'label': 'Committee type',
                    'type': 'radio',
                    'required': True,
                    'choices': [
                        ('unmc', 'UNMC standing committee (admissions, GME, curriculum, senate, IRB)', POINT_VALUES['unmc']),
                        ('nebmed', 'Nebraska Medicine standing committee (MEC/med staff)', POINT_VALUES['nebmed']),
                        ('minor', 'Minor or ad hoc committee', POINT_VALUES['minor']),
                        ('other', 'Other committee', POINT_VALUES['other']),
                    ],
                },
                {
                    'name': 'name',
                    'label': 'Committee name',
                    'type': 'text',
                    'required': True,
                },
                {
                    'name': 'role',
                    'label': 'Your role (member, chair, etc.)',
                    'type': 'text',
                    'required': True,
                },
            ]
        },
        {
            'key': 'dept_activities',
            'name': 'Department Citizenship',
            'trigger': {
                'field': 'trig_cit_dept',
                'label': 'Did you participate in department citizenship activities this quarter (Grand Rounds attendance, QA attendance Journal Club attendance, or student shadowing)?',
                'type': 'yesno',
                'help_text': 'Select Yes to enter details below',
                'info_text': '<strong>Grand Rounds Host:</strong> Pick up speaker, arrive early to set up computer, introduce speaker.<br><br><strong>Grand Rounds Attendance:</strong> In-person attendance at departmental Grand Rounds.<br><br><strong>QA Meeting Attendance:</strong> In-person attendance at Quality Assurance meetings.<br><br><strong>Journal Club Host:</strong> Pick up speaker, department contact person for JC, drop off speaker.<br><br><strong>Journal Club Attendance:</strong> In-person attendance at department or division Journal Club.<br><br><strong>Student Shadowing:</strong> Per day of student shadowing.',
            },
            'type': 'repeating',
            'add_another_label': 'Add another department activity?',
            'fields': [
                {
                    'name': 'type',
                    'label': 'Activity type',
                    'type': 'radio',
                    'required': True,
                    'choices': [
                        ('gr_host', 'Grand Rounds Host', POINT_VALUES['gr_host']),
                        ('gr_attend', 'Grand Rounds Attendance (in person)', POINT_VALUES['gr_attend']),
                        ('qa_attend', 'QA Meeting Attendance (in person)', POINT_VALUES['qa_attend']),
                        ('jc_host', 'Journal Club Host', POINT_VALUES['jc_host']),
                        ('jc_attend', 'Journal Club Attendance (in person; Dept or Division Level)', POINT_VALUES['jc_attend']),
                        ('shadow', 'Student Shadowing Mentor', POINT_VALUES['shadow']),
                    ],
                },
                {
                    'name': 'date',
                    'label': 'Date of activity',
                    'type': 'date',
                    'required': True,
                },
                {
                    'name': 'description',
                    'label': 'Name of Visiting Professor, Shadow Student, or Topic',
                    'type': 'text',
                    'required': True,
                },
            ]
        }
    ]
}

# Education Category Configuration
EDUCATION_CONFIG = {
    'name': 'Education',
    'description': 'Lectures, board preparation, and mentorship activities',
    'subsections': [
        {
            'key': 'lectures',
            'name': 'Lectures & Curriculum',
            'trigger': {
                'field': 'trig_edu_lectures',
                'label': 'Did you give any lectures or contribute to curriculum this quarter?',
                'type': 'yesno',
                'help_text': 'Select Yes to enter details below',
                'info_text': '<strong>UNMC Grand Rounds:</strong> Present Grand Rounds to department.<br><br><strong>New Lecture:</strong> Write and give a new lecture.<br><br><strong>Revised Lecture:</strong> Give a revised/updated lecture.<br><br><strong>Existing Lecture:</strong> Give an unrevised lecture.<br><br><strong>M&M/Practice Oral Boards:</strong> Prepared and ran M&M or Practice Oral Boards session.<br><br><strong>Simulation Event - Resident/Fellow:</strong> Prepared and ran a simulation for Residents/Fellows (includes Cardiac and CC Fellow sims).<br><br><strong>Core COM Faculty - New:</strong> New lecture for College of Medicine core faculty.<br><br><strong>Core COM Faculty - Revised:</strong> Revised lecture for COM core faculty.<br><br><strong>Ad Hoc COM Faculty - New:</strong> New lecture for COM ad hoc faculty.<br><br><strong>Ad Hoc COM Faculty - Revised:</strong> Revised lecture for COM ad hoc faculty.',
            },
            'type': 'repeating',
            'add_another_label': 'Add another lecture?',
            'fields': [
                {
                    'name': 'type',
                    'label': 'Lecture/curriculum type',
                    'type': 'radio',
                    'required': True,
                    'choices': [
                        ('unmc_grand_rounds_presenter', 'UNMC Grand Rounds (presenter)', POINT_VALUES['unmc_grand_rounds_presenter']),
                        ('lecture_new', 'New Lecture', POINT_VALUES['lecture_new']),
                        ('lecture_revised', 'Revised Existing Lecture', POINT_VALUES['lecture_revised']),
                        ('lecture_existing', 'Existing Lecture (no revision)', POINT_VALUES['lecture_existing']),
                        ('lecture_orals_mm', 'Resident M&M and Practice Oral Boards Session', POINT_VALUES['lecture_orals_mm']),
                        ('sim_event_resfel', 'Simulation Event (Resident/Fellow)', POINT_VALUES['sim_event_resfel']),
                        ('com_core_new', 'Core COM Faculty - New Lecture', POINT_VALUES['com_core_new']),
                        ('com_core_revised', 'Core COM Faculty - Revised Lecture', POINT_VALUES['com_core_revised']),
                        ('com_adhoc_new', 'Ad Hoc COM Faculty - New Lecture', POINT_VALUES['com_adhoc_new']),
                        ('com_adhoc_revised', 'Ad Hoc COM Faculty - Revised Lecture', POINT_VALUES['com_adhoc_revised']),
                    ],
                },
                {
                    'name': 'title',
                    'label': 'Lecture title',
                    'type': 'text',
                    'required': True,
                },
                {
                    'name': 'date',
                    'label': 'Date delivered',
                    'type': 'date',
                    'required': True,
                },
            ]
        },
        {
            'key': 'board_prep',
            'name': 'Board Preparation Activities',
            'trigger': {
                'field': 'trig_edu_board',
                'label': 'Did you participate in board preparation activities this quarter (mock exams, OSCE, etc.)?',
                'type': 'yesno',
                'help_text': 'Select Yes to enter details below',
                'info_text': '<strong>Mock Applied Exam Faculty:</strong> Served as faculty for a mock applied (BASIC/ADVANCED) exam session.<br><br><strong>New OSCE Prep:</strong> Created a new OSCE scenario or video for board preparation.<br><br><strong>OSCE Review:</strong> Reviewed OSCE videos for residents - per 5 videos reviewed.<br><br><strong>OSCE/Oral Examiner:</strong> Served as an examiner for mock oral board sessions - each session.',
            },
            'type': 'repeating',
            'add_another_label': 'Add another board prep activity?',
            'fields': [
                {
                    'name': 'type',
                    'label': 'Board prep activity type',
                    'type': 'radio',
                    'required': True,
                    'choices': [
                        ('mock_applied_exam', 'Mock Applied Exam Faculty', POINT_VALUES['mock_applied_exam']),
                        ('osce_new', 'New OSCE Preparation', POINT_VALUES['osce_new']),
                        ('osce_reviewer', 'OSCE Reviewer (per 5 videos)', POINT_VALUES['osce_reviewer']),
                        ('mock_oral_examiner', 'Mock Oral Examiner (per session)', POINT_VALUES['mock_oral_examiner']),
                    ],
                },
                {
                    'name': 'date',
                    'label': 'Date of activity',
                    'type': 'date',
                    'required': True,
                },
            ]
        },
        {
            'key': 'mentorship',
            'name': 'Trainee Mentorship',
            'trigger': {
                'field': 'trig_edu_mentor',
                'label': 'Did you mentor trainees on posters, abstracts, presentations, or publications this quarter?',
                'type': 'yesno',
                'help_text': 'Select Yes to enter details below',
                'info_text': '<strong>Research Abstract:</strong> Mentored trainee on research abstract submission.<br><br><strong>Poster Presentation:</strong> Mentored trainee on poster for MARC/ASA/SCA.<br><br><strong>Presentation:</strong> Helped trainee prepare for oral presentation. Must provide evidence of mentoring or have faculty identify mentor.<br><br><strong>Publication:</strong> Guided trainee through publication process. Must provide evidence of mentoring or have faculty identify mentor.<br><br><strong>Resident Advisor:</strong> Served as formal advisor to assigned resident.',
            },
            'type': 'repeating',
            'add_another_label': 'Add another mentorship activity?',
            'fields': [
                {
                    'name': 'type',
                    'label': 'Mentorship type',
                    'type': 'radio',
                    'required': True,
                    'choices': [
                        ('mentorship_abstract', 'Research abstract mentorship', POINT_VALUES['mentorship_abstract']),
                        ('mentorship_poster', 'Poster presentation (MARC/ASA/SCA/other)', POINT_VALUES['mentorship_poster']),
                        ('mentorship_presentation', 'Presentation mentoring', POINT_VALUES['mentorship_presentation']),
                        ('mentorship_publication', 'Publication mentoring', POINT_VALUES['mentorship_publication']),
                        ('resident_advisor', 'Resident Advisor', POINT_VALUES['resident_advisor']),
                    ],
                },
                {
                    'name': 'trainee',
                    'label': 'Trainee name',
                    'type': 'text',
                    'required': True,
                },
                {
                    'name': 'title',
                    'label': 'Title of poster/abstract/presentation/publication',
                    'type': 'text',
                    'required': True,
                    'hide_for_types': ['resident_advisor'],
                },
                {
                    'name': 'meeting',
                    'label': 'Meeting/Journal Name',
                    'type': 'text',
                    'required': True,
                    'hide_for_types': ['resident_advisor'],
                },
                {
                    'name': 'date',
                    'label': 'Date',
                    'type': 'date',
                    'required': True,
                    'hide_for_types': ['resident_advisor'],
                },
            ]
        },
        {
            'key': 'rotation_director',
            'name': 'Rotation Director',
            'carry_forward': True,  # Report once per year, carries to subsequent quarters
            'trigger': {
                'field': 'trig_edu_rotation',
                'label': 'Are you serving as a Rotation Director?',
                'type': 'yesno',
                'help_text': 'Select Yes to enter rotation details below',
                'info_text': '<strong>Rotation Director:</strong> Responsible for overseeing a specific clinical rotation for residents or fellows. Content must be updated yearly. List each rotation you direct separately.<br><br><em>Report once per academic year - this will carry forward to subsequent quarters.</em>',
            },
            'type': 'repeating',
            'add_another_label': 'Add another rotation?',
            'fields': [
                {
                    'name': 'rotation_name',
                    'label': 'Name of rotation',
                    'type': 'text',
                    'required': True,
                },
            ],
            'points_per_entry': POINT_VALUES['rotation_director'],
        }
    ]
}

# Research Category Configuration
RESEARCH_CONFIG = {
    'name': 'Research',
    'description': 'Grant review, awards, submissions, and thesis committee work',
    'subsections': [
        {
            'key': 'grant_review',
            'name': 'Grant Review (NIH Study Section)',
            'carry_forward': True,
            'trigger': {
                'field': 'trig_res_review',
                'label': 'Did you participate in NIH study section grant review this quarter?',
                'type': 'yesno',
                'help_text': 'Select Yes to enter details below',
                'info_text': '<strong>NIH Study Section - Standing:</strong> Regular member of an NIH study section.<br><br><strong>NIH Study Section - Ad Hoc:</strong> Served as an ad hoc reviewer for an NIH study section.<br><br><em>Report once per academic year - this will carry forward to subsequent quarters.</em>',
            },
            'type': 'repeating',
            'add_another_label': 'Add another grant review?',
            'fields': [
                {
                    'name': 'type',
                    'label': 'Review type',
                    'type': 'radio',
                    'required': True,
                    'choices': [
                        ('nih_standing', 'NIH Study Section - Standing', POINT_VALUES['nih_standing']),
                        ('nih_adhoc', 'NIH Study Section - Ad Hoc', POINT_VALUES['nih_adhoc']),
                    ],
                },
                {
                    'name': 'study_section',
                    'label': 'Study section name',
                    'type': 'text',
                    'required': True,
                },
                {
                    'name': 'date',
                    'label': 'Review date',
                    'type': 'date',
                    'required': False,
                },
            ]
        },
        {
            'key': 'grant_awards',
            'name': 'Grant Awards',
            'trigger': {
                'field': 'trig_res_awards',
                'label': 'Did you receive any grant awards this quarter?',
                'type': 'yesno',
                'help_text': 'Select Yes to enter details below',
                'info_text': 'Report grants that were <strong>awarded</strong> (funded) this quarter. Select tier based on direct costs:<br><br><strong>$100,000+:</strong> Major grants (R01, large foundation grants).<br><br><strong>$50,000-99,999:</strong> Mid-size grants.<br><br><strong>$10,000-49,999:</strong> Smaller grants, pilot funding.<br><br><strong>Under $10,000:</strong> Small grants, seed funding.<br><br>If you are not the PI, indicate the PI name.',
            },
            'type': 'repeating',
            'add_another_label': 'Add another grant award?',
            'fields': [
                {
                    'name': 'type',
                    'label': 'Award level',
                    'type': 'radio',
                    'required': True,
                    'choices': [
                        ('grant_100k_plus', 'Grant ≥ $100,000', POINT_VALUES['grant_100k_plus']),
                        ('grant_50_99k', 'Grant $50,000-99,999', POINT_VALUES['grant_50_99k']),
                        ('grant_10_49k', 'Direct costs $10,000-49,999', POINT_VALUES['grant_10_49k']),
                        ('grant_under_10k', 'Direct costs < $10,000', POINT_VALUES['grant_under_10k']),
                    ],
                },
                {
                    'name': 'title',
                    'label': 'Grant title',
                    'type': 'text',
                    'required': True,
                },
                {
                    'name': 'agency',
                    'label': 'Funding agency',
                    'type': 'text',
                    'required': True,
                },
                {
                    'name': 'pi',
                    'label': 'PI name (if not you)',
                    'type': 'text',
                    'required': False,
                },
            ]
        },
        {
            'key': 'grant_submissions',
            'name': 'Grant Submissions',
            'trigger': {
                'field': 'trig_res_subs',
                'label': 'Did you submit any grants this quarter?',
                'type': 'yesno',
                'help_text': 'Select Yes to enter details below',
                'info_text': 'Report grants <strong>submitted</strong> this quarter (regardless of outcome):<br><br><strong>Scored:</strong> Your grant was reviewed and received a score.<br><br><strong>Not Scored:</strong> Your grant was reviewed but not scored (triaged/not discussed).<br><br><strong>Mentor:</strong> Served as mentor on trainee\'s grant submission. Must provide evidence of mentoring or have faculty identify mentor.',
            },
            'type': 'repeating',
            'add_another_label': 'Add another grant submission?',
            'fields': [
                {
                    'name': 'type',
                    'label': 'Submission type/outcome',
                    'type': 'radio',
                    'required': True,
                    'choices': [
                        ('grant_sub_scored', 'Scored submission', POINT_VALUES['grant_sub_scored']),
                        ('grant_sub_not_scored', 'Not scored submission', POINT_VALUES['grant_sub_not_scored']),
                        ('grant_sub_mentor', 'Mentor on submission', POINT_VALUES['grant_sub_mentor']),
                    ],
                },
                {
                    'name': 'title',
                    'label': 'Grant title',
                    'type': 'text',
                    'required': True,
                },
                {
                    'name': 'agency',
                    'label': 'Agency',
                    'type': 'text',
                    'required': True,
                },
                {
                    'name': 'date',
                    'label': 'Submission date',
                    'type': 'date',
                    'required': False,
                },
            ]
        },
        {
            'key': 'thesis_committees',
            'name': 'Thesis/Dissertation Committees',
            'carry_forward': True,  # Report once per year, carries to subsequent quarters
            'trigger': {
                'field': 'trig_res_thesis',
                'label': 'Are you serving on any thesis or dissertation committees?',
                'type': 'yesno',
                'help_text': 'Select Yes to enter details below',
                'info_text': '<strong>Thesis/Dissertation Committee Member:</strong> Service on graduate student thesis or dissertation committees. This includes PhD, MS, and other graduate degree committees where you serve as a member or advisor.<br><br><em>Report once per academic year - this will carry forward to subsequent quarters.</em>',
            },
            'type': 'repeating',
            'add_another_label': 'Add another committee?',
            'fields': [
                {
                    'name': 'student',
                    'label': 'Graduate student name',
                    'type': 'text',
                    'required': True,
                },
                {
                    'name': 'program',
                    'label': 'Program/degree (PhD, MS, etc.)',
                    'type': 'text',
                    'required': True,
                },
                {
                    'name': 'title',
                    'label': 'Thesis/dissertation title',
                    'type': 'text',
                    'required': True,
                },
            ],
            'points_per_entry': POINT_VALUES['thesis_member'],
        }
    ]
}

# Leadership Category Configuration
LEADERSHIP_CONFIG = {
    'name': 'Leadership',
    'description': 'Education, society, and board examination leadership roles',
    'subsections': [
        {
            'key': 'education_leadership',
            'name': 'Education Leadership',
            'trigger': {
                'field': 'trig_lead_edu',
                'label': 'Did you hold any education leadership roles this quarter (course director, workshop director, moderator, etc.)?',
                'type': 'yesno',
                'help_text': 'Select Yes to enter details below',
                'info_text': '<strong>Course Director - National/International:</strong> Directed a course at a national or international meeting (ASA, SCA, etc.).<br><br><strong>UNMC Course Director:</strong> Directed a course at UNMC.<br><br><strong>Workshop Director:</strong> Directed a hands-on workshop or skills session.<br><br><strong>Panel Moderator:</strong> Moderated a panel discussion at a meeting.<br><br><strong>UNMC Moderator:</strong> Moderated a session at UNMC.<br><br><strong>Guideline Writing:</strong> Led the development of clinical guidelines.',
            },
            'type': 'repeating',
            'add_another_label': 'Add another leadership role?',
            'fields': [
                {
                    'name': 'type',
                    'label': 'Leadership role type',
                    'type': 'radio',
                    'required': True,
                    'choices': [
                        ('course_director_national', 'Course Director (national/international)', POINT_VALUES['course_director_national']),
                        ('unmc_course_director', 'UNMC Course Director', POINT_VALUES['unmc_course_director']),
                        ('guideline_writing_lead', 'Guideline Writing Lead', POINT_VALUES['guideline_writing_lead']),
                        ('workshop_director', 'Workshop Director', POINT_VALUES['workshop_director']),
                        ('panel_moderator', 'Panel Moderator', POINT_VALUES['panel_moderator']),
                        ('unmc_moderator', 'UNMC Moderator', POINT_VALUES['unmc_moderator']),
                    ],
                },
                {
                    'name': 'name',
                    'label': 'Course/workshop/guideline name',
                    'type': 'text',
                    'required': True,
                },
                {
                    'name': 'date',
                    'label': 'Date (first day if multi-day)',
                    'type': 'date',
                    'required': False,
                },
            ]
        },
        {
            'key': 'society_leadership',
            'name': 'Society Leadership',
            'carry_forward': True,  # Report once per year, carries to subsequent quarters
            'trigger': {
                'field': 'trig_lead_society',
                'label': 'Do you hold any society leadership positions (BOD, RRC, committee chair/member)?',
                'type': 'yesno',
                'help_text': 'Select Yes to enter details below',
                'info_text': '<strong>Society BOD Member:</strong> Serve on the Board of Directors of a professional society (ASA, SCA, SOAP, etc.).<br><br><strong>Society RRC Member:</strong> Serve on the Residency Review Committee.<br><br><strong>Major Board Committee Chair:</strong> Chair a major committee of a professional society.<br><br><strong>Major Board Committee Member:</strong> Serve as a member of a major society committee.<br><br><em>Report once per academic year - this will carry forward to subsequent quarters.</em>',
            },
            'type': 'repeating',
            'add_another_label': 'Add another society role?',
            'fields': [
                {
                    'name': 'type',
                    'label': 'Society role type',
                    'type': 'radio',
                    'required': True,
                    'choices': [
                        ('society_bod', 'Society BOD Member', POINT_VALUES['society_bod']),
                        ('society_rrc', 'Society RRC Member', POINT_VALUES['society_rrc']),
                        ('society_committee_chair', 'Major Board Committee Chair', POINT_VALUES['society_committee_chair']),
                        ('society_committee_member', 'Major Board Committee Member', POINT_VALUES['society_committee_member']),
                    ],
                },
                {
                    'name': 'society',
                    'label': 'Society/organization name',
                    'type': 'text',
                    'required': True,
                },
            ]
        },
        {
            'key': 'board_leadership',
            'name': 'Board Examination Leadership',
            'carry_forward': True,  # Report once per year, carries to subsequent quarters
            'trigger': {
                'field': 'trig_lead_board',
                'label': 'Do you hold any board examination leadership roles (editor, examiner, question writer)?',
                'type': 'yesno',
                'help_text': 'Select Yes to enter details below',
                'info_text': '<strong>Boards Editor:</strong> Serve as an editor for ABA or subspecialty board examinations.<br><br><strong>Writing Committee Chair:</strong> Chair a question-writing committee for board exams.<br><br><strong>Board Examiner:</strong> Serve as an oral board examiner.<br><br><strong>Question Writer:</strong> Write questions for board examinations.<br><br><em>Report once per academic year - this will carry forward to subsequent quarters.</em>',
            },
            'type': 'repeating',
            'add_another_label': 'Add another board role?',
            'fields': [
                {
                    'name': 'type',
                    'label': 'Board role type',
                    'type': 'radio',
                    'required': True,
                    'choices': [
                        ('boards_editor', 'Boards Editor', POINT_VALUES['boards_editor']),
                        ('writing_committee_chair', 'Writing Committee Chair', POINT_VALUES['writing_committee_chair']),
                        ('board_examiner', 'Board Examiner', POINT_VALUES['board_examiner']),
                        ('question_writer', 'Question Writer', POINT_VALUES['question_writer']),
                    ],
                },
                {
                    'name': 'board',
                    'label': 'Board/organization name',
                    'type': 'text',
                    'required': True,
                },
            ]
        }
    ]
}

# Content Expert Category Configuration
CONTENT_EXPERT_CONFIG = {
    'name': 'Content Expert',
    'description': 'Speaking, publications, pathways, textbooks, abstracts, and editorial work',
    'subsections': [
        {
            'key': 'speaking',
            'name': 'Invited Speaking',
            'trigger': {
                'field': 'trig_ce_speaking',
                'label': 'Did you give any invited lectures or workshops this quarter (outside of regular UNMC teaching)?',
                'type': 'yesno',
                'help_text': 'Select Yes to enter details below',
                'info_text': 'Report <strong>invited</strong> speaking engagements outside of your regular UNMC teaching duties:<br><br><strong>International/National Lecture:</strong> Invited lecture at a national or international meeting.<br><br><strong>Regional/UNMC Lecture:</strong> Invited lecture at a regional meeting or UNMC event.<br><br><strong>National Workshop:</strong> Hands-on workshop at national meeting.<br><br><strong>Regional/UNMC Workshop:</strong> Hands-on workshop at regional meeting or UNMC.<br><br><strong>Visiting Professor Grand Rounds:</strong> Invited as visiting professor to give Grand Rounds elsewhere.<br><br><strong>Non-Anesth UNMC Grand Rounds:</strong> Present Grand Rounds to other department at UNMC.',
            },
            'type': 'repeating',
            'add_another_label': 'Add another speaking engagement?',
            'fields': [
                {
                    'name': 'type',
                    'label': 'Speaking type',
                    'type': 'radio',
                    'required': True,
                    'choices': [
                        ('lecture_national_international', 'International/National Lecture', POINT_VALUES['lecture_national_international']),
                        ('visiting_prof_grand_rounds', 'Visiting Professor Grand Rounds', POINT_VALUES['visiting_prof_grand_rounds']),
                        ('non_anes_unmc_grand_rounds', 'Non-Anesthesiology UNMC Grand Rounds', POINT_VALUES['non_anes_unmc_grand_rounds']),
                        ('lecture_regional_unmc', 'Regional/UNMC Lecture', POINT_VALUES['lecture_regional_unmc']),
                        ('workshop_national', 'National Workshop', POINT_VALUES['workshop_national']),
                        ('workshop_regional', 'Regional/UNMC Workshop', POINT_VALUES['workshop_regional']),
                    ],
                },
                {
                    'name': 'title',
                    'label': 'Title of talk/workshop',
                    'type': 'text',
                    'required': True,
                },
                {
                    'name': 'conference',
                    'label': 'Conference/meeting name',
                    'type': 'text',
                    'required': True,
                },
                {
                    'name': 'date',
                    'label': 'Date',
                    'type': 'date',
                    'required': False,
                },
                {
                    'name': 'location',
                    'label': 'Location',
                    'type': 'text',
                    'required': False,
                },
            ]
        },
        {
            'key': 'publications_peer',
            'name': 'Peer-Reviewed Publications',
            'trigger': {
                'field': 'trig_ce_peer_pub',
                'label': 'Did you publish any peer-reviewed articles this quarter?',
                'type': 'yesno',
                'help_text': 'Select Yes to enter details below',
                'info_text': 'Report peer-reviewed publications that were <strong>published</strong> (not just accepted) this quarter.<br><br>Points are calculated based on your role and the journal\'s Impact Factor (IF):<br><br><strong>First/Senior Author:</strong> Primary or corresponding author. IF = 1 if low, max IF = 15.<br><br><strong>Co-author:</strong> Contributing author. Same IF calculation.<br><br>Enter the journal\'s Impact Factor (capped at 15 for calculation purposes).',
            },
            'type': 'repeating',
            'add_another_label': 'Add another publication?',
            'fields': [
                {
                    'name': 'role',
                    'label': 'Your role',
                    'type': 'radio',
                    'required': True,
                    'choices': [
                        ('first_senior', 'First or Senior Author (1000 pts per IF point)', POINT_VALUES['pub_peer_first_senior_per_if']),
                        ('coauth', 'Co-author (300 pts per IF point)', POINT_VALUES['pub_peer_coauth_per_if']),
                    ],
                },
                {
                    'name': 'title',
                    'label': 'Publication title',
                    'type': 'text',
                    'required': True,
                },
                {
                    'name': 'journal',
                    'label': 'Journal name',
                    'type': 'text',
                    'required': True,
                },
                {
                    'name': 'impact_factor',
                    'label': 'Journal Impact Factor (max 15)',
                    'type': 'number',
                    'required': True,
                    'max': 15,
                },
                {
                    'name': 'date',
                    'label': 'Publication date',
                    'type': 'date',
                    'required': False,
                },
                {
                    'name': 'doi',
                    'label': 'DOI',
                    'type': 'text',
                    'required': False,
                },
            ]
        },
        {
            'key': 'publications_nonpeer',
            'name': 'Non-Peer-Reviewed Publications',
            'trigger': {
                'field': 'trig_ce_nonpeer_pub',
                'label': 'Did you publish any non-peer-reviewed articles this quarter (newsletters, trade publications, etc.)?',
                'type': 'yesno',
                'help_text': 'Select Yes to enter details below',
                'info_text': 'Report non-peer-reviewed publications such as newsletter articles, trade publications, blog posts for professional organizations, society bulletins, online educational content.<br><br><strong>First/Senior Author:</strong> Primary author of the publication.<br><br><strong>Co-author:</strong> Contributing author.',
            },
            'type': 'repeating',
            'add_another_label': 'Add another publication?',
            'fields': [
                {
                    'name': 'role',
                    'label': 'Your role',
                    'type': 'radio',
                    'required': True,
                    'choices': [
                        ('first_senior', 'First or Senior Author', POINT_VALUES['pub_nonpeer_first_senior']),
                        ('coauth', 'Co-author', POINT_VALUES['pub_nonpeer_coauth']),
                    ],
                },
                {
                    'name': 'title',
                    'label': 'Publication title',
                    'type': 'text',
                    'required': True,
                },
                {
                    'name': 'outlet',
                    'label': 'Journal/newsletter/outlet',
                    'type': 'text',
                    'required': True,
                },
                {
                    'name': 'date',
                    'label': 'Publication date',
                    'type': 'date',
                    'required': False,
                },
            ]
        },
        {
            'key': 'pathways',
            'name': 'Clinical Pathways',
            'carry_forward': True,  # Report once per year, carries to subsequent quarters
            'trigger': {
                'field': 'trig_ce_pathways',
                'label': 'Did you create or revise any clinical pathways this year?',
                'type': 'yesno',
                'help_text': 'Select Yes to enter details below',
                'info_text': 'Clinical pathways are standardized care protocols for specific clinical situations.<br><br><strong>New Pathway:</strong> Created a new pathway from scratch.<br><br><strong>Review and Update Existing Pathway:</strong> Made significant updates to an existing pathway.<br><br><em>Report once per academic year - this will carry forward to subsequent quarters.</em>',
            },
            'type': 'repeating',
            'add_another_label': 'Add another pathway?',
            'fields': [
                {
                    'name': 'type',
                    'label': 'Pathway activity',
                    'type': 'radio',
                    'required': True,
                    'choices': [
                        ('pathway_new', 'New Clinical Pathway', POINT_VALUES['pathway_new']),
                        ('pathway_revised', 'Revised Clinical Pathway', POINT_VALUES['pathway_revised']),
                    ],
                },
                {
                    'name': 'name',
                    'label': 'Pathway name',
                    'type': 'text',
                    'required': True,
                },
                {
                    'name': 'division',
                    'label': 'What Division oversees this Pathway?',
                    'type': 'text',
                    'required': True,
                },
            ]
        },
        {
            'key': 'textbooks',
            'name': 'Textbook Contributions',
            'trigger': {
                'field': 'trig_ce_textbooks',
                'label': 'Did you contribute to any textbooks this quarter (editor, chapter author)?',
                'type': 'yesno',
                'help_text': 'Select Yes to enter details below',
                'info_text': '<strong>Major textbooks:</strong> Widely-used reference texts (Miller\'s Anesthesia, Barash, etc.)<br><strong>Minor textbooks:</strong> Subspecialty or less widely-used texts<br><br><strong>Senior Editor - Major:</strong> Overall editor of major textbook.<br><br><strong>Senior Editor - Minor:</strong> Overall editor of minor textbook.<br><br><strong>Section Editor - Major:</strong> Editor of a section in major textbook.<br><br><strong>Section Editor - Minor:</strong> Editor of a section in minor textbook.<br><br><strong>Chapter First/Senior Author - Major:</strong> Primary author of chapter in major textbook.<br><br><strong>Chapter First/Senior Author - Minor:</strong> Primary author of chapter in minor textbook.<br><br><strong>Chapter Co-Author - Major:</strong> Contributing author in major textbook.<br><br><strong>Chapter Co-Author - Minor:</strong> Contributing author in minor textbook.',
            },
            'type': 'repeating',
            'add_another_label': 'Add another textbook contribution?',
            'fields': [
                {
                    'name': 'type',
                    'label': 'Your role',
                    'type': 'radio',
                    'required': True,
                    'choices': [
                        ('textbook_senior_editor_major', 'Textbook Senior Editor (Major)', POINT_VALUES['textbook_senior_editor_major']),
                        ('textbook_senior_editor_minor', 'Textbook Senior Editor (Minor)', POINT_VALUES['textbook_senior_editor_minor']),
                        ('textbook_section_editor_major', 'Textbook Section Editor (Major)', POINT_VALUES['textbook_section_editor_major']),
                        ('textbook_section_editor_minor', 'Textbook Section Editor (Minor)', POINT_VALUES['textbook_section_editor_minor']),
                        ('chapter_first_senior_major', 'Chapter First/Senior Author (Major)', POINT_VALUES['chapter_first_senior_major']),
                        ('chapter_first_senior_minor', 'Chapter First/Senior Author (Minor)', POINT_VALUES['chapter_first_senior_minor']),
                        ('chapter_coauth_major', 'Chapter Co-author (Major)', POINT_VALUES['chapter_coauth_major']),
                        ('chapter_coauth_minor', 'Chapter Co-author (Minor)', POINT_VALUES['chapter_coauth_minor']),
                    ],
                },
                {
                    'name': 'textbook',
                    'label': 'Textbook title',
                    'type': 'text',
                    'required': True,
                },
                {
                    'name': 'chapter',
                    'label': 'Chapter title (if applicable)',
                    'type': 'text',
                    'required': False,
                },
            ]
        },
        {
            'key': 'abstracts',
            'name': 'Research Abstracts',
            'trigger': {
                'field': 'trig_ce_abstracts',
                'label': 'Did you present any research abstracts/posters this quarter?',
                'type': 'yesno',
                'help_text': 'Select Yes to enter details below',
                'info_text': 'Report abstracts/posters <strong>presented</strong> at meetings this quarter (MARC, ASA, SCA, etc.):<br><br><strong>First/Senior Author:</strong> You are the presenting author or senior/corresponding author.<br><br><strong>Second Author with Trainee First Author:</strong> A trainee is first author and you are second (mentorship credit).<br><br><strong>Co-author:</strong> You are a contributing author but not first, second, or senior.',
            },
            'type': 'repeating',
            'add_another_label': 'Add another abstract?',
            'fields': [
                {
                    'name': 'role',
                    'label': 'Your role',
                    'type': 'radio',
                    'required': True,
                    'choices': [
                        ('abstract_first_senior', 'First or Senior Author', POINT_VALUES['abstract_first_senior']),
                        ('abstract_2nd_trainee_1st', '2nd Author with Trainee as 1st', POINT_VALUES['abstract_2nd_trainee_1st']),
                        ('abstract_coauth', 'Co-author', POINT_VALUES['abstract_coauth']),
                    ],
                },
                {
                    'name': 'title',
                    'label': 'Abstract/poster title',
                    'type': 'text',
                    'required': True,
                },
                {
                    'name': 'meeting',
                    'label': 'Meeting (MARC, ASA, SCA, etc.)',
                    'type': 'text',
                    'required': True,
                },
                {
                    'name': 'date',
                    'label': 'Date',
                    'type': 'date',
                    'required': False,
                },
                {
                    'name': 'location',
                    'label': 'Location',
                    'type': 'text',
                    'required': False,
                },
            ]
        },
        {
            'key': 'journal_editorial',
            'name': 'Journal Editorial Roles',
            'carry_forward': True,  # Report once per year, carries to subsequent quarters
            'trigger': {
                'field': 'trig_ce_editorial',
                'label': 'Do you hold any journal editorial positions?',
                'type': 'yesno',
                'help_text': 'Select Yes to enter details below',
                'info_text': '<strong>Editor-in-Chief:</strong> Chief editor of a peer-reviewed journal.<br><br><strong>Section Editor:</strong> Editor of a specific section within a journal.<br><br><strong>Special Edition Editor:</strong> Guest editor for a special issue or supplement.<br><br><strong>Editorial Board Member:</strong> Serve on the editorial board of a peer-reviewed journal.<br><br><strong>Ad Hoc Reviewer:</strong> Must complete 4+ reviews in the same year for the same journal to qualify.<br><br><em>Report once per academic year - this will carry forward to subsequent quarters.</em>',
            },
            'type': 'repeating',
            'add_another_label': 'Add another editorial role?',
            'fields': [
                {
                    'name': 'type',
                    'label': 'Editorial role',
                    'type': 'radio',
                    'required': True,
                    'choices': [
                        ('journal_editor_chief', 'Journal Editor-in-Chief', POINT_VALUES['journal_editor_chief']),
                        ('journal_section_editor', 'Journal Section Editor', POINT_VALUES['journal_section_editor']),
                        ('journal_special_edition', 'Journal Special Edition Editor', POINT_VALUES['journal_special_edition']),
                        ('journal_editorial_board', 'Editorial Board Member', POINT_VALUES['journal_editorial_board']),
                        ('journal_adhoc_reviewer', 'Ad Hoc Reviewer (4+ reviews/year for same journal)', POINT_VALUES['journal_adhoc_reviewer']),
                    ],
                },
                {
                    'name': 'journal',
                    'label': 'Journal name',
                    'type': 'text',
                    'required': True,
                },
            ]
        }
    ]
}

# All categories
SURVEY_CATEGORIES = {
    'citizenship': CITIZENSHIP_CONFIG,
    'education': EDUCATION_CONFIG,
    'research': RESEARCH_CONFIG,
    'leadership': LEADERSHIP_CONFIG,
    'content_expert': CONTENT_EXPERT_CONFIG,
}

# Category order for navigation
CATEGORY_ORDER = ['citizenship', 'education', 'research', 'leadership', 'content_expert']

# Category display names
CATEGORY_NAMES = {
    'citizenship': 'Citizenship',
    'education': 'Education',
    'research': 'Research',
    'leadership': 'Leadership',
    'content_expert': 'Content Expert',
}


def get_default_config():
    """Get the default survey configuration from this file."""
    return {
        'point_values': POINT_VALUES,
        'categories': SURVEY_CATEGORIES,
        'category_order': CATEGORY_ORDER,
        'category_names': CATEGORY_NAMES,
    }


def get_survey_config_for_year(academic_year=None):
    """
    Get survey configuration for a specific academic year.

    Args:
        academic_year: AcademicYear model instance, or None for default

    Returns:
        Config dict with point_values, categories, category_order, category_names
    """
    if academic_year is not None:
        try:
            from .models import SurveyConfigOverride
            override = SurveyConfigOverride.get_config_for_year(academic_year)
            if override and override.config_json:
                return override.config_json
        except Exception:
            pass  # Fall back to default if any error

    # Return default config
    return get_default_config()


def get_active_survey_config():
    """
    Get the active survey configuration (legacy - no year context).

    Deprecated: Use get_survey_config_for_year() with academic year instead.
    Returns database override if active, otherwise returns default config.
    """
    try:
        from .models import SurveyConfigOverride
        override = SurveyConfigOverride.get_active_config()
        if override and override.config_json:
            return override.config_json
    except Exception:
        pass  # Fall back to default if any error

    return get_default_config()


def get_category_config(category_key, academic_year=None):
    """Get configuration for a specific category."""
    config = get_survey_config_for_year(academic_year)
    categories = config.get('categories', SURVEY_CATEGORIES)
    return categories.get(category_key)


def calculate_subsection_points(subsection_config, subsection_data):
    """
    Calculate points for a subsection based on config and submitted data.

    Args:
        subsection_config: The config dict for this subsection
        subsection_data: The data dict for this subsection

    Returns:
        Total points for this subsection
    """
    total = 0

    # Single type (like rotation_director) - just check trigger
    if subsection_config['type'] == 'single':
        trigger_value = subsection_data.get('trigger')
        if trigger_value == 'yes':
            total = subsection_config.get('points_if_yes', 0)
        return total

    # Repeating type - sum points from entries
    entries = subsection_data.get('entries', [])

    # Filter out carried-forward entries - they were already counted in their source quarter
    new_entries = [e for e in entries if not e.get('_carried_from')]

    # Check if this subsection uses flat points per entry (e.g., thesis committees)
    points_per_entry = subsection_config.get('points_per_entry', 0)
    if points_per_entry:
        return len(new_entries) * points_per_entry

    for entry in new_entries:
        entry_points = 0

        # Find the field with points (usually 'type' or 'role')
        for field in subsection_config['fields']:
            if field['type'] == 'radio' and 'choices' in field:
                selected_value = entry.get(field['name'])
                if selected_value and selected_value != '99':
                    # Find points for this choice
                    for choice_val, choice_label, points in field['choices']:
                        if choice_val == selected_value:
                            entry_points = points
                            break
                elif not selected_value and entry:
                    # Fallback: entry exists but no type selected (imported data)
                    # Give minimum non-zero points from choices
                    non_zero_points = [pts for _, _, pts in field['choices'] if pts > 0]
                    if non_zero_points:
                        entry_points = min(non_zero_points)

        # Special handling for peer-reviewed publications (multiply by impact factor)
        if subsection_config['key'] == 'publications_peer':
            try:
                impact_factor = min(float(entry.get('impact_factor', 0)), 15)  # Max 15
                entry_points = int(entry_points * impact_factor)
            except (ValueError, TypeError):
                pass

        # Special handling for MyTIP (multiply by count)
        if entry.get('type') == 'mytip_each' and entry.get('count'):
            try:
                count = int(entry.get('count', 1))
                entry_points = entry_points * count
                # Cap at 3000 per year (120 mentions at 25 pts each)
                entry_points = min(entry_points, 3000)
            except (ValueError, TypeError):
                pass

        total += entry_points

    return total


def calculate_category_points(category_key, response_data):
    """
    Calculate total points for a category.

    Args:
        category_key: The category (e.g., 'citizenship')
        response_data: Dict with subsection keys mapping to subsection data

    Returns:
        Total points for the category
    """
    config = get_category_config(category_key)
    if not config:
        return 0

    total = 0
    for subsection in config['subsections']:
        subsection_key = subsection['key']
        subsection_data = response_data.get(subsection_key, {})
        total += calculate_subsection_points(subsection, subsection_data)

    return total


def get_next_category(current_category):
    """Get the next category in sequence."""
    try:
        idx = CATEGORY_ORDER.index(current_category)
        if idx < len(CATEGORY_ORDER) - 1:
            return CATEGORY_ORDER[idx + 1]
    except ValueError:
        pass
    return None


def get_prev_category(current_category):
    """Get the previous category in sequence."""
    try:
        idx = CATEGORY_ORDER.index(current_category)
        if idx > 0:
            return CATEGORY_ORDER[idx - 1]
    except ValueError:
        pass
    return None


def get_carry_forward_subsections():
    """
    Get all subsection keys that should carry forward across quarters.

    Returns:
        dict: {category_key: [subsection_keys]} for carry-forward subsections
    """
    result = {}
    for cat_key, cat_config in SURVEY_CATEGORIES.items():
        carry_forward_subs = []
        for sub in cat_config.get('subsections', []):
            if sub.get('carry_forward', False):
                carry_forward_subs.append(sub['key'])
        if carry_forward_subs:
            result[cat_key] = carry_forward_subs
    return result


def extract_carry_forward_data(response_data):
    """
    Extract only carry-forward items from a survey response.

    Args:
        response_data: Full response data dict

    Returns:
        dict: Only the carry-forward subsections with their data
    """
    carry_forward_subs = get_carry_forward_subsections()
    result = {}

    for cat_key, sub_keys in carry_forward_subs.items():
        cat_data = response_data.get(cat_key, {})
        for sub_key in sub_keys:
            sub_data = cat_data.get(sub_key, {})
            # Only include if there are actual entries
            if sub_data.get('trigger') == 'yes' and sub_data.get('entries'):
                if cat_key not in result:
                    result[cat_key] = {}
                result[cat_key][sub_key] = sub_data

    return result
