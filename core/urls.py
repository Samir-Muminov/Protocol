# core/urls.py
from django.contrib import admin
from django.urls import path, include

handler404 = 'protocol_app.views.handler404'
handler500 = 'protocol_app.views.handler500'
handler429 = 'protocol_app.views.handler429'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('protocol_app.urls')),
]