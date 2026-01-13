"""
URL configuration for webapp project.
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('survey/', include('survey_app.urls')),
    path('', include('reports_app.urls')),
]
