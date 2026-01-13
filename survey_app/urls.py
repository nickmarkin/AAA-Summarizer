"""
URL configuration for survey_app.

Admin routes for campaign management and faculty routes for survey completion.
"""
from django.urls import path
from . import views

app_name = 'survey'

urlpatterns = [
    # ==========================================================================
    # Admin/Staff Views - Campaign Management
    # ==========================================================================
    path('admin/campaigns/', views.campaign_list, name='campaign_list'),
    path('admin/campaigns/create/', views.campaign_create, name='campaign_create'),
    path('admin/campaigns/<int:pk>/', views.campaign_detail, name='campaign_detail'),
    path('admin/campaigns/<int:pk>/edit/', views.campaign_edit, name='campaign_edit'),
    path('admin/campaigns/<int:pk>/send/', views.campaign_send_invitations, name='campaign_send'),
    path('admin/campaigns/<int:pk>/remind/', views.campaign_send_reminders, name='campaign_remind'),
    path('admin/invitations/<int:pk>/unlock/', views.invitation_unlock, name='invitation_unlock'),
    path('admin/campaigns/<int:pk>/export/', views.campaign_export_csv, name='campaign_export'),
    path('admin/invitations/<int:pk>/history/', views.invitation_history, name='invitation_history'),

    # ==========================================================================
    # Faculty Survey Views - Token-based access
    # ==========================================================================
    path('s/<str:token>/', views.survey_landing, name='survey_landing'),
    path('s/<str:token>/category/<str:category>/', views.survey_category, name='survey_category'),
    path('s/<str:token>/review/', views.survey_review, name='survey_review'),
    path('s/<str:token>/submit/', views.survey_submit, name='survey_submit'),
    path('s/<str:token>/confirmation/', views.survey_confirmation, name='survey_confirmation'),

    # ==========================================================================
    # AJAX Endpoints
    # ==========================================================================
    path('api/survey/<str:token>/save/', views.survey_save_draft, name='survey_save_draft'),

    # ==========================================================================
    # Faculty Login Fallback
    # ==========================================================================
    path('faculty/login/', views.faculty_login, name='faculty_login'),
    path('faculty/my-survey/', views.faculty_my_survey, name='faculty_my_survey'),
]
