"""
URL configuration for reports_app.
"""
from django.urls import path
from . import views

urlpatterns = [
    # Home / Dashboard
    path('', views.index, name='index'),

    # === Academic Year Management ===
    path('years/', views.academic_year_list, name='year_list'),
    path('years/set-current/', views.set_current_year, name='set_current_year'),
    path('years/select/', views.select_year, name='select_year'),
    path('years/create/', views.create_year, name='create_year'),
    path('toggle-review-mode/', views.toggle_review_mode, name='toggle_review_mode'),

    # === Faculty Roster Management ===
    path('roster/', views.faculty_roster, name='roster'),
    path('roster/add/', views.faculty_add, name='faculty_add'),
    path('roster/import/', views.import_roster, name='import_roster'),
    path('roster/export-portal-links/', views.export_portal_links, name='export_portal_links'),
    path('roster/export/', views.export_roster, name='export_roster'),
    path('roster/<str:email>/', views.faculty_detail, name='faculty_detail'),
    path('roster/<str:email>/edit/', views.faculty_edit, name='faculty_edit'),
    path('roster/<str:email>/toggle-ccc/', views.toggle_ccc, name='toggle_ccc'),

    # === Faculty Summary ===
    path('faculty-summary/', views.faculty_summary, name='faculty_summary'),

    # === Survey Data Import (Database-backed) ===
    path('import/', views.import_survey, name='import_survey'),
    path('import/review/', views.import_review, name='import_review'),
    path('import/confirm/', views.import_confirm, name='import_confirm'),
    path('import/history/', views.import_history, name='import_history'),

    # === Departmental Data Entry ===
    path('departmental/', views.departmental_data, name='departmental_data'),
    path('departmental/update/', views.departmental_update, name='departmental_update'),
    path('departmental/<str:year_code>/', views.departmental_data, name='departmental_data_year'),

    # === Legacy Session-Based Upload (for quick one-off use) ===
    path('quick-upload/', views.upload_csv, name='upload_csv'),
    path('quick/select/', views.select_export, name='select_export'),
    path('quick/export/points/', views.export_points, name='export_points'),
    path('quick/select/faculty/', views.select_faculty, name='select_faculty'),
    path('quick/export/faculty/', views.export_faculty, name='export_faculty'),
    path('quick/select/activities/', views.select_activities, name='select_activities'),
    path('quick/export/activities/', views.export_activities, name='export_activities'),

    # === Database-Backed Reports ===
    path('reports/', views.reports_dashboard, name='reports_dashboard'),
    path('reports/points/', views.db_export_points, name='db_export_points'),
    path('reports/faculty/', views.db_select_faculty, name='db_select_faculty'),
    path('reports/faculty/export/', views.db_export_faculty, name='db_export_faculty'),
    path('reports/activities/', views.db_select_activities, name='db_select_activities'),
    path('reports/activities/export/', views.db_export_activities, name='db_export_activities'),
    path('reports/verify-if/', views.verify_impact_factors, name='verify_impact_factors'),

    # === Activity Browse & Edit ===
    path('activities/', views.activity_category_list, name='activity_categories'),
    # Specific paths must come before generic <str:category> patterns
    path('activities/faculty/<str:email>/', views.faculty_activities, name='faculty_activities'),
    path('activities/add/<str:email>/', views.add_activity, name='add_activity'),
    path('activities/add/<str:email>/<str:category>/<str:subcategory>/', views.add_activity_form, name='add_activity_form'),
    path('activities/edit/<str:email>/<str:category>/<str:subcategory>/<int:index>/', views.edit_activity, name='edit_activity'),
    path('activities/delete/<str:email>/<str:category>/<str:subcategory>/<int:index>/', views.delete_activity, name='delete_activity'),
    # Generic category patterns last
    path('activities/<str:category>/', views.activity_type_list, name='activity_types'),
    path('activities/<str:category>/<str:subcategory>/', views.activity_role_list, name='activity_roles'),
    path('activities/<str:category>/<str:subcategory>/all/', views.activity_entries, name='activity_entries'),
    path('activities/<str:category>/<str:subcategory>/<str:role>/', views.activity_entries_by_role, name='activity_entries_by_role'),

    # === Activity Points Configuration ===
    path('config/points/', views.activity_points_config, name='activity_points_config'),
    path('config/points/create/', views.activity_type_create, name='activity_type_create'),
    path('config/points/<int:pk>/edit/', views.activity_type_edit, name='activity_type_edit'),
    path('config/points/<int:pk>/quick-edit/', views.activity_type_quick_edit, name='activity_type_quick_edit'),

    # === Division Management ===
    path('divisions/', views.divisions_list, name='divisions_list'),
    path('divisions/create/', views.division_create, name='division_create'),
    path('divisions/<str:code>/update-chief/', views.division_update_chief, name='division_update_chief'),
    path('divisions/<str:code>/edit/', views.division_edit, name='division_edit'),
    path('divisions/<str:code>/delete/', views.division_delete, name='division_delete'),
    path('divisions/<str:code>/dashboard/', views.division_dashboard, name='division_dashboard'),
    path('divisions/<str:code>/verify/', views.division_verify, name='division_verify'),

    # === Annual View ===
    path('annual/<str:email>/', views.faculty_annual_view, name='faculty_annual_view'),
    path('annual/<str:email>/review/', views.activity_review_action, name='activity_review_action'),
]
