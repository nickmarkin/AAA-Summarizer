"""
URL configuration for webapp project.
"""
from django.contrib import admin
from django.urls import path, include
from survey_app import views as survey_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('survey/', include('survey_app.urls')),

    # Faculty portal - permanent unique link for each faculty member
    path('my/<str:token>/', survey_views.faculty_portal, name='faculty_portal'),

    path('', include('reports_app.urls')),
]
