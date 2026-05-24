# protocol_app/apps.py
from django.apps import AppConfig


class ProtocolAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'protocol_app'
    verbose_name = 'Protocol OS'