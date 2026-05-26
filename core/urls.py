# core/urls.py
from django.contrib import admin
from django.urls import path, include

# SECURITY: Custom 429 handler
handler429 = 'protocol_app.views.handler429'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('protocol_app.urls')),
]