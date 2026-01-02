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

    # === Faculty Roster Management ===
    path('roster/', views.faculty_roster, name='roster'),
    path('roster/import/', views.import_roster, name='import_roster'),
    path('roster/<str:email>/', views.faculty_detail, name='faculty_detail'),
    path('roster/<str:email>/edit/', views.faculty_edit, name='faculty_edit'),
    path('roster/<str:email>/toggle-ccc/', views.toggle_ccc, name='toggle_ccc'),

    # === Survey Data Import (Database-backed) ===
    path('import/', views.import_survey, name='import_survey'),
    path('import/review/', views.import_review, name='import_review'),
    path('import/confirm/', views.import_confirm, name='import_confirm'),
    path('import/history/', views.import_history, name='import_history'),

    # === Departmental Data Entry ===
    path('departmental/', views.departmental_data, name='departmental_data'),
    path('departmental/<str:year_code>/', views.departmental_data, name='departmental_data_year'),
    path('departmental/update/', views.departmental_update, name='departmental_update'),

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
]
