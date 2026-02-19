"""
Mapping between survey_config.py keys and ActivityType.data_variable.

This allows the survey system to pull point values from the database
(ActivityType table) while using its own internal key names.

The ActivityType table is the single source of truth for point values.
Both REDCap imports and the survey system use these values.
"""

# Map survey_config.py keys to ActivityType.data_variable
# Format: 'survey_key': 'DATABASE_VARIABLE'

SURVEY_TO_DB_MAPPING = {
    # === Citizenship - Committees ===
    'comm_unmc': 'CIT_COMMIT_UNMC',
    'comm_nebmed': 'CIT_COMMIT_NEBMED',
    'comm_minor': 'CIT_COMMIT_MINOR',
    'comm_other': 'CIT_COMMIT_OTHER',
    'unmc': 'CIT_COMMIT_UNMC',
    'nebmed': 'CIT_COMMIT_NEBMED',
    'minor': 'CIT_COMMIT_MINOR',
    'other': 'CIT_COMMIT_OTHER',

    # === Citizenship - Department Activities ===
    'dept_gr_host': 'CIT_DEPT_GR_HOST',
    'dept_gr_attend': 'CIT_DEPT_GR_ATTEND',
    'dept_qa_attend': 'CIT_DEPT_QA_ATTEND',
    'dept_jc_host': 'CIT_DEPT_JC_HOST',
    'dept_jc_attend': 'CIT_DEPT_JC_ATTEND',
    'dept_shadow': 'CIT_DEPT_SHDW_HOST',
    'gr_host': 'CIT_DEPT_GR_HOST',
    'gr_attend': 'CIT_DEPT_GR_ATTEND',
    'qa_attend': 'CIT_DEPT_QA_ATTEND',
    'jc_host': 'CIT_DEPT_JC_HOST',
    'jc_attend': 'CIT_DEPT_JC_ATTEND',
    'shadow': 'CIT_DEPT_SHDW_HOST',

    # === Citizenship - Evaluations ===
    'cit_eval_80': 'CIT_EVAL_80%',

    # === Education - Teaching Recognition ===
    'teacher_of_year': 'EDU_TEACH_TEACHYEAR',
    'teacher_of_year_honorable': 'EDU_TEACH_TEACHHONMEN',
    'teaching_top25': 'EDU_TEACH_TOP25',
    'teaching_25_65': 'EDU_TEACH_2565',

    # === Education - Lectures ===
    'lecture_new': 'EDU_CIRC_LEC_NEW',
    'lecture_revised': 'EDU_CIRC_LEC_REV',
    'lecture_existing': 'EDU_CIRC_LEC_OLD',
    'lecture_orals_mm': 'EDU_CIRC_LEC_ORALS',
    'sim_event_resfel': 'EDU_CLIN_SIM_SESSION',
    'unmc_grand_rounds_presenter': 'EDU_CIRC_UNMC_GR',
    'com_core_new': 'EDU_CIRC_LEC_COM_CORE_NEW',
    'com_core_revised': 'EDU_CIRC_LEC_COM_CORE_REV',
    'com_adhoc_new': 'EDU_CIRC_LEC_COM_ADHOC_NEW',
    'com_adhoc_revised': 'EDU_CIRC_LEC_COM_ADHOC_REV',

    # === Education - Board Prep ===
    'mock_applied_exam': 'EDU_BRD_APPLIED_EXAM',
    'osce_new': 'EDU_BRD_OSCE_PREP_NEW',
    'osce_reviewer': 'EDU_BRD_OSCE_REV',
    'mock_oral_examiner': 'EDU_BRD_OSCE_EXM',

    # === Education - Mentorship ===
    'mentorship_poster': 'EDU_MENT_POSTER',
    'mentorship_abstract': 'EDU_MENT_ABSTRACT',
    'mentorship_presentation': 'EDU_MENT_PRESENT_MENT',
    'mentorship_publication': 'EDU_MENT_PUB_MENT',
    'resident_advisor': 'EDU_MENT_RESADV',

    # === Education - Other ===
    'rotation_director': 'EDU_CLIN_ROTDIR',
    'mtr_winner': 'EDU_FDBK_MTR_WIN',
    'mytip_each': 'EDU_FDBK_MTR_COUNT',

    # === Research - Grant Review ===
    'nih_standing': 'RSCH_EXGNT_REV_NIH_STAND',
    'nih_adhoc': 'RSCH_EXGNT_REV_NIH_ADHOC',

    # === Research - Grant Awards ===
    'grant_100k_plus': 'RSCH_EXGNT_AWARD_100k',
    'grant_50_99k': 'RSCH_EXGNT_AWARD_50-99k',
    'grant_10_49k': 'RSCH_EXGNT_AWARD_10-49k',
    'grant_under_10k': 'RSCH_EXGNT_AWARD_10k',

    # === Research - Grant Submissions ===
    'grant_sub_scored': 'RSCH_GNT_SUB_SCORE',
    'grant_sub_not_scored': 'RSCH_GNT_SUB_NOSCORE',
    'grant_sub_mentor': 'RSCH_GNT_SUB_MENT',

    # === Research - Thesis ===
    'thesis_member': 'RSCH_THESIS_MBR',

    # === Leadership - Education ===
    'course_director_national': 'LEAD_EDU_DIR_COURSE',
    'workshop_director': 'LEAD_EDU_DIR_WRKSHP',
    'panel_moderator': 'LEAD_EDU_MOD',
    'unmc_course_director': 'LEAD_EDU_DIR_COURSE_UNMC',
    'unmc_moderator': 'LEAD_EDU_MOD_UNMC',
    'guideline_writing_lead': 'LEAD_EDU_GUIDELINE',

    # === Leadership - Society ===
    'society_bod': 'LEAD_SOC_MBR_BOD',
    'society_rrc': 'LEAD_SOC_MBR_RRC',
    'society_committee_chair': 'LEAD_SOC_CHAIR_MAJOR',
    'society_committee_member': 'LEAD_SOC_MBR_MAJOR',

    # === Leadership - Board ===
    'boards_editor': 'LEAD_BOARD_EDITOR',
    'writing_committee_chair': 'LEAD_BOARD_CHAIR_WRITE',
    'board_examiner': 'LEAD_BOARD_EXAMINER',
    'question_writer': 'LEAD_BOARD_QWRITE',

    # === Content Expert - Speaking ===
    'lecture_national_international': 'EXPT_SPK_NAT_LEC',
    'lecture_regional_unmc': 'EXPT_SPK_REG_LEC',
    'workshop_national': 'EXPT_SPK_NAT_WRKSHP',
    'workshop_regional': 'EXPT_SPK_REG_WRKSHP',
    'visiting_prof_grand_rounds': 'EXPT_SPK_VPGR',
    'non_anes_unmc_grand_rounds': 'EXPT_SPK_VPGR_UNMC',

    # === Content Expert - Publications ===
    'pub_peer_first_senior_per_if': 'EXPT_PUB_PEER_AUTH',
    'pub_peer_coauth_per_if': 'EXPT_PUB_PEER_COAUTH',
    'pub_nonpeer_first_senior': 'EXPT_PUB_NONPEER_AUTH',
    'pub_nonpeer_coauth': 'EXPT_PUB_NONPEER_COAUTH',
    'first_senior': 'EXPT_PUB_PEER_AUTH',  # Short form for peer-reviewed
    'coauth': 'EXPT_PUB_PEER_COAUTH',  # Short form for peer-reviewed

    # === Content Expert - Pathways ===
    'pathway_new': 'EXPT_PATH_NEW',
    'pathway_revised': 'EXPT_PATH_REV',

    # === Content Expert - Textbooks ===
    'textbook_senior_editor_major': 'EXPT_TXT_SENEDT_MAJOR',
    'textbook_senior_editor_minor': 'EXPT_TXT_SENEDT_MINOR',
    'textbook_section_editor_major': 'EXPT_TXT_SECEDT_MAJOR',
    'textbook_section_editor_minor': 'EXPT_TXT_SECEDT_MINOR',
    'chapter_first_senior_major': 'EXPT_TEXT_CHAP_AUTH_MAJOR',
    'chapter_first_senior_minor': 'EXPT_TEXT_CHAP_AUTH_MINOR',
    'chapter_coauth_major': 'EXPT_TEXT_CHAP_COAUTH_MAJOR',
    'chapter_coauth_minor': 'EXPT_TEXT_CHAP_COAUTH_MINOR',

    # === Content Expert - Abstracts ===
    'abstract_first_senior': 'EXPT_RSCHABST_AUTH',
    'abstract_2nd_trainee_1st': 'EXPT_RSCHABST_AUTH_MENT',
    'abstract_coauth': 'EXPT_RSCHABST_COAUTH',

    # === Content Expert - Journal Editorial ===
    'journal_editor_chief': 'EXPT_JOL_EDITOR',
    'journal_section_editor': 'EXPT_JOL_SECEDIT',
    'journal_special_edition': 'EXPT_JOL_SPECEDIT',
    'journal_editorial_board': 'EXPT_JOL_EDITBRD',
    'journal_adhoc_reviewer': 'EXPT_JOL_EDITADHOC',
}

# Default point values (fallback if database lookup fails)
# These should match the database values
DEFAULT_POINT_VALUES = {
    'comm_unmc': 1000,
    'comm_nebmed': 500,
    'comm_minor': 100,
    'comm_other': 0,
    'unmc': 1000,
    'nebmed': 500,
    'minor': 100,
    'other': 0,
    'dept_gr_host': 300,
    'dept_gr_attend': 50,
    'dept_qa_attend': 50,
    'dept_jc_host': 300,
    'dept_jc_attend': 50,
    'dept_shadow': 50,
    'gr_host': 300,
    'gr_attend': 50,
    'qa_attend': 50,
    'jc_host': 300,
    'jc_attend': 50,
    'shadow': 50,
    'cit_eval_80': 2000,
    'teacher_of_year': 7500,
    'teacher_of_year_honorable': 5000,
    'teaching_top25': 2500,
    'teaching_25_65': 1000,
    'lecture_new': 250,
    'lecture_revised': 100,
    'lecture_existing': 50,
    'lecture_orals_mm': 75,
    'sim_event_resfel': 150,  # Matches DB: EDU_CLIN_SIM_SESSION
    'unmc_grand_rounds_presenter': 500,
    'com_core_new': 500,
    'com_core_revised': 250,
    'com_adhoc_new': 250,
    'com_adhoc_revised': 100,
    'mock_applied_exam': 1000,
    'osce_new': 250,
    'osce_reviewer': 150,
    'mock_oral_examiner': 50,
    'mentorship_poster': 250,
    'mentorship_abstract': 500,
    'mentorship_presentation': 100,
    'mentorship_publication': 100,
    'resident_advisor': 50,
    'rotation_director': 500,
    'mtr_winner': 250,
    'mytip_each': 25,
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
    'course_director_national': 3000,
    'workshop_director': 500,
    'panel_moderator': 250,
    'unmc_course_director': 1000,
    'unmc_moderator': 100,
    'guideline_writing_lead': 1000,
    'society_bod': 5000,
    'society_rrc': 5000,
    'society_committee_chair': 3000,
    'society_committee_member': 1000,
    'boards_editor': 5000,
    'writing_committee_chair': 3000,
    'board_examiner': 2000,
    'question_writer': 1000,
    'lecture_national_international': 500,
    'lecture_regional_unmc': 250,
    'workshop_national': 250,
    'workshop_regional': 100,
    'visiting_prof_grand_rounds': 500,
    'non_anes_unmc_grand_rounds': 250,
    'pub_peer_first_senior_per_if': 1000,
    'pub_peer_coauth_per_if': 300,
    'pub_nonpeer_first_senior': 500,
    'pub_nonpeer_coauth': 150,
    'first_senior': 1000,
    'coauth': 300,
    'pathway_new': 300,
    'pathway_revised': 150,
    'textbook_senior_editor_major': 20000,
    'textbook_senior_editor_minor': 10000,
    'textbook_section_editor_major': 10000,
    'textbook_section_editor_minor': 5000,
    'chapter_first_senior_major': 7000,
    'chapter_first_senior_minor': 3000,
    'chapter_coauth_major': 3000,
    'chapter_coauth_minor': 500,
    'abstract_first_senior': 500,
    'abstract_2nd_trainee_1st': 500,
    'abstract_coauth': 250,
    'journal_editor_chief': 20000,
    'journal_section_editor': 10000,
    'journal_special_edition': 10000,
    'journal_editorial_board': 5000,
    'journal_adhoc_reviewer': 1000,
}


def get_point_value(survey_key):
    """
    Get point value for a survey_config key from the database.

    Falls back to DEFAULT_POINT_VALUES if database lookup fails.
    """
    db_variable = SURVEY_TO_DB_MAPPING.get(survey_key)

    if db_variable is None:
        # No mapping exists, use default (probably 0 points like 'other')
        return DEFAULT_POINT_VALUES.get(survey_key, 0)

    try:
        from reports_app.models import ActivityType
        activity = ActivityType.objects.filter(data_variable=db_variable).first()
        if activity:
            return activity.base_points
    except Exception:
        pass

    # Fallback to default
    return DEFAULT_POINT_VALUES.get(survey_key, 0)


def get_all_point_values():
    """
    Get all point values, pulling from database where possible.

    Returns a dict with all survey_config keys and their point values.
    """
    result = DEFAULT_POINT_VALUES.copy()

    try:
        from reports_app.models import ActivityType

        # Build reverse mapping: DB variable -> survey keys
        db_to_survey = {}
        for survey_key, db_var in SURVEY_TO_DB_MAPPING.items():
            if db_var:
                if db_var not in db_to_survey:
                    db_to_survey[db_var] = []
                db_to_survey[db_var].append(survey_key)

        # Fetch all ActivityTypes and update result
        for activity in ActivityType.objects.filter(is_active=True):
            survey_keys = db_to_survey.get(activity.data_variable, [])
            for survey_key in survey_keys:
                result[survey_key] = activity.base_points
    except Exception:
        pass

    return result
