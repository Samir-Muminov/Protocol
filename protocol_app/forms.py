# protocol_app/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import DailyReport
import datetime


class ProtocolRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model  = User
        fields = ('username', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'protocol-input'})


class DailyReportForm(forms.ModelForm):
    date = forms.DateField(
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'protocol-input',
            'max': str(datetime.date.today()),
        }),
        initial=datetime.date.today,
    )

    class Meta:
        model  = DailyReport
        fields = ('date', 'it_math_hours', 'pages_read', 'calories', 'distance_km')
        widgets = {
            'it_math_hours': forms.NumberInput(attrs={
                'class': 'protocol-input', 'step': '0.5',
                'min': '0', 'max': '24', 'placeholder': '0.0'
            }),
            'pages_read': forms.NumberInput(attrs={
                'class': 'protocol-input', 'min': '0', 'placeholder': '0'
            }),
            'calories': forms.NumberInput(attrs={
                'class': 'protocol-input', 'min': '0', 'placeholder': '0'
            }),
            'distance_km': forms.NumberInput(attrs={
                'class': 'protocol-input', 'step': '0.1',
                'min': '0', 'placeholder': '0.0'
            }),
        }
        labels = {
            'it_math_hours': 'IT / Math (hours)',
            'pages_read':    'Books (pages)',
            'calories':      'Physical (kcal burned)',
            'distance_km':   'Distance (km)',
        }