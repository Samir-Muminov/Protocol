from django.contrib import admin
from django.urls import path, include

# SECURITY: Custom 429 handler for rate limit responses
handler429 = 'protocol_app.views.handler429'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('protocol_app.urls')),
]