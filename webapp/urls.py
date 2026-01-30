"""
URL configuration for webapp project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from survey_app import views as survey_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('survey/', include('survey_app.urls')),

    # Faculty portal - permanent unique link for each faculty member
    path('my/<str:token>/', survey_views.faculty_portal, name='faculty_portal'),

    path('', include('reports_app.urls')),
]

# Serve static files in development (or when web server isn't configured for them)
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    # Also serve from the source static directory if collectstatic hasn't been run
    urlpatterns += static(settings.STATIC_URL, document_root=settings.BASE_DIR / 'static')
